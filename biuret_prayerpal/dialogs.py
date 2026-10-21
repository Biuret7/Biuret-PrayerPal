"""Settings UI with separate compact tabs and live, unsaved reminder preview."""
from __future__ import annotations
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, Signal, QTime, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QSlider, QSpinBox,
    QTabWidget, QTimeEdit, QVBoxLayout, QWidget, QScrollArea, QAbstractSpinBox,
)
from .core import Config, CITIES, PRAYERS, calculate_day
from .preferences import (ReminderPrefs, POSITIONS, ANIMATIONS, SOUND_MODES, BORDERS)
from .theme import style, HoverButton, install_interactions
from .i18n import tr, error_text, translate_tree


class SettingsDialog(QDialog):
    preview_requested = Signal(object, str)

    def __init__(self, conf: Config, prefs: ReminderPrefs, parent=None, commit=None,
                 *, startup_enabled=None):
        super().__init__(parent)
        self.setWindowTitle('إعدادات Biuret PrayerPal')
        self.language = prefs.language
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.language == 'ar'
                                else Qt.LayoutDirection.LeftToRight)
        self.resize(680, 720)
        self.setMinimumSize(540, 430)
        self.setProperty('darkTheme', conf.dark)
        self.setProperty('reducedMotion', prefs.reduced_motion)
        self._commit = commit
        self._closing = False
        self._pending_result = None
        self.result_config = None
        self.result_prefs = None
        self.original = conf
        self.prefs = prefs
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        title = QLabel('تخصيص تجربتك')
        title.setObjectName('brand')
        layout.addWidget(title)
        subtitle = QLabel('المواقيت والتنبيهات • إعداداتك، على جهازك')
        subtitle.setObjectName('caption')
        layout.addWidget(subtitle)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)
        self._build_location(conf)
        self._build_calculation(conf)
        self._build_reminders(prefs)
        self._build_sound(prefs)
        self._build_popup(prefs)
        self._build_general(prefs, startup_enabled)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        save = HoverButton('حفظ التغييرات')
        save.setObjectName('primary')
        save.clicked.connect(self.save)
        cancel = HoverButton('إلغاء')
        cancel.clicked.connect(self.reject)
        footer.addWidget(save)
        footer.addWidget(cancel)
        footer.addStretch(1)
        self.test_button = HoverButton('اختبار التذكير')
        self.test_button.setAccessibleName('اختبار التذكير بالإعدادات الحالية قبل الحفظ')
        self.test_button.clicked.connect(self.preview)
        footer.addWidget(self.test_button)
        layout.addLayout(footer)
        self.setStyleSheet(style(conf.dark))
        translate_tree(self, self.language)
        for control in self.findChildren(QAbstractSpinBox):
            # Qt 6.12's QSS/NoButtons path gives LTR editors a one-pixel width.
            # Keep the native symbols mode; QSS gives both arrow controls zero
            # width instead. Keyboard/wheel stepping and the full editor survive.
            control.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
            control.lineEdit().setTextMargins(6, 0, 6, 0)
        self._fade = QPropertyAnimation(self, b'windowOpacity', self)
        self._fade.setDuration(230)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._animation_finished)
        self.setWindowOpacity(0.0 if not prefs.reduced_motion else 1.0)
        install_interactions(self)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.property('reducedMotion'):
            self._fade.start()

    def done(self, result):
        if self._closing:
            return
        self._closing = True
        if self.property('reducedMotion') or not self.isVisible():
            super().done(result)
            return
        self._pending_result = result
        self._fade.stop()
        self._fade.setDuration(150)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _animation_finished(self):
        if self._pending_result is not None:
            super().done(self._pending_result)

    def closeEvent(self, event):
        event.ignore()
        self.reject()

    def _tab(self, name):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(tab)
        # setWidget enables autoFillBackground; reset it so rectangular pages
        # cannot paint over the rounded pane, including its four corners.
        tab.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setAutoFillBackground(False)
        self.tabs.addTab(scroll, name)
        form = QFormLayout(tab)
        form.setContentsMargins(18, 17, 18, 12)
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _build_location(self, conf):
        form = self._tab('الموقع')
        self.city = QComboBox()
        self.city.setEditable(True)
        for city in [*CITIES, 'مخصص']:
            self.city.addItem(city, city)
        self.city.setCurrentText(conf.city)
        self.lat = QDoubleSpinBox()
        self.lat.setRange(-90, 90)
        self.lat.setDecimals(5)
        self.lat.setValue(conf.lat)
        self.lon = QDoubleSpinBox()
        self.lon.setRange(-180, 180)
        self.lon.setDecimals(5)
        self.lon.setValue(conf.lon)
        self.tz = QComboBox()
        self.tz.setEditable(True)
        self.tz.addItems(['Asia/Hebron', 'Asia/Jerusalem', 'Asia/Amman',
                          'Asia/Riyadh', 'Europe/Istanbul', 'UTC'])
        self.tz.setCurrentText(conf.tz_name)
        for label, field in [('المدينة', self.city), ('خط العرض', self.lat),
                             ('خط الطول', self.lon), ('المنطقة الزمنية', self.tz)]:
            form.addRow(label, field)
        note = QLabel('يُفضّل اختيار التوقيت الذي يطابق المدينة. الحساب فلكي تقريبي.')
        note.setObjectName('hint')
        note.setWordWrap(True)
        form.addRow(note)
        self.time_24 = QCheckBox('عرض الوقت بنظام 24 ساعة')
        self.time_24.setChecked(conf.time_24)
        form.addRow(self.time_24)
        self.city.currentTextChanged.connect(self._city_changed)
        self.lat.valueChanged.connect(self._coordinate_changed)
        self.lon.valueChanged.connect(self._coordinate_changed)

    def _city_value(self):
        index = self.city.currentIndex()
        if index >= 0 and self.city.currentText() == self.city.itemText(index):
            return self.city.itemData(index)
        return self.city.currentText()

    def _city_changed(self, _text):
        city = self._city_value()
        if city in CITIES:
            lat, lon = CITIES[city]
            for field, value in ((self.lat, lat), (self.lon, lon)):
                field.blockSignals(True)
                field.setValue(value)
                field.blockSignals(False)

    def _coordinate_changed(self, _value):
        if self._city_value() in CITIES:
            self.city.blockSignals(True)
            self.city.setCurrentIndex(self.city.findData('مخصص'))
            self.city.blockSignals(False)

    def _build_calculation(self, conf):
        form = self._tab('الحساب')
        self.fajr = QDoubleSpinBox()
        self.fajr.setRange(10, 22)
        self.fajr.setDecimals(1)
        self.fajr.setSuffix('°')
        self.fajr.setValue(conf.fajr_angle)
        self.isha = QDoubleSpinBox()
        self.isha.setRange(10, 22)
        self.isha.setDecimals(1)
        self.isha.setSuffix('°')
        self.isha.setValue(conf.isha_angle)
        self.asr = QComboBox()
        self.asr.addItem('الجمهور (ظل 1)', 1)
        self.asr.addItem('الحنفي (ظل 2)', 2)
        self.asr.setCurrentIndex(0 if conf.asr_shadow == 1 else 1)
        for name, control in [('زاوية الفجر', self.fajr), ('زاوية العشاء', self.isha),
                              ('وقت العصر', self.asr)]:
            form.addRow(name, control)
        self.offsets = {}
        for key, arabic in PRAYERS:
            control = QSpinBox()
            control.setRange(-30, 30)
            control.setSuffix(' د')
            control.setValue(conf.offsets.get(key, 0))
            form.addRow(f'تصحيح {arabic}', control)
            self.offsets[key] = control

    def _build_reminders(self, prefs):
        form = self._tab('التذكيرات')
        self.alerts = QCheckBox('تفعيل التنبيهات')
        self.alerts.setChecked(prefs.enabled)
        form.addRow(self.alerts)
        self.early = QComboBox()
        for minutes in (0, 5, 10, 15, 30):
            self.early.addItem('بدون' if not minutes else f'قبل {minutes} دقائق', minutes)
        self.early.setCurrentIndex((0, 5, 10, 15, 30).index(prefs.early_minutes))
        form.addRow('تنبيه مبكر', self.early)
        self.morning_azkar = QCheckBox('تذكير أذكار الصباح')
        self.morning_azkar.setChecked(prefs.morning_azkar)
        form.addRow(self.morning_azkar)
        self.morning_time = QTimeEdit(QTime.fromString(prefs.morning_time, 'HH:mm'))
        self.morning_time.setDisplayFormat('HH:mm')
        form.addRow('وقت الصباح', self.morning_time)
        self.evening_azkar = QCheckBox('تذكير أذكار المساء')
        self.evening_azkar.setChecked(prefs.evening_azkar)
        form.addRow(self.evening_azkar)
        self.evening_time = QTimeEdit(QTime.fromString(prefs.evening_time, 'HH:mm'))
        self.evening_time.setDisplayFormat('HH:mm')
        form.addRow('وقت المساء', self.evening_time)
        self.duration = QSpinBox()
        self.duration.setRange(4, 30)
        self.duration.setSuffix(' ثانية')
        self.duration.setValue(prefs.duration_seconds)
        self.duration.setToolTip('من 4 إلى 30 ثانية. اكتب المدة أو استخدم − و +.')
        self.duration.setAccessibleName('مدة ظهور النافذة بالثواني')
        duration_row = QHBoxLayout()
        duration_row.setSpacing(6)
        duration_row.addWidget(self.duration, 1)
        self.duration_decrease = HoverButton('−')
        self.duration_increase = HoverButton('+')
        for button, title, action in (
            (self.duration_decrease, 'تقليل مدة ظهور النافذة', self.duration.stepDown),
            (self.duration_increase, 'زيادة مدة ظهور النافذة', self.duration.stepUp),
        ):
            button.setFixedSize(40, 40)
            button.setAccessibleName(title)
            button.setToolTip(title)
            button.clicked.connect(action)
            duration_row.addWidget(button)

        def update_duration_steps(value):
            self.duration_decrease.setEnabled(value > self.duration.minimum())
            self.duration_increase.setEnabled(value < self.duration.maximum())

        self.duration.valueChanged.connect(update_duration_steps)
        update_duration_steps(self.duration.value())
        form.addRow('مدة ظهور النافذة', duration_row)
        self.native_fallback = QCheckBox('عرض إشعار Windows أيضاً (اختياري)')
        self.native_fallback.setChecked(prefs.native_fallback)
        form.addRow(self.native_fallback)

    def _file_selector(self, form, title, value):
        row = QHBoxLayout()
        field = QLineEdit(value)
        field.setPlaceholderText('اختر ملف صوت من جهازك')
        field.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        choose = HoverButton('استعراض...')
        choose.clicked.connect(lambda: self._browse_audio(field))
        row.addWidget(field, 1)
        row.addWidget(choose)
        form.addRow(title, row)
        return field

    def _browse_audio(self, field):
        selected, _ = QFileDialog.getOpenFileName(
            self, tr('اختر ملف صوت', self.language), '',
            tr('ملفات صوت (*.wav *.mp3 *.ogg *.m4a *.flac);;كل الملفات (*)', self.language))
        if selected:
            field.setText(selected)

    def _build_sound(self, prefs):
        form = self._tab('الصوت')
        self.sound = QComboBox()
        for key, label in SOUND_MODES.items():
            self.sound.addItem(label, key)
        self.sound.setCurrentIndex(list(SOUND_MODES).index(prefs.sound_mode))
        form.addRow('نوع الصوت', self.sound)
        self.adhan_file = self._file_selector(form, 'ملف الأذان', prefs.adhan_file)
        self.azkar_file = self._file_selector(form, 'ملف الأذكار', prefs.azkar_file)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setAccessibleName('مستوى صوت التذكير')
        self.volume.setValue(prefs.volume)
        self.volume_label = QLabel(f'{prefs.volume}%')
        row = QHBoxLayout()
        row.addWidget(self.volume, 1)
        row.addWidget(self.volume_label)
        self.volume.valueChanged.connect(lambda value: self.volume_label.setText(f'{value}%'))
        form.addRow('مستوى الصوت', row)
        self.muted = QCheckBox('صامت (Mute)')
        self.muted.setChecked(prefs.muted)
        form.addRow(self.muted)
        self.muted.toggled.connect(lambda muted: self.volume.setEnabled(not muted))
        self.volume.setEnabled(not prefs.muted)
        description = QLabel(
            'أذان عمر هشام العربي مرفق. اختره من نوع الصوت ثم اضغط اختبار التذكير. '
            'يمكنك أيضاً اختيار ملفات أذان أو أذكار من جهازك.')
        description.setObjectName('hint')
        description.setWordWrap(True)
        form.addRow(description)

    def _color(self, form, title, current):
        row = QHBoxLayout()
        edit = QLineEdit(current)
        edit.setMaxLength(7)
        edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        edit.setFixedWidth(112)
        choose = HoverButton('اختيار اللون')

        def pick():
            color = QColorDialog.getColor(QColor(edit.text()), self, tr(title, self.language))
            if color.isValid():
                edit.setText(color.name().upper())
        choose.clicked.connect(pick)
        row.addWidget(edit)
        row.addWidget(choose)
        row.addStretch()
        form.addRow(title, row)
        return edit

    def _build_popup(self, prefs):
        form = self._tab('النافذة')
        self.position = QComboBox()
        for key, value in POSITIONS.items():
            self.position.addItem(value, key)
        self.position.setCurrentIndex(list(POSITIONS).index(prefs.position))
        form.addRow('موضع الإشعار', self.position)
        self.animation = QComboBox()
        for key, value in ANIMATIONS.items():
            self.animation.addItem(value, key)
        self.animation.setCurrentIndex(list(ANIMATIONS).index(prefs.animation))
        form.addRow('حركة الظهور', self.animation)
        self.reduced_motion = QCheckBox('تقليل الحركة والتأثيرات')
        self.reduced_motion.setChecked(prefs.reduced_motion)
        self.reduced_motion.toggled.connect(
            lambda checked: self.setProperty(
                'reducedMotion', checked))
        form.addRow(self.reduced_motion)
        self.border = QComboBox()
        for key, value in BORDERS.items():
            self.border.addItem(value, key)
        self.border.setCurrentIndex(list(BORDERS).index(prefs.border))
        form.addRow('شكل الحدود', self.border)
        self.background = self._color(form, 'لون الخلفية', prefs.background)
        self.foreground = self._color(form, 'لون النص', prefs.foreground)
        self.accent = self._color(form, 'لون التوهج', prefs.accent)
        preset = QComboBox()
        preset.addItems(['ألوان مخصصة', 'زمرد داكن', 'سماوي داكن', 'ذهبي داكن'])
        preset.currentIndexChanged.connect(self._apply_popup_palette)
        form.addRow('لوحة الألوان', preset)
        preview_row = QHBoxLayout()
        self.preview_kind = QComboBox()
        self.preview_kind.addItem('تذكير صلاة', 'prayer')
        self.preview_kind.addItem('تذكير أذكار', 'azkar')
        preview_row.addWidget(self.preview_kind)
        form.addRow('نوع المعاينة', preview_row)

    def _apply_popup_palette(self, index):
        if index:
            background, foreground, accent = (
                ('#12252D', '#EFFBF7', '#6BE3BE'),
                ('#101F30', '#F0F8FF', '#78D9EE'),
                ('#25231D', '#FFF8E8', '#E9C881'),
            )[index - 1]
            self.background.setText(background)
            self.foreground.setText(foreground)
            self.accent.setText(accent)

    def _build_general(self, prefs, startup_enabled):
        form = self._tab('البرنامج')
        self.interface_language = QComboBox()
        self.interface_language.addItem('العربية', 'ar')
        self.interface_language.addItem('English', 'en')
        self.interface_language.setCurrentIndex(0 if prefs.language == 'ar' else 1)
        form.addRow('اللغة', self.interface_language)
        hint = QLabel(
            'تُطبّق اللغة عند الحفظ، ويمكن تبديلها أيضاً من الزر AR / EN في النافذة الرئيسية.')
        hint.setWordWrap(True)
        hint.setObjectName('hint')
        form.addRow(hint)
        self.start_on_login = QCheckBox('بدء البرنامج تلقائياً عند تسجيل الدخول إلى Windows')
        self.start_on_login.setChecked(prefs.start_on_login if startup_enabled is None
                                       else startup_enabled)
        form.addRow(self.start_on_login)
        hint = QLabel('خيار اختياري لحسابك الحالي. يبدأ في شريط النظام عند توفره. '
                      'لا يتغير حتى تضغط حفظ.')
        hint.setWordWrap(True)
        hint.setObjectName('hint')
        form.addRow(hint)

    def _collect_prefs(self):
        prefs = ReminderPrefs(
            enabled=self.alerts.isChecked(), early_minutes=self.early.currentData(),
            morning_azkar=self.morning_azkar.isChecked(),
            evening_azkar=self.evening_azkar.isChecked(),
            morning_time=self.morning_time.time().toString('HH:mm'),
            evening_time=self.evening_time.time().toString('HH:mm'),
            position=self.position.currentData(), animation=self.animation.currentData(),
            duration_seconds=self.duration.value(), sound_mode=self.sound.currentData(),
            adhan_file=self.adhan_file.text().strip(), azkar_file=self.azkar_file.text().strip(),
            volume=self.volume.value(), muted=self.muted.isChecked(),
            background=self.background.text().strip(),
            foreground=self.foreground.text().strip(), accent=self.accent.text().strip(),
            border=self.border.currentData(), native_fallback=self.native_fallback.isChecked(),
            reduced_motion=self.reduced_motion.isChecked(),
            language=self.interface_language.currentData(),
            start_on_login=self.start_on_login.isChecked(),
        )
        prefs.validate()
        return prefs

    def _collect_config(self):
        conf = Config(
            city=self._city_value(), lat=self.lat.value(), lon=self.lon.value(),
            tz_name=self.tz.currentText().strip(), fajr_angle=self.fajr.value(),
            isha_angle=self.isha.value(), asr_shadow=self.asr.currentData(),
            offsets={name: field.value() for name, field in self.offsets.items()},
            alerts=self.alerts.isChecked(), early_minutes=self.early.currentData(),
            dark=self.original.dark, time_24=self.time_24.isChecked(),
        )
        conf.validate()
        return conf

    def preview(self):
        try:
            prefs = self._collect_prefs()
        except ValueError as error:
            QMessageBox.warning(self, tr('إعداد غير صالح', self.language),
                                error_text(error, self.language))
            return
        self.preview_requested.emit(prefs, self.preview_kind.currentData())

    def save(self):
        if self._closing:
            return
        try:
            conf = self._collect_config()
            prefs = self._collect_prefs()
            today = datetime.now(conf.zone).date()
            for shift in (-1, 0, 1):
                calculate_day(today + timedelta(days=shift), conf)
            if self._commit is not None:
                self._commit(conf, prefs)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, tr('تعذّر حفظ الإعدادات', self.language),
                                error_text(error, self.language))
            return
        self.result_config = conf
        self.result_prefs = prefs
        self.accept()
