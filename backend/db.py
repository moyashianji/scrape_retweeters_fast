"""SQLite データベース管理（ジョブ履歴・ユーザーキャッシュ）"""

import os
import re
import sqlite3
import threading
from datetime import datetime
from backend.chrome_utils import get_base_dir


class Database:
    """Thread-safe SQLite wrapper"""

    def __init__(self):
        base = get_base_dir()
        db_dir = os.path.join(base, "data")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "xcampaign.db")
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                scraper_type TEXT NOT NULL,
                url TEXT NOT NULL,
                tweet_id TEXT,
                max_users INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                result_count INTEGER DEFAULT 0,
                result_file TEXT
            );

            CREATE TABLE IF NOT EXISTS user_cache (
                username TEXT PRIMARY KEY,
                name TEXT,
                bio TEXT,
                verified INTEGER DEFAULT 0,
                profile_image_url TEXT,
                location TEXT,
                url TEXT,
                followers_count TEXT,
                following_count TEXT,
                can_dm INTEGER,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_users (
                job_id TEXT NOT NULL,
                username TEXT NOT NULL,
                quote_text TEXT,
                PRIMARY KEY (job_id, username)
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
            CREATE INDEX IF NOT EXISTS idx_job_users_user ON job_users(username);
        """)
        conn.commit()

    # --- Job operations ---

    def save_job(self, job):
        """完了/失敗したジョブをDBに保存"""
        conn = self._get_conn()
        tweet_id = None
        m = re.search(r"/status/(\d+)", job.url)
        if m:
            tweet_id = m.group(1)

        result_count = len(job.results) if job.results else 0

        conn.execute(
            """INSERT OR REPLACE INTO jobs
               (id, scraper_type, url, tweet_id, max_users, status,
                created_at, completed_at, result_count, result_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job.id, job.scraper_type, job.url, tweet_id, job.max_users,
             job.status, job.created_at, job.completed_at,
             result_count, job.result_file),
        )

        if job.results:
            conn.executemany(
                """INSERT OR REPLACE INTO job_users (job_id, username, quote_text)
                   VALUES (?, ?, ?)""",
                [(job.id, u.get("username"), u.get("quote_text"))
                 for u in job.results if u.get("username")],
            )

        conn.commit()

    def list_jobs(self, limit=100, offset=0):
        """履歴一覧（新しい順）"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, scraper_type, url, tweet_id, max_users, status,
                      created_at, completed_at, result_count, result_file
               FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_job(self, job_id):
        """ジョブ詳細"""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def get_job_results(self, job_id):
        """job_users + user_cache をJOINしてユーザー一覧を再構成"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT uc.username, uc.name, uc.bio, uc.verified,
                      uc.profile_image_url, uc.location, uc.url,
                      uc.followers_count, uc.following_count, uc.can_dm,
                      ju.quote_text
               FROM job_users ju
               JOIN user_cache uc ON ju.username = uc.username
               WHERE ju.job_id = ?""",
            (job_id,),
        ).fetchall()

        results = []
        for r in rows:
            user = dict(r)
            user["verified"] = bool(user.get("verified"))
            if user.get("can_dm") is not None:
                user["can_dm"] = bool(user["can_dm"])
            results.append(user)
        return results

    def delete_job(self, job_id):
        """ジョブと関連データを削除"""
        conn = self._get_conn()
        conn.execute("DELETE FROM job_users WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()

    # --- User cache operations ---

    def cache_users(self, users_list):
        """ユーザーリストをキャッシュに保存/更新（NULLフィールドは上書きしない）"""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        for user in users_list:
            username = user.get("username")
            if not username:
                continue

            existing = conn.execute(
                "SELECT * FROM user_cache WHERE username = ?", (username,)
            ).fetchone()

            if existing:
                # 既存データがある場合: 新しいデータの非NULLフィールドで更新
                updates = {}
                for field in ("name", "bio", "profile_image_url", "location",
                              "url", "followers_count", "following_count"):
                    new_val = user.get(field)
                    if new_val is not None:
                        updates[field] = new_val

                if user.get("verified"):
                    updates["verified"] = 1
                if user.get("can_dm") is not None:
                    updates["can_dm"] = 1 if user["can_dm"] else 0

                if updates:
                    updates["updated_at"] = now
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    vals = list(updates.values()) + [username]
                    conn.execute(
                        f"UPDATE user_cache SET {set_clause} WHERE username = ?",
                        vals,
                    )
            else:
                # 新規ユーザー
                can_dm = None
                if user.get("can_dm") is not None:
                    can_dm = 1 if user["can_dm"] else 0

                conn.execute(
                    """INSERT INTO user_cache
                       (username, name, bio, verified, profile_image_url,
                        location, url, followers_count, following_count,
                        can_dm, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (username, user.get("name"), user.get("bio"),
                     1 if user.get("verified") else 0,
                     user.get("profile_image_url"), user.get("location"),
                     user.get("url"), user.get("followers_count"),
                     user.get("following_count"), can_dm, now),
                )

        conn.commit()

    def get_cached_users(self, usernames):
        """複数ユーザーのキャッシュを一括取得"""
        if not usernames:
            return {}

        conn = self._get_conn()
        result = {}
        # SQLiteのパラメータ上限対策: 100人ずつ
        for i in range(0, len(usernames), 100):
            batch = usernames[i:i + 100]
            placeholders = ",".join("?" * len(batch))
            rows = conn.execute(
                f"SELECT * FROM user_cache WHERE username IN ({placeholders})",
                batch,
            ).fetchall()
            for r in rows:
                d = dict(r)
                d["verified"] = bool(d.get("verified"))
                if d.get("can_dm") is not None:
                    d["can_dm"] = bool(d["can_dm"])
                result[d["username"]] = d
        return result

    def get_cache_stats(self):
        """キャッシュ統計"""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM user_cache").fetchone()[0]
        with_dm = conn.execute(
            "SELECT COUNT(*) FROM user_cache WHERE can_dm IS NOT NULL"
        ).fetchone()[0]
        jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return {
            "cached_users": total,
            "users_with_dm": with_dm,
            "total_jobs": jobs_count,
        }
