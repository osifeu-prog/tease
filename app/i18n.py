from __future__ import annotations

from typing import Dict
from app.core.config import settings

# מילון טקסטים לפי שפה ומפתח
TEXTS: Dict[str, Dict[str, str]] = {
    # ==================== ENGLISH ====================
    "en": {
        # --- Language menu ---
        "LANGUAGE_MENU_TITLE": "Choose your preferred language:",
        "LANGUAGE_BUTTON_EN": "English 🇬🇧",
        "LANGUAGE_BUTTON_HE": "עברית 🇮🇱",
        "LANGUAGE_BUTTON_RU": "Русский 🇷🇺",
        "LANGUAGE_BUTTON_ES": "Español 🇪🇸",
        "LANGUAGE_BUTTON_AR": "العربية 🇦🇪",
        "LANGUAGE_SET_CONFIRM": "Your preferred language is now set to English.",
        "LANGUAGE_SET_CONFIRM_HE": "Your preferred language is now set to Hebrew.",
        "LANGUAGE_SET_CONFIRM_RU": "Your preferred language is now set to Russian.",
        "LANGUAGE_SET_CONFIRM_ES": "Your preferred language is now set to Spanish.",
        "LANGUAGE_SET_CONFIRM_AR": "Your preferred language is now set to Arabic.",

        # --- /start texts ---
        "START_TITLE": "Welcome to the SLH Investor Gateway.",
        "START_MIN_INVEST_LINE": (
            "This bot is intended for strategic investors (minimum {min_invest} ILS)."
        ),
        "START_FEATURES_INTRO": "With this bot you can:",
        "START_FEATURE_1": "- Link your personal BNB wallet (BSC)",
        "START_FEATURE_2": "- View your off-chain SLH balance",
        "START_FEATURE_3": "- Transfer SLH units to other investors (off-chain)",
        "START_FEATURE_4": "- Access external links for BNB purchase and staking info",
        "START_NEXT_STEPS_TITLE": "Next steps:",
        "START_STEP_1_NO_WALLET": (
            "1) Use /link_wallet to connect your BNB (BSC) address."
        ),
        "START_STEP_1_HAS_WALLET": (
            "1) BNB wallet linked: {address}"
        ),
        "START_STEP_2_NO_BALANCE": (
            "2) Once your existing investment is recorded, you will see your SLH balance via /balance."
        ),
        "START_STEP_2_HAS_BALANCE": (
            "2) Current SLH balance: {balance} (see /balance)."
        ),
        "START_STEP_3": (
            "3) Use /wallet to view full wallet details and ecosystem links."
        ),
        "START_STEP_4": (
            "4) Use /whoami to see your ID, username and wallet status."
        ),
        "START_STEP_5": (
            "5) Use /summary for a full investor dashboard."
        ),
        "START_STEP_6": (
            "6) Use /history to review your latest transactions."
        ),
        "START_MENU_HINT": (
            "You can also open /menu for a button-based experience."
        ),
        "START_LANGUAGE_HINT": (
            "You can change the interface language via /language."
        ),

        # --- /help texts ---
        "HELP_TEXT": (
            "SLH Wallet Bot – Help\n\n"
            "/start – Intro and onboarding\n"
            "/menu – Main menu with buttons\n"
            "/summary – Full investor dashboard (wallet + balance + profile)\n"
            "/wallet – Wallet details and ecosystem links\n"
            "/link_wallet – Link your personal BNB (BSC) address\n"
            "/balance – View your SLH off-chain balance (+ On-Chain if available)\n"
            "/history – Last transactions in the internal ledger\n"
            "/transfer – Internal off-chain transfer to another user\n"
            "/send_slh – Quick transfer: /send_slh <amount> <@user|id>\n"
            "/whoami – See your Telegram ID, username and wallet status\n"
            "/docs – Open the official SLH investor docs\n"
            "/language – Choose your preferred interface language\n\n"
            "Admin only:\n"
            "/admin_menu – Admin tools overview\n"
            "/admin_credit – Credit SLH to a user\n"
            "/admin_list_users – List users with balances\n"
            "/admin_ledger – Global ledger view (last 50 txs)\n"
            "/admin_selftest – Run deep self-test (DB/ENV/BSC/Telegram)\n\n"
            "At this stage there is no redemption of principal – "
            "only usage of SLH units inside the ecosystem.\n"
            "BNB and gas remain in your own wallet via external providers."
        ),
    },

    # ==================== HEBREW ====================
    "he": {
        "LANGUAGE_MENU_TITLE": "בחר שפה מועדפת לבוט:",
        "LANGUAGE_BUTTON_EN": "English 🇬🇧",
        "LANGUAGE_BUTTON_HE": "עברית 🇮🇱",
        "LANGUAGE_BUTTON_RU": "Русский 🇷🇺",
        "LANGUAGE_BUTTON_ES": "Español 🇪🇸",
        "LANGUAGE_BUTTON_AR": "العربية 🇦🇪",
        "LANGUAGE_SET_CONFIRM": "השפה המועדפת שלך עודכנה לעברית.",
        "LANGUAGE_SET_CONFIRM_HE": "השפה המועדפת שלך עודכנה לעברית.",
        "LANGUAGE_SET_CONFIRM_RU": "השפה המועדפת שלך עודכנה לרוסית.",
        "LANGUAGE_SET_CONFIRM_ES": "השפה המועדפת שלך עודכנה לספרדית.",
        "LANGUAGE_SET_CONFIRM_AR": "השפה המועדפת שלך עודכנה לערבית.",

        "START_TITLE": "ברוך הבא לשער ההשקעות של SLH.",
        "START_MIN_INVEST_LINE": (
            "הבוט מיועד למשקיעים אסטרטגיים (מינימום השקעה של {min_invest} ₪)."
        ),
        "START_FEATURES_INTRO": "בעזרת הבוט תוכל:",
        "START_FEATURE_1": "- לקשר את ארנק ה־BNB האישי שלך (BSC)",
        "START_FEATURE_2": "- לצפות ביתרת ה־SLH שלך במערכת (off-chain)",
        "START_FEATURE_3": "- להעביר יחידות SLH למשקיעים אחרים במערכת (off-chain)",
        "START_FEATURE_4": "- לקבל קישורים חיצוניים לרכישת BNB ולמידע על סטייקינג",
        "START_NEXT_STEPS_TITLE": "הצעדים הבאים:",
        "START_STEP_1_NO_WALLET": (
            "1) הפעל /link_wallet כדי לקשר את כתובת ה־BNB (רשת BSC) שלך."
        ),
        "START_STEP_1_HAS_WALLET": (
            "1) ארנק BNB מקושר: {address}"
        ),
        "START_STEP_2_NO_BALANCE": (
            "2) לאחר שיוקלטו ההשקעות שלך במערכת, תוכל לראות את יתרת ה־SLH בעזרת /balance."
        ),
        "START_STEP_2_HAS_BALANCE": (
            "2) יתרת SLH נוכחית: {balance} (ראה /balance)."
        ),
        "START_STEP_3": (
            "3) השתמש ב־/wallet כדי לראות פרטי ארנק וקישורים רלוונטיים באקו־סיסטם."
        ),
        "START_STEP_4": (
            "4) השתמש ב־/whoami כדי לראות את ה־ID שלך, שם המשתמש והסטטוס של הארנק."
        ),
        "START_STEP_5": (
            "5) השתמש ב־/summary כדי לראות דשבורד משקיע מלא."
        ),
        "START_STEP_6": (
            "6) השתמש ב־/history כדי לצפות בהיסטוריית הטרנזקציות שלך במערכת."
        ),
        "START_MENU_HINT": (
            "אפשר גם לפתוח /menu לחוויית שימוש עם כפתורים."
        ),
        "START_LANGUAGE_HINT": (
            "אפשר לשנות את שפת הממשק בעזרת /language."
        ),

        "HELP_TEXT": (
            "SLH Wallet Bot – עזרה\n\n"
            "/start – מסך פתיחה והצטרפות למערכת\n"
            "/menu – תפריט ראשי עם כפתורים\n"
            "/summary – דשבורד משקיע מלא (ארנק + יתרה + פרופיל)\n"
            "/wallet – פרטי ארנק וקישורים באקו־סיסטם\n"
            "/link_wallet – קישור ארנק BNB אישי (רשת BSC)\n"
            "/balance – צפייה ביתרת ה־SLH במערכת (off-chain) + נתוני on-chain אם זמינים\n"
            "/history – 10 הטרנזקציות האחרונות שבהן אתה מעורב\n"
            "/transfer – העברת SLH פנימית למשתמש אחר במערכת\n"
            "/send_slh – קיצור להעברה: /send_slh <amount> <@user|id>\n"
            "/whoami – הצגת ה־Telegram ID, שם משתמש וסטטוס הארנק שלך\n"
            "/docs – פתיחת מסמכי ההשקעה הרשמיים של SLH\n"
            "/language – בחירת שפת הממשק המועדפת\n\n"
            "פקודות אדמין בלבד:\n"
            "/admin_menu – תפריט כלים לאדמין\n"
            "/admin_credit – טעינת SLH למשתמש\n"
            "/admin_list_users – רשימת משתמשים ויתרות\n"
            "/admin_ledger – תצוגת Ledger גלובלית (50 טרנזקציות אחרונות)\n"
            "/admin_selftest – בדיקת Self-Test מלאה (DB / ENV / BSC / Telegram)\n\n"
            "בשלב זה אין פדיון של הקרן – השימוש ביחידות SLH הוא בתוך האקו־סיסטם בלבד.\n"
            "ה־BNB והגז נשארים בארנק הפרטי שלך מול ספקים חיצוניים."
        ),
    },

    # ==================== RUSSIAN ====================
    "ru": {
        "LANGUAGE_MENU_TITLE": "Выберите предпочитаемый язык:",
        "LANGUAGE_BUTTON_EN": "English 🇬🇧",
        "LANGUAGE_BUTTON_HE": "עברית 🇮🇱",
        "LANGUAGE_BUTTON_RU": "Русский 🇷🇺",
        "LANGUAGE_BUTTON_ES": "Español 🇪🇸",
        "LANGUAGE_BUTTON_AR": "العربية 🇦🇪",
        "LANGUAGE_SET_CONFIRM": "Ваш предпочтительный язык установлен на русский.",
        "LANGUAGE_SET_CONFIRM_HE": "Ваш предпочтительный язык установлен на иврит.",
        "LANGUAGE_SET_CONFIRM_RU": "Ваш предпочтительный язык установлен на русский.",
        "LANGUAGE_SET_CONFIRM_ES": "Ваш предпочтительный язык установлен на испанский.",
        "LANGUAGE_SET_CONFIRM_AR": "Ваш предпочтительный язык установлен на арабский.",

        "START_TITLE": "Добро пожаловать в SLH Investor Gateway.",
        "START_MIN_INVEST_LINE": (
            "Этот бот предназначен для стратегических инвесторов (минимум {min_invest} ILS)."
        ),
        "START_FEATURES_INTRO": "С помощью этого бота вы можете:",
        "START_FEATURE_1": "- Привязать свой личный кошелёк BNB (BSC)",
        "START_FEATURE_2": "- Просматривать свой off-chain баланс SLH",
        "START_FEATURE_3": "- Переводить SLH другим инвесторам внутри системы (off-chain)",
        "START_FEATURE_4": "- Получать внешние ссылки для покупки BNB и информации по стейкингу",
        "START_NEXT_STEPS_TITLE": "Следующие шаги:",
        "START_STEP_1_NO_WALLET": (
            "1) Используйте /link_wallet, чтобы привязать свой BNB-адрес (сеть BSC)."
        ),
        "START_STEP_1_HAS_WALLET": (
            "1) BNB-кошелёк привязан: {address}"
        ),
        "START_STEP_2_NO_BALANCE": (
            "2) Как только ваши инвестиции будут внесены в систему, "
            "вы увидите баланс SLH через /balance."
        ),
        "START_STEP_2_HAS_BALANCE": (
            "2) Текущий баланс SLH: {balance} (см. /balance)."
        ),
        "START_STEP_3": (
            "3) Используйте /wallet, чтобы увидеть детали кошелька и ссылки экосистемы."
        ),
        "START_STEP_4": (
            "4) Используйте /whoami, чтобы увидеть свой ID, username и статус кошелька."
        ),
        "START_STEP_5": (
            "5) Используйте /summary для полного дашборда инвестора."
        ),
        "START_STEP_6": (
            "6) Используйте /history, чтобы просмотреть последние транзакции."
        ),
        "START_MENU_HINT": (
            "Вы также можете открыть /menu для интерфейса с кнопками."
        ),
        "START_LANGUAGE_HINT": (
            "Вы можете поменять язык интерфейса через /language."
        ),

        "HELP_TEXT": (
            "SLH Wallet Bot – помощь\n\n"
            "/start – вводный экран и онбординг\n"
            "/menu – главное меню с кнопками\n"
            "/summary – полный дашборд инвестора (кошелёк + баланс + профиль)\n"
            "/wallet – детали кошелька и ссылки экосистемы\n"
            "/link_wallet – привязать личный BNB-адрес (сеть BSC)\n"
            "/balance – off-chain баланс SLH + on-chain данные (если доступны)\n"
            "/history – последние 10 транзакций, где вы участвуете\n"
            "/transfer – внутренний перевод SLH другому пользователю\n"
            "/send_slh – быстрый перевод: /send_slh <amount> <@user|id>\n"
            "/whoami – ваш Telegram ID, username и статус кошелька\n"
            "/docs – открыть официальную документацию для инвесторов\n"
            "/language – выбор языка интерфейса\n\n"
            "Команды только для администратора:\n"
            "/admin_menu – обзор админ-инструментов\n"
            "/admin_credit – начисление SLH пользователю\n"
            "/admin_list_users – список пользователей и балансов\n"
            "/admin_ledger – глобальный Ledger (последние 50 транзакций)\n"
            "/admin_selftest – глубокий self-test (DB / ENV / BSC / Telegram)\n\n"
            "На данном этапе нет выкупа основного капитала – "
            "SLH используется только внутри экосистемы.\n"
            "BNB и газ остаются в вашем личном кошельке у внешних провайдеров."
        ),
    },

    # ==================== SPANISH ====================
    "es": {
        "LANGUAGE_MENU_TITLE": "Elige tu idioma preferido:",
        "LANGUAGE_BUTTON_EN": "English 🇬🇧",
        "LANGUAGE_BUTTON_HE": "עברית 🇮🇱",
        "LANGUAGE_BUTTON_RU": "Русский 🇷🇺",
        "LANGUAGE_BUTTON_ES": "Español 🇪🇸",
        "LANGUAGE_BUTTON_AR": "العربية 🇦🇪",
        "LANGUAGE_SET_CONFIRM": "Tu idioma preferido ahora es español.",
        "LANGUAGE_SET_CONFIRM_HE": "Tu idioma preferido ahora es hebreo.",
        "LANGUAGE_SET_CONFIRM_RU": "Tu idioma preferido ahora es ruso.",
        "LANGUAGE_SET_CONFIRM_ES": "Tu idioma preferido ahora es español.",
        "LANGUAGE_SET_CONFIRM_AR": "Tu idioma preferido ahora es árabe.",

        "START_TITLE": "Bienvenido al SLH Investor Gateway.",
        "START_MIN_INVEST_LINE": (
            "Este bot está destinado a inversores estratégicos (inversión mínima de {min_invest} ILS)."
        ),
        "START_FEATURES_INTRO": "Con este bot puedes:",
        "START_FEATURE_1": "- Vincular tu monedero personal BNB (BSC)",
        "START_FEATURE_2": "- Ver tu saldo SLH off-chain en el sistema",
        "START_FEATURE_3": "- Transferir unidades SLH a otros inversores (off-chain)",
        "START_FEATURE_4": "- Acceder a enlaces externos para compra de BNB e información de staking",
        "START_NEXT_STEPS_TITLE": "Próximos pasos:",
        "START_STEP_1_NO_WALLET": (
            "1) Usa /link_wallet para conectar tu dirección BNB (red BSC)."
        ),
        "START_STEP_1_HAS_WALLET": (
            "1) Monedero BNB vinculado: {address}"
        ),
        "START_STEP_2_NO_BALANCE": (
            "2) Cuando tu inversión existente se registre en el sistema, "
            "verás tu saldo SLH con /balance."
        ),
        "START_STEP_2_HAS_BALANCE": (
            "2) Saldo actual de SLH: {balance} (ver /balance)."
        ),
        "START_STEP_3": (
            "3) Usa /wallet para ver detalles del monedero y enlaces del ecosistema."
        ),
        "START_STEP_4": (
            "4) Usa /whoami para ver tu ID, nombre de usuario y estado del monedero."
        ),
        "START_STEP_5": (
            "5) Usa /summary para un panel completo de inversor."
        ),
        "START_STEP_6": (
            "6) Usa /history para revisar tus últimas transacciones."
        ),
        "START_MENU_HINT": (
            "También puedes abrir /menu para una experiencia basada en botones."
        ),
        "START_LANGUAGE_HINT": (
            "Puedes cambiar el idioma de la interfaz con /language."
        ),

        "HELP_TEXT": (
            "SLH Wallet Bot – ayuda\n\n"
            "/start – pantalla de inicio y onboarding\n"
            "/menu – menú principal con botones\n"
            "/summary – panel completo del inversor (monedero + saldo + perfil)\n"
            "/wallet – detalles del monedero y enlaces del ecosistema\n"
            "/link_wallet – vincular tu dirección BNB personal (red BSC)\n"
            "/balance – ver tu saldo SLH off-chain + datos on-chain si están disponibles\n"
            "/history – últimas 10 transacciones en las que participas\n"
            "/transfer – transferencia interna de SLH a otro usuario\n"
            "/send_slh – atajo de transferencia: /send_slh <amount> <@user|id>\n"
            "/whoami – ver tu Telegram ID, nombre de usuario y estado del monedero\n"
            "/docs – abrir la documentación oficial para inversores\n"
            "/language – elegir el idioma de la interfaz\n\n"
            "Solo administrador:\n"
            "/admin_menu – herramientas para admin\n"
            "/admin_credit – acreditar SLH a un usuario\n"
            "/admin_list_users – listar usuarios y saldos\n"
            "/admin_ledger – vista global del ledger (últimas 50 transacciones)\n"
            "/admin_selftest – self-test profundo (DB / ENV / BSC / Telegram)\n\n"
            "En esta etapa no hay rescate del capital principal – "
            "las unidades SLH se usan solo dentro del ecosistema.\n"
            "BNB y el gas permanecen en tu monedero personal con proveedores externos."
        ),
    },

    # ==================== ARABIC ====================
    "ar": {
        "LANGUAGE_MENU_TITLE": "اختر لغة الواجهة المفضلة لديك:",
        "LANGUAGE_BUTTON_EN": "English 🇬🇧",
        "LANGUAGE_BUTTON_HE": "עברית 🇮🇱",
        "LANGUAGE_BUTTON_RU": "Русский 🇷🇺",
        "LANGUAGE_BUTTON_ES": "Español 🇪🇸",
        "LANGUAGE_BUTTON_AR": "العربية 🇦🇪",
        "LANGUAGE_SET_CONFIRM": "تم ضبط اللغة المفضلة إلى العربية.",
        "LANGUAGE_SET_CONFIRM_HE": "تم ضبط اللغة المفضلة إلى العبرية.",
        "LANGUAGE_SET_CONFIRM_RU": "تم ضبط اللغة المفضلة إلى الروسية.",
        "LANGUAGE_SET_CONFIRM_ES": "تم ضبط اللغة المفضلة إلى الإسبانية.",
        "LANGUAGE_SET_CONFIRM_AR": "تم ضبط اللغة المفضلة إلى العربية.",

        "START_TITLE": "مرحبًا بك في بوابة الاستثمار SLH.",
        "START_MIN_INVEST_LINE": (
            "هذا البوت مخصص للمستثمرين الاستراتيجيين (حد أدنى للاستثمار قدره {min_invest} شيكل)."
        ),
        "START_FEATURES_INTRO": "من خلال هذا البوت يمكنك:",
        "START_FEATURE_1": "- ربط محفظة BNB الشخصية الخاصة بك (شبكة BSC)",
        "START_FEATURE_2": "- عرض رصيد SLH الخاص بك في النظام (off-chain)",
        "START_FEATURE_3": "- تحويل وحدات SLH إلى مستثمرين آخرين داخل النظام (off-chain)",
        "START_FEATURE_4": "- الوصول إلى روابط خارجية لشراء BNB ومعلومات عن الـ Staking",
        "START_NEXT_STEPS_TITLE": "الخطوات التالية:",
        "START_STEP_1_NO_WALLET": (
            "1) استخدم /link_wallet لربط عنوان BNB الخاص بك (شبكة BSC)."
        ),
        "START_STEP_1_HAS_WALLET": (
            "1) تم ربط محفظة BNB: {address}"
        ),
        "START_STEP_2_NO_BALANCE": (
            "2) بعد تسجيل استثماراتك الحالية في النظام، "
            "سترى رصيد SLH الخاص بك عبر /balance."
        ),
        "START_STEP_2_HAS_BALANCE": (
            "2) رصيد SLH الحالي: {balance} (انظر /balance)."
        ),
        "START_STEP_3": (
            "3) استخدم /wallet لعرض تفاصيل المحفظة وروابط منظومة SLH."
        ),
        "START_STEP_4": (
            "4) استخدم /whoami لعرض معرف تيليجرام، اسم المستخدم وحالة المحفظة."
        ),
        "START_STEP_5": (
            "5) استخدم /summary للحصول على لوحة معلومات كاملة للمستثمر."
        ),
        "START_STEP_6": (
            "6) استخدم /history لمراجعة آخر المعاملات الخاصة بك داخل النظام."
        ),
        "START_MENU_HINT": (
            "يمكنك أيضًا فتح /menu للحصول على واجهة تعتمد على الأزرار."
        ),
        "START_LANGUAGE_HINT": (
            "يمكنك تغيير لغة الواجهة باستخدام /language."
        ),

        "HELP_TEXT": (
            "SLH Wallet Bot – مساعدة\n\n"
            "/start – شاشة البداية والانضمام للنظام\n"
            "/menu – القائمة الرئيسية مع أزرار\n"
            "/summary – لوحة معلومات كاملة للمستثمر (محفظة + رصيد + ملف شخصي)\n"
            "/wallet – تفاصيل المحفظة وروابط منظومة SLH\n"
            "/link_wallet – ربط عنوان BNB الشخصي (شبكة BSC)\n"
            "/balance – عرض رصيد SLH في النظام (off-chain) + بيانات on-chain إذا توفرت\n"
            "/history – آخر 10 معاملات شاركت فيها داخل النظام\n"
            "/transfer – تحويل داخلي لوحدات SLH إلى مستخدم آخر\n"
            "/send_slh – اختصار للتحويل: /send_slh <amount> <@user|id>\n"
            "/whoami – عرض معرف تيليجرام، اسم المستخدم وحالة المحفظة\n"
            "/docs – فتح مستندات المستثمر الرسمية لـ SLH\n"
            "/language – اختيار لغة الواجهة المفضلة\n\n"
            "أوامر للمسؤول فقط:\n"
            "/admin_menu – قائمة أدوات المسؤول\n"
            "/admin_credit – إضافة رصيد SLH لمستخدم\n"
            "/admin_list_users – قائمة المستخدمين والأرصدة\n"
            "/admin_ledger – عرض السجل العام (آخر 50 معاملة)\n"
            "/admin_selftest – فحص كامل للنظام (قاعدة بيانات / بيئة / BSC / تيليجرام)\n\n"
            "في هذه المرحلة لا يوجد استرداد لرأس المال الأصلي – "
            "يتم استخدام وحدات SLH داخل منظومة SLH فقط.\n"
            "يبقى BNB والغاز في محفظتك الخاصة لدى مزودي الخدمة الخارجيين."
        ),
    },
}


