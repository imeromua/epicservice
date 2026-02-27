#!/bin/bash
# build_android.sh - Автоматична збірка Android APK для EpicService
# Автоматично оновлює versionName та versionCode в build.gradle

set -e  # Зупинка при помилках

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="$HOME/epicservice"
ANDROID_DIR="$PROJECT_ROOT/android-app/android"
APK_OUTPUT="$ANDROID_DIR/app/build/outputs/apk"
BUILD_GRADLE="$ANDROID_DIR/app/build.gradle"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 EpicService Android Builder${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Перевірка що запущено з правильної директорії
cd "$PROJECT_ROOT" || {
    echo -e "${RED}❌ Помилка: каталог $PROJECT_ROOT не знайдено${NC}"
    exit 1
}

# Генерація версії: ГГММДД.ЧЧММ
VERSION_NAME=$(date +"%y%m%d.%H%M")
# versionCode: ГГММДДЧЧ (без хвилин, 8 цифр, без нулів на початку)
VERSION_CODE=$(date +"%-y%m%d%H" | sed 's/^0*//')


echo -e "${CYAN}📌 Нова версія: ${VERSION_NAME} (code: ${VERSION_CODE})${NC}\n"

# 1. Git sync
echo -e "${YELLOW}📡 Крок 1/6: Синхронізація з Git...${NC}"
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

# 3. Оновлення версії в build.gradle
echo -e "${YELLOW}🔢 Крок 2/6: Оновлення версії...${NC}"
if [ -f "$BUILD_GRADLE" ]; then
    # Backup
    cp "$BUILD_GRADLE" "$BUILD_GRADLE.bak"
    
    # Використовуємо perl для надійнішої заміни (працює однаково на Linux/macOS)
    perl -i -pe "s/versionCode\s+\d+/versionCode $VERSION_CODE/g" "$BUILD_GRADLE"
    perl -i -pe "s/versionName\s+\"[^\"]*\"/versionName \"$VERSION_NAME\"/g" "$BUILD_GRADLE"
    
    # Перевірка що заміна відбулась
    if grep -q "versionCode $VERSION_CODE" "$BUILD_GRADLE" && grep -q "versionName \"$VERSION_NAME\"" "$BUILD_GRADLE"; then
        echo -e "${GREEN}✓ Версія оновлена в build.gradle${NC}"
        echo -e "${CYAN}  versionName: $VERSION_NAME${NC}"
        echo -e "${CYAN}  versionCode: $VERSION_CODE${NC}\n"
    else
        echo -e "${RED}❌ Помилка оновлення версії!${NC}"
        echo -e "${YELLOW}Відновлюємо backup...${NC}"
        mv "$BUILD_GRADLE.bak" "$BUILD_GRADLE"
        exit 1
    fi
else
    echo -e "${RED}❌ Файл build.gradle не знайдено!${NC}"
    exit 1
fi

# 4. Генерація іконок (якщо є epicenter.png)
echo -e "${YELLOW}📦 Крок 3/6: Перевірка іконок...${NC}"
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

# 5. Capacitor sync
echo -e "${YELLOW}⚡ Крок 4/6: Capacitor sync...${NC}"
cd "$PROJECT_ROOT/android-app"
npx cap sync android
echo -e "${GREEN}✓ Sync завершено${NC}\n"

# 6. Вибір типу збірки
echo -e "${YELLOW}🔨 Крок 5/6: Збірка Android...${NC}"
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
        OUTPUT_EXT="apk"
        BUILD_TYPE="release"
        ;;
    3)
        echo -e "${BLUE}Збираємо Release AAB...${NC}"
        ./gradlew clean bundleRelease
        APK_PATH="$ANDROID_DIR/app/build/outputs/bundle/release/app-release.aab"
        OUTPUT_EXT="aab"
        BUILD_TYPE="release"
        ;;
    *)
        echo -e "${BLUE}Збираємо Debug APK...${NC}"
        ./gradlew clean assembleDebug
        APK_PATH="$APK_OUTPUT/debug/app-debug.apk"
        OUTPUT_EXT="apk"
        BUILD_TYPE="debug"
        ;;
esac

# 7. Результат
echo -e "\n${YELLOW}📋 Крок 6/6: Результат${NC}"
if [ -f "$APK_PATH" ]; then
    FILE_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Збірка успішна!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "📦 Файл: ${BLUE}$APK_PATH${NC}"
    echo -e "📏 Розмір: ${BLUE}$FILE_SIZE${NC}"
    echo -e "🏷️  Версія: ${CYAN}$VERSION_NAME${NC} (code: ${VERSION_CODE})"
    
    # Копіювання з версією в імені
    DEPLOY_DIR="$PROJECT_ROOT/android-app/builds"
    mkdir -p "$DEPLOY_DIR"
    DEPLOY_FILENAME="epicservice-${BUILD_TYPE}-${VERSION_NAME}.${OUTPUT_EXT}"
    DEPLOY_PATH="$DEPLOY_DIR/$DEPLOY_FILENAME"
    cp "$APK_PATH" "$DEPLOY_PATH"
    echo -e "📂 Копія: ${BLUE}$DEPLOY_PATH${NC}"
    
    # Створення symlink на останню збірку
    LATEST_LINK="$DEPLOY_DIR/epicservice-${BUILD_TYPE}-latest.${OUTPUT_EXT}"
    ln -sf "$DEPLOY_FILENAME" "$LATEST_LINK"
    echo -e "🔗 Symlink: ${BLUE}$LATEST_LINK${NC} → ${DEPLOY_FILENAME}"
    
    echo -e "\n${YELLOW}Наступні кроки:${NC}"
    if [[ $build_choice == 1 ]] || [[ $build_choice == 2 ]]; then
        echo -e "  ${BLUE}adb install -r \"$DEPLOY_PATH\"${NC}"
        echo -e "  або:"
        echo -e "  ${BLUE}adb install -r \"$LATEST_LINK\"${NC}"
    else
        echo "  - Завантаж AAB в Google Play Console"
        echo "  - Файл: $DEPLOY_PATH"
    fi
    
    # Видалення backup після успішної збірки
    rm -f "$BUILD_GRADLE.bak"
    
    # Commit оновленої версії (опціонально)
    echo ""
    read -p "Закомітити нову версію в Git? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$PROJECT_ROOT"
        git add "$BUILD_GRADLE"
        git commit -m "chore: bump version to $VERSION_NAME" || echo "Нічого для коміту"
        git push origin main
        echo -e "${GREEN}✓ Версія закомічена${NC}"
    fi
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Збірка не вдалась!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Відновлення backup
    if [ -f "$BUILD_GRADLE.bak" ]; then
        echo -e "${YELLOW}⚠ Відновлюємо build.gradle з backup...${NC}"
        mv "$BUILD_GRADLE.bak" "$BUILD_GRADLE"
        echo -e "${GREEN}✓ Файл відновлено${NC}"
    fi
    exit 1
fi

echo -e "\n${GREEN}🎉 Готово!${NC}\n"
