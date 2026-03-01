#!/usr/bin/env python3
"""
リツイーター取得 (プロフィール付き)
Selenium + 手動ログイン
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
    print("=" * 60)
    print("リツイーター取得 (プロフィール付き)")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人"
    # 専用プロファイル
    profile_dir = os.path.join(os.path.dirname(__file__), "x_chrome_profile")
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

    print("\nChromeを起動中...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    retweeters = {}

    try:
        # ログイン確認
        print("X.com を開いています...")
        driver.get("https://x.com/home")
        time.sleep(3)

        if "login" in driver.current_url or "i/flow" in driver.current_url:
            print("\n" + "=" * 60)
            print("【手動ログインが必要です】")
            print("ブラウザでログインしてください。")
            print("完了したらEnterを押してください。")
            print("=" * 60)
            input("\n>>> Enter...")
            time.sleep(2)
        else:
            print("ログイン済みです。")

        # リツイーターページ
        retweets_url = url if "/retweets" in url else url.rstrip("/") + "/retweets"
        print(f"\nリツイーターページを開いています...")
        driver.get(retweets_url)
        time.sleep(4)

        print("スクロールしてリツイーターを取得中...\n")

        last_count = 0
        no_change_count = 0

        while len(retweeters) < max_users:
            # UserCell を取得
            user_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

            for cell in user_cells:
                try:
                    # ユーザー名を取得
                    username = None
                    links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if "/status/" not in href:
                            match = re.search(r"x\.com/([^/?\s]+)$", href)
                            if match:
                                uname = match.group(1)
                                skip = ["home", "explore", "notifications", "messages", "i", "settings"]
                                if uname and uname.lower() not in skip:
                                    username = uname
                                    break

                    if not username or username in retweeters:
                        continue

                    # 表示名を取得
                    display_name = username
                    try:
                        # 最初の太字テキストが表示名
                        name_spans = cell.find_elements(By.CSS_SELECTOR, 'a span')
                        for span in name_spans:
                            text = span.text.strip()
                            if text and not text.startswith("@"):
                                display_name = text
                                break
                    except:
                        pass

                    # プロフィール（自己紹介）を取得
                    bio = ""
                    try:
                        # UserCellの中でリンク以外のテキスト部分を探す
                        all_text = cell.text
                        lines = all_text.split("\n")
                        # 名前と@username以外の行がプロフィール
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith("@") and line != display_name:
                                # フォローボタンなどを除外
                                if line not in ["フォロー", "フォロー中", "Follow", "Following"]:
                                    bio = line
                                    break
                    except:
                        pass

                    retweeters[username] = {
                        "username": username,
                        "name": display_name,
                        "bio": bio
                    }

                    # 表示
                    print(f"{len(retweeters)}. @{username}")
                    print(f"   名前: {display_name}")
                    if bio:
                        print(f"   プロフ: {bio[:50]}{'...' if len(bio) > 50 else ''}")
                    print()

                except Exception as e:
                    continue

            # 変化チェック
            if len(retweeters) == last_count:
                no_change_count += 1
                if no_change_count >= 10:
                    print("これ以上のユーザーは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(retweeters)

            # スクロール
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.2)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(retweeters.values())


def main():
    url = input("ツイートURL (デフォルト: https://x.com/ampxtak/status/2004877245396201605): ").strip()
    if not url:
        url = "https://x.com/ampxtak/status/2004877245396201605"

    max_users = input("最大取得数 (デフォルト: 500): ").strip()
    max_users = int(max_users) if max_users else 500

    retweeters = scrape_retweeters(url, max_users)

    print(f"\n取得完了: {len(retweeters)}人")

    if retweeters:
        match = re.search(r"/status/(\d+)", url)
        tweet_id = match.group(1) if match else "unknown"

        # TXT保存
        txt_file = f"retweeters_{tweet_id}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for u in retweeters:
                f.write(f"@{u['username']}\t{u['name']}\t{u['bio']}\n")
        print(f"保存: {txt_file}")

        # JSON保存
        json_file = f"retweeters_{tweet_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(retweeters, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_file}")


if __name__ == "__main__":
    main()
