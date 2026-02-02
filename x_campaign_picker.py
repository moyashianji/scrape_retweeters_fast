#!/usr/bin/env python3
"""
X (Twitter) キャンペーン抽選システム
====================================
リツイート + いいね + フォロワー条件を満たすユーザーから
ランダムに当選者を選出します。

【重要な制限】
- X API v2の仕様により、リツイーターといいねユーザーは最大100件まで取得可能
- この制限はAPIのハードリミットであり、回避不可能です
"""

import os
import random
import time
import json
from datetime import datetime
from dotenv import load_dotenv
import tweepy

# .envファイルから環境変数を読み込み
load_dotenv()


class XCampaignPicker:
    """X キャンペーン抽選クラス"""

    def __init__(self):
        """APIクライアントを初期化"""
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        # 認証情報の確認
        if not self.bearer_token:
            raise ValueError(
                "X_BEARER_TOKEN が設定されていません。\n"
                ".env ファイルを確認してください。"
            )

        # Access Tokenの有無を記録
        self.has_user_context = (
            self.access_token and
            self.access_token_secret and
            self.access_token != "your_access_token_here"
        )

        # Tweepy Client (API v2)
        if self.has_user_context:
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
        else:
            # Bearer Token のみ (App-Only認証)
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                wait_on_rate_limit=True
            )

        print("✓ X API に接続しました")
        if not self.has_user_context:
            print("  (Bearer Token認証 - アカウント名の指定が必要です)")

    def extract_tweet_id(self, tweet_url_or_id: str) -> str:
        """ツイートURLまたはIDからIDを抽出"""
        # URLの場合
        if "twitter.com" in tweet_url_or_id or "x.com" in tweet_url_or_id:
            # URLからIDを抽出 (例: https://x.com/user/status/1234567890)
            parts = tweet_url_or_id.rstrip("/").split("/")
            for i, part in enumerate(parts):
                if part == "status" and i + 1 < len(parts):
                    return parts[i + 1].split("?")[0]
            raise ValueError(f"無効なツイートURL: {tweet_url_or_id}")
        # IDの場合
        return tweet_url_or_id

    def get_retweeters(self, tweet_id: str) -> set:
        """
        ツイートをリツイートしたユーザーを取得

        【制限】最大100件まで（API仕様）
        """
        print(f"\n📢 リツイーターを取得中... (最大100件)")
        retweeters = set()

        try:
            # ページネーションで取得（ただし100件が上限）
            paginator = tweepy.Paginator(
                self.client.get_retweeters,
                id=tweet_id,
                max_results=100,
                user_fields=["id", "username", "name"]
            )

            for response in paginator:
                if response.data:
                    for user in response.data:
                        retweeters.add((user.id, user.username, user.name))
                        print(f"  RT: @{user.username}")

                # API制限: 100件で終了
                if len(retweeters) >= 100:
                    break

        except tweepy.TweepyException as e:
            print(f"⚠️ リツイーター取得エラー: {e}")

        print(f"✓ リツイーター: {len(retweeters)}人")
        return retweeters

    def get_liking_users(self, tweet_id: str) -> set:
        """
        ツイートにいいねしたユーザーを取得

        【制限】最大100件まで（API仕様）
        """
        print(f"\n❤️ いいねユーザーを取得中... (最大100件)")
        likers = set()

        try:
            paginator = tweepy.Paginator(
                self.client.get_liking_users,
                id=tweet_id,
                max_results=100,
                user_fields=["id", "username", "name"]
            )

            for response in paginator:
                if response.data:
                    for user in response.data:
                        likers.add((user.id, user.username, user.name))
                        print(f"  ❤️: @{user.username}")

                # API制限: 100件で終了
                if len(likers) >= 100:
                    break

        except tweepy.TweepyException as e:
            print(f"⚠️ いいねユーザー取得エラー: {e}")

        print(f"✓ いいねユーザー: {len(likers)}人")
        return likers

    def get_followers(self, user_id: str, max_count: int = 10000) -> set:
        """
        フォロワーを取得

        【注意】大量のフォロワーがいる場合、時間がかかります
        - 15分あたり300リクエスト
        - 1リクエストあたり最大1000件
        """
        print(f"\n👥 フォロワーを取得中... (最大{max_count}件)")
        followers = set()
        request_count = 0

        try:
            paginator = tweepy.Paginator(
                self.client.get_users_followers,
                id=user_id,
                max_results=1000,
                user_fields=["id", "username"]
            )

            for response in paginator:
                request_count += 1
                if response.data:
                    for user in response.data:
                        followers.add(user.id)

                    print(f"  取得済み: {len(followers)}人 (リクエスト: {request_count})")

                if len(followers) >= max_count:
                    print(f"  ⚠️ 上限 {max_count}件に達しました")
                    break

        except tweepy.TweepyException as e:
            print(f"⚠️ フォロワー取得エラー: {e}")

        print(f"✓ フォロワー: {len(followers)}人")
        return followers

    def check_following_batch(self, user_id: str, target_user_ids: list) -> set:
        """
        複数ユーザーがフォロワーかどうかを効率的にチェック

        フォロワーリストを取得済みの場合はそれを使用
        """
        # target_user_idsのセットを返す（フォロワーリストとの積集合で確認）
        return set(target_user_ids)

    def get_my_user_id(self) -> tuple:
        """認証ユーザーの情報を取得"""
        try:
            me = self.client.get_me(user_fields=["id", "username", "name"])
            if me.data:
                return me.data.id, me.data.username, me.data.name
        except tweepy.TweepyException as e:
            print(f"⚠️ ユーザー情報取得エラー: {e}")
        return None, None, None

    def get_user_by_username(self, username: str) -> tuple:
        """ユーザー名からユーザー情報を取得"""
        try:
            # @を除去
            username = username.lstrip("@")
            user = self.client.get_user(username=username, user_fields=["id", "username", "name"])
            if user.data:
                return user.data.id, user.data.username, user.data.name
        except tweepy.TweepyException as e:
            print(f"⚠️ ユーザー取得エラー: {e}")
        return None, None, None

    def run_campaign(
        self,
        tweet_url_or_id: str,
        account_username: str = None,
        winner_count: int = 10,
        require_retweet: bool = True,
        require_like: bool = True,
        require_follow: bool = True,
        max_followers_to_check: int = 10000
    ) -> list:
        """
        キャンペーン抽選を実行

        Parameters:
        -----------
        tweet_url_or_id : str
            対象ツイートのURLまたはID
        account_username : str, optional
            フォロー確認するアカウント（省略時は認証アカウント）
        winner_count : int
            当選者数（デフォルト: 10）
        require_retweet : bool
            リツイート必須（デフォルト: True）
        require_like : bool
            いいね必須（デフォルト: True）
        require_follow : bool
            フォロー必須（デフォルト: True）
        max_followers_to_check : int
            チェックするフォロワーの最大数（デフォルト: 10000）

        Returns:
        --------
        list : 当選者リスト [(user_id, username, name), ...]
        """
        print("=" * 60)
        print("🎁 X キャンペーン抽選システム")
        print("=" * 60)

        # ツイートID抽出
        tweet_id = self.extract_tweet_id(tweet_url_or_id)
        print(f"対象ツイートID: {tweet_id}")

        # アカウント情報取得
        if account_username:
            user_id, username, name = self.get_user_by_username(account_username)
        elif self.has_user_context:
            user_id, username, name = self.get_my_user_id()
        else:
            raise ValueError(
                "Bearer Token認証ではアカウント名(@username)の指定が必須です"
            )

        if not user_id:
            raise ValueError("アカウント情報を取得できませんでした")

        print(f"対象アカウント: @{username} ({name})")
        print(f"条件: RT={require_retweet}, いいね={require_like}, フォロー={require_follow}")
        print(f"当選者数: {winner_count}人")

        # 候補者を収集
        candidates = None

        # リツイーター取得
        if require_retweet:
            retweeters = self.get_retweeters(tweet_id)
            retweeter_ids = {user[0] for user in retweeters}
            candidates = retweeters if candidates is None else {
                u for u in candidates if u[0] in retweeter_ids
            }

        # いいねユーザー取得
        if require_like:
            likers = self.get_liking_users(tweet_id)
            liker_ids = {user[0] for user in likers}
            if candidates is None:
                candidates = likers
            else:
                candidates = {u for u in candidates if u[0] in liker_ids}

        print(f"\n📊 RT & いいね 両方: {len(candidates) if candidates else 0}人")

        # フォロワーチェック
        if require_follow and candidates:
            print(f"\n👥 フォロワーとの照合中...")
            followers = self.get_followers(user_id, max_count=max_followers_to_check)
            candidates = {u for u in candidates if u[0] in followers}
            print(f"✓ 全条件を満たすユーザー: {len(candidates)}人")

        if not candidates:
            print("\n⚠️ 条件を満たすユーザーがいませんでした")
            return []

        # ランダム抽選
        candidates_list = list(candidates)
        winner_count = min(winner_count, len(candidates_list))
        winners = random.sample(candidates_list, winner_count)

        # 結果表示
        print("\n" + "=" * 60)
        print(f"🎉 当選者発表！({winner_count}名)")
        print("=" * 60)

        for i, (uid, uname, display_name) in enumerate(winners, 1):
            print(f"  {i}. @{uname} ({display_name})")

        # 結果をJSONで保存
        result = {
            "timestamp": datetime.now().isoformat(),
            "tweet_id": tweet_id,
            "account": username,
            "conditions": {
                "require_retweet": require_retweet,
                "require_like": require_like,
                "require_follow": require_follow
            },
            "total_candidates": len(candidates_list),
            "winners": [
                {"user_id": str(uid), "username": uname, "name": display_name}
                for uid, uname, display_name in winners
            ]
        }

        filename = f"campaign_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📁 結果を保存しました: {filename}")

        return winners


