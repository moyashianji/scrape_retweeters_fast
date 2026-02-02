#!/usr/bin/env python3
"""
twikit を使ってフォロー中リストを取得
最新の方法（2025-2026対応）
"""

import asyncio
import getpass
import json
import os

from twikit import Client

COOKIES_FILE = "cookies.json"


async def main():
    print("=" * 50)
    print("X フォロー中リスト取得ツール (twikit)")
    print("=" * 50)
    print("\n※ 初回はログインが必要です")
    print("※ 2回目以降はCookieを再利用します\n")

    client = Client('ja-JP')

    # Cookieファイルがあれば再利用
    if os.path.exists(COOKIES_FILE):
        print(f"既存のCookieを読み込み中: {COOKIES_FILE}")
        try:
            client.load_cookies(COOKIES_FILE)
            print("Cookie読み込み成功")
        except Exception as e:
            print(f"Cookie読み込み失敗: {e}")
            os.remove(COOKIES_FILE)
            print("Cookieファイルを削除しました。再ログインしてください。")
            return
    else:
        # ログイン
        print("--- Xアカウント認証 ---")
        username = input("ユーザー名 (@なし): ").strip()
        email = input("メールアドレス: ").strip()
        password = getpass.getpass("パスワード: ")

        print("\nログイン中...")
        try:
            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password
            )
            # Cookieを保存
            client.save_cookies(COOKIES_FILE)
            print("ログイン成功！Cookieを保存しました。")
        except Exception as e:
            print(f"ログイン失敗: {e}")
            return

    # 取得対象
    print("\n--- 取得対象 ---")
    target_username = input("フォロー中を取得したいユーザー名 (@なし): ").strip()
    limit = input("取得件数 (デフォルト: 100): ").strip()
    limit = int(limit) if limit else 100

    # ユーザー情報取得
    print(f"\n@{target_username} を検索中...")
    try:
        user = await client.get_user_by_screen_name(target_username)
        print(f"ユーザー発見: {user.name} (@{user.screen_name})")
        print(f"  フォロー中: {user.following_count}人")
        print(f"  フォロワー: {user.followers_count}人")
    except Exception as e:
        print(f"ユーザー取得失敗: {e}")
        return

    # フォロー中リスト取得
    print(f"\nフォロー中リストを取得中... (最大{limit}件)")
    following_list = []

    try:
        # get_user_following は User オブジェクトのリストを返す
        following_users = await user.get_following()

        count = 0
        for f_user in following_users:
            if count >= limit:
                break
            following_list.append({
                "id": f_user.id,
                "username": f_user.screen_name,
                "name": f_user.name
            })
            print(f"  {len(following_list)}. @{f_user.screen_name} ({f_user.name})")
            count += 1

        # ページネーション（もっと取得する場合）
        while len(following_list) < limit:
            try:
                more_users = await following_users.next()
                if not more_users:
                    break
                for f_user in more_users:
                    if len(following_list) >= limit:
                        break
                    following_list.append({
                        "id": f_user.id,
                        "username": f_user.screen_name,
                        "name": f_user.name
                    })
                    print(f"  {len(following_list)}. @{f_user.screen_name} ({f_user.name})")
            except Exception:
                break

    except Exception as e:
        print(f"フォロー中取得エラー: {e}")

    print(f"\n取得完了: {len(following_list)}人")

    # ファイル保存
    if following_list:
        filename = f"following_{target_username}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for u in following_list:
                f.write(f"@{u['username']}\t{u['name']}\n")
        print(f"保存: {filename}")

        json_filename = f"following_{target_username}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(following_list, f, ensure_ascii=False, indent=2)
        print(f"保存: {json_filename}")


if __name__ == "__main__":
    asyncio.run(main())
