#!/usr/bin/env python3
"""
Selenium でリツイーターページをスクロールして全員取得
ブラウザの既存プロファイル（ログイン済み）を使用
"""

import json
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def get_chrome_profile_path():
    """Chrome のデフォルトプロファイルパスを取得"""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_app_data, "Google", "Chrome", "User Data")


def get_edge_profile_path():
    """Edge のデフォルトプロファイルパスを取得"""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_app_data, "Microsoft", "Edge", "User Data")


def scrape_retweeters(url, max_users=500, browser="chrome"):
    """
    リツイーターページからユーザーを取得

    Parameters:
    -----------
    url : str
        リツイーターページのURL (例: https://x.com/user/status/123/retweets)
    max_users : int
        取得する最大ユーザー数
    browser : str
        使用するブラウザ ("chrome" or "edge")
    """
    print("=" * 60)
    print("リツイーター取得ツール (Selenium)")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人")
    print(f"ブラウザ: {browser}")

    # Chrome オプション設定
    options = Options()

    if browser == "edge":
        from selenium.webdriver.edge.service import Service as EdgeService
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        options = EdgeOptions()
        profile_path = get_edge_profile_path()
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--profile-directory=Default")
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    else:
        profile_path = get_chrome_profile_path()
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--profile-directory=Default")
        # ヘッドレスモードは使わない（ログイン状態を維持するため）
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    # 自動化検出を回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    retweeters = {}
    last_count = 0
    no_change_count = 0

    try:
        print("\nページを読み込み中...")
        driver.get(url)

        # ページ読み込み待機
        time.sleep(5)

        print("スクロールしてリツイーターを取得中...\n")

        while len(retweeters) < max_users:
            # ユーザーセルを取得
            try:
                # ユーザーリンクを探す
                user_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

                for cell in user_cells:
                    try:
                        # ユーザー名リンクを探す
                        links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                        for link in links:
                            href = link.get_attribute("href")
                            if href and "/status/" not in href and href.count("/") == 3:
                                username = href.split("/")[-1]
                                if username and username not in retweeters:
                                    # 表示名を取得
                                    try:
                                        name_elem = cell.find_element(By.CSS_SELECTOR, '[dir="ltr"] span')
                                        display_name = name_elem.text
                                    except:
                                        display_name = username

                                    retweeters[username] = {
                                        "username": username,
                                        "name": display_name
                                    }
                                    print(f"  {len(retweeters)}. @{username} ({display_name})")
                                    break
                    except Exception as e:
                        continue

            except Exception as e:
                print(f"要素取得エラー: {e}")

            # 変化チェック
            if len(retweeters) == last_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print("\nこれ以上のユーザーは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(retweeters)

            # スクロール
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)

            # 最大数チェック
            if len(retweeters) >= max_users:
                print(f"\n最大取得数 {max_users} に達しました。")
                break

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(retweeters.values())


def main():
    print("\n【重要】")
    print("1. 先にブラウザ(Chrome/Edge)で X.com にログインしてください")
    print("2. ブラウザを完全に閉じてから、このスクリプトを実行してください")
    print("   (同じプロファイルを2つのプロセスで使えないため)\n")

    # URL入力
    url = input("リツイーターページURL (例: https://x.com/user/status/123/retweets): ").strip()
    if not url:
        url = "https://x.com/ampxtak/status/2004877245396201605/retweets"

    # 最大取得数
    max_users = input("最大取得数 (デフォルト: 500): ").strip()
    max_users = int(max_users) if max_users else 500

    # ブラウザ選択
    browser = input("ブラウザ (chrome/edge, デフォルト: chrome): ").strip().lower()
    if browser not in ["chrome", "edge"]:
        browser = "chrome"

    # 取得実行
    retweeters = scrape_retweeters(url, max_users, browser)

    print(f"\n取得完了: {len(retweeters)}人")

    # 保存
    if retweeters:
        # URLからツイートIDを抽出
        match = re.search(r"/status/(\d+)", url)
        tweet_id = match.group(1) if match else "unknown"

        filename = f"retweeters_{tweet_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for u in retweeters:
                f.write(f"@{u['username']}\t{u['name']}\n")
        print(f"保存: {filename}")

        json_filename = f"retweeters_{tweet_id}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(retweeters, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_filename}")


if __name__ == "__main__":
    main()
