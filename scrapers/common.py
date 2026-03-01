"""スクレイパー共通ユーティリティ"""

import re
import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_text_with_emoji(driver, element):
    """要素からテキストを取得（絵文字imgのalt属性も含む、ブロック要素で改行）"""
    script = """
    function getTextWithEmoji(element) {
        let result = '';
        const blockTags = new Set([
            'DIV', 'P', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
            'TR', 'BLOCKQUOTE', 'SECTION', 'ARTICLE', 'HEADER', 'FOOTER'
        ]);
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
            null,
            false
        );
        let node;
        while (node = walker.nextNode()) {
            if (node.nodeType === Node.TEXT_NODE) {
                result += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName === 'IMG' && node.alt) {
                    result += node.alt;
                } else if (node.tagName === 'BR') {
                    result += '\\n';
                } else if (blockTags.has(node.tagName)) {
                    if (result.length > 0 && !result.endsWith('\\n')) {
                        result += '\\n';
                    }
                }
            }
        }
        return result;
    }
    return getTextWithEmoji(arguments[0]);
    """
    try:
        return driver.execute_script(script, element)
    except:
        return element.text


def dismiss_hovercard(driver, actions):
    """ホバーカードを閉じる"""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element_with_offset(body, 0, 0).perform()
        time.sleep(0.3)
    except:
        pass


def extract_from_hovercard(driver, hover_card, username):
    """ホバーカードから情報を抽出"""
    data = {
        "username": username,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
        "location": None,
        "url": None,
        "followers_count": None,
        "following_count": None,
    }

    try:
        # 名前を絵文字込みで取得
        try:
            name_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserName"] span span')
            data["name"] = get_text_with_emoji(driver, name_elem).strip()
        except:
            pass

        # bioを絵文字込みで取得
        try:
            bio_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            data["bio"] = get_text_with_emoji(driver, bio_elem).strip()
        except:
            pass

        # フォロワー数・フォロー中数
        raw_text = get_text_with_emoji(driver, hover_card)
        for line in raw_text.split("\n"):
            following_match = re.search(r"([\d,\.]+[KMB]?)\s*(Following|フォロー中)", line)
            if following_match:
                data["following_count"] = following_match.group(1)

            followers_match = re.search(r"([\d,\.]+[KMB]?)\s*(Followers?|フォロワー)", line)
            if followers_match:
                data["followers_count"] = followers_match.group(1)

        # 認証バッジ
        try:
            badges = hover_card.find_elements(By.CSS_SELECTOR,
                '[data-testid="icon-verified"], svg[aria-label*="Verified"], svg[aria-label*="認証"]')
            if badges:
                data["verified"] = True
        except:
            pass

        # プロフィール画像
        try:
            img = hover_card.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

        # 場所
        try:
            location_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserLocation"]')
            data["location"] = get_text_with_emoji(driver, location_elem).strip()
        except:
            pass

        # URL
        try:
            url_elem = hover_card.find_element(By.CSS_SELECTOR, '[data-testid="UserUrl"] a')
            data["url"] = url_elem.get_attribute("href")
        except:
            pass

    except:
        pass

    return data


def extract_from_cell(driver, cell, username):
    """UserCellから情報を抽出（フォールバック）"""
    data = {
        "username": username,
        "name": None,
        "bio": None,
        "verified": False,
        "profile_image_url": None,
        "location": None,
        "url": None,
        "followers_count": None,
        "following_count": None,
    }

    try:
        # CSSセレクターで名前を取得
        try:
            name_container = cell.find_element(By.CSS_SELECTOR,
                '[data-testid="UserName"] a div:first-child span span')
            data["name"] = get_text_with_emoji(driver, name_container).strip()
        except:
            try:
                name_container = cell.find_element(By.CSS_SELECTOR,
                    '[data-testid="UserName"] span span')
                name_text = get_text_with_emoji(driver, name_container).strip()
                if name_text and not name_text.startswith("@"):
                    data["name"] = name_text
            except:
                # テキスト解析フォールバック
                raw_text = get_text_with_emoji(driver, cell)
                lines = raw_text.split("\n")
                for line in lines:
                    if line.strip() and not line.strip().startswith("@"):
                        data["name"] = line.strip()
                        break

        # bioをCSSセレクターで取得
        try:
            bio_elem = cell.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            data["bio"] = get_text_with_emoji(driver, bio_elem).strip()
        except:
            pass

        try:
            img = cell.find_element(By.CSS_SELECTOR, 'img[src*="profile_images"]')
            data["profile_image_url"] = img.get_attribute("src")
        except:
            pass

        try:
            badges = cell.find_elements(By.CSS_SELECTOR,
                '[data-testid="icon-verified"], svg[aria-label*="Verified"]')
            if badges:
                data["verified"] = True
        except:
            pass
    except:
        pass

    return data


