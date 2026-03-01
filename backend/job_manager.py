"""ジョブ管理（スクレイプジョブの状態管理・キューイング）"""

import uuid
import asyncio
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Job:
    id: str
    scraper_type: str  # "retweeters_fast", "retweeters_hover", "quotes"
    url: str
    max_users: int
    status: str = "pending"  # pending, running, completed, failed, cancelled
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[List[Dict]] = None
    result_file: Optional[str] = None
    error: Optional[str] = None
    log_lines: List[str] = field(default_factory=list)
    use_cache: bool = True
    thread: Optional[threading.Thread] = field(default=None, repr=False)


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.log_queue: asyncio.Queue = asyncio.Queue()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def set_loop(self, loop):
        self.loop = loop

    def create_job(self, scraper_type: str, url: str, max_users: int, use_cache: bool = True) -> Job:
        job_id = str(uuid.uuid4())[:8]
        job = Job(
            id=job_id,
            scraper_type=scraper_type,
            url=url,
            max_users=max_users,
            use_cache=use_cache,
            created_at=datetime.now().isoformat(),
        )
        with self._lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def has_running_job(self) -> bool:
        return any(j.status == "running" for j in self.jobs.values())

    def list_jobs(self) -> List[Dict]:
        return [
            {
                "id": j.id,
                "scraper_type": j.scraper_type,
                "url": j.url,
                "max_users": j.max_users,
                "status": j.status,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
                "result_count": len(j.results) if j.results else 0,
                "error": j.error,
            }
            for j in reversed(list(self.jobs.values()))
        ]

    def notify_status(self, job: Job):
        """ジョブステータス変更をWebSocketに通知"""
        if self.loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.log_queue.put({
                        "job_id": job.id,
                        "type": "status",
                        "status": job.status,
                        "result_count": len(job.results) if job.results else 0,
                        "error": job.error,
                    }),
                    self.loop
                )
            except:
                pass
