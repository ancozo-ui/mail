# Vercel Serverless Function: /api/check-messages (Cron 1분마다 호출)
# 파일명: check_messages.py → 경로: /api/check-messages
import json
import os
import sys

# 프로젝트 루트에서 imap_client import 가능하도록
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # CRON_SECRET 인증 (선택사항이지만 보안을 위해 권장)
        cron_secret = os.environ.get("CRON_SECRET")
        if cron_secret:
            auth_header = self.headers.get("Authorization", "")
            if auth_header != f"Bearer {cron_secret}":
                body = json.dumps({"ok": False, "error": "Unauthorized"}).encode("utf-8")
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        try:
            from imap_client import fetch_mails

            # 메일 체크 실행
            fetch_mails(include_read=True, limit=20)
            
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        pass