def _supported_from_env() -> set[str]:
    """
    מחלץ את רשימת השפות הנתמכות מתוך SUPPORTED_LANGUAGES,
    או מתוך TEXTS אם לא הוגדר.
    """
    env = (settings.SUPPORTED_LANGUAGES or "").strip()
    if env:
        parts = [p.strip().lower() for p in env.split(",") if p.strip()]
        return set(p for p in parts if p in TEXTS)
    # אם לא הוגדר – כל השפות המופיעות ב-TEXTS
    return set(TEXTS.keys())


SUPPORTED_LANGS = _supported_from_env()

DEFAULT_LANG = (settings.DEFAULT_LANGUAGE or "en").lower()
if DEFAULT_LANG not in TEXTS:
    DEFAULT_LANG = "en"


def normalize_lang(raw: str | None) -> str:
    """
    מחזיר קוד שפה תקין מתוך SUPPORTED_LANGS, או DEFAULT_LANG.
    תומך בקודים כמו he-IL, en-US, ar-IL וכו'.
    """
    if not raw:
        return DEFAULT_LANG

    lc = raw.lower()

    if lc in ("he", "iw", "he-il"):
        base = "he"
    elif lc.startswith("he-"):
        base = "he"
    elif lc in ("ru", "ru-ru"):
        base = "ru"
    elif lc.startswith("ru-"):
        base = "ru"
    elif lc in ("es", "es-es", "es-419"):
        base = "es"
    elif lc.startswith("es-"):
        base = "es"
    elif lc in ("ar", "ar-il", "ar-sa", "ar-ae"):
        base = "ar"
    elif lc.startswith("ar-"):
        base = "ar"
    else:
        base = lc.split("-", 1)[0]

    if base in SUPPORTED_LANGS:
        return base
    if DEFAULT_LANG in SUPPORTED_LANGS:
        return DEFAULT_LANG
    return "en"


def t(lang: str, key: str) -> str:
    """
    מחזיר טקסט לפי שפה ומפתח.
    אם אין בשפה – ננסה באנגלית,
    ואם גם שם לא קיים – נחזיר את המפתח עצמו.
    """
    lang = normalize_lang(lang)
    if lang in TEXTS and key in TEXTS[lang]:
        return TEXTS[lang][key]

    if "en" in TEXTS and key in TEXTS["en"]:
        return TEXTS["en"][key]

    return key