def hover_and_get_profile(driver, actions, element, username):
    """要素のアバターにホバーしてプロフィール情報を取得"""
    try:
        avatar = element.find_element(By.CSS_SELECTOR,
            '[data-testid^="UserAvatar"] a, img[src*="profile_images"]')

        scroll_before = driver.execute_script("return window.pageYOffset;")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", avatar)
        time.sleep(0.3)

        actions.move_to_element(avatar).perform()
        time.sleep(1.2)

        hover_card = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="HoverCard"]'))
        )
        data = extract_from_hovercard(driver, hover_card, username)
        dismiss_hovercard(driver, actions)

        scroll_after = driver.execute_script("return window.pageYOffset;")
        restore_to = max(scroll_before, scroll_after)
        driver.execute_script(f"window.scrollTo(0, {restore_to});")

        return data

    except:
        dismiss_hovercard(driver, actions)
        return None


def extract_username_from_links(element):
    """要素内のリンクからusernameを抽出"""
    try:
        links = element.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
        for link in links:
            href = link.get_attribute("href") or ""
            if "/status/" not in href and "x.com/" in href:
                match = re.search(r"x\.com/([A-Za-z0-9_]+)$", href)
                if match:
                    uname = match.group(1)
                    skip = ["home", "explore", "notifications", "messages",
                            "i", "settings", "search", "compose"]
                    if uname.lower() not in skip:
                        return uname
    except:
        pass
    return None


def print_user(num, user_data):
    """ユーザー情報を表示"""
    print(f"{num}. @{user_data.get('username', '?')}")
    if user_data.get("name"):
        print(f"   名前: {user_data['name']}")
    if user_data.get("verified"):
        print(f"   認証: ✓")
    if user_data.get("followers_count"):
        print(f"   フォロワー: {user_data['followers_count']}")
    if user_data.get("following_count"):
        print(f"   フォロー中: {user_data['following_count']}")
    if user_data.get("can_dm") is not None:
        dm_status = "✉ DM開放" if user_data["can_dm"] else "✗ DM閉鎖"
        print(f"   DM: {dm_status}")
    if user_data.get("bio"):
        bio_preview = user_data["bio"].replace("\n", " ")[:50]
        if len(user_data["bio"]) > 50:
            bio_preview += "..."
        print(f"   プロフ: {bio_preview}")
    if user_data.get("quote_text"):
        qt_preview = user_data["quote_text"].replace("\n", " ")[:60]
        if len(user_data["quote_text"]) > 60:
            qt_preview += "..."
        print(f"   引用: {qt_preview}")
    if user_data.get("location"):
        print(f"   場所: {user_data['location']}")
    if user_data.get("url"):
        print(f"   URL: {user_data['url']}")
    print()


_INTERCEPTOR_JS = """
if (!window.__dmInterceptorInstalled) {
    window.__dmInterceptorInstalled = true;
    window.__graphqlResponses = window.__graphqlResponses || [];

    // --- fetch interceptor ---
    const _origFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await _origFetch.apply(this, args);
        try {
            const url = (args[0] instanceof Request) ? args[0].url : String(args[0]);
            if (url.includes('/graphql/') || url.includes('/i/api/')) {
                const clone = response.clone();
                const text = await clone.text();
                window.__graphqlResponses.push({ url: url, body: text });
            }
        } catch(e) {}
        return response;
    };

    // --- XHR interceptor ---
    const _origOpen = XMLHttpRequest.prototype.open;
    const _origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__intUrl = url;
        return _origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        this.addEventListener('load', function() {
            try {
                var u = this.__intUrl || '';
                if (u.includes('/graphql/') || u.includes('/i/api/')) {
                    window.__graphqlResponses.push({ url: u, body: this.responseText });
                }
            } catch(e) {}
        });
        return _origSend.apply(this, arguments);
    };
}
"""


def inject_fetch_interceptor(driver):
    """fetch + XHR をインターセプトしてGraphQL/APIレスポンスを記録するJSを注入。"""
    try:
        driver.execute_script(_INTERCEPTOR_JS)
    except:
        pass


def inject_interceptor_cdp(driver):
    """CDP経由でインターセプターを注入。driver.get()でのページ遷移後も自動で有効になる。"""
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": _INTERCEPTOR_JS
        })
    except Exception as e:
        print(f"[CDP] addScriptToEvaluateOnNewDocument失敗: {e}")
        # フォールバック: 通常の注入
        inject_fetch_interceptor(driver)


def extract_dm_status_from_responses(driver):
    """注入済みインターセプターから集めたレスポンスを解析して
    username → can_dm (bool) のマッピングを返す。"""
    dm_map = {}

    try:
        responses = driver.execute_script("return window.__graphqlResponses || [];")
    except:
        print("[DM] レスポンスデータ取得失敗")
        return dm_map

    print(f"[DM] キャプチャ済みレスポンス数: {len(responses)}")

    for resp in responses:
        try:
            url = resp.get("url", "")
            body_str = resp.get("body", "{}")
            data = json.loads(body_str)

            temp_map = {}
            _extract_can_dm_recursive(data, temp_map)
            if temp_map:
                endpoint = "API"
                for kw in ["Retweeters", "TweetDetail", "UserByScreenName",
                           "Likes", "Followers", "Following", "SearchTimeline"]:
                    if kw in url:
                        endpoint = kw
                        break
                print(f"[DM] {endpoint}: {len(temp_map)}人のDM情報")
                dm_map.update(temp_map)
        except:
            continue

    print(f"[DM] インターセプター合計: {len(dm_map)}人")
    return dm_map


