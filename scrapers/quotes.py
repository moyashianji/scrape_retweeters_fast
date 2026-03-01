"""引用ツイート取得（GraphQL APIでフォロワー数等も取得）"""

import re
import time
from selenium.webdriver.common.by import By
from backend.chrome_utils import create_driver, wait_for_login
from scrapers.common import (
    get_text_with_emoji, extract_username_from_links,
    inject_fetch_interceptor, inject_interceptor_cdp,
    extract_dm_status_from_responses,
    fetch_user_profiles, apply_dm_status
)


def extract_quote_from_article(driver, article):
    """引用ツイートのarticle要素からユーザー名と引用テキストを抽出"""
    username = None
    name = None
    quote_text = None

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

    try:
        name_elem = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] span span')
        name = get_text_with_emoji(driver, name_elem).strip()
    except:
        pass

    try:
        tweet_text_elem = article.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
        quote_text = get_text_with_emoji(driver, tweet_text_elem).strip()
    except:
        pass

    return username, name, quote_text


def scrape_quotes(url, max_users=500):
    """引用ツイートを取得"""
    print("=" * 60)
    print("引用ツイート取得")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人")

    print("\nChromeを起動中...")
    driver = create_driver()
    quotes = {}

    try:
        print("X.com を開いています...")
        driver.get("https://x.com/home")
        time.sleep(3)
        wait_for_login(driver)

        # CDP経由でインターセプター注入（ページ遷移後も自動で有効）
        inject_interceptor_cdp(driver)

        quotes_url = url if "/quotes" in url else url.rstrip("/") + "/quotes"
        print(f"\n引用ツイートページを開いています...")
        print(f"  {quotes_url}")
        driver.get(quotes_url)
        time.sleep(4)

        print("スクロールして引用ツイートを取得中...\n")

        last_count = 0
        no_change_count = 0
        max_scroll_pos = 0

        while len(quotes) < max_users:
            articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

            for article in articles:
                if len(quotes) >= max_users:
                    break

                try:
                    username, name, quote_text = extract_quote_from_article(driver, article)
                    if not username or username in quotes:
                        continue

                    user_data = {
                        "username": username,
                        "name": name,
                        "bio": None,
                        "verified": False,
                        "profile_image_url": None,
                        "quote_text": quote_text,
                    }

                    # プロフィール画像
                    try:
                        img = article.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
                        user_data["profile_image_url"] = img.get_attribute("src")
                    except:
                        pass

                    quotes[username] = user_data
                    print(f"{len(quotes)}. @{username} - {name or ''}")
                    if quote_text:
                        qt = quote_text.replace("\n", " ")[:60]
                        if len(quote_text) > 60:
                            qt += "..."
                        print(f"   引用: {qt}")
                    print()

                except:
                    continue

            if len(quotes) == last_count:
                no_change_count += 1
                if no_change_count >= 15:
                    print("これ以上の引用ツイートは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(quotes)

            if articles:
                try:
                    last_article = articles[-1]
                    bottom = driver.execute_script(
                        "var r = arguments[0].getBoundingClientRect();"
                        "return window.pageYOffset + r.bottom;",
                        last_article
                    )
                    target = max(bottom, max_scroll_pos + 800)
                    max_scroll_pos = target
                    driver.execute_script(f"window.scrollTo(0, {target});")
                except:
                    max_scroll_pos += 800
                    driver.execute_script(f"window.scrollTo(0, {max_scroll_pos});")
            else:
                max_scroll_pos += 800
                driver.execute_script(f"window.scrollTo(0, {max_scroll_pos});")

            if no_change_count >= 3:
                time.sleep(2.5)
            else:
                time.sleep(1.2)

        # === プロフィール情報取得（インターセプト優先 + API補完） ===
        fetch_user_profiles(driver, quotes)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(quotes.values())
