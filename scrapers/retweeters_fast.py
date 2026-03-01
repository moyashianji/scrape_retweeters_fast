"""リツイーター取得（高速版・ホバーなし・絵文字対応）"""

import re
import time
from selenium.webdriver.common.by import By
from backend.chrome_utils import create_driver, wait_for_login
from scrapers.common import get_text_with_emoji, inject_fetch_interceptor, inject_interceptor_cdp, extract_dm_status_from_responses, fetch_user_profiles, apply_dm_status


def extract_user_data(driver, cell):
    """UserCellから全情報を抽出（CSSセレクター優先 + テキスト解析フォールバック）"""
    data = {
        "username": None,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
    }

    try:
        # 1. username をリンクから取得（最も確実）
        links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
        for link in links:
            href = link.get_attribute("href") or ""
            if "/status/" not in href and "x.com/" in href:
                match = re.search(r"x\.com/([A-Za-z0-9_]+)$", href)
                if match:
                    uname = match.group(1)
                    skip = ["home", "explore", "notifications", "messages",
                            "i", "settings", "search"]
                    if uname.lower() not in skip:
                        data["username"] = uname
                        break

        # 2. 名前をCSSセレクターで取得
        try:
            # X の UserCell は [data-testid="UserName"] 内に名前がある
            name_container = cell.find_element(By.CSS_SELECTOR,
                '[data-testid="UserName"] a div:first-child span span')
            data["name"] = get_text_with_emoji(driver, name_container).strip()
        except:
            try:
                # フォールバック: UserName 直下の最初の div
                name_container = cell.find_element(By.CSS_SELECTOR,
                    '[data-testid="UserName"] span span')
                name_text = get_text_with_emoji(driver, name_container).strip()
                # @username 部分を除外
                if name_text and not name_text.startswith("@"):
                    data["name"] = name_text
            except:
                pass

        # 3. bio をCSSセレクターで取得
        try:
            bio_elem = cell.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            data["bio"] = get_text_with_emoji(driver, bio_elem).strip()
        except:
            pass

        # 4. テキスト解析フォールバック（CSS で取得できなかった場合）
        if not data["name"] or (not data["bio"] and not data["username"]):
            raw_text = get_text_with_emoji(driver, cell)
            lines = raw_text.split("\n")

            found_username = False
            found_follow_button = False
            bio_lines = []

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                if re.match(r"^@[A-Za-z0-9_]+$", line_stripped):
                    if not found_username:
                        if not data["username"]:
                            data["username"] = line_stripped[1:]
                        found_username = True
                        continue
                    else:
                        bio_lines.append(line_stripped)
                        continue

                if not data["name"] and not found_username and not line_stripped.startswith("@"):
                    data["name"] = line_stripped
                    continue

                if line_stripped in ["Follow", "フォロー", "Following", "フォロー中",
                                   "Follows you", "フォローされています"]:
                    found_follow_button = True
                    continue

                if found_follow_button:
                    bio_lines.append(line_stripped)

            if not data["bio"] and bio_lines:
                data["bio"] = "\n".join(bio_lines)

        # 5. 認証バッジ
        try:
            badge_selectors = [
                '[data-testid="icon-verified"]',
                'svg[aria-label*="認証"]',
                'svg[aria-label*="Verified"]',
                'svg[aria-label*="verified"]'
            ]
            for selector in badge_selectors:
                badges = cell.find_elements(By.CSS_SELECTOR, selector)
                if badges:
                    data["verified"] = True
                    break
        except:
            pass

        # 6. プロフィール画像
        try:
            img = cell.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

    except:
        pass

    return data


def scrape_retweeters(url, max_users=500):
    """リツイーターを取得（高速版）"""
    print("=" * 60)
    print("リツイーター取得 (高速版)")
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
                try:
                    user_data = extract_user_data(driver, cell)
                    if not user_data or not user_data.get("username"):
                        continue

                    username = user_data["username"]
                    if username in retweeters:
                        continue

                    retweeters[username] = user_data
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
                except:
                    continue

            if len(retweeters) == last_count:
                no_change_count += 1
                if no_change_count >= 10:
                    print("これ以上のユーザーは見つかりませんでした。")
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
