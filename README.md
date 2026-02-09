# allwayz 도메인 메일 관리자

Daum 스마트워크의 **allwayz** 폴더(op@allwayzio.com 도메인 메일)만 보여주는 그룹웨어 대시보드입니다.

## 요구 사항

- Python 3.8+
- Daum IMAP: `imap.daum.net:993` (SSL)

## 설치 및 실행

```bash
cd dev/mail
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

브라우저에서 **http://localhost:5050** 으로 접속합니다. (`PORT` 환경 변수로 포트 변경 가능)

## 동작 방식

- **폴더**: INBOX가 아닌 `allwayz` 폴더만 사용합니다. (`config.py`의 `TARGET_FOLDER`)
- **동기화**: `SELECT "allwayz", readonly=False` 로 폴더를 선택해 서버 상태를 갱신한 뒤, `UID SEARCH UNSEEN/ALL` 로 목록을 가져옵니다.
- **읽음 상태 유지**: 메일 본문은 `BODY.PEEK[]` 로만 가져와서, 앱에서 읽어도 Daum 쪽에서는 안 읽음으로 유지됩니다.
- **프론트**: 새로고침 버튼으로 API를 호출해 목록을 갱신하고, 안 읽은 메일은 강조 표시되며, 항목 클릭 시 모달로 본문을 봅니다.

## 설정

`config.py` 또는 환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `IMAP_HOST` | imap.daum.net | IMAP 서버 |
| `IMAP_PORT` | 993 | SSL 포트 |
| `IMAP_USER` | cpu-ho | 로그인 ID |
| `IMAP_PASS` | (설정된 값) | 비밀번호 |
| `IMAP_FOLDER` | allwayz | 대상 폴더 |
| `SMTP_HOST` | smtp.gmail.com | 답장 발송용 SMTP 서버 |
| `SMTP_PORT` | 587 | SMTP 포트 |
| `SMTP_USER` | hhcho@surff.kr | 답장 발신 주소 (op@allwayzio.com이 아님) |
| `SMTP_PASS` | (비어 있음) | **필수** 답장용 비밀번호(또는 앱 비밀번호) |

**답장 기능**: 메일 읽기 모달에서 "답장" 버튼을 누르면 **hhcho@surff.kr** 계정으로 발송됩니다. `SMTP_PASS`를 반드시 설정해야 합니다. Gmail이면 앱 비밀번호 사용을 권장합니다.

프로덕션에서는 반드시 `IMAP_PASS`, `SMTP_PASS` 등을 환경 변수로 설정해 사용하세요.

## Vercel에 프론트만 배포할 때 (자동 수신 등 API 연동)

프론트(HTML/JS)만 Vercel에 올리면 `/api/mails` 요청이 Vercel 쪽으로 가서 백엔드가 없어 **자동 수신(30초 폴링)·목록·답장**이 동작하지 않습니다.

**방법 1 – 백엔드 URL 지정**

1. Flask 백엔드는 **Railway, Render, Fly.io** 등 다른 서비스에 배포합니다.
2. `static/index.html`의 `<head>` 안에 아래 한 줄을 넣습니다 (백엔드 주소만 본인 걸로 바꿈).

   ```html
   <meta name="mail-api-base" content="https://your-backend.railway.app">
   ```

3. Vercel에 다시 배포하면, 자동 수신·목록·답장 요청이 모두 위 백엔드로 갑니다.

**방법 2 – 스크립트로 지정**

`index.html`의 `<script>` 바로 위에 추가:

```html
<script>window.MAIL_API_BASE = 'https://your-backend.railway.app';</script>
```

백엔드 서버에서는 **CORS**가 허용돼 있어야 합니다. (`app.py`에 `CORS(app)` 있음)