def _ensure_query_hash(driver, operation_name="UserByScreenName",
                       cache_key="__ubsn_hash"):
    """JSバンドルからGraphQLオペレーションのクエリハッシュを取得（キャッシュ付き）"""
    script = """
    var callback = arguments[arguments.length - 1];
    var opName = arguments[0];
    var cacheKey = arguments[1];

    (async function() {
        try {
            var hash = window[cacheKey] || null;
            if (hash) { callback({hash: hash, cached: true}); return; }

            var allScripts = document.querySelectorAll('script[src]');
            var urls = [];
            for (var s = 0; s < allScripts.length; s++) {
                var src = allScripts[s].src || '';
                if (src.endsWith('.js') && !src.includes('polyfill')) urls.push(src);
            }
            var scanned = 0;
            for (var s = 0; s < urls.length; s++) {
                try {
                    var r = await fetch(urls[s]);
                    var txt = await r.text();
                    scanned++;
                    var p1 = new RegExp('queryId:"([^"]+)"[^}]{0,300}operationName:"' + opName + '"');
                    var p2 = new RegExp('operationName:"' + opName + '"[^}]{0,300}queryId:"([^"]+)"');
                    var m = txt.match(p1) || txt.match(p2);
                    if (m) { hash = m[1]; break; }
                } catch(e) {}
            }
            if (hash) {
                window[cacheKey] = hash;
                callback({hash: hash, scanned: scanned});
            } else {
                callback({error: 'query_hash_not_found', scanned: scanned, total: urls.length});
            }
        } catch(e) { callback({error: e.toString()}); }
    })();
    """
    driver.set_script_timeout(60)
    return driver.execute_async_script(script, operation_name, cache_key)


def _fetch_profile_batch(driver, names_batch, delay_ms=200):
    """1バッチ分（最大50人）のプロフィール全データをGraphQL APIで取得。
    DM情報含むフォロワー数等もすべて返す。
    delay_ms: リクエスト間のディレイ（レート制限対策で動的に変更可能）"""
    script = """
    var callback = arguments[arguments.length - 1];
    var names = arguments[0];
    var delayMs = arguments[1];

    (async function() {
        try {
            var hash = window.__ubsn_hash;
            var csrfM = document.cookie.match(/ct0=([^;]+)/);
            if (!hash || !csrfM) { callback({_error: 'no_hash_or_csrf'}); return; }
            var csrf = csrfM[1];

            var features = JSON.stringify({
                "hidden_profile_subscriptions_enabled":true,
                "responsive_web_graphql_exclude_directive_enabled":true,
                "verified_phone_label_enabled":false,
                "subscriptions_verification_info_is_identity_verified_enabled":true,
                "subscriptions_verification_info_verified_since_enabled":true,
                "highlights_tweets_tab_ui_enabled":true,
                "responsive_web_twitter_article_notes_tab_enabled":true,
                "subscriptions_feature_can_gift_premium":true,
                "creator_subscriptions_tweet_preview_api_enabled":true,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,
                "responsive_web_graphql_timeline_navigation_enabled":true
            });
            var fieldToggles = JSON.stringify({"withAuxiliaryUserLabels":false});
            var results = {};
            var success = 0, fail = 0;
            var rateLimited = false;

            for (var i = 0; i < names.length; i++) {
                try {
                    var variables = JSON.stringify({
                        "screen_name": names[i],
                        "withSafetyModeUserFields": true
                    });
                    var url = 'https://x.com/i/api/graphql/' + hash +
                        '/UserByScreenName?variables=' + encodeURIComponent(variables) +
                        '&features=' + encodeURIComponent(features) +
                        '&fieldToggles=' + encodeURIComponent(fieldToggles);

                    var resp = await fetch(url, {
                        headers: {
                            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                            'x-csrf-token': csrf,
                            'x-twitter-active-user': 'yes',
                            'x-twitter-auth-type': 'OAuth2Session',
                            'content-type': 'application/json'
                        },
                        credentials: 'include'
                    });

                    if (resp.status === 429) {
                        // レート制限検知 → 残りは全てスキップ
                        rateLimited = true;
                        fail += (names.length - i);
                        break;
                    }

                    if (resp.ok) {
                        var data = await resp.json();
                        var result = data && data.data && data.data.user && data.data.user.result;

                        if (result) {
                            var legacy = result.legacy || {};
                            var dm_perms = result.dm_permissions || {};
                            var loc = result.location || {};
                            var priv = result.privacy || {};

                            // can_dm判定
                            var can_dm = null;
                            if ('can_dm' in dm_perms) {
                                can_dm = !!dm_perms.can_dm;
                            } else if ('can_dm' in legacy) {
                                can_dm = !!legacy.can_dm;
                            }

                            results[names[i]] = {
                                can_dm: can_dm,
                                followers_count: legacy.followers_count,
                                following_count: legacy.friends_count,
                                statuses_count: legacy.statuses_count,
                                favourites_count: legacy.favourites_count,
                                media_count: legacy.media_count,
                                listed_count: legacy.listed_count,
                                created_at: (result.core && result.core.created_at) || legacy.created_at,
                                location: (loc.location) || legacy.location || null,
                                url: legacy.url || null,
                                description: legacy.description || null,
                                name: (result.core && result.core.name) || legacy.name || null,
                                verified: !!(result.verification && result.verification.verified),
                                is_blue_verified: !!result.is_blue_verified,
                                protected: !!(priv.protected),
                                default_profile_image: !!legacy.default_profile_image,
                                profile_image_url: (result.avatar && result.avatar.image_url)
                                    || legacy.profile_image_url_https || null,
                                profile_banner_url: legacy.profile_banner_url || null,
                                rest_id: result.rest_id || null,
                            };
                            success++;
                        } else {
                            fail++;
                        }
                    } else {
                        fail++;
                        // 連続失敗でレート制限と判断（成功0で5連続失敗）
                        if (success === 0 && fail >= 5) {
                            rateLimited = true;
                            fail += (names.length - i - 1);
                            break;
                        }
                    }

                    // リクエスト間ディレイ
                    if (i < names.length - 1) {
                        await new Promise(function(resolve) { setTimeout(resolve, delayMs); });
                    }
                } catch(e) {
                    fail++;
                    if (success === 0 && fail >= 5) {
                        rateLimited = true;
                        fail += (names.length - i - 1);
                        break;
                    }
                }
            }

            results._stats = {success: success, fail: fail, rateLimited: rateLimited};
            callback(results);
        } catch(e) { callback({_error: e.toString()}); }
    })();
    """
    timeout = max(120, len(names_batch) * 3)
    driver.set_script_timeout(timeout)
    return driver.execute_async_script(script, names_batch, delay_ms)


