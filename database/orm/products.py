# epicservice/database/orm/products.py

import asyncio
import logging
import re
from difflib import SequenceMatcher

import pandas as pd
from sqlalchemy import delete, func, select, update
from thefuzz import fuzz

from database.engine import async_session, sync_session
from database.models import Product

# Налаштовуємо логер для цього модуля
logger = logging.getLogger(__name__)


# --- Допоміжні класи та функції для мапінгу колонок ---

class SmartColumnMapper:
    """
    Клас для евристичного розпізнавання колонок Excel файлу.
    Дозволяє знаходити відповідності між внутрішніми назвами полів та заголовками файлу.
    """
    
    # Словник синонімів для кожної цільової колонки
    COLUMN_SYNONYMS = {
        "article": [
            "артикул", "код", "code", "articul", "id", "sku", "item_code", "товар"
        ],
        "name": [
            "назва", "name", "title", "найменування", "product", "description", "опис", "номенклатура", "товар"
        ],
        "department": [
            "відділ", "department", "dep", "секція", "група", "group", "div", "підрозділ"
        ],
        "group": [
            "група", "group", "category", "категорія", "клас", "підгрупа"
        ],
        "quantity": [
            "кількість", "к-ть", "count", "qty", "quantity", "залишок", "amount", 
            "залишок (кількість)", "залишок к-ть", "кть", "штук", "шт"
        ],
        "price": [
            "ціна", "price", "cost", "вартість", "price_unit", "ціна за од"
        ],
        "stock_sum": [
            "сума", "sum", "total", "залишок сума", "сума залишку", "вартість залишку"
        ],
        "months_without_sale": [
            "місяці", "місяців", "м", "без руху", "months", "no sale", "неліквід", "період"
        ]
    }

    @staticmethod
    def normalize_header(header: str) -> str:
        """Приводить заголовок до нижнього регістру та видаляє зайві символи."""
        return str(header).lower().strip()

    @classmethod
    def find_best_match(cls, headers: list[str], target_field: str, threshold: float = 0.8) -> str | None:
        """
        Знаходить найкращий відповідник серед заголовків файлу для заданого поля.
        Використовує точний збіг, входження підрядка та нечіткий пошук.
        """
        synonyms = cls.COLUMN_SYNONYMS.get(target_field, [])
        normalized_headers = {h: cls.normalize_header(h) for h in headers}
        
        # 1. Точний збіг (пріоритет)
        for original, normalized in normalized_headers.items():
            if normalized in synonyms:
                return original
        
        # 2. Частковий збіг (наприклад, "Залишок (к-ть)" містить "к-ть")
        for original, normalized in normalized_headers.items():
            for synonym in synonyms:
                # Перевіряємо, чи синонім є окремим словом у заголовку
                if re.search(r'\b' + re.escape(synonym) + r'\b', normalized):
                    return original

        # 3. Нечіткий пошук (SequenceMatcher)
        best_match = None
        best_score = 0.0
        
        for original, normalized in normalized_headers.items():
            for synonym in synonyms:
                score = SequenceMatcher(None, normalized, synonym).ratio()
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = original
        
        return best_match

    @classmethod
    def map_columns(cls, df: pd.DataFrame) -> dict[str, str]:
        """
        Створює словник мапінгу {внутрішнє_поле: колонка_файлу}.
        """
        headers = list(df.columns)
        mapping = {}
        
        # Обов'язкові та бажані поля
        target_fields = [
            "article", "name", "department", "group", 
            "quantity", "price", "stock_sum", "months_without_sale"
        ]
        
        used_headers = set()
        
        for field in target_fields:
            # Шукаємо найкращий збіг, ігноруючи вже використані колонки
            available_headers = [h for h in headers if h not in used_headers]
            match = cls.find_best_match(available_headers, field)
            
            # Спеціальна логіка для "Товар" -> Артикул vs Назва
            # Якщо "Товар" містить цифри - це артикул, якщо текст - назва.
            # Але на етапі заголовків ми це не знаємо точно, тому покладаємось на порядок:
            # спочатку шукаємо артикул (він частіше має унікальні назви типу code), потім назву.
            
            if match:
                mapping[field] = match
                used_headers.add(match)
        
        return mapping


