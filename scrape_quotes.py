#!/usr/bin/env python3
"""
引用ツイート取得 (ホバーカードでフォロワー数等も取得)
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


def get_text_with_emoji(driver, element):
    """要素からテキストを取得（絵文字imgのalt属性も含む）"""
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
        return driver.execute_script(script, element)
    except:
        return element.text


def dismiss_hovercard(driver, actions):
    """ホバーカードを閉じる"""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element_with_offset(body, 0, 0).perform()
        time.sleep(0.3)
    except:
        pass


def extract_from_hovercard(driver, hover_card, username):
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
    }

    try:
        # 名前を絵文字込みで取得
        try:
            name_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserName"] span span')
            data["name"] = get_text_with_emoji(driver, name_elem).strip()
        except:
            pass

        # bioを絵文字込みで取得
        try:
            bio_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            data["bio"] = get_text_with_emoji(driver, bio_elem).strip()
        except:
            pass

        # フォロワー数・フォロー中数
        raw_text = get_text_with_emoji(driver, hover_card)
        for line in raw_text.split("\n"):
            following_match = re.search(r"([\d,\.]+[KMB]?)\s*(Following|フォロー中)", line)
            if following_match:
                data["following_count"] = following_match.group(1)

            followers_match = re.search(r"([\d,\.]+[KMB]?)\s*(Followers?|フォロワー)", line)
            if followers_match:
                data["followers_count"] = followers_match.group(1)

        # 認証バッジ
        try:
            badges = hover_card.find_elements(By.CSS_SELECTOR,
                '[data-testid="icon-verified"], svg[aria-label*="Verified"], svg[aria-label*="認証"]')
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

        # 場所
        try:
            location_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserLocation"]')
            data["location"] = get_text_with_emoji(driver, location_elem).strip()
        except:
            pass

        # URL
        try:
            url_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserUrl"] a')
            data["url"] = url_elem.get_attribute("href")
        except:
            pass

    except:
        pass

    return data


def extract_quote_from_article(driver, article):
    """引用ツイートのarticle要素からユーザー名と引用テキストを抽出"""
    username = None
    name = None
    quote_text = None

    # ユーザー名をリンクから取得
    try:
        links = article.find_elements(By.CSS_SELECTOR, 'a[href^="/"][role="link"]')
        for link in links:
            href = link.get_attribute("href") or ""
            if "/status/" not in href and "x.com/" in href:
                match = re.search(r"x\.com/([A-Za-z0-9_]+)$", href)
                if match:
                    uname = match.group(1)
                    skip = ["home", "explore", "notifications", "messages",
                            "i", "settings", "search", "compose"]
                    if uname.lower() not in skip:
                        username = uname
                        break
    except:
        pass

    # 表示名を取得
    try:
        name_elem = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] span span')
        name = get_text_with_emoji(driver, name_elem).strip()
    except:
        pass

    # 引用ツイートのテキストを取得
    try:
        tweet_text_elem = article.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
        quote_text = get_text_with_emoji(driver, tweet_text_elem).strip()
    except:
        pass

    return username, name, quote_text


def hover_and_get_profile(driver, actions, article, username):
    """記事内のアバターにホバーしてプロフィール情報を取得"""
    try:
        avatar = article.find_element(By.CSS_SELECTOR,
            '[data-testid^="UserAvatar"] a, img[src*="profile_images"]')

        # ホバー前のスクロール位置を保存
        scroll_before = driver.execute_script("return window.pageYOffset;")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", avatar)
        time.sleep(0.3)

        actions.move_to_element(avatar).perform()
        time.sleep(1.2)

        hover_card = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="HoverCard"]'))
        )
        data = extract_from_hovercard(driver, hover_card, username)
        dismiss_hovercard(driver, actions)

        # スクロール位置を復帰（巻き戻りを防止: 前より進んだ位置を維持）
        scroll_after = driver.execute_script("return window.pageYOffset;")
        restore_to = max(scroll_before, scroll_after)
        driver.execute_script(f"window.scrollTo(0, {restore_to});")

        return data

    except:
        dismiss_hovercard(driver, actions)
        return None


def print_user(num, user_data):
    """ユーザー情報を表示"""
    print(f"{num}. @{user_data.get('username', '?')}")
    if user_data.get("name"):
        print(f"   名前: {user_data['name']}")
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
    if user_data.get("quote_text"):
        qt_preview = user_data["quote_text"].replace("\n", " ")[:60]
        if len(user_data["quote_text"]) > 60:
            qt_preview += "..."
        print(f"   引用: {qt_preview}")
    if user_data.get("location"):
        print(f"   場所: {user_data['location']}")
    if user_data.get("url"):
        print(f"   URL: {user_data['url']}")
    print()


def scrape_quotes(url, max_users=500):
    print("=" * 60)
    print("引用ツイート取得 (ホバーカード版)")
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
    quotes = {}

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

        # 引用ツイートページ
        quotes_url = url if "/quotes" in url else url.rstrip("/") + "/quotes"
        print(f"\n引用ツイートページを開いています...")
        print(f"  {quotes_url}")
        driver.get(quotes_url)
        time.sleep(4)

        print("スクロール & ホバーで引用ツイートを取得中...\n")

        last_count = 0
        no_change_count = 0
        max_scroll_pos = 0

        while len(quotes) < max_users:
            # ツイート article を取得
            articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

            for article in articles:
                if len(quotes) >= max_users:
                    break

                try:
                    username, name, quote_text = extract_quote_from_article(driver, article)

                    if not username or username in quotes:
                        continue

                    # ホバーカードでプロフィール取得
                    profile_data = hover_and_get_profile(driver, actions, article, username)

                    if profile_data:
                        user_data = profile_data
                    else:
                        # ホバー失敗時のフォールバック
                        user_data = {
                            "username": username,
                            "name": name,
                            "bio": None,
                            "verified": False,
                            "profile_image_url": None,
                            "location": None,
                            "url": None,
                            "followers_count": None,
                            "following_count": None,
                        }

                    # 引用テキストを追加
                    user_data["quote_text"] = quote_text

                    # 表示名がホバーで取れなかった場合、article から補完
                    if not user_data.get("name") and name:
                        user_data["name"] = name

                    quotes[username] = user_data
                    print_user(len(quotes), user_data)

                except Exception:
                    continue

            # 変化チェック
            if len(quotes) == last_count:
                no_change_count += 1
                if no_change_count >= 15:
                    print("これ以上の引用ツイートは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(quotes)

            # スクロール: 最後の article の下端までスクロール
            if articles:
                try:
                    last_article = articles[-1]
                    bottom = driver.execute_script(
                        "var r = arguments[0].getBoundingClientRect();"
                        "return window.pageYOffset + r.bottom;",
                        last_article
                    )
                    # 常に前より先に進む
                    target = max(bottom, max_scroll_pos + 800)
                    max_scroll_pos = target
                    driver.execute_script(f"window.scrollTo(0, {target});")
                except:
                    max_scroll_pos += 800
                    driver.execute_script(f"window.scrollTo(0, {max_scroll_pos});")
            else:
                max_scroll_pos += 800
                driver.execute_script(f"window.scrollTo(0, {max_scroll_pos});")

            # コンテンツ読み込み待ち（変化がないときは長めに待つ）
            if no_change_count >= 3:
                time.sleep(2.5)
            else:
                time.sleep(1.2)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(quotes.values())


def main():
    url = input("ツイートURL (またはquotesページURL): ").strip()
    if not url:
        print("URLを入力してください。")
        return

    max_users = input("最大取得数 (デフォルト: 500): ").strip()
    max_users = int(max_users) if max_users else 500

    results = scrape_quotes(url, max_users)

    print(f"\n取得完了: {len(results)}人")

    if results:
        match = re.search(r"/status/(\d+)", url)
        tweet_id = match.group(1) if match else "unknown"

        # TXT保存
        txt_file = f"quotes_{tweet_id}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for u in results:
                bio = (u.get("bio") or "").replace("\n", " ").replace("\t", " ")
                qt = (u.get("quote_text") or "").replace("\n", " ").replace("\t", " ")
                f.write(f"@{u['username']}\t{u.get('name', '')}\t"
                        f"{u.get('followers_count', '')}\t{u.get('following_count', '')}\t"
                        f"{bio}\t{qt}\n")
        print(f"保存: {txt_file}")

        # JSON保存
        json_file = f"quotes_{tweet_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_file}")

        # 統計
        verified_count = sum(1 for u in results if u.get("verified"))
        with_bio = sum(1 for u in results if u.get("bio"))
        with_followers = sum(1 for u in results if u.get("followers_count"))
        with_quote = sum(1 for u in results if u.get("quote_text"))
        print(f"\n--- 統計 ---")
        print(f"総ユーザー数: {len(results)}")
        print(f"認証済み: {verified_count}")
        print(f"プロフあり: {with_bio}")
        print(f"フォロワー数あり: {with_followers}")
        print(f"引用テキストあり: {with_quote}")


if __name__ == "__main__":
    main()
