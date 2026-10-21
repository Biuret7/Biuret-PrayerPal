"""Local Arabic/English presentation; stable prayer, city and preference IDs."""
from __future__ import annotations

ENGLISH = {
    'إعدادات Biuret PrayerPal':
        'Biuret PrayerPal settings',
    'Biuret PrayerPal | مواقيت الصلاة':
        'Biuret PrayerPal | Prayer times',
    'تخصيص تجربتك':
        'Make it yours',
    'المواقيت والتنبيهات • إعداداتك، على جهازك':
        'Prayer times and reminders • Stored on your device',
    'الموقع':
        'Location',
    'الحساب':
        'Calculation',
    'التذكيرات':
        'Reminders',
    'الصوت':
        'Sound',
    'النافذة':
        'Popup',
    'البرنامج':
        'App',
    'حفظ التغييرات':
        'Save changes',
    'إلغاء':
        'Cancel',
    'اختبار التذكير':
        'Test reminder',
    'اختبار التذكير بالإعدادات الحالية قبل الحفظ':
        'Test current settings before saving',
    'المدينة':
        'City',
    'خط العرض':
        'Latitude',
    'خط الطول':
        'Longitude',
    'المنطقة الزمنية':
        'Time zone',
    'مخصص':
        'Custom',
    'رام الله':
        'Ramallah',
    'القدس':
        'Jerusalem',
    'نابلس':
        'Nablus',
    'الخليل':
        'Hebron',
    'غزة':
        'Gaza',
    'جنين':
        'Jenin',
    'بيت لحم':
        'Bethlehem',
    'يُفضّل اختيار التوقيت الذي يطابق المدينة. الحساب فلكي تقريبي.':
        'Choose the time zone for your city. Prayer times are astronomical estimates.',
    'عرض الوقت بنظام 24 ساعة':
        'Use 24-hour time',
    'زاوية الفجر':
        'Fajr angle',
    'زاوية العشاء':
        'Isha angle',
    'وقت العصر':
        'Asr method',
    'الجمهور (ظل 1)':
        'Standard (shadow factor 1)',
    'الحنفي (ظل 2)':
        'Hanafi (shadow factor 2)',
    'تفعيل التنبيهات':
        'Enable reminders',
    'بدون':
        'None',
    'تنبيه مبكر':
        'Early reminder',
    'تذكير أذكار الصباح':
        'Morning Azkar reminder',
    'وقت الصباح':
        'Morning time',
    'تذكير أذكار المساء':
        'Evening Azkar reminder',
    'وقت المساء':
        'Evening time',
    'مدة ظهور النافذة':
        'Popup duration',
    'عرض إشعار Windows أيضاً (اختياري)':
        'Also show a Windows notification (optional)',
    'استعراض...':
        'Browse…',
    'اختر ملف صوت من جهازك':
        'Choose an audio file on your device',
    'اختر ملف صوت':
        'Choose audio',
    'ملفات صوت (*.wav *.mp3 *.ogg *.m4a *.flac);;كل الملفات (*)':
        'Audio files (*.wav *.mp3 *.ogg *.m4a *.flac);;All files (*)',
    'نوع الصوت':
        'Sound type',
    'ملف الأذان':
        'Custom Adhan file',
    'ملف الأذكار':
        'Custom Azkar file',
    'مستوى الصوت':
        'Volume',
    'مستوى صوت التذكير':
        'Reminder volume',
    'صامت (Mute)':
        'Mute',
    (
        'أذان عمر هشام العربي مرفق. اختره من نوع الصوت ثم اضغط اختبار '
        'التذكير. يمكنك أيضاً اختيار ملفات أذان أو أذكار من جهازك.'
    ):
        (
            'Adhan by Omar Hisham Al Arabi is included. Select it and click '
            'Test reminder. You can also choose your own Adhan or Azkar audio.'
    ),
    'اختيار اللون':
        'Choose color',
    'موضع الإشعار':
        'Position',
    'حركة الظهور':
        'Transition',
    'تقليل الحركة والتأثيرات':
        'Reduce motion and effects',
    'شكل الحدود':
        'Border',
    'لون الخلفية':
        'Background color',
    'لون النص':
        'Text color',
    'لون التوهج':
        'Accent color',
    'ألوان مخصصة':
        'Custom colors',
    'زمرد داكن':
        'Dark emerald',
    'سماوي داكن':
        'Dark cyan',
    'ذهبي داكن':
        'Dark gold',
    'لوحة الألوان':
        'Color preset',
    'نوع المعاينة':
        'Preview type',
    'تذكير صلاة':
        'Prayer reminder',
    'تذكير أذكار':
        'Azkar reminder',
    'أعلى اليمين':
        'Top right',
    'أعلى اليسار':
        'Top left',
    'أسفل اليمين':
        'Bottom right',
    'أسفل اليسار':
        'Bottom left',
    'وسط الشاشة':
        'Center',
    'تلاشي':
        'Fade',
    'انزلاق':
        'Slide',
    'تكبير':
        'Zoom',
    'نغمة هادئة':
        'Gentle chime',
    'أذان عمر هشام العربي (مرفق)':
        'Omar Hisham Al Arabi Adhan (included)',
    'ملف أذان':
        'Custom Adhan',
    'ملف صوت أذكار':
        'Custom Azkar',
    'بدون صوت':
        'Silent',
    'هادئ':
        'Soft',
    'متوهج':
        'Glow',
    'واضح':
        'Solid',
    'بلا إطار':
        'None',
    'اللغة':
        'Language',
    'التشغيل مع Windows':
        'Start with Windows',
    'بدء البرنامج تلقائياً عند تسجيل الدخول إلى Windows':
        'Start PrayerPal when I sign in to Windows',
    'خيار اختياري لحسابك الحالي. يبدأ في شريط النظام عند توفره. لا يتغير حتى تضغط حفظ.':
        (
            'Optional, for your account only. Starts in the notification area '
            'when available. Applied only when you save.'
    ),
    'تُطبّق اللغة عند الحفظ، ويمكن تبديلها أيضاً من الزر AR / EN في النافذة الرئيسية.':
        'Language changes when you save. You can also use AR / EN in the main window.',
    'رفيقك لمواقيت الصلاة':
        'Your prayer-time companion',
    'تحديث المواقيت':
        'Refresh times',
    'الوضع الداكن/الفاتح':
        'Dark / light mode',
    'تبديل المظهر الداكن والفاتح':
        'Switch dark / light mode',
    'الصلاة القادمة':
        'Next prayer',
    'جاري الحساب...':
        'Calculating…',
    'مواقيت اليوم':
        "Today's times",
    'إيقاف الصوت':
        'Stop audio',
    'الصوت متوقف':
        'No audio playing',
    'يظهر زر إيقاف الصوت أثناء تشغيل تسجيل فقط.':
        'Stop audio appears while a recording is playing.',
    'إيقاف التسجيل حتى بعد اختفاء الإشعار':
        'Stop the recording, even after the popup closes',
    'الإعدادات':
        'Settings',
    'اختبار تنبيه':
        'Test reminder',
    'إخفاء للخلفية':
        'Hide to tray',
    'حساب محلي • لا يحتاج إنترنت':
        'Calculated locally • Works offline',
    'فتح البرنامج':
        'Open PrayerPal',
    'خروج نهائي':
        'Quit',
    'تعذّر الحساب':
        'Unable to calculate',
    'راجع الإعدادات':
        'Review your settings',
    'خطأ في حساب المواقيت — اضغط تحديث للتفاصيل':
        'Calculation failed — refresh for details',
    'تعذّر حساب المواقيت':
        'Unable to calculate prayer times',
    'تم تحديث المواقيت':
        'Times refreshed',
    'اليوم':
        'Today',
    'غداً':
        'Tomorrow',
    'لا توجد صلاة قادمة':
        'No upcoming prayer',
    'الصلاة الحالية: {prayer}':
        'Current prayer: {prayer}',
    'الشروق اليوم: {time}':
        'Sunrise today: {time}',
    'الشروق معلومة فلكية لليوم، وليس الصلاة الحالية أو القادمة.':
        'Sunrise is a solar time for today, not the current or next prayer.',
    'تعذّر حفظ سجل التنبيهات؛ قد يتكرر آخر تنبيه بعد إعادة التشغيل.':
        'Could not save reminder history; the last alert may repeat after restart.',
    'أذكار الصباح • تجربة':
        'Morning Azkar • Preview',
    'خذ لحظة للذكر والاستغفار. هذا إشعار تجريبي.':
        'Take a moment for remembrance. This is a test reminder.',
    'حان وقت الصلاة • تجربة':
        'Prayer time • Preview',
    'حان وقت صلاة الظهر. هذا إشعار تجريبي.':
        'It is time for Dhuhr. This is a test reminder.',
    'العمل بالخلفية':
        'Background operation',
    'أيقونة شريط النظام غير متاحة حالياً، اترك النافذة مفتوحة للتذكيرات.':
        'The notification area is unavailable. Keep this window open for reminders.',
    'إعداد غير صالح':
        'Invalid setting',
    'تعذّر حفظ الإعدادات':
        'Could not save settings',
    'إغلاق الإشعار':
        'Close notification',
    'إغلاق الإشعار وإيقاف الصوت':
        'Close notification and stop audio',
    'حان وقت الصلاة':
        'Prayer time',
    'اقترب وقت الصلاة':
        'Prayer approaching',
    'حان الآن وقت صلاة {prayer}. تقبّل الله طاعتكم.':
        'It is time for {prayer}. May Allah accept your prayers.',
    'تبقى {minutes} دقائق على صلاة {prayer}.':
        '{prayer} starts in {minutes} minutes.',
    'أذكار الصباح':
        'Morning Azkar',
    'أذكار المساء':
        'Evening Azkar',
    'لحظات من الذكر والاستغفار لبداية يومك.':
        'Begin your day with remembrance and seeking forgiveness.',
    'خصص دقائق لأذكار المساء والطمأنينة.':
        'Take a few peaceful minutes for evening Azkar.',
    'تعذّر تشغيل الصوت. تحقق من الملف وصيغته وجهاز الإخراج.':
        'Could not play audio. Check the file, format and output device.',
    'ملف الصوت غير متاح. اختر ملفاً صالحاً من الإعدادات.':
        'Audio unavailable. Choose a valid file in settings.',
    'أدخل اسم المدينة.':
        'Enter a city name.',
    'تصحيحات الدقائق غير صالحة.':
        'Invalid minute adjustments.',
    'خط العرض يجب أن يكون بين -90 و90.':
        'Latitude must be between -90 and 90.',
    'خط الطول يجب أن يكون بين -180 و180.':
        'Longitude must be between -180 and 180.',
    'زاوية الفجر والعشاء يجب أن تكون بين 10 و22 درجة.':
        'Fajr and Isha angles must be between 10 and 22 degrees.',
    'طريقة العصر غير صحيحة.':
        'Invalid Asr method.',
    'مدة التنبيه المبكر غير مدعومة.':
        'Unsupported early reminder interval.',
    'تصحيح الدقائق يجب أن يكون بين -30 و30.':
        'Minute adjustments must be between -30 and 30.',
    'تعذّر حفظ الإعدادات. تحقق من صلاحية الكتابة.':
        'Could not save preferences. Check write permissions.',
    'اللون يجب أن يكون بصيغة #RRGGBB.':
        'Use a color in #RRGGBB format.',
}

