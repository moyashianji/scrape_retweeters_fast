#!/usr/bin/env python3
"""
Selenium でリツイーターページをスクロールして全員取得
新規プロファイルを使用（手動ログイン）
"""

import json
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def scrape_retweeters(url, max_users=500):
    """
    リツイーターページからユーザーを取得
    """
    print("=" * 60)
    print("リツイーター取得ツール (Selenium)")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人")

    # 専用のプロファイルディレクトリ
    profile_dir = os.path.join(os.path.dirname(__file__), "chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)

    # Chrome オプション設定
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("\nChromeを起動中...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 自動化検出を回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    retweeters = {}

    try:
        # まずX.comのトップページを開く
        print("X.com を開いています...")
        driver.get("https://x.com")
        time.sleep(3)

        # ログイン確認
        print("\n" + "=" * 60)
        print("【手動操作が必要です】")
        print("=" * 60)
        print("1. ブラウザでX.comにログインしてください")
        print("2. ログイン完了したら、このコンソールに戻って")
        print("3. Enterキーを押してください")
        print("=" * 60)
        input("\nログイン完了後、Enterを押してください...")

        # リツイーターページに移動
        print(f"\nリツイーターページを開いています...")
        driver.get(url)
        time.sleep(5)

        print("スクロールしてリツイーターを取得中...\n")

        last_count = 0
        no_change_count = 0

        while len(retweeters) < max_users:
            # ユーザーセルを取得
            try:
                user_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

                for cell in user_cells:
                    try:
                        # ユーザー名リンクを探す
                        links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                        for link in links:
                            href = link.get_attribute("href")
                            if href and "/status/" not in href:
                                # URLからユーザー名を抽出
                                match = re.search(r"x\.com/([^/?\s]+)$", href)
                                if match:
                                    username = match.group(1)
                                    if username and username not in retweeters and username not in ["home", "explore", "notifications", "messages", "i"]:
                                        # 表示名を取得
                                        try:
                                            spans = cell.find_elements(By.CSS_SELECTOR, 'span')
                                            display_name = ""
                                            for span in spans:
                                                text = span.text.strip()
                                                if text and not text.startswith("@") and len(text) > 0:
                                                    display_name = text
                                                    break
                                        except:
                                            display_name = username

                                        retweeters[username] = {
                                            "username": username,
                                            "name": display_name or username
                                        }
                                        print(f"  {len(retweeters)}. @{username} ({display_name or username})")
                                        break
                    except:
                        continue

            except Exception as e:
                print(f"要素取得エラー: {e}")

            # 変化チェック
            if len(retweeters) == last_count:
                no_change_count += 1
                if no_change_count >= 10:
                    print("\nこれ以上のユーザーは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(retweeters)

            # スクロール
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

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
    # URL入力
    url = input("リツイーターページURL\n(デフォルト: https://x.com/ampxtak/status/2004877245396201605/retweets): ").strip()
    if not url:
        url = "https://x.com/ampxtak/status/2004877245396201605/retweets"

    # 最大取得数
    max_users = input("最大取得数 (デフォルト: 500): ").strip()
    max_users = int(max_users) if max_users else 500

    # 取得実行
    retweeters = scrape_retweeters(url, max_users)

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
