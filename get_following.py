#!/usr/bin/env python3
"""
twscrape を使ってフォロー中リストを取得
"""

import asyncio
import getpass
from twscrape import API, gather

async def main():
    print("=" * 50)
    print("X フォロー中リスト取得ツール (twscrape)")
    print("=" * 50)
    print("\n⚠️ 注意: X利用規約違反のリスクがあります")
    print("   捨てアカウントの使用を推奨します\n")

    # 認証情報入力
    print("--- Xアカウント認証情報 ---")
    username = input("ユーザー名 (@なし): ").strip()
    password = getpass.getpass("パスワード: ")
    email = input("登録メールアドレス: ").strip()

    # メールパスワードは不要な場合もある
    email_password = getpass.getpass("メールパスワード (不要なら空欄): ")
    if not email_password:
        email_password = password  # 同じパスワードを使用

    # 取得対象
    print("\n--- 取得対象 ---")
    target = input("フォロー中を取得したいユーザー名 (@なし): ").strip()
    limit = input("取得件数 (デフォルト: 100): ").strip()
    limit = int(limit) if limit else 100

    # API初期化
    api = API()

    print("\n🔄 ログイン中...")
    try:
        await api.pool.add_account(username, password, email, email_password)
        await api.pool.login_all()
        print("✓ ログイン成功")
    except Exception as e:
        print(f"✗ ログイン失敗: {e}")
        return

    # ユーザーID取得
    print(f"\n🔍 @{target} の情報を取得中...")
    try:
        user = await api.user_by_login(target)
        if not user:
            print(f"✗ ユーザー @{target} が見つかりません")
            return
        print(f"✓ ユーザー発見: {user.displayname} (@{user.username})")
        print(f"  フォロー中: {user.friendsCount}人")
    except Exception as e:
        print(f"✗ ユーザー取得エラー: {e}")
        return

    # フォロー中取得
    print(f"\n📥 フォロー中リストを取得中... (最大{limit}件)")
    following_list = []

    try:
        async for following_user in api.following(user.id, limit=limit):
            following_list.append({
                "id": following_user.id,
                "username": following_user.username,
                "name": following_user.displayname
            })
            print(f"  {len(following_list)}. @{following_user.username} ({following_user.displayname})")
    except Exception as e:
        print(f"⚠️ 取得エラー: {e}")

    print(f"\n✓ 取得完了: {len(following_list)}人")

    # ファイル保存
    if following_list:
        filename = f"following_{target}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for u in following_list:
                f.write(f"@{u['username']}\t{u['name']}\n")
        print(f"📁 保存しました: {filename}")

        # JSON形式でも保存
        import json
        json_filename = f"following_{target}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(following_list, f, ensure_ascii=False, indent=2)
        print(f"📁 保存しました: {json_filename}")

if __name__ == "__main__":
    asyncio.run(main())
