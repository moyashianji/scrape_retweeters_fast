#!/usr/bin/env python3
"""
twscrape + ブラウザCookie で Cloudflare を回避
"""

import asyncio
import json
import browser_cookie3
from twscrape import API, gather


def get_browser_cookies_string():
    """ブラウザからX.comのCookieを取得して文字列形式で返す"""
    print("ブラウザからCookieを取得中...")
    print("※ ブラウザを閉じてから実行してください\n")

    cookies = {}

    # Chrome
    try:
        cj = browser_cookie3.chrome(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Chrome: {len(cookies)}個")
    except Exception as e:
        print(f"  Chrome: 失敗 - {type(e).__name__}")

    # twitter.com も試す
    try:
        cj = browser_cookie3.chrome(domain_name=".twitter.com")
        for cookie in cj:
            if cookie.name not in cookies:
                cookies[cookie.name] = cookie.value
    except:
        pass

    # Edge
    try:
        cj = browser_cookie3.edge(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Edge: {len(cookies)}個")
    except Exception as e:
        print(f"  Edge: 失敗 - {type(e).__name__}")

    # Firefox
    try:
        cj = browser_cookie3.firefox(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Firefox: {len(cookies)}個")
    except Exception as e:
        print(f"  Firefox: 失敗 - {type(e).__name__}")

    if not cookies:
        return None

    # JSON形式で返す
    return json.dumps(cookies)


async def main():
    print("=" * 55)
    print("X フォロー中リスト取得 (twscrape + ブラウザCookie)")
    print("=" * 55)
    print("\n【重要】先にブラウザでX.comにログインしてください！\n")

    # Cookieを取得
    cookies_str = get_browser_cookies_string()

    if not cookies_str:
        print("\nCookieを取得できませんでした。")
        print("ブラウザでX.comにログインしてから再実行してください。")
        return

    cookies_dict = json.loads(cookies_str)

    # 必須Cookie確認
    if "auth_token" not in cookies_dict or "ct0" not in cookies_dict:
        print("\n必須Cookie (auth_token, ct0) がありません。")
        print("ブラウザでX.comにログインしてから再実行してください。")
        return

    print(f"\n認証Cookie取得成功！ (auth_token, ct0 確認済み)")

    # twscrape API初期化
    api = API("browser_account.db")

    # アカウント追加（Cookieベース）
    print("\ntwscrapeにアカウントを登録中...")
    try:
        # 既存のアカウントを削除してから追加
        await api.pool.delete_accounts(["browser_user"])
    except:
        pass

    try:
        await api.pool.add_account(
            username="browser_user",
            password="dummy",
            email="dummy@example.com",
            email_password="dummy",
            cookies=cookies_str
        )
        print("アカウント登録成功！")
    except Exception as e:
        print(f"アカウント登録エラー: {e}")
        # 既に存在する場合は続行
        pass

    # 取得対象
    target = input("\nフォロー中を取得したいユーザー名 (@なし): ").strip()
    limit = input("取得件数 (デフォルト: 100): ").strip()
    limit = int(limit) if limit else 100

    # ユーザー情報取得
    print(f"\n@{target} を検索中...")
    try:
        user = await api.user_by_login(target)
        if not user:
            print(f"ユーザー @{target} が見つかりません")
            return
        print(f"ユーザー発見: {user.displayname} (@{user.username})")
        print(f"  ID: {user.id}")
        print(f"  フォロー中: {user.friendsCount}人")
        print(f"  フォロワー: {user.followersCount}人")
    except Exception as e:
        print(f"ユーザー取得エラー: {e}")
        return

    # フォロー中取得
    print(f"\nフォロー中リストを取得中... (最大{limit}件)")
    following_list = []

    try:
        async for f_user in api.following(user.id, limit=limit):
            following_list.append({
                "id": f_user.id,
                "username": f_user.username,
                "name": f_user.displayname
            })
            print(f"  {len(following_list)}. @{f_user.username} ({f_user.displayname})")
    except Exception as e:
        print(f"フォロー中取得エラー: {e}")

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
    asyncio.run(main())