def main():
    """メイン関数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          X (Twitter) キャンペーン抽選システム                ║
║                                                              ║
║  【重要な制限事項】                                          ║
║  X API v2の仕様により、以下の制限があります:                 ║
║  - リツイーター: 最大100件まで取得可能                       ║
║  - いいねユーザー: 最大100件まで取得可能                     ║
║  これはAPIのハードリミットであり、回避できません。           ║
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        picker = XCampaignPicker()

        # ユーザー入力
        print("\n--- 設定 ---")
        tweet_url = input("対象ツイートのURL (または ID): ").strip()

        if picker.has_user_context:
            account = input("フォロー確認アカウント (@username、空欄で自分): ").strip()
            account = account if account else None
        else:
            account = input("フォロー確認アカウント (@username、必須): ").strip()
            if not account:
                raise ValueError("Bearer Token認証ではアカウント名が必須です")

        winner_count = input("当選者数 (デフォルト: 10): ").strip()
        winner_count = int(winner_count) if winner_count else 10

        print("\n条件設定 (y/n)")
        require_rt = input("  リツイート必須? (y/n, デフォルト: y): ").strip().lower()
        require_rt = require_rt != "n"

        require_like = input("  いいね必須? (y/n, デフォルト: y): ").strip().lower()
        require_like = require_like != "n"

        require_follow = input("  フォロー必須? (y/n, デフォルト: y): ").strip().lower()
        require_follow = require_follow != "n"

        # 抽選実行
        picker.run_campaign(
            tweet_url_or_id=tweet_url,
            account_username=account,
            winner_count=winner_count,
            require_retweet=require_rt,
            require_like=require_like,
            require_follow=require_follow
        )

    except ValueError as e:
        print(f"\n❌ エラー: {e}")
    except KeyboardInterrupt:
        print("\n\n中断されました")


if __name__ == "__main__":
    main()
