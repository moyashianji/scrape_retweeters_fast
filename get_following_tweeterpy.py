#!/usr/bin/env python3
"""
TweeterPy でフォロー中リストを取得
curl-cffi 使用で Cloudflare 回避
"""

import json
import os
from tweeterpy import TweeterPy

SESSION_FILE = "tweeterpy_session.json"


def main():
    print("=" * 55)
    print("X フォロー中リスト取得 (TweeterPy)")
    print("=" * 55)

    # TweeterPy 初期化
    twitter = TweeterPy(log_level="INFO")

    # セッション復元を試みる
    if os.path.exists(SESSION_FILE):
        print(f"\n既存セッションを読み込み中: {SESSION_FILE}")
        try:
            twitter.load_session(SESSION_FILE)
            print("セッション読み込み成功！")
        except Exception as e:
            print(f"セッション読み込み失敗: {e}")
            os.remove(SESSION_FILE)

    # ログイン確認
    if not twitter.logged_in():
        print("\n--- ログイン ---")
        username = input("ユーザー名 (@なし): ").strip()
        password = input("パスワード: ").strip()

        print("\nログイン中...")
        try:
            twitter.login(username, password)
            # セッション保存
            twitter.save_session(SESSION_FILE)
            print("ログイン成功！セッションを保存しました。")
        except Exception as e:
            print(f"ログインエラー: {e}")
            return
    else:
        print("\nログイン済みです。")

    # 取得対象
    target = input("\nフォロー中を取得したいユーザー名 (@なし): ").strip()
    limit = input("取得件数 (デフォルト: 100): ").strip()
    limit = int(limit) if limit else 100

    # ユーザー情報取得
    print(f"\n@{target} を検索中...")
    try:
        user_id = twitter.get_user_id(target)
        print(f"ユーザーID: {user_id}")

        user_data = twitter.get_user_data(target)
        name = user_data.get("legacy", {}).get("name", target)
        following_count = user_data.get("legacy", {}).get("friends_count", 0)
        followers_count = user_data.get("legacy", {}).get("followers_count", 0)

        print(f"ユーザー: {name} (@{target})")
        print(f"  フォロー中: {following_count}人")
        print(f"  フォロワー: {followers_count}人")
    except Exception as e:
        print(f"ユーザー取得エラー: {e}")
        return

    # フォロー中取得
    print(f"\nフォロー中リストを取得中... (最大{limit}件)")
    following_list = []

    try:
        # get_friends = フォロー中のユーザー
        friends = twitter.get_friends(user_id, total=limit)

        if isinstance(friends, dict) and "data" in friends:
            users = friends.get("data", [])
        elif isinstance(friends, list):
            users = friends
        else:
            users = []

        for u in users:
            legacy = u.get("legacy", {}) if isinstance(u, dict) else {}
            user_info = {
                "id": u.get("rest_id") or u.get("id"),
                "username": legacy.get("screen_name") or u.get("screen_name", ""),
                "name": legacy.get("name") or u.get("name", "")
            }
            if user_info["username"]:
                following_list.append(user_info)
                print(f"  {len(following_list)}. @{user_info['username']} ({user_info['name']})")

    except Exception as e:
        print(f"フォロー中取得エラー: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n取得完了: {len(following_list)}人")

    # 保存
    if following_list:
        filename = f"following_{target}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for u in following_list:
                f.write(f"@{u['username']}\t{u['name']}\n")
        print(f"保存: {filename}")

        json_filename = f"following_{target}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(following_list, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_filename}")


if __name__ == "__main__":
    main()
