# Daily AI Brief 메일 자동 발송 설정

워크플로(`.github/workflows/publish_daily_ai_brief.yml`)에 메일 발송 단계가 추가되어 있습니다.

## 1) GitHub Secrets 등록

리포지토리 `Settings > Secrets and variables > Actions`에서 아래 값을 추가하세요.

- `EMAIL_SMTP_HOST` : SMTP 서버 주소 (예: `smtp.gmail.com`)
- `EMAIL_SMTP_PORT` : SMTP 포트 (TLS: `587`, SSL: `465`)
- `EMAIL_SMTP_USER` : 발신 계정 아이디(일반적으로 이메일 주소)
- `EMAIL_SMTP_PASSWORD` : SMTP 비밀번호 (Gmail은 앱 비밀번호 권장)
- `EMAIL_FROM` : 발신자 주소 (보통 `EMAIL_SMTP_USER`와 동일)
- `EMAIL_TO` : 수신자 주소(여러 명이면 콤마로 구분)

예시:

```text
EMAIL_TO=ceo@example.com,team@example.com
```

## 2) 동작 방식

- 평일 오전 9시(KST) 또는 수동 실행 시:
  1. 기사 수집/요약 생성
  2. `docs/data` 갱신 및 커밋
  3. 최신 리포트를 SMTP 메일로 발송

- 메일 관련 시크릿이 비어 있으면 메일 단계는 자동 스킵됩니다.

## 3) 로컬 테스트 (선택)

환경변수 설정 후 아래 명령으로 메일 단계만 테스트할 수 있습니다.

```powershell
python scripts/send_daily_report_email.py --input-dir docs/data --dry-run
```

실제 발송:

```powershell
python scripts/send_daily_report_email.py --input-dir docs/data
```
