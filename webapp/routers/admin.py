# (truncated for brevity - keeping only the changed function)

@router.get("/products/info")
async def get_products_info(user_id: int = Query(...)):
    """
    Отримати інформацію про товари з було/стало статистикою.
    Враховує доступні товари та зібрані за сесію.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        # Якщо немає товарів - повертаємо порожні дані зі статусом 200
        if not all_products:
            return JSONResponse(content={
                "success": True,
                "current_articles": 0,
                "current_sum": 0.0,
                "original_articles": 0,
                "original_sum": 0.0,
                "collected_articles": 0,
                "collected_sum": 0.0,
                "departments": [],
                "last_import": None
            })
        
        # Підраховуємо резерви з temp_list
        temp_reservations = {}
        for item in temp_list_items:
            temp_reservations[item.product_id] = temp_reservations.get(item.product_id, 0) + item.quantity
        
        # Розділяємо на доступні та зібрані
        available_products = []
        collected_products = []
        dept_stats_current = {}
        dept_stats_original = {}
        current_sum = 0.0
        collected_sum = 0.0
        
        for product in all_products:
            try:
                stock_qty = float(str(product.кількість).replace(',', '.'))
            except (ValueError, TypeError):
                stock_qty = 0
            
            # Рахуємо доступну кількість
            reserved = (product.відкладено or 0) + temp_reservations.get(product.id, 0)
            available = stock_qty - reserved
            dept = product.відділ
            price = product.ціна or 0.0
            
            if available > 0:
                # Доступні товари
                available_products.append(product)
                dept_stats_current[dept] = dept_stats_current.get(dept, 0) + 1
                current_sum += available * price
            elif reserved > 0 or stock_qty == 0:
                # Зібрані товари (було, але відкладено або кількість 0)
                collected_products.append(product)
                collected_sum += reserved * price
        
        # Було = доступні + зібрані
        for product in available_products + collected_products:
            dept = product.відділ
            dept_stats_original[dept] = dept_stats_original.get(dept, 0) + 1
        
        departments = [
            {
                "department": dept_id,
                "current_count": dept_stats_current.get(dept_id, 0),
                "original_count": dept_stats_original.get(dept_id, 0)
            }
            for dept_id in sorted(set(list(dept_stats_current.keys()) + list(dept_stats_original.keys())))
        ]
        
        # Остання дата імпорту
        last_import = None
        if all_products and hasattr(all_products[0], 'created_at'):
            last_import = all_products[0].created_at.strftime('%d.%m - %H:%M')
        
        original_count = len(available_products) + len(collected_products)
        original_sum = current_sum + collected_sum
        
        return JSONResponse(content={
            "success": True,
            # Поточний стан
            "current_articles": len(available_products),
            "current_sum": round(current_sum, 2),
            # Початковий стан
            "original_articles": original_count,
            "original_sum": round(original_sum, 2),
            # Зібрано
            "collected_articles": len(collected_products),
            "collected_sum": round(collected_sum, 2),
            # Деталі
            "departments": departments,
            "last_import": last_import
        })
    
    except Exception as e:
        logger.error("Помилка отримання інформації про товари: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання даних"}, status_code=500)