def _extract_article_and_name(row_val: str) -> tuple[str | None, str | None]:
    """
    Намагається розділити рядок типу "52250196 - Склянка..." на артикул та назву.
    """
    if not isinstance(row_val, str):
        row_val = str(row_val)
    
    # Шукаємо патерн: (цифри) (розділювач) (текст)
    # Розділювачі: " - ", " ", ".", тощо.
    match = re.match(r"^(\d{5,})\s*[-–.]?\s*(.+)$", row_val.strip())
    if match:
        return match.group(1), match.group(2)
    
    # Якщо просто артикул (тільки цифри)
    if re.match(r"^\d+$", row_val.strip()):
        return row_val.strip(), None
        
    return None, row_val.strip()


def _normalize_value(value: any, is_float: bool = True) -> float | str:
    """
    Приводить значення до стандартизованого числового типу (float) або рядка.
    """
    if pd.isna(value):
        return 0.0 if is_float else "0"

    s_value = str(value).replace(',', '.').strip()
    # Видаляємо все, крім цифр, мінуса та крапки
    s_value = re.sub(r'[^0-9.-]', '', s_value)
    
    try:
        return float(s_value) if is_float else s_value
    except (ValueError, TypeError):
        return 0.0 if is_float else "0"


# --- Функції імпорту та оновлення даних ---

