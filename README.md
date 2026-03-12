# Daily AI Scrap Repository Guide (Tracked Files Only)

## 범위
이 문서는 **Git에 추적되고(push 대상인) 파일만** 설명합니다.

- 기준 명령: `git ls-files`
- 기준 커밋: `e107cd3`
- 추적 파일 수: **26개**
- 제외 대상: 로컬 전용(untracked) 파일/폴더 전체

## 저장소 목적
이 저장소는 아래 기능을 제공하는 배포형 프로젝트입니다.

1. 일일 AI 뉴스 수집/요약 리포트 생성
2. GitHub Actions를 통한 자동 발행
3. GitHub Pages + PWA 웹앱으로 리포트 제공
4. 최신 리포트 alias/index 생성 및 이메일 발송 보조 스크립트 제공

## 디렉터리 구조 요약
| 경로 | 파일 수 | 설명 |
|---|---:|---|
| `(root)` | 7 | 실행 엔트리, 설정, 문서 |
| `.github/` | 1 | 배포 자동화 워크플로 |
| `scripts/` | 3 | 발행/메일/보안 스크립트 |
| `docs/` | 15 | 웹앱(PWA) + 배포 데이터 |

---

## 1) 루트 파일 상세 (7)

### `.gitignore`
- 역할: 가상환경/산출물 무시 규칙 정의
- 특징: `docs/data/**`는 예외적으로 추적 허용(배포 데이터 유지 목적)

### `DAILY_AI_AGENT.md`
- 역할: `daily_ai_news_agent.py` 실행 가이드
- 내용: 기본 실행, dry-run, 설정 변경, GitHub Pages/Actions 배포 절차

### `daily_ai_agent_config.json`
- 역할: 뉴스 수집/분류/요약 정책 설정
- 주요 키 구조:
  - `sources[]`: RSS/Atom 피드 목록
  - `topic_rules`: 주제 분류 규칙
  - `issue_rules`: 핵심 이슈 라벨 규칙
  - `llm`: 요약 모델 옵션
  - `report_options`: 기사 수/중복 제거/조회 기간 옵션

### `daily_ai_news_agent.py`
- 역할: 메인 실행 스크립트(수집→가공→요약→리포트 출력)
- 처리 흐름:
  1. 피드 수집(`sources`)
  2. RSS/Atom 파싱
  3. URL/제목 시그니처 기반 중복 제거
  4. 기간 필터링 + 부족 시 백필(backfill)
  5. 주제/이슈/키워드 분류
  6. LLM 요약(또는 fallback 요약)
  7. Markdown/JSON 리포트 생성
- 주요 출력 파일명 패턴:
  - `daily_ai_brief_YYYY-MM-DD.md`
  - `daily_ai_brief_YYYY-MM-DD.json`

### `EMAIL_AUTOSEND_SETUP.md`
- 역할: GitHub Secrets 기반 SMTP 메일 자동 발송 설정 문서

### `requirements_daily_agent.txt`
- 역할: 런타임 의존성 정의
- 현재 항목:
  - `openai>=1.30.0`
  - `python-dotenv>=1.0.1`

### `README.md`
- 역할: 현재 문서

---

## 2) GitHub Actions 파일 상세 (1)

### `.github/workflows/publish_daily_ai_brief.yml`
- 역할: 일일 리포트 자동 생성/게시 파이프라인
- 트리거:
  - `workflow_dispatch` (수동)
  - `schedule` (평일 크론)
- 단계:
  1. Checkout
  2. Python 설정 및 의존성 설치
  3. `daily_ai_news_agent.py` 실행 (`docs/data`에 산출)
  4. `scripts/publish_latest_report.py` 실행 (`latest.*`, `index.json` 갱신)
  5. 변경분 커밋/푸시
  6. `scripts/send_daily_report_email.py` 실행

---

## 3) 스크립트 파일 상세 (3)

### `scripts/publish_latest_report.py`
- 역할: 날짜별 리포트 중 최신본을 alias로 갱신
- 입력: `docs/data/daily_ai_brief_YYYY-MM-DD.json|md`
- 출력:
  - `docs/data/latest.json`
  - `docs/data/latest.md`
  - `docs/data/index.json`

### `scripts/secret_scan.py`
- 역할: 텍스트 파일에서 잠재 비밀키 정규식 스캔
- 탐지 규칙 예:
  - Google/OpenAI/Anthropic 키 패턴
  - GitHub token/pat
  - AWS access key
  - generic `api_key/secret/token` 대입 패턴

