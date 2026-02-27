#!/bin/bash
# build_android.sh - Автоматична збірка Android APK для EpicService

set -e  # Зупинка при помилках

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$HOME/epicservice"
ANDROID_DIR="$PROJECT_ROOT/android-app/android"
APK_OUTPUT="$ANDROID_DIR/app/build/outputs/apk"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 EpicService Android Builder${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Перевірка що запущено з правильної директорії
cd "$PROJECT_ROOT" || {
    echo -e "${RED}❌ Помилка: каталог $PROJECT_ROOT не знайдено${NC}"
    exit 1
}

# 1. Git sync
echo -e "${YELLOW}📡 Крок 1/5: Синхронізація з Git...${NC}"
git fetch origin
git status

read -p "Запушити зміни в Git? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Commit message: " commit_msg
    if [ -n "$commit_msg" ]; then
        git add .
        git commit -m "$commit_msg" || echo "Нічого нового для коміту"
        git push origin main
        echo -e "${GREEN}✓ Push завершено${NC}\n"
    fi
else
    echo -e "${BLUE}⊳ Пропущено push${NC}\n"
fi

# 2. Оновлення з Git (опціонально)
read -p "Стянути зміни з Git? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git pull origin main
    echo -e "${GREEN}✓ Pull завершено${NC}\n"
else
    echo -e "${BLUE}⊳ Пропущено pull${NC}\n"
fi

# 3. Генерація іконок (якщо є epicenter.png)
echo -e "${YELLOW}📦 Крок 2/5: Перевірка іконок...${NC}"
ICON_SOURCE="$PROJECT_ROOT/android-app/epicenter.png"
if [ -f "$ICON_SOURCE" ]; then
    read -p "Регенерувати іконки з epicenter.png? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 "$PROJECT_ROOT/android-app/make_app_icons.py" "$ICON_SOURCE"
        echo -e "${GREEN}✓ Іконки оновлено${NC}\n"
    else
        echo -e "${BLUE}⊳ Іконки не змінено${NC}\n"
    fi
else
    echo -e "${BLUE}⊳ epicenter.png не знайдено, пропускаємо${NC}\n"
fi

# 4. Capacitor sync
echo -e "${YELLOW}⚡ Крок 3/5: Capacitor sync...${NC}"
cd "$PROJECT_ROOT/android-app"
npx cap sync android
echo -e "${GREEN}✓ Sync завершено${NC}\n"

# 5. Вибір типу збірки
echo -e "${YELLOW}🔨 Крок 4/5: Збірка Android...${NC}"
echo "Оберіть тип збірки:"
echo "  1) Debug APK (швидко, для тестування)"
echo "  2) Release APK (підписаний, для розповсюдження)"
echo "  3) Release AAB (для Google Play)"
read -p "Вибір [1-3]: " build_choice

cd "$ANDROID_DIR"

case $build_choice in
    2)
        echo -e "${BLUE}Збираємо Release APK...${NC}"
        ./gradlew clean assembleRelease
        APK_PATH="$APK_OUTPUT/release/app-release.apk"
        ;;
    3)
        echo -e "${BLUE}Збираємо Release AAB...${NC}"
        ./gradlew clean bundleRelease
        APK_PATH="$ANDROID_DIR/app/build/outputs/bundle/release/app-release.aab"
        ;;
    *)
        echo -e "${BLUE}Збираємо Debug APK...${NC}"
        ./gradlew clean assembleDebug
        APK_PATH="$APK_OUTPUT/debug/app-debug.apk"
        ;;
esac

# 6. Результат
echo -e "\n${YELLOW}📋 Крок 5/5: Результат${NC}"
if [ -f "$APK_PATH" ]; then
    FILE_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Збірка успішна!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "📦 Файл: ${BLUE}$APK_PATH${NC}"
    echo -e "📏 Розмір: ${BLUE}$FILE_SIZE${NC}"
    
    # Копіювання в зручне місце
    DEPLOY_DIR="$PROJECT_ROOT/android-app/builds"
    mkdir -p "$DEPLOY_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    FILENAME=$(basename "$APK_PATH")
    DEPLOY_PATH="$DEPLOY_DIR/${FILENAME%.*}_${TIMESTAMP}.${FILENAME##*.}"
    cp "$APK_PATH" "$DEPLOY_PATH"
    echo -e "📂 Копія: ${BLUE}$DEPLOY_PATH${NC}"
    
    echo -e "\n${YELLOW}Наступні кроки:${NC}"
    if [[ $build_choice == 1 ]]; then
        echo -e "  ${BLUE}adb install -r \"$APK_PATH\"${NC}"
    elif [[ $build_choice == 2 ]]; then
        echo "  - Встанови APK на пристрій вручну"
        echo "  - Або: adb install -r \"$APK_PATH\""
    else
        echo "  - Завантаж AAB в Google Play Console"
    fi
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Збірка не вдалась!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 Готово!${NC}\n"
