#!/bin/bash
# ============================================
#  X Campaign Picker — macOS 初回起動ヘルパー
#  ダブルクリックで実行してください
# ============================================

APP_NAME="X Campaign Picker.app"
APPS_DIR="/Applications"
APP_PATH="$APPS_DIR/$APP_NAME"

# アプリが /Applications にあるか確認
if [ ! -d "$APP_PATH" ]; then
    # 同じフォルダ内を探す
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    APP_PATH="$(find "$SCRIPT_DIR" -maxdepth 1 -name "$APP_NAME" -print -quit 2>/dev/null)"
fi

if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
    echo ""
    echo "❌ $APP_NAME が見つかりませんでした。"
    echo "   先にアプリを /Applications フォルダにドラッグしてください。"
    echo ""
    read -p "Enterキーで閉じます..."
    exit 1
fi

echo ""
echo "🔧 セキュリティ属性を解除しています..."
echo "   対象: $APP_PATH"
echo ""

xattr -cr "$APP_PATH"

echo "✅ 完了！ これでセキュリティ警告なしで起動できます。"
echo ""
echo "   アプリを開いてください: $APP_NAME"
echo ""
read -p "Enterキーで閉じます..."
