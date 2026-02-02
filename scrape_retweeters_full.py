#!/usr/bin/env python3
"""
リツイーター取得 (全情報・絵文字対応)
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
    print("リツイーター取得 (全情報・絵文字対応)")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人")

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
                    user_data = extract_user_data(cell)

                    if not user_data or not user_data.get("username"):
                        continue

                    username = user_data["username"]
                    if username in retweeters:
                        continue

                    retweeters[username] = user_data

                    # 表示
                    print(f"{len(retweeters)}. @{username}")
                    print(f"   名前: {user_data.get('name', '')}")
                    if user_data.get("verified"):
                        print(f"   認証: ✓")
                    if user_data.get("bio"):
                        bio_preview = user_data["bio"].replace("\n", " ")[:60]
                        if len(user_data["bio"]) > 60:
                            bio_preview += "..."
                        print(f"   プロフ: {bio_preview}")
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


def extract_user_data(cell):
    """UserCellから全情報を抽出"""
    data = {
        "username": None,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
        "raw_text": None
    }

    try:
        # セル全体のテキストを取得（絵文字・メンション・ハッシュタグ含む）
        raw_text = cell.text
        data["raw_text"] = raw_text

        # テキストを行で分割
        lines = raw_text.split("\n")

        # パース
        # 構造: [表示名] [@username] [Follow/フォロー] [プロフィール...]

        display_name = None
        username = None
        bio_lines = []
        found_username = False
        found_follow_button = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # @username の行を検出（単独で@から始まりスペースなし）
            if re.match(r"^@[A-Za-z0-9_]+$", line_stripped):
                if not found_username:
                    # これがこのユーザーの@username
                    username = line_stripped[1:]  # @を除去
                    found_username = True
                    continue
                else:
                    # プロフィール内のメンション（単独行）
                    bio_lines.append(line_stripped)
                    continue

            # 表示名（最初の非@行）
            if display_name is None and not line_stripped.startswith("@"):
                display_name = line_stripped
                continue

            # Follow/フォローボタン
            if line_stripped in ["Follow", "フォロー", "Following", "フォロー中", "Follows you", "フォローされています"]:
                found_follow_button = True
                continue

            # フォローボタン以降がプロフィール
            if found_follow_button:
                bio_lines.append(line_stripped)

        data["name"] = display_name
        data["username"] = username

        # プロフィールを結合（改行を保持）
        if bio_lines:
            data["bio"] = "\n".join(bio_lines)

        # ユーザー名がまだ取れてない場合、リンクから取得
        if not data["username"]:
            links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
            for link in links:
                href = link.get_attribute("href") or ""
                if "/status/" not in href and "x.com/" in href:
                    match = re.search(r"x\.com/([A-Za-z0-9_]+)$", href)
                    if match:
                        uname = match.group(1)
                        skip = ["home", "explore", "notifications", "messages", "i", "settings", "search"]
                        if uname.lower() not in skip:
                            data["username"] = uname
                            break

        # 認証バッジの確認
        try:
            # 複数のパターンをチェック
            verified = False
            badge_selectors = [
                '[data-testid="icon-verified"]',
                'svg[aria-label*="認証"]',
                'svg[aria-label*="Verified"]',
                'svg[aria-label*="verified"]'
            ]
            for selector in badge_selectors:
                badges = cell.find_elements(By.CSS_SELECTOR, selector)
                if badges:
                    verified = True
                    break
            data["verified"] = verified
        except:
            pass

        # プロフィール画像URL
        try:
            img = cell.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

    except Exception as e:
        pass

    return data


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

        # TXT保存（主要情報のみ）
        txt_file = f"retweeters_{tweet_id}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for u in retweeters:
                bio = (u.get("bio") or "").replace("\n", " ").replace("\t", " ")
                f.write(f"@{u['username']}\t{u.get('name', '')}\t{bio}\n")
        print(f"保存: {txt_file}")

        # JSON保存（全情報）
        json_file = f"retweeters_{tweet_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(retweeters, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_file}")

        # 統計表示
        verified_count = sum(1 for u in retweeters if u.get("verified"))
        with_bio = sum(1 for u in retweeters if u.get("bio"))
        print(f"\n--- 統計 ---")
        print(f"総ユーザー数: {len(retweeters)}")
        print(f"認証済み: {verified_count}")
        print(f"プロフあり: {with_bio}")


if __name__ == "__main__":
    main()
