"""print()出力をキャプチャしてWebSocket経由で配信"""

import io
import asyncio


class LogCapture(io.TextIOBase):
    """sys.stdout の差し替え用。print() の出力をキャプチャして asyncio.Queue に転送。
    job.log_lines にも同期書き込みしてREST APIポーリングでもリアルタイム配信可能。"""

    def __init__(self, job_id, queue, loop, job=None):
        self.job_id = job_id
        self.queue = queue
        self.loop = loop
        self.job = job  # Jobオブジェクト参照（REST API用にリアルタイム更新）
        self.buffer = ""
        self.lines = []

    def _emit(self, line):
        """1行をログリストに追加し、WebSocket キューに送信"""
        self.lines.append(line)
        # Jobオブジェクトにもリアルタイム反映（REST APIポーリング用）
        if self.job is not None:
            self.job.log_lines = self.lines
        try:
            asyncio.run_coroutine_threadsafe(
                self.queue.put({
                    "job_id": self.job_id,
                    "type": "log",
                    "line": line
                }),
                self.loop
            )
        except:
            pass

    def write(self, text):
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line:
                self._emit(line)
        return len(text)

    def flush(self):
        if self.buffer:
            self._emit(self.buffer)
            self.buffer = ""
