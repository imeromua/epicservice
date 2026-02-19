

@router.get("/users/all")
async def get_all_users_with_stats(user_id: int = Query(...)):
    """
    Отримати всіх користувачів з історією архівів та загальною сумою.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        
        users_data = []
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        
        for uid in user_ids:
            # Підраховуємо архіви користувача
            archives_count = 0
            total_amount = 0.0
            last_activity = None
            
            if os.path.exists(archives_dir):
                user_files = [f for f in os.listdir(archives_dir) if f.startswith(f"user_{uid}_")]
                archives_count = len(user_files)
                
                # Знаходимо останній файл
                if user_files:
                    latest_file = max(user_files, key=lambda f: os.path.getmtime(os.path.join(archives_dir, f)))
                    last_activity = datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(archives_dir, latest_file))
                    ).strftime('%d.%m.%Y %H:%M')
                    
                    # Читаємо всі файли користувача для підрахунку суми
                    for filename in user_files:
                        try:
                            filepath = os.path.join(archives_dir, filename)
                            df = pd.read_excel(filepath)
                            if 'Сума' in df.columns:
                                total_amount += df['Сума'].sum()
                        except Exception as e:
                            logger.warning(f"Не вдалося прочитати {filename}: {e}")
            
            users_data.append({
                "user_id": uid,
                "username": f"User {uid}",
                "archives_count": archives_count,
                "total_amount": round(total_amount, 2),
                "last_activity": last_activity
            })
        
        # Сортуємо за кількістю архівів
        users_data.sort(key=lambda x: x['archives_count'], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "users": users_data
        })
    
    except Exception as e:
        logger.error("Помилка отримання користувачів: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання користувачів"}, status_code=500)


@router.get("/products/info")
async def get_products_info(user_id: int = Query(...)):
    """
    Отримати інформацію про товари: кількість артикулів, сума, розбивка по відділах.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        
        if not all_products:
            return JSONResponse(content={
                "success": False,
                "message": "Немає товарів у базі"
            }, status_code=404)
        
        # Підрахунки
        total_articles = len(all_products)
        total_sum = sum(p.сума_залишку for p in all_products if p.сума_залишку)
        
        # Групуємо по відділах
        dept_stats = {}
        for product in all_products:
            dept = product.відділ
            dept_stats[dept] = dept_stats.get(dept, 0) + 1
        
        departments = [
            {"department": dept_id, "count": count}
            for dept_id, count in sorted(dept_stats.items())
        ]
        
        # Остання дата імпорту (з першого товару)
        last_import = None
        if all_products and hasattr(all_products[0], 'created_at'):
            last_import = all_products[0].created_at.strftime('%d.%m - %H.%M')
        
        return JSONResponse(content={
            "success": True,
            "total_articles": total_articles,
            "total_sum": round(total_sum, 2),
            "departments": departments,
            "last_import": last_import
        })
    
    except Exception as e:
        logger.error("Помилка отримання інформації про товари: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання даних"}, status_code=500)


@router.get("/reserved/by-department")
async def get_reserved_by_department(user_id: int = Query(...)):
    """
    Отримати розбивку резервів по відділах з детальною статистикою.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        if not temp_list_items:
            return JSONResponse(content={
                "success": True,
                "departments": []
            })
        
        # Групуємо по відділах
        dept_data = {}
        for item in temp_list_items:
            dept = item.product.відділ
            if dept not in dept_data:
                dept_data[dept] = {
                    "department": dept,
                    "reserved_sum": 0.0,
                    "products_count": set(),
                    "users_count": set()
                }
            
            dept_data[dept]["reserved_sum"] += item.quantity * (item.product.ціна or 0.0)
            dept_data[dept]["products_count"].add(item.product_id)
            dept_data[dept]["users_count"].add(item.user_id)
        
        # Конвертуємо set в count
        departments = []
        for dept_id, data in sorted(dept_data.items()):
            departments.append({
                "department": dept_id,
                "reserved_sum": round(data["reserved_sum"], 2),
                "products_count": len(data["products_count"]),
                "users_count": len(data["users_count"])
            })
        
        # Сортуємо за сумою резерву
        departments.sort(key=lambda x: x["reserved_sum"], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "departments": departments
        })
    
    except Exception as e:
        logger.error("Помилка отримання резервів по відділах: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання даних"}, status_code=500)