AR_PRAYERS = {'Fajr': 'الفجر', 'Dhuhr': 'الظهر', 'Asr': 'العصر',
              'Maghrib': 'المغرب', 'Isha': 'العشاء'}
ENGLISH.update({arabic: english for english, arabic in AR_PRAYERS.items()})
ENGLISH.update({
    'من 4 إلى 30 ثانية. اكتب المدة أو استخدم − و +.':
        '4 to 30 seconds. Type a duration or use the − and + buttons.',
    'مدة ظهور النافذة بالثواني': 'Popup duration in seconds',
    'تقليل مدة ظهور النافذة': 'Decrease popup duration',
    'زيادة مدة ظهور النافذة': 'Increase popup duration',
    'التطبيق قيد التشغيل بالفعل أو تعذّر قفل مجلد البيانات. تحقق من أيقونة شريط النظام.':
        'PrayerPal is already running or the data folder could not be locked. '
        'Check its notification area icon.',
    'تعذّر فتح مجلد بيانات التطبيق للكتابة.':
        'Could not open the application data folder for writing.',
})


def prayer_name(key, language='ar'):
    return key if language == 'en' else AR_PRAYERS[key]


def tr(source, language='ar', **values):
    if language == 'en':
        translated = ENGLISH.get(source)
        if translated is None and source.startswith('تصحيح '):
            translated = next(('Adjust ' + key for key, value in AR_PRAYERS.items()
                               if source == 'تصحيح ' + value), None)
        if translated is None and source.startswith('قبل ') and source.endswith(' دقائق'):
            translated = source.split()[1] + ' minutes before'
        source = translated if translated is not None else source
    return source.format(**values) if values else source


