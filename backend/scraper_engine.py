"""スクレイパー実行エンジン（バックグラウンドスレッドで実行）"""

import sys
import json
import csv
import io
import os
import re
from datetime import datetime
from backend.log_capture import LogCapture
from backend.chrome_utils import get_base_dir
from backend.db import Database


def _enrich_from_cache(db, results):
    """キャッシュから不足情報を補完"""
    usernames = [u.get("username") for u in results if u.get("username")]
    if not usernames:
        return results

    cached = db.get_cached_users(usernames)
    if not cached:
        return results

    enriched_count = 0
    for user in results:
        uname = user.get("username")
        if not uname or uname not in cached:
            continue

        cached_user = cached[uname]
        changed = False
        for field in ("name", "bio", "profile_image_url", "location",
                      "url", "followers_count", "following_count"):
            if not user.get(field) and cached_user.get(field):
                user[field] = cached_user[field]
                changed = True

        if user.get("can_dm") is None and cached_user.get("can_dm") is not None:
            user["can_dm"] = cached_user["can_dm"]
            changed = True

        if changed:
            enriched_count += 1

    if enriched_count > 0:
        print(f"[キャッシュ] {enriched_count}人のプロフィールをキャッシュから補完しました")

    return results


def run_scraper_job(job, job_manager):
    """スクレイパーをバックグラウンドスレッドで実行"""
    capture = LogCapture(job.id, job_manager.log_queue, job_manager.loop, job=job)
    old_stdout = sys.stdout
    db = Database()

    try:
        sys.stdout = capture
        job.status = "running"
        job.started_at = datetime.now().isoformat()
        job_manager.notify_status(job)

        if job.scraper_type == "retweeters_fast":
            from scrapers.retweeters_fast import scrape_retweeters
            results = scrape_retweeters(job.url, job.max_users)
        elif job.scraper_type == "retweeters_hover":
            from scrapers.retweeters_hover import scrape_retweeters
            results = scrape_retweeters(job.url, job.max_users)
        elif job.scraper_type == "quotes":
            from scrapers.quotes import scrape_quotes
            results = scrape_quotes(job.url, job.max_users)
        else:
            raise ValueError(f"Unknown scraper type: {job.scraper_type}")

        # キャッシュから不足情報を補完
        if job.use_cache:
            results = _enrich_from_cache(db, results)
        else:
            print("[キャッシュ] キャッシュ補完: OFF")

        job.results = results
        result_file = _save_results(job)
        job.result_file = result_file

        # DBに保存（キャッシュOFFでもDB保存とキャッシュ更新は行う）
        db.save_job(job)
        db.cache_users(results)

        job.status = "completed"
        job.completed_at = datetime.now().isoformat()
        print(f"\n完了: {len(results)}件取得しました。")

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.completed_at = datetime.now().isoformat()
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        sys.stdout = old_stdout
        job_manager.notify_status(job)


def _save_results(job):
    """結果をJSONファイルに保存"""
    base = get_base_dir()
    results_dir = os.path.join(base, "results")
    os.makedirs(results_dir, exist_ok=True)

    # ツイートIDを抽出
    match = re.search(r"/status/(\d+)", job.url)
    tweet_id = match.group(1) if match else "unknown"

    prefix = {
        "retweeters_fast": "retweeters",
        "retweeters_hover": "retweeters",
        "quotes": "quotes",
    }.get(job.scraper_type, "results")

    filename = f"{prefix}_{tweet_id}_{job.id}.json"
    filepath = os.path.join(results_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(job.results, f, ensure_ascii=False, indent=2)

    print(f"保存: {filepath}")
    return filepath


def generate_csv(results):
    """結果をCSV文字列に変換"""
    if not results:
        return ""

    output = io.StringIO()
    fields = ["username", "name", "followers_count", "following_count",
              "statuses_count", "favourites_count", "media_count", "listed_count",
              "bio", "quote_text", "verified", "is_blue_verified", "can_dm",
              "protected", "created_at", "location", "url", "rest_id"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()

    for row in results:
        clean = {}
        for k in fields:
            val = row.get(k, "")
            if val is None:
                val = ""
            clean[k] = str(val).replace("\n", " ").replace("\r", "")
        writer.writerow(clean)

    return output.getvalue()