def _sync_smart_import(dataframe: pd.DataFrame) -> dict:
    """
    Синхронно виконує "розумний" імпорт товарів з DataFrame у базу даних.
    Автоматично розпізнає колонки та адаптується до структури файлу.
    """
    try:
        # 1. Мапінг колонок
        mapping = SmartColumnMapper.map_columns(dataframe)
        logger.info(f"Знайдено колонки: {mapping}")
        
        # Перевірка критично важливих полів (хоча б кількість має бути)
        if "quantity" not in mapping and "stock_sum" not in mapping:
             logger.error("Не знайдено колонку з кількістю або сумою.")
             return {}

        file_articles_data = {}
        
        for index, row in dataframe.iterrows():
            article = None
            name = None
            
            # --- Спроба 1: Артикул в окремій колонці ---
            if "article" in mapping:
                val = row[mapping["article"]]
                if pd.notna(val):
                    # Якщо в колонці артикулу текст типу "123 - Назва", пробуємо розбити
                    a, n = _extract_article_and_name(str(val))
                    article = a
                    if n and "name" not in mapping: # Якщо назви окремо немає, беремо звідси
                        name = n
            
            # --- Спроба 2: Артикул разом з назвою в колонці Name ---
            if not article and "name" in mapping:
                val = row[mapping["name"]]
                if pd.notna(val):
                    a, n = _extract_article_and_name(str(val))
                    article = a
                    name = n or str(val) # Якщо не розбилось, то весь рядок - назва
            
            # Якщо після всіх спроб артикулу немає - пропускаємо рядок
            if not article:
                continue

            # --- Отримання інших даних ---
            department = 0
            if "department" in mapping:
                try:
                    # Відділ - завжди цифра, очищаємо від сміття
                    dep_val = row[mapping["department"]]
                    department = int(_normalize_value(dep_val))
                except:
                    department = 0

            # Група
            group = ""
            if "group" in mapping:
                group = str(row[mapping["group"]]).strip()
            
            # Якщо назва все ще порожня, беремо її з групи або заглушку
            if not name:
                name = group or f"Товар {article}"

            # --- Розрахунок кількості, ціни та суми ---
            qty = 0.0
            price = 0.0
            stock_sum = 0.0
            
            if "quantity" in mapping:
                qty = float(_normalize_value(row[mapping["quantity"]]))
            
            if "stock_sum" in mapping:
                stock_sum = float(_normalize_value(row[mapping["stock_sum"]]))
            
            if "price" in mapping:
                price = float(_normalize_value(row[mapping["price"]]))
            
            # Евристика: розрахунок відсутніх даних
            # 1. Є Сума і Кількість -> Рахуємо Ціну
            if price == 0 and qty > 0 and stock_sum > 0:
                price = stock_sum / qty
            
            # 2. Є Ціна і Кількість -> Рахуємо Суму
            if stock_sum == 0 and price > 0 and qty > 0:
                stock_sum = price * qty
            
            # 3. Є Сума і Ціна -> Рахуємо Кількість (рідкісний кейс)
            if qty == 0 and stock_sum > 0 and price > 0:
                qty = stock_sum / price

            months = None
            if "months_without_sale" in mapping:
                months = int(_normalize_value(row[mapping["months_without_sale"]]))

            # Формуємо запис
            file_articles_data[article] = {
                "назва": name.strip(),
                "відділ": department,
                "група": group,
                "кількість": str(qty) if qty % 1 != 0 else str(int(qty)), # Якщо ціле число - без .0
                "місяці_без_руху": months,
                "сума_залишку": stock_sum,
                "ціна": price,
                "активний": True
            }

        # --- Оновлення БД (Upsert / Soft Delete) ---
        file_articles = set(file_articles_data.keys())
        updated_count, added_count, deactivated_count, reactivated_count = 0, 0, 0, 0
        department_stats = {}

        with sync_session() as session:
            existing_products = {p.артикул: p for p in session.execute(select(Product)).scalars()}
            db_articles = set(existing_products.keys())

            articles_to_add = file_articles - db_articles
            articles_to_update = db_articles.intersection(file_articles)
            articles_to_deactivate = db_articles - file_articles # Нема у файлі, є в БД -> Вимикаємо

            # 1. Деактивація (Soft Delete)
            if articles_to_deactivate:
                stmt = update(Product).where(
                    Product.артикул.in_(articles_to_deactivate), 
                    Product.активний == True
                ).values(активний=False)
                result = session.execute(stmt)
                deactivated_count = result.rowcount

            # 2. Оновлення існуючих
            if articles_to_update:
                products_to_update_mappings = []
                for article in articles_to_update:
                    product_db = existing_products[article]
                    new_data = file_articles_data[article]

                    # Якщо товар був неактивний - активуємо
                    if not product_db.активний:
                        reactivated_count += 1
                    
                    # Логіка збереження старої ціни, якщо нова 0
                    if new_data["ціна"] == 0.0 and product_db.ціна and product_db.ціна > 0.0:
                         new_data["ціна"] = product_db.ціна
                         # Перераховуємо суму, якщо зберегли стару ціну
                         try:
                             qty_float = float(new_data["кількість"])
                             new_data["сума_залишку"] = qty_float * new_data["ціна"]
                         except: pass

                    # Логіка збереження місяців, якщо в файлі немає колонки
                    if new_data["місяці_без_руху"] is None:
                        new_data["місяці_без_руху"] = product_db.місяці_без_руху or 0

                    update_entry = {"id": product_db.id, "артикул": article, **new_data}
                    products_to_update_mappings.append(update_entry)
                
                if products_to_update_mappings:
                    session.bulk_update_mappings(Product, products_to_update_mappings)
                    updated_count = len(products_to_update_mappings)

            # 3. Додавання нових
            if articles_to_add:
                products_to_add_objects = []
                for article in articles_to_add:
                    data = file_articles_data[article]
                    if data["місяці_без_руху"] is None:
                        data["місяці_без_руху"] = 0
                    products_to_add_objects.append(Product(артикул=article, **data))
                
                if products_to_add_objects:
                    session.bulk_save_objects(products_to_add_objects)
                    added_count = len(products_to_add_objects)
            
            # Скидаємо резерви (відкладено) в нуль, бо прийшов свіжий файл залишків
            session.execute(update(Product).values(відкладено=0))
            session.commit()

            total_in_db = session.execute(select(func.count(Product.id)).where(Product.активний == True)).scalar_one()

            # Статистика по відділах для звіту
            for data in file_articles_data.values():
                dep = data["відділ"]
                department_stats[dep] = department_stats.get(dep, 0) + 1
            
            return {
                'added': added_count, 'updated': updated_count,
                'deactivated': deactivated_count, 'reactivated': reactivated_count,
                'total_in_db': total_in_db, 'total_in_file': len(file_articles),
                'department_stats': department_stats
            }

    except Exception as e:
        logger.error(f"Помилка під час синхронного імпорту: {e}", exc_info=True)
        return {}


