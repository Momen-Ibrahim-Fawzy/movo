"""Generate Imaa/Resources/{en,ar}.lproj/Localizable.strings.

Gesture names come from the desktop string tables so all platforms use the same words.
Usage: python mobile/ios/scripts/make_strings.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "mobile" / "ios" / "Imaa" / "Resources"
DESKTOP = {lang: json.loads((ROOT / "desktop" / "imaa" / "i18n" / f"{lang}.json").read_text(encoding="utf-8")) for lang in ("en", "ar")}

GESTURES = [
    "thumb_up", "thumb_down", "point_right", "point_left", "pinch", "index_up_move_up", "index_up_move_down",
    "pinch_drag_up", "pinch_drag_down", "swipe_right", "swipe_left", "victory", "call", "fist", "rock", "three",
    "nod", "shake", "tilt_right", "tilt_left", "look_up", "look_down", "turn_right", "turn_left", "mouth_open", "smile", "brows_up",
]

STRINGS = {
    "app.name": ("Imaa", "إيماءة"),
    "nav.home": ("Home", "الرئيسية"),
    "nav.viewer": ("Viewer", "العارض"),
    "nav.remote": ("Remote", "عن بُعد"),
    "nav.settings": ("Settings", "الإعدادات"),
    "state.stopped": ("Stopped", "متوقف"),
    "state.running": ("Watching", "يعمل"),
    "state.paused": ("Paused", "متوقف مؤقتًا"),
    "state.stopped_d": ("Tap the button to start watching for gestures.", "اضغط الزر لبدء التعرّف على الإيماءات."),
    "state.running_d": (
        "Gestures control the Viewer, or your computer in Remote mode. Make 🤘 to pause.",
        "الإيماءات تتحكم في العارض، أو في حاسوبك في وضع التحكم عن بُعد. أشر بعلامة 🤘 للإيقاف المؤقت.",
    ),
    "state.paused_d": ("Gestures are ignored until you resume.", "سيتم تجاهل الإيماءات حتى تستأنف."),
    "home.seeing": ("Seeing:", "يرى الآن:"),
    "home.idle": ("Resting — nobody in view", "في وضع الراحة — لا أحد أمام الكاميرا"),
    "home.pause": ("Pause", "إيقاف مؤقت"),
    "home.resume": ("Resume", "استئناف"),
    "home.camera_denied": (
        "Imaa needs the camera to see your gestures. The picture never leaves your device.",
        "يحتاج التطبيق إلى الكاميرا لرؤية إيماءاتك. الصورة لا تغادر جهازك أبدًا.",
    ),
    "home.open_settings": ("Open Settings", "فتح الإعدادات"),
    "home.quick": ("Quick switches", "مفاتيح سريعة"),
    "home.hand": ("Hand gestures", "إيماءات اليد"),
    "home.head": ("Head gestures", "إيماءات الرأس"),
    "home.practice": ("Practice mode", "وضع التدريب"),
    "home.practice_d": ("See what Imaa recognises without doing anything", "اعرف ما يتعرّف عليه التطبيق دون تنفيذ أي إجراء"),
    "home.last": ("Last action", "آخر إجراء"),
    "home.nothing": (
        "Nothing yet — open a PDF in the Viewer and point 👉 to turn the page.",
        "لا شيء بعد — افتح ملف PDF في العارض وأشر 👉 لتقليب الصفحة.",
    ),
    "home.privacy": (
        "The camera picture is processed on this device only. Nothing is recorded, saved or sent.",
        "تتم معالجة صورة الكاميرا على هذا الجهاز فقط. لا يُسجَّل أي شيء ولا يُحفظ ولا يُرسل.",
    ),
    "a.start": ("Start", "تشغيل"),
    "a.stop": ("Stop", "إيقاف"),
    "a.none": ("Do nothing", "لا شيء"),
    "a.next": ("Next page", "الصفحة التالية"),
    "a.previous": ("Previous page", "الصفحة السابقة"),
    "a.scroll_up": ("Scroll up", "تمرير للأعلى"),
    "a.scroll_down": ("Scroll down", "تمرير للأسفل"),
    "a.zoom_in": ("Zoom in", "تكبير"),
    "a.zoom_out": ("Zoom out", "تصغير"),
    "a.pause_control": ("Pause / resume", "إيقاف / استئناف"),
    "viewer.empty": (
        "Open a PDF (slides, books, sheet music) or photos, then turn pages with 👉 👈, scroll with ☝️ and zoom with a pinch-and-pull.",
        "افتح ملف PDF (شرائح أو كتب أو نوتات موسيقية) أو صورًا، ثم قلّب الصفحات بـ 👉 👈، ومرّر بـ ☝️، وكبّر بالقرص والسحب.",
    ),
    "viewer.open_pdf": ("Open PDF", "فتح ملف PDF"),
    "viewer.open_photos": ("Open photos", "فتح الصور"),
    "remote.title": ("Remote camera", "كاميرا عن بُعد"),
    "remote.body": (
        "Use this iPhone or iPad as a gesture camera for your computer. Only gesture names are sent over your Wi-Fi — never video.",
        "استخدم هذا الجهاز ككاميرا إيماءات لحاسوبك. تُرسَل أسماء الإيماءات فقط عبر شبكة Wi-Fi — وليس الفيديو أبدًا.",
    ),
    "remote.steps": (
        "On the computer: Imaa → Settings → Integrations → “Use my phone as a remote camera”. Scan the QR code with the Camera app, or type the details below.",
        "على الحاسوب: إيماءة ← الإعدادات ← التكاملات ← «استخدام هاتفي ككاميرا عن بُعد». امسح رمز QR بتطبيق الكاميرا أو أدخل البيانات أدناه.",
    ),
    "remote.paired": ("Pairing details received", "تم استلام بيانات الاقتران"),
    "remote.host": ("Computer address", "عنوان الحاسوب"),
    "remote.port": ("Port", "المنفذ"),
    "remote.code": ("Pairing code", "رمز الاقتران"),
    "remote.use": ("Send gestures to the computer", "إرسال الإيماءات إلى الحاسوب"),
    "remote.status": ("Status", "الحالة"),
    "remote.off": ("Not connected", "غير متصل"),
    "remote.connecting": ("Connecting…", "جارٍ الاتصال…"),
    "remote.connected": ("Connected", "متصل"),
    "remote.failed": ("Couldn't connect — check the address, the code and the Wi-Fi", "تعذّر الاتصال — تحقق من العنوان والرمز وشبكة Wi-Fi"),
    "settings.appearance": ("Appearance", "المظهر"),
    "settings.theme": ("Theme", "السمة"),
    "settings.system": ("System", "النظام"),
    "settings.light": ("Light", "فاتح"),
    "settings.dark": ("Dark", "داكن"),
    "settings.language": ("Language (opens Settings)", "اللغة (تفتح الإعدادات)"),
    "settings.detection": ("Detection", "التعرّف"),
    "settings.power": ("Power mode", "وضع الطاقة"),
    "settings.power_eco": ("Eco", "اقتصادي"),
    "settings.power_balanced": ("Balanced", "متوازن"),
    "settings.power_performance": ("Performance", "أداء عالٍ"),
    "settings.hold": ("Hold time", "مدة الثبات"),
    "settings.head_sens": ("Head sensitivity", "حساسية الرأس"),
    "settings.recalibrate": ("Recalibrate head", "إعادة معايرة الرأس"),
    "settings.gestures": ("Gestures in the Viewer", "الإيماءات في العارض"),
    "settings.privacy": ("Privacy", "الخصوصية"),
    "settings.privacy_text": (
        "Imaa looks at the camera only while it is running, and only on this device. Pictures are analysed in memory and immediately discarded. No accounts, no analytics, no ads.",
        "لا ينظر التطبيق إلى الكاميرا إلا أثناء تشغيله وعلى هذا الجهاز فقط. تُحلَّل الصور في الذاكرة ثم تُحذف فورًا. لا حسابات ولا تحليلات ولا إعلانات.",
    ),
    "settings.about": ("About", "حول التطبيق"),
    "settings.meaning": ("“Imaa” (إيماءة) is Arabic for a gesture or a nod.", "«إيماءة» تعني الإشارة باليد أو الإيماء بالرأس."),
    "settings.version": ("Version", "الإصدار"),
    "help.title": ("How to use Imaa", "طريقة استخدام إيماءة"),
    "help.gestures": ("Gestures", "الإيماءات"),
    "help.s1": ("Start Imaa", "شغّل التطبيق"),
    "help.s1_d": ("Tap the power button on Home and allow the camera.", "اضغط زر التشغيل في الصفحة الرئيسية واسمح بالكاميرا."),
    "help.s2": ("Open something to control", "افتح شيئًا للتحكم فيه"),
    "help.s2_d": ("In Viewer, open a PDF or photos. Turn pages with 👉 👈, scroll with ☝️, zoom with pinch-and-pull.", "في العارض افتح ملف PDF أو صورًا. قلّب الصفحات بـ 👉 👈، ومرّر بـ ☝️، وكبّر بالقرص والسحب."),
    "help.s3": ("Prop up your device", "اسند جهازك"),
    "help.s3_d": ("Stand it so the front camera sees your hand 30–80 cm away, with light in front of you.", "ضعه بحيث ترى الكاميرا الأمامية يدك على بُعد 30–80 سم، مع إضاءة أمامك."),
    "help.s4": ("Control your computer", "تحكّم في حاسوبك"),
    "help.s4_d": ("In Remote, scan the QR code shown by Imaa on your computer, then turn on “Send gestures to the computer”.", "في صفحة عن بُعد امسح رمز QR الظاهر في تطبيق إيماءة على حاسوبك، ثم فعّل «إرسال الإيماءات إلى الحاسوب»."),
    "help.s5": ("Pause any time", "أوقف مؤقتًا في أي وقت"),
    "help.s5_d": ("Make the 🤘 sign or tap Pause on Home.", "أشر بعلامة 🤘 أو اضغط إيقاف مؤقت في الصفحة الرئيسية."),
}


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main() -> None:
    for index, lang in enumerate(("en", "ar")):
        lines = [f"/* Imaa — {lang}. Generated by scripts/make_strings.py */"]
        lines += [f'"{key}" = "{escape(pair[index])}";' for key, pair in STRINGS.items()]
        lines += [f'"g.{g}" = "{escape(DESKTOP[lang]["g." + g])}";' for g in GESTURES]
        target = OUT / f"{lang}.lproj" / "Localizable.strings"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("wrote", target)


if __name__ == "__main__":
    main()
