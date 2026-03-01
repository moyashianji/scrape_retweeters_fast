"""FastAPI アプリケーション（REST API + WebSocket）"""

import asyncio
import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from backend.job_manager import JobManager
from backend.scraper_engine import run_scraper_job, generate_csv
from backend.db import Database


# --- グローバル ---
job_manager = JobManager()
db = Database()
connected_clients: set = set()


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    job_manager.set_loop(loop)
    task = asyncio.create_task(broadcast_logs())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

# Electron からのリクエストを受け付けるため CORS を許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic モデル ---
class StartScrapeRequest(BaseModel):
    scraper_type: str
    url: str
    max_users: int = 500
    use_cache: bool = True


# --- REST API ---

@app.post("/api/scrape")
async def start_scrape(req: StartScrapeRequest):
    if req.scraper_type not in ("retweeters_fast", "retweeters_hover", "quotes"):
        return JSONResponse(status_code=400, content={"error": "Invalid scraper type"})

    if job_manager.has_running_job():
        return JSONResponse(status_code=409, content={
            "error": "別のジョブが実行中です。完了してからもう一度お試しください。"
        })

    job = job_manager.create_job(
        scraper_type=req.scraper_type,
        url=req.url,
        max_users=req.max_users,
        use_cache=req.use_cache,
    )

    thread = threading.Thread(
        target=run_scraper_job,
        args=(job, job_manager),
        daemon=True,
    )
    job.thread = thread
    thread.start()

    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs")
async def list_jobs():
    return job_manager.list_jobs()


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return {
        "id": job.id,
        "scraper_type": job.scraper_type,
        "url": job.url,
        "max_users": job.max_users,
        "status": job.status,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "result_count": len(job.results) if job.results else 0,
        "error": job.error,
    }


@app.get("/api/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    job = job_manager.get_job(job_id)
    if not job or not job.results:
        return JSONResponse(status_code=404, content={"error": "No results"})
    return job.results


@app.get("/api/jobs/{job_id}/csv")
async def download_csv(job_id: str):
    job = job_manager.get_job(job_id)
    if not job or not job.results:
        return JSONResponse(status_code=404, content={"error": "No results"})

    csv_content = generate_csv(job.results)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="results_{job_id}.csv"'
        }
    )


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return {"lines": job.log_lines}


# --- 履歴 API ---

@app.get("/api/history")
async def list_history(limit: int = 100, offset: int = 0):
    return db.list_jobs(limit=limit, offset=offset)


@app.get("/api/history/{job_id}/results")
async def get_history_results(job_id: str):
    results = db.get_job_results(job_id)
    if not results:
        return JSONResponse(status_code=404, content={"error": "No results"})
    return results


@app.get("/api/history/{job_id}/csv")
async def download_history_csv(job_id: str):
    results = db.get_job_results(job_id)
    if not results:
        return JSONResponse(status_code=404, content={"error": "No results"})
    csv_content = generate_csv(results)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="results_{job_id}.csv"'},
    )


@app.delete("/api/history/{job_id}")
async def delete_history(job_id: str):
    db.delete_job(job_id)
    return {"ok": True}


@app.get("/api/cache/stats")
async def cache_stats():
    return db.get_cache_stats()


# --- WebSocket ---

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # クライアントからのメッセージを待つ（接続維持のため）
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except:
        connected_clients.discard(websocket)


async def broadcast_logs():
    """ログキューからメッセージを読み出してWebSocketクライアントに配信"""
    while True:
        try:
            msg = await job_manager.log_queue.get()
            disconnected = set()
            for client in list(connected_clients):
                try:
                    await client.send_json(msg)
                except:
                    disconnected.add(client)
            connected_clients -= disconnected
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
