#!/usr/bin/env python3
"""
リツイーター取得 (ホバーカードから全情報取得)
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def scrape_retweeters(url, max_users=500):
    print("=" * 60)
    print("リツイーター取得 (ホバーカード版)")
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

    actions = ActionChains(driver)
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

        print("ホバーして詳細情報を取得中...\n")

        processed_usernames = set()
        last_count = 0
        no_change_count = 0

        while len(retweeters) < max_users:
            # UserCell を取得
            user_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

            for cell in user_cells:
                if len(retweeters) >= max_users:
                    break

                try:
                    # まずユーザー名を取得
                    username = None
                    links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if "/status/" not in href and "x.com/" in href:
                            match = re.search(r"x\.com/([A-Za-z0-9_]+)$", href)
                            if match:
                                uname = match.group(1)
                                skip = ["home", "explore", "notifications", "messages", "i", "settings", "search"]
                                if uname.lower() not in skip:
                                    username = uname
                                    break

                    if not username or username in processed_usernames:
                        continue

                    processed_usernames.add(username)

                    # プロフィール画像にホバー
                    try:
                        avatar = cell.find_element(By.CSS_SELECTOR, '[data-testid="UserAvatar-Container-unknown"] a, [data-testid^="UserAvatar"] a, img[src*="profile_images"]')

                        # 要素が見えるようにスクロール
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", avatar)
                        time.sleep(0.3)

                        # ホバー
                        actions.move_to_element(avatar).perform()
                        time.sleep(1.2)  # ホバーカードが表示されるまで待つ

                    except Exception as e:
                        # アバターが見つからない場合はセルの情報だけ使う
                        user_data = extract_from_cell(cell, username)
                        retweeters[username] = user_data
                        print_user(len(retweeters), user_data)
                        continue

                    # ホバーカードを探す
                    try:
                        hover_card = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="HoverCard"]'))
                        )
                        user_data = extract_from_hovercard(hover_card, username)
                    except:
                        # ホバーカードが出ない場合はセルから取得
                        user_data = extract_from_cell(cell, username)

                    retweeters[username] = user_data
                    print_user(len(retweeters), user_data)

                    # ホバーカードを閉じる（マウスを移動）
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        actions.move_to_element_with_offset(body, 0, 0).perform()
                        time.sleep(0.3)
                    except:
                        pass

                except Exception as e:
                    continue

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
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.8)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(retweeters.values())


def get_text_with_emoji(element):
    """要素からテキストを取得（絵文字imgのalt属性も含む）"""
    from selenium.webdriver.common.by import By

    # JavaScriptで全テキスト（絵文字含む）を取得
    script = """
    function getTextWithEmoji(element) {
        let result = '';
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
            null,
            false
        );

        let node;
        while (node = walker.nextNode()) {
            if (node.nodeType === Node.TEXT_NODE) {
                result += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName === 'IMG' && node.alt) {
                    // 絵文字画像のalt属性を取得
                    result += node.alt;
                } else if (node.tagName === 'BR') {
                    result += '\\n';
                }
            }
        }
        return result;
    }
    return getTextWithEmoji(arguments[0]);
    """
    try:
        return element.parent.execute_script(script, element)
    except:
        return element.text


def extract_from_hovercard(hover_card, username):
    """ホバーカードから情報を抽出"""
    data = {
        "username": username,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
        "location": None,
        "url": None,
        "followers_count": None,
        "following_count": None,
        "raw_text": None
    }

    try:
        # 絵文字を含むテキストを取得
        raw_text = get_text_with_emoji(hover_card)
        data["raw_text"] = raw_text

        lines = raw_text.split("\n")

        # 表示名（最初の行で@で始まらない）
        for line in lines:
            if line.strip() and not line.strip().startswith("@"):
                data["name"] = line.strip()
                break

        # フォロワー数・フォロー中数を探す
        for line in lines:
            # "123 Following" "456 Followers" のパターン
            following_match = re.search(r"([\d,\.]+[KMB]?)\s*(Following|フォロー中)", line)
            if following_match:
                data["following_count"] = following_match.group(1)

            followers_match = re.search(r"([\d,\.]+[KMB]?)\s*(Followers|フォロワー)", line)
            if followers_match:
                data["followers_count"] = followers_match.group(1)

        # プロフィール（自己紹介）
        # 名前、@username、フォロー/フォロワー数、ボタン以外の行
        skip_patterns = [
            r"^@[A-Za-z0-9_]+$",  # @username単独
            r"^\d+[\d,\.]*[KMB]?\s*(Following|Followers|フォロー|フォロワー)",  # フォロー数
            r"^(Follow|フォロー|Following|フォロー中)$",  # ボタン
            r"^(Follows you|フォローされています)$",
        ]

        bio_lines = []
        found_username = False
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 表示名をスキップ
            if line_stripped == data["name"]:
                continue

            # @username行をスキップ（ただしこれ以降は収集）
            if re.match(r"^@[A-Za-z0-9_]+$", line_stripped):
                found_username = True
                continue

            # パターンにマッチしたらスキップ
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue

            # @username以降の行をbioに追加
            if found_username:
                bio_lines.append(line_stripped)

        if bio_lines:
            data["bio"] = "\n".join(bio_lines)

        # 認証バッジ
        try:
            badges = hover_card.find_elements(By.CSS_SELECTOR, '[data-testid="icon-verified"], svg[aria-label*="Verified"], svg[aria-label*="認証"]')
            if badges:
                data["verified"] = True
        except:
            pass

        # プロフィール画像
        try:
            img = hover_card.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

        # 場所（locationアイコンの近く）
        try:
            location_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserLocation"]')
            data["location"] = get_text_with_emoji(location_elem).strip()
        except:
            pass

        # URL
        try:
            url_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserUrl"] a')
            data["url"] = url_elem.get_attribute("href")
        except:
            pass

        # 名前を絵文字込みで再取得
        try:
            name_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserName"] span span')
            name_with_emoji = get_text_with_emoji(name_elem)
            if name_with_emoji:
                data["name"] = name_with_emoji.strip()
        except:
            pass

        # bioを絵文字込みで再取得
        try:
            bio_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            bio_with_emoji = get_text_with_emoji(bio_elem)
            if bio_with_emoji:
                data["bio"] = bio_with_emoji.strip()
        except:
            pass

    except Exception as e:
        pass

    return data


def extract_from_cell(cell, username):
    """UserCellから情報を抽出（フォールバック）"""
    data = {
        "username": username,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
        "location": None,
        "url": None,
        "followers_count": None,
        "following_count": None,
        "raw_text": None
    }

    try:
        # 絵文字を含むテキストを取得
        raw_text = get_text_with_emoji(cell)
        data["raw_text"] = raw_text

        lines = raw_text.split("\n")

        # 表示名
        for line in lines:
            if line.strip() and not line.strip().startswith("@"):
                data["name"] = line.strip()
                break

        # プロフィール画像
        try:
            img = cell.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

        # 認証バッジ
        try:
            badges = cell.find_elements(By.CSS_SELECTOR, '[data-testid="icon-verified"], svg[aria-label*="Verified"]')
            if badges:
                data["verified"] = True
        except:
            pass

    except:
        pass

    return data


def print_user(num, user_data):
    """ユーザー情報を表示"""
    print(f"{num}. @{user_data.get('username', '?')}")
    print(f"   名前: {user_data.get('name', '')}")
    if user_data.get("verified"):
        print(f"   認証: ✓")
    if user_data.get("followers_count"):
        print(f"   フォロワー: {user_data['followers_count']}")
    if user_data.get("following_count"):
        print(f"   フォロー中: {user_data['following_count']}")
    if user_data.get("bio"):
        bio_preview = user_data["bio"].replace("\n", " ")[:50]
        if len(user_data["bio"]) > 50:
            bio_preview += "..."
        print(f"   プロフ: {bio_preview}")
    if user_data.get("location"):
        print(f"   場所: {user_data['location']}")
    if user_data.get("url"):
        print(f"   URL: {user_data['url']}")
    print()


def main():
    url = input("ツイートURL (デフォルト: https://x.com/ampxtak/status/2004877245396201605): ").strip()
    if not url:
        url = "https://x.com/ampxtak/status/2004877245396201605"

    max_users = input("最大取得数 (デフォルト: 100): ").strip()
    max_users = int(max_users) if max_users else 100

    retweeters = scrape_retweeters(url, max_users)

    print(f"\n取得完了: {len(retweeters)}人")

    if retweeters:
        match = re.search(r"/status/(\d+)", url)
        tweet_id = match.group(1) if match else "unknown"

        # TXT保存
        txt_file = f"retweeters_{tweet_id}_full.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for u in retweeters:
                bio = (u.get("bio") or "").replace("\n", " ").replace("\t", " ")
                f.write(f"@{u['username']}\t{u.get('name', '')}\t{u.get('followers_count', '')}\t{u.get('following_count', '')}\t{bio}\n")
        print(f"保存: {txt_file}")

        # JSON保存
        json_file = f"retweeters_{tweet_id}_full.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(retweeters, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_file}")

        # 統計
        verified_count = sum(1 for u in retweeters if u.get("verified"))
        with_bio = sum(1 for u in retweeters if u.get("bio"))
        with_followers = sum(1 for u in retweeters if u.get("followers_count"))
        print(f"\n--- 統計 ---")
        print(f"総ユーザー数: {len(retweeters)}")
        print(f"認証済み: {verified_count}")
        print(f"プロフあり: {with_bio}")
        print(f"フォロワー数あり: {with_followers}")


if __name__ == "__main__":
    main()