### `scripts/send_daily_report_email.py`
- 역할: 최신 리포트를 SMTP 메일로 발송
- 입력 환경변수:
  - `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`
  - `EMAIL_FROM`, `EMAIL_TO`, `REPORT_SITE_URL`
- 기능:
  - `latest.json` 또는 지정 날짜 JSON 선택
  - 본문 구성 + JSON/MD 첨부
  - `--dry-run` 지원

---

## 4) 웹앱/배포 파일 상세 (`docs/`, 15)

### 4.1 웹앱 런타임 파일

#### `docs/index.html`
- 역할: Daily AI Brief 웹 UI 메인
- 기능:
  - `docs/data/latest.json` 로드 및 카드 렌더링
  - 과거 리포트 링크(`docs/data/index.json`)
  - PWA 설치 UX
  - 오프라인/캐시 표시
  - 선택형 질문 기능(사용자 opt-in + API key 입력 시 외부 API 호출)

#### `docs/sw.js`
- 역할: Service Worker 캐시 전략
- 전략:
  - App shell 캐시
  - `docs/data/*.json` stale-while-revalidate
  - navigation network-first + offline fallback

#### `docs/manifest.webmanifest`
- 역할: PWA 메타
- 포함: 앱명, scope/start_url, theme/background, icons

#### `docs/offline.html`
- 역할: 오프라인 상태 안내 페이지

#### `docs/icons/icon-192.png`
#### `docs/icons/icon-512.png`
#### `docs/icons/icon-512-maskable.png`
- 역할: 설치 아이콘 세트

#### `docs/PWA_MOBILE_TEST_CHECKLIST.md`
- 역할: Android/iOS 설치/오프라인/보안 검증 절차 문서

### 4.2 배포 데이터 파일 (`docs/data/`)

#### `docs/data/daily_ai_brief_2026-03-10.json`
#### `docs/data/daily_ai_brief_2026-03-11.json`
- 역할: 날짜별 리포트 JSON 원본
- 상위 구조 키:
  - `report_date`, `generated_at`, `article_count`
  - `issues_top`, `source_totals`, `source_kept`, `llm_stats`, `articles[]`
- `articles[]` 주요 필드:
  - `source`, `authority`, `title`, `title_original`, `link`
  - `published_raw`, `published_local`, `primary_topic`, `topics`
  - `issues`, `keywords`, `keywords_original`
  - `summary`, `summary_original`

#### `docs/data/daily_ai_brief_2026-03-10.md`
#### `docs/data/daily_ai_brief_2026-03-11.md`
- 역할: 날짜별 리포트 Markdown 본문
- 구조:
  - 헤더(생성시각/기사수)
  - 주요 이슈
  - 주제별 기사 목록
  - 소스 커버리지 표

#### `docs/data/latest.json`
#### `docs/data/latest.md`
- 역할: 최신 리포트 alias
- 생성 주체: `scripts/publish_latest_report.py`

#### `docs/data/index.json`
- 역할: 리포트 히스토리 인덱스
- 구조:
  - `latest_date`
  - `reports[]` (`date`, `json`, `md`, `article_count`)

---

## 5) 추적 파일 전수 목록 (git ls-files)
아래는 현재 커밋 기준 추적 파일 전체 목록입니다.

```text
.github/workflows/publish_daily_ai_brief.yml
.gitignore
DAILY_AI_AGENT.md
daily_ai_agent_config.json
daily_ai_news_agent.py
docs/data/daily_ai_brief_2026-03-10.json
docs/data/daily_ai_brief_2026-03-10.md
docs/data/daily_ai_brief_2026-03-11.json
docs/data/daily_ai_brief_2026-03-11.md
docs/data/index.json
docs/data/latest.json
docs/data/latest.md
docs/icons/icon-192.png
docs/icons/icon-512.png
docs/icons/icon-512-maskable.png
docs/index.html
docs/manifest.webmanifest
docs/offline.html
docs/PWA_MOBILE_TEST_CHECKLIST.md
docs/sw.js
EMAIL_AUTOSEND_SETUP.md
README.md
requirements_daily_agent.txt
scripts/publish_latest_report.py
scripts/secret_scan.py
scripts/send_daily_report_email.py
```
