# Biuret PrayerPal V1.0.1 — 2026-10-21

**[تنزيل مثبّت Windows x64](https://github.com/Biuret7/Biuret-PrayerPal/releases/download/V1.0.1/BiuretPrayerPal-V1.0.1-Setup-Windows-x64.exe)**

تحديث لتحسين الواجهة وسهولة الاستخدام، مع دعم الإنجليزية وخيار التشغيل مع Windows.

## ما أُضيف وما تم إصلاحه

- **اللغة الإنجليزية:** التبديل من زر EN / AR أعلى النافذة، أو الإعدادات ← البرنامج ← اللغة. تشمل الترجمة الإعدادات وقائمة شريط النظام والتنبيهات، مع اتجاه مناسب لكل لغة.
- **التشغيل مع Windows:** خيار اختياري لحسابك الحالي من الإعدادات ← البرنامج. يُطبّق عند الحفظ، ويبدأ في شريط النظام عند توفره. لا يتفعّل تلقائياً عند التحديث.
- **حركة تبديل المظهر:** انتقال متحرك بين الشمس والهلال وبين المظهرين الداكن والفاتح، مع دعم تقليل الحركة والتبديل المتكرر.
- **حدود الأزرار:** معالجة بقاء إطار التركيز بعد النقر بالماوس، مع إبقاء علامة التركيز عند استخدام لوحة المفاتيح.
- **الصلاة الحالية والشروق:** عرض الصلاة الحالية بوضوح، وتسمية الشروق «الشروق اليوم» لتمييزه عن الصلاة الحالية والقادمة.
- **حالة الصوت:** زر إيقاف الصوت يظهر أثناء التشغيل فقط، مع حالة نصية واضحة عند توقفه.
- **صفحات الإعدادات:** إصلاح الزوايا المربعة داخل الحواف المستديرة، وتنظيف حدود حقول الأرقام والوقت، وإصلاح اختفاء قيم بعض الحقول في الإنجليزية.
- **مدة ظهور النافذة:** إضافة زري − و+، مع الكتابة المباشرة ومدى واضح من 4 إلى 30 ثانية. القيمة تُحفظ وتُستخدم في مؤقّت النافذة المخصصة. إشعار Windows الإضافي يخضع لسلوك النظام.

الأذان بصوت **عمر هشام العربي** ما زال مرفقاً داخل البرنامج. لتجربته: الإعدادات ← الصوت ← أذان عمر هشام العربي (مرفق)، ثم ألغِ الكتم واضبط مستوى الصوت واضغط اختبار التذكير. لا تحتاج إلى ملف جديد.

## التحديث والتحقق

اخرج من البرنامج من أيقونة شريط النظام، ثم شغّل المثبّت الجديد. يحتفظ التحديث بتفضيلاتك السابقة. لا تحتاج إلى Python أو صلاحيات مسؤول.

نجح **40 اختباراً للمنطق والحفظ والبناء و31 اختباراً للواجهة والعمليات** على Windows وبنمط offscreen. نجح فحص EXE الفعلي والموارد والأذان وWAV بمخرج مكتوم، وفحص دورة التثبيت والإزالة بهوية اختبار معزولة لحماية التثبيت الشخصي.

المثبّت والبرنامج **غير موقّعين رقمياً**. تجربة جهاز Windows نظيف، وجلسة تسجيل دخول فعلية لخيار بدء التشغيل، وفحوص Narrator وDPI والأجهزة المتعددة ما زالت غير متحققة.

ملفات SHA-256 مرفقة للتحقق من التنزيل. الحزمة الأساسية هي **Setup**؛ لا توجد نسخة Portable ضمن مرفقات هذا الإصدار.

[تفاصيل الفحص](https://github.com/Biuret7/Biuret-PrayerPal/blob/V1.0.1/docs/V1.0.1_REVIEW.md) · [إصلاح مدة النافذة](https://github.com/Biuret7/Biuret-PrayerPal/blob/V1.0.1/docs/DURATION_FIX.md) · [نسبة التسجيل](https://github.com/Biuret7/Biuret-PrayerPal/blob/V1.0.1/assets/sounds/README.md)

## English

**[Download the Windows x64 installer](https://github.com/Biuret7/Biuret-PrayerPal/releases/download/V1.0.1/BiuretPrayerPal-V1.0.1-Setup-Windows-x64.exe)**

- Added English/Arabic switching through EN / AR or Settings → App → Language, including settings, tray menus and reminders.
- Added opt-in, current-user Windows login startup. Changes apply on Save; startup opens in the tray when available.
- Added animated sun/moon and theme transitions, with reduced-motion support.
- Fixed mouse-click focus borders while preserving keyboard focus cues.
- Clarified the current prayer and today's sunrise; Stop Audio now appears during playback.
- Fixed rounded settings corners and numeric/time field rendering, including invisible English numeric values.
- Added explicit −/+ duration controls and keyboard input for 4–30 seconds, with preview, timer and persistence checks.

Bundled Adhan by Omar Hisham Al Arabi remains available without another download. Exit the existing app from its tray icon before installing; preferences are preserved. Python and administrator elevation are not required.

Validation: 40 core/storage/build tests and 31 Qt/process tests passed, plus frozen GUI and muted WAV/MP3 playback checks. Installer lifecycle checks used a separate OS identity to preserve the existing installation. The app and installer are unsigned. Clean-PC, real login-session, Narrator and broader DPI/device coverage remain unverified.
