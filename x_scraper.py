#!/usr/bin/env python3
"""
X スクレイパー (Selenium + 手動ログイン)
リツイーター、いいね、フォロー中を取得
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


class XScraper:
    def __init__(self):
        self.driver = None
        self.profile_dir = os.path.join(os.path.dirname(__file__), "x_chrome_profile")
        os.makedirs(self.profile_dir, exist_ok=True)

    def start_browser(self):
        """ブラウザを起動"""
        print("\nChromeを起動中...")

        options = Options()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def ensure_logged_in(self):
        """ログイン確認"""
        print("X.com を開いています...")
        self.driver.get("https://x.com/home")
        time.sleep(3)

        # ログインページにリダイレクトされたか確認
        current_url = self.driver.current_url
        if "login" in current_url or "i/flow" in current_url:
            print("\n" + "=" * 60)
            print("【手動ログインが必要です】")
            print("=" * 60)
            print("ブラウザでX.comにログインしてください。")
            print("ログイン完了後、Enterキーを押してください。")
            print("=" * 60)
            input("\n>>> ログイン完了後、Enterを押す...")
            time.sleep(2)
        else:
            print("ログイン済みです。")

    def scroll_and_collect_users(self, url, max_users=500):
        """ページをスクロールしてユーザーを収集"""
        print(f"\nページを開いています: {url}")
        self.driver.get(url)
        time.sleep(4)

        users = {}
        last_count = 0
        no_change_count = 0

        print(f"スクロールしてユーザーを取得中... (最大{max_users}人)\n")

        while len(users) < max_users:
            # ユーザーセルを取得
            try:
                user_cells = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')

                for cell in user_cells:
                    try:
                        links = cell.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                        for link in links:
                            href = link.get_attribute("href")
                            if href and "/status/" not in href:
                                match = re.search(r"x\.com/([^/?\s]+)$", href)
                                if match:
                                    username = match.group(1)
                                    skip_names = ["home", "explore", "notifications", "messages", "i", "settings", "search"]
                                    if username and username not in users and username.lower() not in skip_names:
                                        # 表示名を取得
                                        display_name = username
                                        try:
                                            spans = cell.find_elements(By.CSS_SELECTOR, 'span')
                                            for span in spans:
                                                text = span.text.strip()
                                                if text and not text.startswith("@") and len(text) > 1:
                                                    display_name = text
                                                    break
                                        except:
                                            pass

                                        users[username] = {
                                            "username": username,
                                            "name": display_name
                                        }
                                        print(f"  {len(users)}. @{username} ({display_name})")
                                        break
                    except:
                        continue

            except Exception as e:
                print(f"エラー: {e}")

            # 変化チェック
            if len(users) == last_count:
                no_change_count += 1
                if no_change_count >= 8:
                    print("\nこれ以上のユーザーは見つかりませんでした。")
                    break
            else:
                no_change_count = 0
                last_count = len(users)

            # スクロール
            self.driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.2)

        return list(users.values())

    def get_retweeters(self, tweet_url, max_users=500):
        """リツイーターを取得"""
        # URLを正規化
        if "/retweets" not in tweet_url:
            tweet_url = tweet_url.rstrip("/") + "/retweets"
        return self.scroll_and_collect_users(tweet_url, max_users)

    def get_likers(self, tweet_url, max_users=500):
        """いいねしたユーザーを取得"""
        # URLを正規化
        base_url = re.sub(r"/(retweets|likes|quotes).*$", "", tweet_url)
        likes_url = base_url + "/likes"
        return self.scroll_and_collect_users(likes_url, max_users)

    def get_following(self, username, max_users=500):
        """フォロー中を取得"""
        username = username.lstrip("@")
        url = f"https://x.com/{username}/following"
        return self.scroll_and_collect_users(url, max_users)

    def get_followers(self, username, max_users=500):
        """フォロワーを取得"""
        username = username.lstrip("@")
        url = f"https://x.com/{username}/followers"
        return self.scroll_and_collect_users(url, max_users)

    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            print("\nブラウザを閉じています...")
            self.driver.quit()


def save_results(users, filename_prefix):
    """結果を保存"""
    if not users:
        print("保存するユーザーがいません。")
        return

    txt_file = f"{filename_prefix}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        for u in users:
            f.write(f"@{u['username']}\t{u['name']}\n")
    print(f"保存: {txt_file}")

    json_file = f"{filename_prefix}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"保存: {json_file}")


def main():
    print("=" * 60)
    print("       X スクレイパー (Selenium)")
    print("=" * 60)
    print("\n取得タイプを選択:")
    print("  1. リツイーター")
    print("  2. いいね (Likes)")
    print("  3. フォロー中 (Following)")
    print("  4. フォロワー (Followers)")
    print("  5. キャンペーン抽選 (RT + いいね + フォロワー)")

    choice = input("\n選択 (1-5): ").strip()

    scraper = XScraper()

    try:
        scraper.start_browser()
        scraper.ensure_logged_in()

        if choice == "1":
            # リツイーター
            url = input("\nツイートURL: ").strip()
            if not url:
                url = "https://x.com/ampxtak/status/2004877245396201605"
            max_users = input("最大取得数 (デフォルト: 500): ").strip()
            max_users = int(max_users) if max_users else 500

            users = scraper.get_retweeters(url, max_users)
            print(f"\n取得完了: {len(users)}人")

            match = re.search(r"/status/(\d+)", url)
            tweet_id = match.group(1) if match else "unknown"
            save_results(users, f"retweeters_{tweet_id}")

        elif choice == "2":
            # いいね
            url = input("\nツイートURL: ").strip()
            max_users = input("最大取得数 (デフォルト: 500): ").strip()
            max_users = int(max_users) if max_users else 500

            users = scraper.get_likers(url, max_users)
            print(f"\n取得完了: {len(users)}人")

            match = re.search(r"/status/(\d+)", url)
            tweet_id = match.group(1) if match else "unknown"
            save_results(users, f"likers_{tweet_id}")

        elif choice == "3":
            # フォロー中
            username = input("\nユーザー名 (@なしでOK): ").strip()
            max_users = input("最大取得数 (デフォルト: 500): ").strip()
            max_users = int(max_users) if max_users else 500

            users = scraper.get_following(username, max_users)
            print(f"\n取得完了: {len(users)}人")
            save_results(users, f"following_{username.lstrip('@')}")

        elif choice == "4":
            # フォロワー
            username = input("\nユーザー名 (@なしでOK): ").strip()
            max_users = input("最大取得数 (デフォルト: 500): ").strip()
            max_users = int(max_users) if max_users else 500

            users = scraper.get_followers(username, max_users)
            print(f"\n取得完了: {len(users)}人")
            save_results(users, f"followers_{username.lstrip('@')}")

        elif choice == "5":
            # キャンペーン抽選
            print("\n--- キャンペーン抽選モード ---")
            tweet_url = input("対象ツイートURL: ").strip()
            account = input("フォロー確認アカウント (@なしでOK): ").strip()
            winner_count = input("当選者数 (デフォルト: 10): ").strip()
            winner_count = int(winner_count) if winner_count else 10

            print("\n[1/3] リツイーターを取得中...")
            retweeters = scraper.get_retweeters(tweet_url, max_users=500)
            rt_set = {u["username"] for u in retweeters}
            print(f"リツイーター: {len(rt_set)}人")

            print("\n[2/3] いいねユーザーを取得中...")
            likers = scraper.get_likers(tweet_url, max_users=500)
            like_set = {u["username"] for u in likers}
            print(f"いいね: {len(like_set)}人")

            print("\n[3/3] フォロワーを取得中...")
            followers = scraper.get_followers(account, max_users=2000)
            follower_set = {u["username"] for u in followers}
            print(f"フォロワー: {len(follower_set)}人")

            # 条件を満たすユーザー
            candidates = rt_set & like_set & follower_set
            print(f"\n全条件を満たすユーザー: {len(candidates)}人")

            if candidates:
                import random
                winners = random.sample(list(candidates), min(winner_count, len(candidates)))

                print("\n" + "=" * 60)
                print(f"当選者発表！ ({len(winners)}名)")
                print("=" * 60)
                for i, w in enumerate(winners, 1):
                    print(f"  {i}. @{w}")

                # 保存
                match = re.search(r"/status/(\d+)", tweet_url)
                tweet_id = match.group(1) if match else "unknown"

                result = {
                    "tweet_id": tweet_id,
                    "account": account,
                    "retweeters_count": len(rt_set),
                    "likers_count": len(like_set),
                    "followers_count": len(follower_set),
                    "candidates_count": len(candidates),
                    "winners": winners
                }

                with open(f"campaign_result_{tweet_id}.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n保存: campaign_result_{tweet_id}.json")
            else:
                print("条件を満たすユーザーがいませんでした。")

        else:
            print("無効な選択です。")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
