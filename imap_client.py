# -*- coding: utf-8 -*-
"""
allwayz 폴더 전용 IMAP 클라이언트.

[동기화 이슈 해결]
- Daum 웹메일에서 '읽음' 처리해야만 앱에 보이던 문제를 줄이기 위해:
  1. SELECT 시 readonly=False: Read-only 모드가 아니어야 서버가 RECENT/UNSEEN
     인덱스를 최신으로 갱신합니다. 일부 서버는 readonly면 갱신이 지연됩니다.
  2. UID SEARCH: imap.search(None, 'ALL') 대신 conn.uid('search', None, 'UNSEEN')
     및 'ALL'을 사용해 UID 기준으로 안정적으로 검색합니다.
  3. BODY.PEEK[]: FETCH 시 BODY[] 대신 BODY.PEEK[]를 사용해 메일을 가져와도
     서버에 \\Seen 플래그가 세워지지 않습니다. 사용자가 원할 때만 읽음 처리 가능.

[추가 개선 가능]
- IDLE (RFC 2177): SELECT 후 conn.idle() 로 서버 푸시 알림을 받으면
  새 메일 도착 시 즉시 반영할 수 있습니다. 장기 연결이 필요합니다.
- 주기적 RECENT 체크: SELECT 응답의 RECENT 개수를 주기적으로 확인해
  변경 시에만 전체 목록을 다시 가져오는 방식으로 실시간성을 높일 수 있습니다.
"""
import imaplib
import email
from email import policy
from email.parser import BytesParser
import ssl
from typing import List, Dict, Any, Optional
import logging

from config import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS, TARGET_FOLDER

logger = logging.getLogger(__name__)


def decode_mime_words(s: str) -> str:
    """RFC 2047 인코딩된 헤더(예: =?UTF-8?B?...) 디코딩."""
    if not s:
        return ""
    try:
        decoded_parts = email.header.decode_header(s)
        result = []
        for part, enc in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                result.append(part or "")
        return " ".join(result).strip()
    except Exception:
        return str(s)


def get_text_from_msg(msg: email.message.Message) -> str:
    """멀티파트 메시지에서 텍스트 본문 추출 (HTML이면 텍스트 우선, 없으면 HTML)."""
    text_body = ""
    html_body = ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain":
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    text_body = payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
            except Exception:
                pass
        elif ctype == "text/html":
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
            except Exception:
                pass
    return text_body.strip() or html_body.strip() or "(본문 없음)"


def fetch_mails(
    include_read: bool = True,
    limit: int = 100,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
):
    """
    'allwayz' 폴더에서 메일 목록을 가져옵니다.
    - page, per_page 가 둘 다 주어지면: 해당 페이지만 페치하고 {"mails": [...], "total": N} 반환.
    - 그 외: limit 개만 페치하고 리스트만 반환 (기존 동작).
    - BODY.PEEK[] 로 페치하여 읽음 상태 변경 없음.
    """
    result: List[Dict[str, Any]] = []
    ssl_context = ssl.create_default_context()
    conn: Optional[imaplib.IMAP4_SSL] = None
    use_pagination = page is not None and per_page is not None and per_page > 0 and page >= 1

    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl_context)
        conn.login(IMAP_USER, IMAP_PASS)

        status, _ = conn.select(TARGET_FOLDER, readonly=False)
        if status != "OK":
            logger.warning("select(%s) failed: %s", TARGET_FOLDER, _)
            return {"mails": [], "total": 0} if use_pagination else []

        unseen_uids: List[bytes] = []
        try:
            _status, unseen_data = conn.uid("search", None, "UNSEEN")
            if _status == "OK" and unseen_data and unseen_data[0]:
                unseen_uids = unseen_data[0].split()
        except Exception as e:
            logger.warning("UNSEEN search failed: %s", e)

        all_uids: List[bytes] = []
        try:
            _status, all_data = conn.uid("search", None, "ALL")
            if _status == "OK" and all_data and all_data[0]:
                all_uids = all_data[0].split()
        except Exception as e:
            logger.warning("ALL search failed: %s", e)

        def uid_sort_key(b: bytes) -> int:
            try:
                return int(b)
            except (ValueError, TypeError):
                return 0
        if not include_read:
            ordered_uids = sorted(unseen_uids, key=uid_sort_key, reverse=True)
        else:
            ordered_uids = sorted(all_uids, key=uid_sort_key, reverse=True)

        if use_pagination:
            total = len(ordered_uids)
            start = (page - 1) * per_page
            page_uids = ordered_uids[start : start + per_page]
            if not page_uids:
                return {"mails": [], "total": total}
            ordered_uids = page_uids
        else:
            ordered_uids = ordered_uids[:limit]
            if not ordered_uids:
                return []

        uid_list = b",".join(ordered_uids)
        status, data = conn.uid("fetch", uid_list, "(FLAGS BODY.PEEK[])")
        if status != "OK" or not data:
            return {"mails": [], "total": total} if use_pagination else []

        for item in data:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            raw = item[1]
            if raw is None:
                continue
            try:
                msg = BytesParser(policy=policy.default).parsebytes(raw)
            except Exception:
                continue

            # fetch 응답 첫 번째 요소: b'1 (FLAGS (\\Seen) UID 123 BODY.PEEK[] ...'
            header = item[0]
            if isinstance(header, bytes):
                header = header.decode("utf-8", errors="replace")
            is_seen = "\\Seen" in header or "Seen" in header
            # UID 추출 (마지막 숫자 시퀀스가 UID)
            uid = None
            for part in header.replace(")", " ").replace("(", " ").split():
                if part.isdigit():
                    uid = part
            # BODY 앞의 숫자가 UID인 경우가 많음
            if "UID" in header:
                i = header.find("UID")
                rest = header[i + 3 :].strip()
                uid = rest.split()[0] if rest.split() else uid

            from_hdr = msg.get("From", "")
            to_hdr = msg.get("To", "")
            subj_hdr = msg.get("Subject", "")
            date_hdr = msg.get("Date", "")

            result.append({
                "uid": uid,
                "from": decode_mime_words(from_hdr),
                "to": decode_mime_words(to_hdr),
                "subject": decode_mime_words(subj_hdr),
                "date": date_hdr,
                "body": get_text_from_msg(msg),
                "seen": is_seen,
            })

        result.sort(key=lambda m: int(m.get("uid") or 0), reverse=True)
    except imaplib.IMAP4.error as e:
        logger.exception("IMAP error: %s", e)
        raise
    finally:
        if conn:
            try:
                conn.logout()
            except Exception:
                pass

    if use_pagination:
        return {"mails": result, "total": total}
    return result


def mark_as_read(uid: str) -> bool:
    """
    해당 UID 메일을 서버에서 읽음(\\Seen) 처리합니다.
    allwayz 폴더 선택 후 UID STORE로 +FLAGS \\Seen 수행.
    """
    if not uid:
        return False
    ssl_context = ssl.create_default_context()
    conn: Optional[imaplib.IMAP4_SSL] = None
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl_context)
        conn.login(IMAP_USER, IMAP_PASS)
        status, _ = conn.select(TARGET_FOLDER, readonly=False)
        if status != "OK":
            return False
        conn.uid("store", str(uid), "+FLAGS", "\\Seen")
        return True
    except Exception as e:
        logger.warning("mark_as_read(%s) failed: %s", uid, e)
        return False
    finally:
        if conn:
            try:
                conn.logout()
            except Exception:
                pass
