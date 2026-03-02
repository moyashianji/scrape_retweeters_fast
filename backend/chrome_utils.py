"""Chrome WebDriver の共通セットアップ"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def get_base_dir():
    """ベースディレクトリを取得（PyInstaller対応）

    パッケージ版: ユーザーの書き込み可能ディレクトリを返す
      - Windows: %APPDATA%/XCampaignPicker
      - macOS:   ~/Library/Application Support/XCampaignPicker
    開発版: プロジェクトルートを返す
    """
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            base = os.path.join(os.path.expanduser('~'),
                                'Library', 'Application Support', 'XCampaignPicker')
        elif sys.platform == 'win32':
            base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                                'XCampaignPicker')
        else:
            base = os.path.join(os.path.expanduser('~'), '.xcampaignpicker')
        os.makedirs(base, exist_ok=True)
        return base
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_driver():
    """設定済み Chrome WebDriver を生成"""
    base = get_base_dir()
    profile_dir = os.path.join(base, "x_chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def wait_for_login(driver, timeout=300):
    """ログイン待ち（input()の代わりにURL pollingで自動検出）"""
    import time
    if "login" not in driver.current_url and "i/flow" not in driver.current_url:
        print("ログイン済みです。")
        return True

    print("\n" + "=" * 60)
    print("【手動ログインが必要です】")
    print("ブラウザでXにログインしてください。")
    print("自動で検出します。")
    print("=" * 60)

    waited = 0
    while ("login" in driver.current_url or "i/flow" in driver.current_url) and waited < timeout:
        time.sleep(3)
        waited += 3
        if waited % 15 == 0:
            print(f"ログイン待機中... ({waited}秒)")

    if waited >= timeout:
        raise TimeoutError("ログインのタイムアウト（5分）")

    print("ログインを検出しました！")
    time.sleep(2)
    return True
