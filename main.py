#!/usr/bin/env python3
"""X Campaign Picker - デスクトップアプリ エントリポイント"""

import os
import sys
import time
import socket
import webbrowser
import threading


def find_free_port():
    """空いているポートを自動検出"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def open_browser(port):
    """サーバー起動後にブラウザを自動オープン"""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")


def main():
    # プロジェクトルートをパスに追加
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, base_dir)

    port = find_free_port()
    print(f"X Campaign Picker を起動中...")
    print(f"http://localhost:{port}")

    # バックグラウンドでブラウザ起動
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