async def orm_smart_import(dataframe: pd.DataFrame) -> dict:
    """
    Асинхронна обгортка для запуску синхронної функції імпорту.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_smart_import, dataframe)


def _sync_subtract_collected_from_stock(dataframe: pd.DataFrame) -> dict:
    """
    Синхронно віднімає кількість зібраних товарів від залишків
    та перераховує суму залишку.
    """
    processed_count, not_found_count, error_count = 0, 0, 0
    
    # Використовуємо той самий мапер для пошуку колонок
    mapping = SmartColumnMapper.map_columns(dataframe)
    col_article = mapping.get("article")
    col_qty = mapping.get("quantity")
    
    if not col_article or not col_qty:
        logger.error("Віднімання: не знайдено колонки артикулу або кількості.")
        return {'processed': 0, 'not_found': 0, 'errors': 0, 'msg': 'Колонки не знайдено'}

    with sync_session() as session:
        for _, row in dataframe.iterrows():
            # Отримання артикулу (може бути злитий з назвою)
            val = row[col_article]
            article_cand, _ = _extract_article_and_name(val)
            article = article_cand if article_cand else str(val).strip()
            
            if not article:
                continue

            product = session.execute(select(Product).where(Product.артикул == article)).scalar_one_or_none()
            if not product:
                not_found_count += 1
                continue

            try:
                current_stock = float(str(product.кількість).replace(',', '.'))
                quantity_to_subtract = float(_normalize_value(row[col_qty]))
                
                new_stock = current_stock - quantity_to_subtract
                # Захист від від'ємних залишків? (Можна залишити як є, раптом пересорт)
                
                price = product.ціна or 0.0
                new_stock_sum = new_stock * price

                session.execute(
                    update(Product)
                    .where(Product.id == product.id)
                    .values(
                        кількість=str(new_stock), # Зберігаємо як рядок для сумісності з поточним полем
                        сума_залишку=new_stock_sum
                    )
                )
                processed_count += 1
            except (ValueError, TypeError) as e:
                error_count += 1
                logger.error(f"Помилка конвертації числа для артикула {article}: {e}")
                continue
        session.commit()
    return {'processed': processed_count, 'not_found': not_found_count, 'errors': error_count}


async def orm_subtract_collected(dataframe: pd.DataFrame) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_subtract_collected_from_stock, dataframe)


# --- Функції пошуку та отримання товарів ---

async def orm_find_products(search_query: str) -> list[Product]:
    """
    Виконує нечіткий пошук товарів у базі даних серед активних товарів.
    """
    async with async_session() as session:
        like_query = f"%{search_query}%"
        stmt = select(Product).where(
            Product.активний == True,
            (Product.назва.ilike(like_query)) | (Product.артикул.ilike(like_query))
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        if not candidates: return []

        scored_products = []
        search_query_lower = search_query.lower()

        for product in candidates:
            if search_query == product.артикул: article_score = 200
            else: article_score = fuzz.ratio(search_query, product.артикул) * 1.5

            name_lower = product.назва.lower()
            token_set_score = fuzz.token_set_ratio(search_query_lower, name_lower)
            partial_score = fuzz.partial_ratio(search_query_lower, name_lower)
            
            if name_lower.startswith(search_query_lower): name_score = 100
            else: name_score = (token_set_score * 0.7) + (partial_score * 0.3)

            final_score = max(article_score, name_score)

            if final_score > 65:
                scored_products.append((product, final_score))
        
        scored_products.sort(key=lambda x: x[1], reverse=True)
        return [product for product, score in scored_products[:15]]


async def orm_get_product_by_id(session, product_id: int, for_update: bool = False) -> Product | None:
    query = select(Product).where(Product.id == product_id)
    if for_update: query = query.with_for_update()
    result = await session.execute(query)
    return result.scalar_one_or_none()


def orm_get_all_products_sync() -> list[Product]:
    with sync_session() as session:
        query = select(Product).where(Product.активний == True).order_by(Product.відділ, Product.назва)
        result = session.execute(query)
        return result.scalars().all()
