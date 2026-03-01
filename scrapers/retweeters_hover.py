"""リツイーター取得（詳細版・GraphQL APIでフォロワー数等も取得）"""

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


def extract_user_data_basic(driver, cell):
    """UserCellから基本情報を抽出（テキスト解析フォールバック付き）"""
    data = {
        "username": None,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
    }

    try:
        # username
        data["username"] = extract_username_from_links(cell)

        # name - CSSセレクターで取得
        try:
            name_elem = cell.find_element(By.CSS_SELECTOR,
                '[data-testid="UserName"] a div:first-child span span')
            data["name"] = get_text_with_emoji(driver, name_elem).strip()
        except:
            try:
                name_elem = cell.find_element(By.CSS_SELECTOR,
                    '[data-testid="UserName"] span span')
                text = get_text_with_emoji(driver, name_elem).strip()
                if text and not text.startswith("@"):
                    data["name"] = text
            except:
                pass

        # name - テキスト解析フォールバック
        if not data["name"]:
            try:
                raw_text = get_text_with_emoji(driver, cell)
                lines = raw_text.split("\n")
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    if line_stripped.startswith("@"):
                        continue
                    if line_stripped in ["Follow", "フォロー", "Following", "フォロー中",
                                        "Follows you", "フォローされています"]:
                        continue
                    data["name"] = line_stripped
                    break
            except:
                pass

        # bio
        try:
            bio_elem = cell.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            data["bio"] = get_text_with_emoji(driver, bio_elem).strip()
        except:
            pass

        # verified
        try:
            for sel in ['[data-testid="icon-verified"]',
                         'svg[aria-label*="認証"]', 'svg[aria-label*="Verified"]']:
                if cell.find_elements(By.CSS_SELECTOR, sel):
                    data["verified"] = True
                    break
        except:
            pass

        # profile image
        try:
            img = cell.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass
    except:
        pass

    return data


def scrape_retweeters(url, max_users=500):
    """リツイーターを取得（詳細版・GraphQL API使用）"""
    print("=" * 60)
    print("リツイーター取得 (詳細版)")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"最大取得数: {max_users}人")

    print("\nChromeを起動中...")
    driver = create_driver()
    retweeters = {}

    try:
        print("X.com を開いています...")
        driver.get("https://x.com/home")
        time.sleep(3)
        wait_for_login(driver)

        # CDP経由でインターセプター注入（ページ遷移後も自動で有効）
        inject_interceptor_cdp(driver)

        retweets_url = url if "/retweets" in url else url.rstrip("/") + "/retweets"
        print(f"\nリツイーターページを開いています...")
        driver.get(retweets_url)
        time.sleep(4)

        print("スクロールしてリツイーターを取得中...\n")

        last_count = 0
        no_change_count = 0

        while len(retweeters) < max_users:
            user_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

            for cell in user_cells:
                if len(retweeters) >= max_users:
                    break
                try:
                    user_data = extract_user_data_basic(driver, cell)
                    if not user_data or not user_data.get("username"):
                        continue
                    username = user_data["username"]
                    if username in retweeters:
                        continue
                    retweeters[username] = user_data
                    name_display = user_data.get('name') or ''
                    print(f"{len(retweeters)}. @{username} - {name_display}")
                except:
                    continue

            if len(retweeters) == last_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print("\nこれ以上のユーザーは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(retweeters)

            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.8)

        # === プロフィール情報取得（インターセプト優先 + API補完） ===
        fetch_user_profiles(driver, retweeters)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nブラウザを閉じています...")
        driver.quit()

    return list(retweeters.values())
