"""PyInstaller エントリポイント: バックエンドサーバーを起動する"""
import sys
import uvicorn

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("backend.app:app", host="127.0.0.1", port=port, log_level="warning")
