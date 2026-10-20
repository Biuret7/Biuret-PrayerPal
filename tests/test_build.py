"""Build cleanup must preserve unrelated trees and reject linked staging paths."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class BuildSafetyTests(unittest.TestCase):
    @unittest.skipUnless(build.os.name == 'nt', 'Windows byte-range build lock')
    def test_concurrent_build_lock_is_refused_and_released(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'build.lock'
            with build.build_lock(path):
                with self.assertRaises(OSError):
                    with build.build_lock(path):
                        self.fail('The second build acquired an active lock')
            with build.build_lock(path):
                self.assertTrue(path.exists())

    def test_owned_staging_is_removed_and_unowned_content_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            owned = root / 'build'
            owned.mkdir()
            (owned / build.MARKER).write_text(build.OWNER)
            (owned / 'temporary.bin').write_bytes(b'data')
            build.clean(owned, root)
            self.assertFalse(owned.exists())
            unowned = root / 'dist'
            unowned.mkdir()
            payload = unowned / 'keep.exe'
            payload.write_bytes(b'keep me')
            with self.assertRaises(OSError):
                build.clean(unowned, root)
            self.assertEqual(payload.read_bytes(), b'keep me')

    def test_other_directory_and_nested_reparse_point_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sibling = root / 'release'
            sibling.mkdir()
            with self.assertRaises(OSError):
                build.clean(sibling, root)
            staging = root / 'build'
            staging.mkdir()
            (staging / build.MARKER).write_text(build.OWNER)
            nested = staging / 'linked-file'
            nested.write_text('preserve')
            with patch.object(build, 'linked', side_effect=lambda path: path == nested):
                with self.assertRaises(OSError):
                    build.clean(staging, root)
            self.assertTrue(nested.exists())

    def test_parent_traversal_outside_project_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'project'
            root.mkdir()
            outside = root.parent / 'build'
            outside.mkdir()
            with self.assertRaises(OSError):
                build.clean(outside, root)
            self.assertTrue(outside.exists())