def error_text(message, language='ar'):
    translated = tr(str(message), language)
    if language == 'en' and any('\u0600' <= char <= '\u06ff' for char in translated):
        return ('Could not apply this setting. Check the values, file access and '
                'Windows permissions.')
    return translated


def display_time(value, twenty_four, language='ar'):
    from .core import time_text
    result = time_text(value, twenty_four)
    return result.replace('ص', 'AM').replace('م', 'PM') if language == 'en' else result


def translate_tree(root, language):
    """Translate visible static text, never editable user content or combo data."""
    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QLabel, QLineEdit,
                                   QAbstractSpinBox, QTabWidget, QWidget)
    root.setLocale(QLocale('en_US' if language == 'en' else 'ar_PS'))
    root.setWindowTitle(tr(root.windowTitle(), language))
    for widget in [root, *root.findChildren(QWidget)]:
        if isinstance(widget, (QLabel, QAbstractButton)):
            widget.setText(tr(widget.text(), language))
        if isinstance(widget, QComboBox):
            original = widget.blockSignals(True)
            editable_text = widget.currentText()
            selected_label = widget.itemText(widget.currentIndex())
            for index in range(widget.count()):
                widget.setItemText(index, tr(widget.itemText(index), language))
            if widget.isEditable() and editable_text != selected_label:
                widget.setEditText(editable_text)
            widget.blockSignals(original)
        if isinstance(widget, QTabWidget):
            for index in range(widget.count()):
                widget.setTabText(index, tr(widget.tabText(index), language))
        if isinstance(widget, QLineEdit):
            widget.setPlaceholderText(tr(widget.placeholderText(), language))
        if isinstance(widget, QAbstractSpinBox) and language == 'en':
            if hasattr(widget, 'suffix'):
                widget.setSuffix({' د': ' min', ' ثانية': ' s'}.get(
                    widget.suffix(), widget.suffix()))
        widget.setToolTip(tr(widget.toolTip(), language))
        widget.setAccessibleName(tr(widget.accessibleName(), language))
