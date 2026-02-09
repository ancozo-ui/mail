# -*- coding: utf-8 -*-
"""
allwayz 도메인 메일 관리자 - Flask API.
IMAP으로 'allwayz' 폴더 메일을 JSON 반환.
"""
import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from imap_client import fetch_mails, mark_as_read
from smtp_sender import send_mail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)


@app.route("/")
def index():
    """프론트엔드 페이지."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/mails")
def api_mails():
    """
    allwayz 폴더의 최신 메일 목록을 JSON으로 반환.
    - page, per_page 가 있으면 페이지네이션 응답: { mails, total, page, per_page }.
    - 없으면 limit(기본 100)만큼 반환. 자동 동기화 시 limit=20 등 사용.
    """
    try:
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)
        if page is not None and per_page is not None and per_page >= 1 and page >= 1:
            per_page = min(per_page, 100)
            out = fetch_mails(include_read=True, page=page, per_page=per_page)
            return jsonify({
                "ok": True,
                "mails": out["mails"],
                "total": out["total"],
                "page": page,
                "per_page": per_page,
            })
        limit = request.args.get("limit", type=int) or 100
        limit = min(max(limit, 1), 200)
        mails = fetch_mails(include_read=True, limit=limit)
        return jsonify({"ok": True, "mails": mails})
    except Exception as e:
        logger.exception("api_mails error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/send-mail", methods=["POST"])
def api_send_mail():
    """답장 메일 발송. 발신은 SMTP_USER(hhcho@surff.kr)로 전송."""
    try:
        data = request.get_json() or {}
        to = (data.get("to") or "").strip()
        subject = (data.get("subject") or "").strip()
        body = data.get("body") or ""
        if not to:
            return jsonify({"ok": False, "error": "to required"}), 400
        if send_mail(to, subject, body):
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "send failed"}), 500
    except Exception as e:
        logger.exception("api_send_mail error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mails/<uid>/read", methods=["POST"])
def api_mark_read(uid):
    """메일을 읽음 처리합니다. 모달에서 열었을 때 호출."""
    try:
        if mark_as_read(uid):
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "mark failed"}), 400
    except Exception as e:
        logger.exception("api_mark_read error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
