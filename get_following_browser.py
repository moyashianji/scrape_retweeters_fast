#!/usr/bin/env python3
"""
ブラウザのCookieを使ってフォロー中リストを取得
Cloudflare回避の最終手段
"""

import json
import time
import httpx
import browser_cookie3

# X.com の GraphQL エンドポイント
FOLLOWING_URL = "https://x.com/i/api/graphql/eWTmcJY3EMh-dxIR7CYTKw/Following"

# 必要なヘッダー
HEADERS = {
    "accept": "*/*",
    "accept-language": "ja,en-US;q=0.9,en;q=0.8",
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    "content-type": "application/json",
    "x-twitter-active-user": "yes",
    "x-twitter-auth-type": "OAuth2Session",
    "x-twitter-client-language": "ja",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def get_browser_cookies():
    """ブラウザからX.comのCookieを取得"""
    print("ブラウザからCookieを取得中...")

    cookies = {}

    # Chrome
    try:
        cj = browser_cookie3.chrome(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Chrome: {len(cookies)}個のCookie")
    except Exception as e:
        print(f"  Chrome: 取得失敗 ({e})")

    # Edge
    try:
        cj = browser_cookie3.edge(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Edge: {len(cookies)}個のCookie")
    except Exception as e:
        print(f"  Edge: 取得失敗 ({e})")

    # Firefox
    try:
        cj = browser_cookie3.firefox(domain_name=".x.com")
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        print(f"  Firefox: {len(cookies)}個のCookie")
    except Exception as e:
        print(f"  Firefox: 取得失敗 ({e})")

    # twitter.com のCookieも試す
    try:
        cj = browser_cookie3.chrome(domain_name=".twitter.com")
        for cookie in cj:
            if cookie.name not in cookies:
                cookies[cookie.name] = cookie.value
    except:
        pass

    return cookies


def get_user_by_screen_name(client, screen_name, cookies):
    """ユーザー情報を取得"""
    url = "https://x.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName"

    variables = {
        "screen_name": screen_name,
        "withSafetyModeUserFields": True
    }

    features = {
        "hidden_profile_subscriptions_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "subscriptions_verification_info_is_identity_verified_enabled": True,
        "subscriptions_verification_info_verified_since_enabled": True,
        "highlights_tweets_tab_ui_enabled": True,
        "responsive_web_twitter_article_notes_tab_enabled": True,
        "subscriptions_feature_can_gift_premium": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True
    }

    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(features)
    }

    headers = HEADERS.copy()
    if "ct0" in cookies:
        headers["x-csrf-token"] = cookies["ct0"]

    response = client.get(url, params=params, headers=headers, cookies=cookies)

    if response.status_code != 200:
        raise Exception(f"Status {response.status_code}: {response.text[:200]}")

    data = response.json()
    return data.get("data", {}).get("user", {}).get("result", {})


def get_following(client, user_id, cookies, count=100):
    """フォロー中リストを取得"""
    following_list = []
    cursor = None

    while len(following_list) < count:
        variables = {
            "userId": user_id,
            "count": min(50, count - len(following_list)),
            "includePromotedContent": False
        }

        if cursor:
            variables["cursor"] = cursor

        features = {
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False
        }

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(features)
        }

        headers = HEADERS.copy()
        if "ct0" in cookies:
            headers["x-csrf-token"] = cookies["ct0"]

        response = client.get(FOLLOWING_URL, params=params, headers=headers, cookies=cookies)

        if response.status_code != 200:
            print(f"エラー: {response.status_code}")
            break

        data = response.json()

        # レスポンスからユーザーを抽出
        instructions = data.get("data", {}).get("user", {}).get("result", {}).get("timeline", {}).get("timeline", {}).get("instructions", [])

        found_users = False
        for instruction in instructions:
            if instruction.get("type") == "TimelineAddEntries":
                entries = instruction.get("entries", [])
                for entry in entries:
                    content = entry.get("content", {})

                    # カーソルの場合
                    if content.get("cursorType") == "Bottom":
                        cursor = content.get("value")
                        continue

                    # ユーザーの場合
                    item_content = content.get("itemContent", {})
                    if item_content.get("itemType") == "TimelineUser":
                        user_results = item_content.get("user_results", {}).get("result", {})
                        legacy = user_results.get("legacy", {})

                        if legacy:
                            found_users = True
                            user_info = {
                                "id": user_results.get("rest_id"),
                                "username": legacy.get("screen_name"),
                                "name": legacy.get("name")
                            }
                            following_list.append(user_info)
                            print(f"  {len(following_list)}. @{user_info['username']} ({user_info['name']})")

        if not found_users or not cursor:
            break

        time.sleep(1)  # レート制限対策

    return following_list


def main():
    print("=" * 50)
    print("X フォロー中リスト取得 (ブラウザCookie使用)")
    print("=" * 50)
    print("\n【重要】先にブラウザでX.comにログインしてください！")
    print("Chrome, Edge, Firefox のいずれかでOK\n")

    # ブラウザからCookie取得
    cookies = get_browser_cookies()

    # 必須Cookieの確認
    required = ["auth_token", "ct0"]
    missing = [r for r in required if r not in cookies]

    if missing:
        print(f"\n必須Cookieがありません: {missing}")
        print("ブラウザでX.comにログインしてから再実行してください。")
        print("※ブラウザを閉じてから実行してください（Cookieがロックされている場合があります）")
        return

    print(f"\n認証Cookie取得成功！")

    # HTTPクライアント
    client = httpx.Client(timeout=30)

    # 取得対象
    target = input("\nフォロー中を取得したいユーザー名 (@なし): ").strip()
    limit = input("取得件数 (デフォルト: 100): ").strip()
    limit = int(limit) if limit else 100

    # ユーザー情報取得
    print(f"\n@{target} を検索中...")
    try:
        user = get_user_by_screen_name(client, target, cookies)
        user_id = user.get("rest_id")
        legacy = user.get("legacy", {})
        name = legacy.get("name", "")
        following_count = legacy.get("friends_count", 0)

        print(f"ユーザー発見: {name} (@{target})")
        print(f"  フォロー中: {following_count}人")
    except Exception as e:
        print(f"ユーザー取得失敗: {e}")
        return

    # フォロー中取得
    print(f"\nフォロー中リストを取得中... (最大{limit}件)")
    following_list = get_following(client, user_id, cookies, limit)

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