def _fetch_profile_batch_by_rest_id(driver, id_name_pairs, delay_ms=200):
    """1バッチ分のプロフィールをUserByRestId APIで取得（レート制限500/15分）。
    id_name_pairs: [(rest_id, screen_name), ...]のリスト。
    結果は screen_name をキーにした辞書。"""
    script = """
    var callback = arguments[arguments.length - 1];
    var pairs = arguments[0];
    var delayMs = arguments[1];

    (async function() {
        try {
            var hash = window.__ubri_hash;
            var csrfM = document.cookie.match(/ct0=([^;]+)/);
            if (!hash || !csrfM) { callback({_error: 'no_hash_or_csrf'}); return; }
            var csrf = csrfM[1];

            var features = JSON.stringify({
                "hidden_profile_subscriptions_enabled":true,
                "responsive_web_graphql_exclude_directive_enabled":true,
                "verified_phone_label_enabled":false,
                "subscriptions_verification_info_is_identity_verified_enabled":true,
                "subscriptions_verification_info_verified_since_enabled":true,
                "highlights_tweets_tab_ui_enabled":true,
                "responsive_web_twitter_article_notes_tab_enabled":true,
                "subscriptions_feature_can_gift_premium":true,
                "creator_subscriptions_tweet_preview_api_enabled":true,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,
                "responsive_web_graphql_timeline_navigation_enabled":true
            });
            var results = {};
            var success = 0, fail = 0;
            var rateLimited = false;

            for (var i = 0; i < pairs.length; i++) {
                var restId = pairs[i][0];
                var screenName = pairs[i][1];
                try {
                    var variables = JSON.stringify({
                        "userId": restId,
                        "withSafetyModeUserFields": true
                    });
                    var url = 'https://x.com/i/api/graphql/' + hash +
                        '/UserByRestId?variables=' + encodeURIComponent(variables) +
                        '&features=' + encodeURIComponent(features);

                    var resp = await fetch(url, {
                        headers: {
                            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                            'x-csrf-token': csrf,
                            'x-twitter-active-user': 'yes',
                            'x-twitter-auth-type': 'OAuth2Session',
                            'content-type': 'application/json'
                        },
                        credentials: 'include'
                    });

                    if (resp.status === 429) {
                        rateLimited = true;
                        fail += (pairs.length - i);
                        break;
                    }

                    if (resp.ok) {
                        var data = await resp.json();
                        var result = data && data.data && data.data.user && data.data.user.result;

                        if (result) {
                            var legacy = result.legacy || {};
                            var dm_perms = result.dm_permissions || {};
                            var loc = result.location || {};
                            var priv = result.privacy || {};

                            var can_dm = null;
                            if ('can_dm' in dm_perms) {
                                can_dm = !!dm_perms.can_dm;
                            } else if ('can_dm' in legacy) {
                                can_dm = !!legacy.can_dm;
                            }

                            results[screenName] = {
                                can_dm: can_dm,
                                followers_count: legacy.followers_count,
                                following_count: legacy.friends_count,
                                statuses_count: legacy.statuses_count,
                                favourites_count: legacy.favourites_count,
                                media_count: legacy.media_count,
                                listed_count: legacy.listed_count,
                                created_at: (result.core && result.core.created_at) || legacy.created_at,
                                location: (loc.location) || legacy.location || null,
                                url: legacy.url || null,
                                description: legacy.description || null,
                                name: (result.core && result.core.name) || legacy.name || null,
                                verified: !!(result.verification && result.verification.verified),
                                is_blue_verified: !!result.is_blue_verified,
                                protected: !!(priv.protected),
                                default_profile_image: !!legacy.default_profile_image,
                                profile_image_url: (result.avatar && result.avatar.image_url)
                                    || legacy.profile_image_url_https || null,
                                profile_banner_url: legacy.profile_banner_url || null,
                                rest_id: result.rest_id || null,
                            };
                            success++;
                        } else {
                            fail++;
                        }
                    } else {
                        fail++;
                        if (success === 0 && fail >= 5) {
                            rateLimited = true;
                            fail += (pairs.length - i - 1);
                            break;
                        }
                    }

                    if (i < pairs.length - 1) {
                        await new Promise(function(resolve) { setTimeout(resolve, delayMs); });
                    }
                } catch(e) {
                    fail++;
                    if (success === 0 && fail >= 5) {
                        rateLimited = true;
                        fail += (pairs.length - i - 1);
                        break;
                    }
                }
            }

            results._stats = {success: success, fail: fail, rateLimited: rateLimited};
            callback(results);
        } catch(e) { callback({_error: e.toString()}); }
    })();
    """
    timeout = max(120, len(id_name_pairs) * 3)
    driver.set_script_timeout(timeout)
    return driver.execute_async_script(script, id_name_pairs, delay_ms)


