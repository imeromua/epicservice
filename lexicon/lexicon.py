# epicservice/lexicon/lexicon.py

class Lexicon:
    """
    Клас, що містить усі текстові константи (лексикон) для бота.
    """
    # --- Кнопки підтвердження (keyboards/inline.py) ---
    BUTTON_CONFIRM_YES = "✅ Так"
    BUTTON_CONFIRM_NO = "❌ Ні"
    BUTTON_NOTIFY_USERS = "🗣️ Надіслати сповіщення"
    BUTTON_FORCE_SAVE = "💾 Примусово зберегти"
    BUTTON_YES_NOTIFY = "✅ Так, сповістити"
    BUTTON_NO_NOTIFY = "❌ Ні, тихий режим"
    BUTTON_BACK_TO_ADMIN_PANEL = "⬅️ Назад до адмін-панелі"

    # --- Імпорт ---
    IMPORT_PROMPT = "Будь ласка, надішліть мені файл Excel (`.xlsx`) з оновленими залишками.\n\nДля скасування натисніть кнопку нижче."
    IMPORT_WRONG_FORMAT = "❌ Помилка. Будь ласка, надішліть файл у форматі `.xlsx`."
    IMPORT_PROCESSING = "Завантажую та перевіряю файл..."
    IMPORT_INVALID_COLUMNS = "❌ *Помилка валідації!*\nНазви колонок у файлі неправильні.\nОчікується: `в, г, н, к`.\nУ вашому файлі відсутні: `{columns}`."
    IMPORT_CRITICAL_READ_ERROR = "❌ Критична помилка при читанні файлу: {error}"
    IMPORT_STARTING = "Файл виглядає добре. Починаю імпорт та обнулення старих резервів..."
    IMPORT_SYNC_ERROR = "❌ Сталася критична помилка під час синхронізації з базою даних: {error}"
    IMPORT_ASK_FOR_NOTIFICATION = "Сповістити всіх користувачів про це оновлення?"
    BROADCAST_STARTING = "✅ Імпорт завершено. Починаю розсилку сповіщень користувачам..."
    BROADCAST_SKIPPED = "✅ Імпорт завершено. Сповіщення користувачам не надсилались ('тихий режим')."

    IMPORT_REPORT_TITLE = "✅ *Синхронізацію завершено!*\n"
    IMPORT_REPORT_ADDED = "➕ *Додано нових:* {added}"
    IMPORT_REPORT_UPDATED = "🔄 *Оновлено існуючих:* {updated}"
    IMPORT_REPORT_DEACTIVATED = "➖ *Деактивовано (зникли з файлу):* {deactivated}"
    IMPORT_REPORT_REACTIVATED = "♻️ *Повторно активовано:* {reactivated}\n"
    IMPORT_REPORT_TOTAL = "🗃️ *Всього активних артикулів у базі:* {total}"

    # --- Звіти ---
    EXPORTING_STOCK = "Починаю формування звіту по залишкам..."
    STOCK_REPORT_CAPTION = "✅ Ось ваш звіт по актуальним залишкам."
    STOCK_REPORT_ERROR = "❌ Не вдалося створити звіт про залишки."
    COLLECTED_REPORT_CAPTION = "✅ Ось зведений звіт по всім зібраним товарам."
    COLLECTED_REPORT_EMPTY = "Наразі немає жодного зібраного товару у збережених списках."
    COLLECTED_REPORT_PROCESSING = "Починаю формування зведеного звіту..."
    SUBTRACT_PROMPT = "Будь ласка, надішліть мені звіт по зібраному (`.xlsx`), щоб відняти ці позиції від залишків на складі."
    SUBTRACT_PROCESSING = "Обробляю звіт по зібраному..."
    SUBTRACT_INVALID_COLUMNS = "❌ *Помилка!* Назви колонок у файлі для віднімання неправильні.\nОчікується: `Відділ, Група, Назва, Кількість`.\nУ вашому файлі: `{columns}`."
    SUBTRACT_REPORT_TITLE = "✅ *Віднімання зібраного завершено!*\n"
    SUBTRACT_REPORT_PROCESSED = "🔄 *Опрацьовано рядків:* {processed}"
    SUBTRACT_REPORT_NOT_FOUND = "⚠️ *Не знайдено в базі:* {not_found}"
    SUBTRACT_REPORT_ERROR = "❌ *Помилки (нечислові залишки):* {errors}"

    # --- Керування списками (адмін) ---
    DELETE_ALL_LISTS_CONFIRM = "🔴 *УВАГА!*\n\nВи збираєтесь видалити *ВСІ* збережені списки *ВСІХ* користувачів та їхні файли. Ця дія *НЕЗВОРОТНЯ*.\n\nВи впевнені?"
    DELETE_ALL_LISTS_SUCCESS = "✅ Всі збережені списки ({count} шт.) та їхні файли було успішно видалено."
    NO_LISTS_TO_DELETE = "Немає збережених списків для видалення."

    # --- Архіви (адмін) ---
    NO_USERS_WITH_ARCHIVES = "Жоден користувач ще не зберіг жодного списку."
    USER_HAS_NO_ARCHIVES = "У цього користувача немає збережених списків."

    # --- Блокування та сповіщення ---
    ACTIVE_LISTS_BLOCK = (
        "🔴 *Дію заблоковано!*\n\n"
        "Неможливо виконати операцію, оскільки наступні користувачі мають незавершені списки:\n"
        "{users_info}\n\n"
        "Оберіть дію:"
    )
    NOTIFICATIONS_SENT = "✅ Сповіщення успішно надіслано вказаним користувачам."
    USER_SAVE_LIST_NOTIFICATION = (
        "❗️ *Будь ласка, збережіть ваш поточний список!*\n\n"
        "Адміністратор планує оновити базу даних. Незавершені списки можуть бути втрачені або збережені примусово."
    )

    # --- Сповіщення користувачів після імпорту ---
    USER_IMPORT_NOTIFICATION_TITLE = "✅ <b>Базу товарів оновлено!</b>\n\n"
    USER_IMPORT_NOTIFICATION_SUMMARY = (
        "<b>Кількість артикулів:</b> <i>{total_in_db} шт.</i>\n"
        "<b>Загальна сума збору:</b> <i>{total_sum} грн</i>\n\n"
    )
    USER_IMPORT_NOTIFICATION_DETAILS = (
        "➕ <i>Додано нових:</i> {added}\n"
        "🔄 <i>Оновлено існуючих:</i> {updated}\n"
        "➖ <i>Деактивовано:</i> {deactivated}\n"
    )
    USER_IMPORT_NOTIFICATION_DEPARTMENTS_TITLE = "\n📦 <i>Актуальна кількість артикулів по відділах:</i>\n"
    USER_IMPORT_NOTIFICATION_DEPARTMENT_ITEM = "- Відділ <code>{dep_id}</code>: <b>{count}</b> арт.\n"

    # --- Збереження списку (force_save_helper) ---
    TRANSACTION_ERROR = "Сталася критична помилка під час збереження. Зміни було скасовано. Спробуйте зберегти список знову."

    # --- Загальна помилка ---
    UNEXPECTED_ERROR = (
        "😔 *Ой, щось пішло не так...*\n"
        "Виникла непередбачена помилка. Ми вже отримали сповіщення і працюємо над її вирішенням. Спробуйте повторити дію пізніше."
    )

LEXICON = Lexicon()
