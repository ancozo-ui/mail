# Daum 스마트워크 IMAP 설정
# 프로덕션에서는 환경 변수로 덮어쓰세요: IMAP_HOST, IMAP_USER, IMAP_PASS
import os

IMAP_HOST = os.environ.get("IMAP_HOST", "imap.daum.net")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = os.environ.get("IMAP_USER", "cpu-ho")
IMAP_PASS = os.environ.get("IMAP_PASS", "jtacdmswymrnmpgn")
# allwayz: 계정 내 메일이 자동 분류되는 폴더 (INBOX가 아님)
TARGET_FOLDER = os.environ.get("IMAP_FOLDER", "allwayz")

# 답장 발송용 SMTP (Daum 스마트워크 op@allwayzio.com 동일 계정)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.daum.net")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "op@allwayzio.com")
SMTP_PASS = os.environ.get("SMTP_PASS", IMAP_PASS)