def _process_profile_batch_by_rest_id(driver, id_name_pairs, users_dict, delay_ms=200):
    """UserByRestIdで1バッチ処理。(success, fail, failed_pairs, rate_limited)を返す"""
    try:
        result = _fetch_profile_batch_by_rest_id(driver, id_name_pairs, delay_ms)

        if not result:
            print(f"  結果なし")
            return 0, len(id_name_pairs), list(id_name_pairs), True
        elif "_error" in result:
            print(f"  エラー: {result['_error']}")
            return 0, len(id_name_pairs), list(id_name_pairs), True
        else:
            stats = result.pop("_stats", {})
            s = stats.get("success", 0)
            f = stats.get("fail", 0)
            rate_limited = stats.get("rateLimited", False)
            if rate_limited:
                print(f"  成功: {s}人 / 失敗: {f}人 ⚠ レート制限検知")
            else:
                print(f"  成功: {s}人 / 失敗: {f}人")

            failed_pairs = []
            for rest_id, username in id_name_pairs:
                profile = result.get(username)
                if username in users_dict and isinstance(profile, dict):
                    user = users_dict[username]
                    for key, val in profile.items():
                        if val is not None:
                            user[key] = val
                    if profile.get("description") and not user.get("bio"):
                        user["bio"] = profile["description"]
                elif username in users_dict:
                    failed_pairs.append((rest_id, username))
            return s, f, failed_pairs, rate_limited

    except Exception as e:
        print(f"  バッチ例外: {e}")
        return 0, len(id_name_pairs), list(id_name_pairs), True


def _fetch_dm_batch(driver, names_batch):
    """1バッチ分のDM情報を取得（後方互換用ラッパー）"""
    result = _fetch_profile_batch(driver, names_batch, delay_ms=200)
    if not result or "_error" in result:
        return result
    # プロフィールデータからcan_dmだけ抽出して旧形式に変換
    dm_result = {}
    for key, val in result.items():
        if key == "_stats":
            dm_result[key] = val
        elif isinstance(val, dict):
            dm_result[key] = val.get("can_dm")
        else:
            dm_result[key] = val
    return dm_result


def fetch_dm_status_direct(driver, usernames):
    """ブラウザのログイン済みセッションを使ってGraphQL UserByScreenName APIから
    直接DM情報を取得。バッチ処理で大量ユーザーにも対応。"""
    dm_map = {}
    username_list = list(usernames)

    if not username_list:
        return dm_map

    total = len(username_list)
    print(f"\n[DM直接API] {total}人のDM開放状態をGraphQL APIで直接取得中...")

    # Step 1: クエリハッシュを取得
    try:
        hash_result = _ensure_query_hash(driver)
        if not hash_result or hash_result.get("error"):
            print(f"[DM直接API] ハッシュ取得失敗: {hash_result}")
            return dm_map
        print(f"[DM直接API] ハッシュ: {hash_result.get('hash', '?')}")
    except Exception as e:
        print(f"[DM直接API] ハッシュ取得例外: {e}")
        return dm_map

    # Step 2: 50人ずつバッチ処理
    BATCH_SIZE = 50
    total_success = 0
    total_fail = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = username_list[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[DM直接API] バッチ {batch_num}/{total_batches} ({len(batch)}人)...")

        try:
            result = _fetch_dm_batch(driver, batch)

            if not result:
                print(f"  結果なし")
                total_fail += len(batch)
            elif "_error" in result:
                print(f"  エラー: {result['_error']}")
                total_fail += len(batch)
            else:
                stats = result.pop("_stats", {})
                s = stats.get("success", 0)
                f = stats.get("fail", 0)
                total_success += s
                total_fail += f
                dm_map.update(result)
                print(f"  成功: {s}人 / 失敗: {f}人")

        except Exception as e:
            print(f"  バッチ例外: {e}")
            total_fail += len(batch)

    open_c = sum(1 for v in dm_map.values() if v is True)
    closed_c = sum(1 for v in dm_map.values() if v is False)
    print(f"[DM直接API] 合計 成功: {total_success}人 / 失敗: {total_fail}人")
    print(f"[DM直接API] DM開放: {open_c}人 / DM閉鎖: {closed_c}人")

    return dm_map


def _extract_can_dm_recursive(obj, dm_map):
    """JSONを再帰的に走査してDM情報を抽出。
    新API構造(dm_permissions)と旧構造(legacy.can_dm)の両方に対応。"""
    if isinstance(obj, dict):
        # legacy + dm_permissions がある場合（新旧API両対応）
        if "legacy" in obj and "dm_permissions" in obj:
            legacy = obj["legacy"] if isinstance(obj.get("legacy"), dict) else {}
            core = obj.get("core", {}) if isinstance(obj.get("core"), dict) else {}
            dm_perms = obj["dm_permissions"]
            # screen_name: legacy (旧) → core (新)
            screen_name = legacy.get("screen_name") or core.get("screen_name")
            if screen_name and isinstance(dm_perms, dict):
                if "can_dm" in dm_perms:
                    dm_map[screen_name] = dm_perms["can_dm"]
                elif "can_dm" in legacy:
                    dm_map[screen_name] = legacy["can_dm"]

        # 旧構造: screen_name と can_dm が同じオブジェクトにある場合
        elif "screen_name" in obj and "can_dm" in obj:
            screen_name = obj["screen_name"]
            can_dm = obj["can_dm"]
            dm_map[screen_name] = can_dm

        for v in obj.values():
            _extract_can_dm_recursive(v, dm_map)
    elif isinstance(obj, list):
        for item in obj:
            _extract_can_dm_recursive(item, dm_map)


def _extract_profiles_recursive(obj, profiles_map):
    """JSONを再帰的に走査してユーザーのプロフィール情報をすべて抽出。
    Retweeters/Likes等のAPIレスポンスからlegacyデータを取得する。
    新旧両方のAPI構造に対応:
      旧: legacy.screen_name, legacy.name, legacy.profile_image_url_https
      新: core.screen_name, core.name, avatar.image_url (legacyから移動)"""
    if isinstance(obj, dict):
        # Xのユーザーオブジェクト: legacy があるケース
        if "legacy" in obj and isinstance(obj["legacy"], dict):
            legacy = obj["legacy"]
            core = obj.get("core", {}) if isinstance(obj.get("core"), dict) else {}
            avatar = obj.get("avatar", {}) if isinstance(obj.get("avatar"), dict) else {}
            location_obj = obj.get("location", {}) if isinstance(obj.get("location"), dict) else {}
            privacy_obj = obj.get("privacy", {}) if isinstance(obj.get("privacy"), dict) else {}

            # screen_name: legacy (旧) → core (新)
            screen_name = legacy.get("screen_name") or core.get("screen_name")

            if screen_name and screen_name not in profiles_map:
                profile = {}
                # フォロワー数等 (legacyに残存)
                if "followers_count" in legacy:
                    profile["followers_count"] = legacy["followers_count"]
                if "friends_count" in legacy:
                    profile["following_count"] = legacy["friends_count"]
                if "statuses_count" in legacy:
                    profile["statuses_count"] = legacy["statuses_count"]
                if "favourites_count" in legacy:
                    profile["favourites_count"] = legacy["favourites_count"]
                if "media_count" in legacy:
                    profile["media_count"] = legacy["media_count"]
                if "listed_count" in legacy:
                    profile["listed_count"] = legacy["listed_count"]
                # プロフィール情報: legacy (旧) → core/avatar (新)
                desc = legacy.get("description")
                if not desc:
                    # 新API: profile_bio.description
                    pb = obj.get("profile_bio")
                    if isinstance(pb, dict):
                        desc = pb.get("description")
                if desc:
                    profile["bio"] = desc
                    profile["description"] = desc
                # name: legacy (旧) → core (新)
                name = legacy.get("name") or core.get("name")
                if name:
                    profile["name"] = name
                # location: legacy (旧) → location obj (新)
                loc = legacy.get("location")
                if not loc and location_obj:
                    loc = location_obj.get("location")
                if loc:
                    profile["location"] = loc
                if legacy.get("url"):
                    profile["url"] = legacy["url"]
                # profile_image: legacy (旧) → avatar (新)
                img = legacy.get("profile_image_url_https")
                if not img and avatar:
                    img = avatar.get("image_url")
                if img:
                    profile["profile_image_url"] = img
                if legacy.get("profile_banner_url"):
                    profile["profile_banner_url"] = legacy["profile_banner_url"]
                # created_at: legacy (旧) → core (新)
                created = legacy.get("created_at") or core.get("created_at")
                if created:
                    profile["created_at"] = created
                # verified / blue
                if obj.get("is_blue_verified"):
                    profile["is_blue_verified"] = True
                profile["verified"] = bool(
                    obj.get("verification", {}).get("verified") if isinstance(obj.get("verification"), dict) else False
                )
                profile["default_profile_image"] = bool(legacy.get("default_profile_image"))
                profile["protected"] = bool(
                    legacy.get("protected") or privacy_obj.get("protected")
                )
                if obj.get("rest_id"):
                    profile["rest_id"] = obj["rest_id"]
                # DM情報
                dm_perms = obj.get("dm_permissions", {})
                if isinstance(dm_perms, dict) and "can_dm" in dm_perms:
                    profile["can_dm"] = dm_perms["can_dm"]
                elif "can_dm" in legacy:
                    profile["can_dm"] = legacy["can_dm"]

                if profile:
                    profiles_map[screen_name] = profile

        for v in obj.values():
            _extract_profiles_recursive(v, profiles_map)
    elif isinstance(obj, list):
        for item in obj:
            _extract_profiles_recursive(item, profiles_map)


def extract_profiles_from_responses(driver):
    """インターセプトしたGraphQLレスポンスから全プロフィール情報を抽出。
    username → {followers_count, bio, location, ...} のマッピングを返す。"""
    profiles_map = {}

    try:
        responses = driver.execute_script("return window.__graphqlResponses || [];")
    except:
        print("[プロフィール抽出] レスポンスデータ取得失敗")
        return profiles_map

    print(f"[プロフィール抽出] キャプチャ済みレスポンス数: {len(responses)}")

    for resp in responses:
        try:
            url = resp.get("url", "")
            body_str = resp.get("body", "{}")
            data = json.loads(body_str)

            before = len(profiles_map)
            _extract_profiles_recursive(data, profiles_map)
            added = len(profiles_map) - before
            if added > 0:
                endpoint = "API"
                for kw in ["Retweeters", "TweetDetail", "UserByScreenName",
                           "Likes", "Followers", "Following", "SearchTimeline"]:
                    if kw in url:
                        endpoint = kw
                        break
                print(f"[プロフィール抽出] {endpoint}: +{added}人")
        except:
            continue

    has_dm = sum(1 for p in profiles_map.values() if "can_dm" in p)
    has_followers = sum(1 for p in profiles_map.values() if "followers_count" in p)
    print(f"[プロフィール抽出] 合計: {len(profiles_map)}人 "
          f"(フォロワー数: {has_followers}人, DM情報: {has_dm}人)")
    return profiles_map


def apply_dm_status(users_dict, dm_map):
    """ユーザーデータにcan_dmを適用"""
    for username, user_data in users_dict.items():
        if username in dm_map:
            user_data["can_dm"] = dm_map[username]


def _process_profile_batch(driver, batch, users_dict, delay_ms=200):
    """1バッチ処理してusers_dictにマージ。(success, fail, failed_names, rate_limited)を返す"""
    try:
        result = _fetch_profile_batch(driver, batch, delay_ms)

        if not result:
            print(f"  結果なし")
            return 0, len(batch), list(batch), True
        elif "_error" in result:
            print(f"  エラー: {result['_error']}")
            return 0, len(batch), list(batch), True
        else:
            stats = result.pop("_stats", {})
            s = stats.get("success", 0)
            f = stats.get("fail", 0)
            rate_limited = stats.get("rateLimited", False)
            if rate_limited:
                print(f"  成功: {s}人 / 失敗: {f}人 ⚠ レート制限検知")
            else:
                print(f"  成功: {s}人 / 失敗: {f}人")

            failed_names = []
            for username in batch:
                profile = result.get(username)
                if username in users_dict and isinstance(profile, dict):
                    user = users_dict[username]
                    for key, val in profile.items():
                        if val is not None:
                            user[key] = val
                    # GraphQLの description を bio にもマッピング
                    if profile.get("description") and not user.get("bio"):
                        user["bio"] = profile["description"]
                elif username in users_dict:
                    failed_names.append(username)
            return s, f, failed_names, rate_limited

    except Exception as e:
        print(f"  バッチ例外: {e}")
        return 0, len(batch), list(batch), True


def fetch_user_profiles(driver, users_dict):
    """ユーザープロフィール情報を取得してusers_dictにマージする。
    1. まずインターセプトしたRetweeters等のレスポンスからプロフィール情報を抽出
    2. 不足分のみGraphQL UserByScreenName APIで補完
    レート制限が来たら諦める（インターセプトデータで大半は取得済みのため）。"""
    username_list = list(users_dict.keys())
    if not username_list:
        return

    total = len(username_list)

    # === Phase 1: インターセプトデータからプロフィール情報を抽出 ===
    print("\n" + "=" * 40)
    print("Phase 1: スクロール時のAPIレスポンスからプロフィール抽出")
    print("=" * 40)

    intercepted = extract_profiles_from_responses(driver)

    # インターセプトデータをusers_dictに適用
    enriched_count = 0
    for username, user_data in users_dict.items():
        profile = intercepted.get(username)
        if not profile:
            continue
        changed = False
        for key, val in profile.items():
            if val is not None:
                # 既にある値は上書きしない（UserCellで取得した名前等を優先）
                if key in ("name", "bio") and user_data.get(key):
                    continue
                user_data[key] = val
                changed = True
        if changed:
            enriched_count += 1

    print(f"[Phase 1] {enriched_count}/{total}人のプロフィールをインターセプトデータから適用")

    # === Phase 2: 不足ユーザーを UserByRestId API で補完（500リクエスト/15分） ===
    # can_dm が不明なユーザー、または followers_count がないユーザーを対象
    missing_users = [
        u for u in username_list
        if users_dict[u].get("can_dm") is None
        or users_dict[u].get("followers_count") is None
    ]

    if not missing_users:
        print(f"\n[Phase 2] 全ユーザーのプロフィール情報が取得済みです。API呼び出し不要。")
    else:
        # rest_idがあるユーザーとないユーザーを分ける
        pairs_with_id = []  # [(rest_id, username), ...]
        users_without_id = []  # [username, ...]
        for u in missing_users:
            rest_id = users_dict[u].get("rest_id")
            if rest_id:
                pairs_with_id.append((str(rest_id), u))
            else:
                users_without_id.append(u)

        api_success = 0

        # --- Phase 2a: UserByRestId (500リクエスト/15分) ---
        if pairs_with_id:
            print(f"\n{'=' * 40}")
            print(f"Phase 2a: UserByRestId APIで{len(pairs_with_id)}人を補完")
            print(f"  (レート制限: 500リクエスト/15分)")
            print(f"{'=' * 40}")

            try:
                hash_result = _ensure_query_hash(
                    driver, "UserByRestId", "__ubri_hash")
                if not hash_result or hash_result.get("error"):
                    print(f"[Phase 2a] ハッシュ取得失敗: {hash_result}")
                    # フォールバック: UserByScreenNameに回す
                    users_without_id.extend([u for _, u in pairs_with_id])
                    pairs_with_id = []
                else:
                    print(f"[Phase 2a] ハッシュ: {hash_result.get('hash', '?')}")
            except Exception as e:
                print(f"[Phase 2a] ハッシュ取得例外: {e}")
                users_without_id.extend([u for _, u in pairs_with_id])
                pairs_with_id = []

            BATCH_SIZE = 50
            BATCH_DELAY = 2
            REQUEST_DELAY_MS = 200
            batches_done = 0

            for batch_start in range(0, len(pairs_with_id), BATCH_SIZE):
                batch = pairs_with_id[batch_start:batch_start + BATCH_SIZE]
                batch_num = batch_start // BATCH_SIZE + 1
                batch_total = (len(pairs_with_id) + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"[Phase 2a] バッチ {batch_num}/{batch_total} ({len(batch)}人)...")

                if batches_done > 0:
                    time.sleep(BATCH_DELAY)

                s, f, failed, rate_limited = _process_profile_batch_by_rest_id(
                    driver, batch, users_dict, REQUEST_DELAY_MS)
                api_success += s
                batches_done += 1

                if rate_limited:
                    # 失敗分をUserByScreenNameにフォールバック
                    remaining_pairs = pairs_with_id[batch_start + BATCH_SIZE:]
                    fallback = [u for _, u in failed] + [u for _, u in remaining_pairs]
                    users_without_id.extend(fallback)
                    print(f"[Phase 2a] ⚠ レート制限。残り{len(fallback)}人は"
                          f"UserByScreenNameにフォールバック。")
                    break

            if pairs_with_id:
                print(f"[Phase 2a] API補完: {api_success}人成功")

        # --- Phase 2b: UserByScreenName フォールバック (95リクエスト/15分) ---
        if users_without_id:
            print(f"\n{'=' * 40}")
            print(f"Phase 2b: UserByScreenName APIで残り{len(users_without_id)}人を補完")
            print(f"  (rest_idなし or Phase 2aフォールバック)")
            print(f"{'=' * 40}")

            try:
                hash_result = _ensure_query_hash(driver)
                if not hash_result or hash_result.get("error"):
                    print(f"[Phase 2b] ハッシュ取得失敗: {hash_result}")
                    users_without_id = []
                else:
                    print(f"[Phase 2b] ハッシュ: {hash_result.get('hash', '?')}")
            except Exception as e:
                print(f"[Phase 2b] ハッシュ取得例外: {e}")
                users_without_id = []

            BATCH_SIZE = 50
            BATCH_DELAY = 2
            REQUEST_DELAY_MS = 250
            batches_done = 0

            for batch_start in range(0, len(users_without_id), BATCH_SIZE):
                batch = users_without_id[batch_start:batch_start + BATCH_SIZE]
                batch_num = batch_start // BATCH_SIZE + 1
                batch_total = (len(users_without_id) + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"[Phase 2b] バッチ {batch_num}/{batch_total} ({len(batch)}人)...")

                if batches_done > 0:
                    time.sleep(BATCH_DELAY)

                s, f, failed, rate_limited = _process_profile_batch(
                    driver, batch, users_dict, REQUEST_DELAY_MS)
                api_success += s
                batches_done += 1

                if rate_limited:
                    remaining = len(users_without_id) - batch_start - BATCH_SIZE
                    if remaining > 0:
                        print(f"[Phase 2b] ⚠ レート制限。残り約{remaining}人は取得できず。")
                    break

        print(f"[Phase 2] API補完合計: {api_success}人成功")

    # 最終サマリー
    dm_open = sum(1 for u in users_dict.values() if u.get("can_dm") is True)
    dm_closed = sum(1 for u in users_dict.values() if u.get("can_dm") is False)
    dm_unknown = sum(1 for u in users_dict.values() if u.get("can_dm") is None)
    has_followers = sum(1 for u in users_dict.values()
                        if u.get("followers_count") is not None)
    print(f"\n[結果] === 最終結果 ===")
    print(f"[結果] フォロワー数取得: {has_followers}/{total}人")
    print(f"[結果] DM開放: {dm_open}人 / DM閉鎖: {dm_closed}人 / 不明: {dm_unknown}人")
