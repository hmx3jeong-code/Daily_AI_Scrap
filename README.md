# Daily AI Scrap Repository Guide

## 1. 문서 목적
이 README는 이 저장소의 **코드 파일**과 **기록/산출물 파일**을 모두 대상으로, 각 파일(또는 대량 파일군)의 역할과 구조를 설명합니다.

- 작성 기준 시점: 2026-03-12
- 스캔 기준: 프로젝트 루트 하위 파일 전체(숨김 포함)
- 제외: 최상위 `.git/`, `.venv/`, `.venv2/`, `.venv_new/`, `.tmp/` 내부
- 스캔 결과 파일 수: **780개**

## 2. 저장소 핵심 목적
이 저장소는 크게 두 축으로 구성됩니다.

1. `daily_ai_news_agent.py` 기반의 일일 AI 뉴스 수집/요약/리포트 생성 파이프라인
2. PDF 기반 RAG 실험(문서 파싱, 청킹, 임베딩, FAISS, 챗봇) 아카이브

## 3. 전체 구조(요약)
| Top Directory | 파일 수 | 역할 |
|---|---:|---|
| `(root)` | 12 | 실행 엔트리, 설정, 문서 |
| `.github` | 1 | GitHub Actions 자동화 워크플로 |
| `docs` | 15 | GitHub Pages 정적 웹앱(PWA) |
| `scripts` | 5 | 보조 자동화 스크립트(발행/메일/시크릿 스캔) |
| `daily_ai_reports` | 2 | 로컬 일일 리포트 산출물 |
| `docs/data` (docs 하위) | 7 | 웹에서 읽는 배포용 최신/히스토리 리포트 |
| `.local_backup_docs_data` | 5 | `docs/data` 로컬 백업본 |
| `data` | 47 | Docling 청크 단위 파싱 결과(중간 산출물) |
| `main.py_results` | 18 | 파서별 실험 결과 비교 출력 |
| `final_chunks` | 4 | 앙상블 청킹 결과 |
| `upstage_results` | 3 | Upstage 단일 파싱 결과 |
| `upstage_batch_results` | 3 | Upstage 배치 병합 결과 |
| `upstage_batch_results2` | 4 | Upstage 배치 병합/클린 버전 |
| `ETC` | 26 | PDF/RAG 실험용 스크립트/결과/노트북 |
| `Final` | 473 | RAG 챗봇 최종 실험 아카이브 + Poppler 벤더 파일 |
| `automation_logs` | 1 | 자동화 에이전트 로그 |
| `devA`, `devB` | 37, 45 | 충돌 실습용 로컬 저장소 스냅샷 |
| `git-training` | 48 | Git 학습용 로컬 저장소 |
| `remote.git` | 28 | bare 형태 로컬 원격 저장소 |
| `__pycache__` | 2 | 루트 파이썬 캐시 |

## 4. 핵심 코드 파일 상세(파일 단위)

### 4.1 루트 실행/설정
- `daily_ai_news_agent.py`
  - 역할: RSS/Atom 수집 → 중복 제거 → 주제/이슈 분류 → 요약 생성(LLM 또는 fallback) → MD/JSON 리포트 생성
  - 주요 구조:
    - `Source`, `Article` 데이터 클래스
    - `LlmSummarizer` 클래스(Gemini OpenAI-compatible endpoint 사용)
    - 피드 파싱 함수(`parse_rss_items`, `parse_atom_items`, `parse_feed_items`)
    - 중복 제거(`dedupe_articles`, signature 기반)
    - 과거 리포트 중복 제거(`load_historical_article_signatures`, `filter_previously_reported_articles`)
    - 리포트 생성(`build_markdown_report`, `build_json_report`)
    - 메인 실행(`run`) 및 CLI 인자(`--config`, `--output-dir`, `--report-date`, `--lookback-days`, `--target-articles`, `--max-total-articles`, `--max-per-source`, `--timeout-sec`, `--dry-run`)
  - 출력:
    - `daily_ai_brief_YYYY-MM-DD.md`
    - `daily_ai_brief_YYYY-MM-DD.json`

- `daily_ai_agent_config.json`
  - 역할: 소스 목록, 주제/이슈 규칙, LLM 옵션, 리포트 옵션 설정
  - 구조:
    - `sources[]` (name, feed_url, fallback_feed_urls, authority, topic_hint, max_items)
    - `topic_rules`, `issue_rules`
    - `llm` (enabled, provider, model, temperature, max_articles_per_run, api_key_env, base_url)
    - `report_options` (lookback/target/max_total/history_dedupe_days)

- `.env`
  - 역할: 로컬 환경변수 저장(키/엔드포인트)
  - 주의: 민감정보 파일이며 Git 추적 제외되어야 함

- `requirements_daily_agent.txt`
  - 역할: 일일 에이전트 실행 의존성(`openai`, `python-dotenv`)

- `requirements-dev.txt`
  - 역할: 개발 도구 의존성(`pre-commit`)

- `.pre-commit-config.yaml`
  - 역할: 커밋 전 `scripts/secret_scan.py` 실행

- `.gitignore`
  - 역할: 환경/산출물 제외 규칙 및 `docs/data` 예외 추적 규칙

### 4.2 자동화/유틸 스크립트 (`scripts/`)
- `scripts/publish_latest_report.py`
  - 역할: `docs/data` 내 최신 날짜 JSON/MD를 `latest.*`로 복사, `index.json` 생성
  - 구조: `list_reports` → `build_index` → `main`

- `scripts/send_daily_report_email.py`
  - 역할: SMTP로 최신 리포트 본문/첨부 발송
  - 구조: 리포트 선택(`pick_report_json`) → 본문 생성(`build_body`) → 발송(`send_email`)
  - 입력 환경변수: `EMAIL_SMTP_*`, `EMAIL_FROM`, `EMAIL_TO`, `REPORT_SITE_URL`

- `scripts/secret_scan.py`
  - 역할: 정규식 기반 잠재 비밀키 탐지(커밋 차단)
  - 구조: 규칙 집합(`RULES`) + 파일 스캔 + finding 출력

- `scripts/__pycache__/*.pyc`
  - 역할: 파이썬 바이트코드 캐시(실행 산출물)

### 4.3 배포/웹앱 (`docs/`)
- `docs/index.html`
  - 역할: 배포용 단일 페이지 UI(리포트 렌더링, 설치 UX, 옵션형 LLM 질문)
  - 구조:
    - `docs/data/latest.json`, `docs/data/index.json` fetch
    - PWA 설치 버튼/안내
    - LLM 질문 기능 opt-in + API key localStorage 저장
    - URL 안전성 검사, 오프라인 캐시 fallback 표시

- `docs/sw.js`
  - 역할: Service Worker 캐싱 전략
  - 구조:
    - App shell 캐시
    - JSON 요청 stale-while-revalidate
    - navigation network-first + offline fallback

- `docs/manifest.webmanifest`
  - 역할: 앱 설치 메타(이름/아이콘/테마/start_url/scope)

- `docs/offline.html`
  - 역할: 오프라인 진입 시 fallback 페이지

- `docs/icons/icon-192.png`, `icon-512.png`, `icon-512-maskable.png`
  - 역할: 설치 아이콘 세트

- `docs/PWA_MOBILE_TEST_CHECKLIST.md`
  - 역할: Android/iOS 설치 및 검증 체크리스트

- `docs/data/*.json`, `docs/data/*.md`
  - 역할: 웹 표시용 리포트 데이터
  - 구조:
    - `daily_ai_brief_YYYY-MM-DD.json|md`: 날짜별 본문
    - `latest.json|md`: 최신 alias
    - `index.json`: 히스토리 인덱스

### 4.4 GitHub Actions
- `.github/workflows/publish_daily_ai_brief.yml`
  - 역할: 평일 자동 실행 + 수동 실행
  - 구조:
    1. Python 환경 구성
    2. `daily_ai_news_agent.py`로 `docs/data` 생성
    3. `scripts/publish_latest_report.py` 실행
    4. `docs/data` 커밋/푸시
    5. `scripts/send_daily_report_email.py` 메일 전송

### 4.5 문서 파일
- `DAILY_AI_AGENT.md`: 일일 뉴스 에이전트 사용 가이드
- `EMAIL_AUTOSEND_SETUP.md`: 메일 자동발송 시크릿/설정 가이드
- `PRECOMMIT_SECRET_SCAN.md`: pre-commit 시크릿 스캔 설정 가이드

## 5. 실험 코드 상세 (`ETC/`, `Final/`의 .py/.ipynb)

### 5.1 `ETC/` Python 스크립트
- `ETC/automation_agent.py`
  - 역할: JSON 잡 정의 기반 명령 실행 자동화 에이전트
  - 출력: `automation_logs/*.log`

- `ETC/main.py`
  - 역할: 다중 PDF 파서(SimpleDirectoryReader, PyMuPDF, Docling, LlamaParse 등) 비교 테스트
  - 출력: `main.py_results/*.json|*.txt`

- `ETC/step2_chunking.py`
  - 역할: 파서 결과 앙상블 정제 + 청킹
  - 출력: `final_chunks/*.json|*.txt`

- `ETC/chunking_final.py`
  - 역할: 병합 JSON에서 semantic chunk 생성
  - 출력: `Final/semantic_chunks.json|txt`

- `ETC/Embedding_VectorDB.py`
  - 역할: Azure OpenAI 임베딩 생성 + FAISS 인덱스 구축
  - 출력: `faiss_index_large2.bin`, `faiss_mapping_large2.json`

- `ETC/GPT_TEST.py`
  - 역할: FAISS 검색 + CrossEncoder 리랭킹 + GPT 질의 루프

- `ETC/json_merge.py`
  - 역할: Docling/Upstage 파싱 결과 병합

- `ETC/Plus_json.py`
  - 역할: JSON 텍스트에서 표 추출/병합(후처리)

- `ETC/Shift.py`
  - 역할: JSON 특정 키(page_in_chunk, global_id) 제거 클리너

### 5.2 `Final/` Python/Notebook
- `Final/ChatBot_Multiturn_Streamlit.py`
  - 역할: Streamlit 기반 멀티턴 RAG 챗봇 UI
  - 구조: 세션 상태, 질의 의도 분석, 리랭킹, PDF 페이지 링크 렌더링

- `Final/ChatBot_Final.py`
  - 역할: 콘솔형 멀티턴 RAG 챗봇(캐시/프리패치/리랭크)

- `Final/AgentOCR_Chat.py`, `Final/AgentOCR_Chat copy.py`
  - 역할: OCR+RAG 결합형 채팅 실험 버전

- `Final/docling_chunk_out/docling_worker.py`
  - 역할: Docling 호출 워커(단일 PDF→Markdown JSON)

- `Final/ChatBot_Multiturn_Improved.ipynb`, `Final/VectorDB.ipynb`
  - 역할: 멀티턴/벡터DB 실험 노트북

### 5.3 실험/결과 JSON·TXT·BIN
- `main.py_results/*.json|*.txt`: 파서별 비교 결과
- `final_chunks/*.json|*.txt`: 스마트/골든 청킹 결과
- `upstage_results/*`, `upstage_batch_results/*`, `upstage_batch_results2/*`: Upstage 파싱 결과 및 병합/클린본
- `ETC/*.json`, `Final/*.json`: 중간 병합 데이터, 매핑, 청크 데이터
- `ETC/*.bin`, `Final/*.bin`: FAISS 인덱스 바이너리

## 6. 기록/산출물 폴더 구조(패턴 상세)

### 6.1 리포트 계열
- `daily_ai_reports/daily_ai_brief_YYYY-MM-DD.{md,json}`
  - 로컬 실행 산출물
- `docs/data/daily_ai_brief_YYYY-MM-DD.{md,json}`
  - 웹 배포 산출물
- `docs/data/latest.{md,json}`
  - 최신 리포트 alias
- `docs/data/index.json`
  - 히스토리 인덱스 (`latest_date`, `reports[]`)
- `.local_backup_docs_data/*`
  - `docs/data` 백업 스냅샷

### 6.2 Docling 파이프라인 산출물 (`data/docling_chunk_out/`)
- `chunks/chunk_XXX_pXXXX_XXXX.pdf`
  - 페이지 구간별 분할 PDF
- `results/chunk_XXX_*.json|txt`
  - 청크별 파싱 결과
- `log.json`
  - 전체 실행 로그/결과 집계
- `merged.txt`
  - 병합 텍스트 결과

### 6.3 기타 산출물
- `automation_logs/*.log`: 자동화 실행 로그
- `main.py_results/*`: 파서 비교 실험 결과
- `final_chunks/*`: 최종 청크 결과
- `upstage_*/*`: Upstage 파서 결과

## 7. 학습/실습용 로컬 저장소 및 메타 파일
- `devA/`, `devB/`, `git-training/`
  - 역할: Git 충돌/브랜치 학습 실습용 디렉터리
  - 포함: 내부 `.git/` 객체, 훅 샘플, 로그, refs
- `remote.git/`
  - 역할: bare 저장소 형태 실습 원격

## 8. 벤더/대용량 아카이브 (`Final/`)
- `Final/poppler-25.12.0/**`
  - 역할: Poppler 바이너리/헤더/매뉴얼/문자맵 데이터(외부 의존성 포함본)
  - 구성:
    - `Library/bin/*.dll, *.exe`
    - `Library/include/poppler/**/*.h`
    - `Library/lib/*.lib, *.pc`
    - `share/poppler/cMap/*`, `cidToUnicode/*`, `unicodeMap/*`, 매뉴얼(`*.1`)

## 9. 루트 기타 파일
- `conflict.txt`, `devA/conflict.txt`, `devB/conflict.txt`
  - 역할: 충돌 해결 실습 텍스트
- `git-training/a.txt`, `git-training/app.txt`, `git-training/login.txt`
  - 역할: Git 학습용 샘플 텍스트
- `.vscode/settings.json`
  - 역할: VSCode 경고 억제 설정(`git.ignoreLimitWarning`)

## 10. 전체 파일 인벤토리(전수 목록)
아래 목록은 README 작성 시점 기준 전수 스캔 결과입니다.

```text

.env
.github\workflows\publish_daily_ai_brief.yml
.gitignore
.local_backup_docs_data\daily_ai_brief_2026-03-10.json
.local_backup_docs_data\daily_ai_brief_2026-03-10.md
.local_backup_docs_data\index.json
.local_backup_docs_data\latest.json
.local_backup_docs_data\latest.md
.pre-commit-config.yaml
.vscode\settings.json
__pycache__\automation_agent.cpython-314.pyc
__pycache__\daily_ai_news_agent.cpython-314.pyc
automation_logs\20260309_082637_build_rag_pipeline.log
conflict.txt
DAILY_AI_AGENT.md
daily_ai_agent_config.json
daily_ai_news_agent.py
daily_ai_reports\daily_ai_brief_2026-03-10.json
daily_ai_reports\daily_ai_brief_2026-03-10.md
data\docling_chunk_out\chunks\chunk_001_p0001_0010.pdf
data\docling_chunk_out\chunks\chunk_002_p0011_0020.pdf
data\docling_chunk_out\chunks\chunk_003_p0021_0030.pdf
data\docling_chunk_out\chunks\chunk_004_p0031_0040.pdf
data\docling_chunk_out\chunks\chunk_005_p0041_0050.pdf
data\docling_chunk_out\chunks\chunk_006_p0051_0060.pdf
data\docling_chunk_out\chunks\chunk_007_p0061_0070.pdf
data\docling_chunk_out\chunks\chunk_008_p0071_0080.pdf
data\docling_chunk_out\chunks\chunk_009_p0081_0090.pdf
data\docling_chunk_out\chunks\chunk_010_p0091_0100.pdf
data\docling_chunk_out\chunks\chunk_011_p0101_0110.pdf
data\docling_chunk_out\chunks\chunk_012_p0111_0120.pdf
data\docling_chunk_out\chunks\chunk_013_p0121_0130.pdf
data\docling_chunk_out\chunks\chunk_014_p0131_0140.pdf
data\docling_chunk_out\chunks\chunk_015_p0141_0148.pdf
data\docling_chunk_out\log.json
data\docling_chunk_out\merged.txt
data\docling_chunk_out\results\chunk_001_p0001_0010.json
data\docling_chunk_out\results\chunk_001_p0001_0010.txt
data\docling_chunk_out\results\chunk_002_p0011_0020.json
data\docling_chunk_out\results\chunk_002_p0011_0020.txt
data\docling_chunk_out\results\chunk_003_p0021_0030.json
data\docling_chunk_out\results\chunk_003_p0021_0030.txt
data\docling_chunk_out\results\chunk_004_p0031_0040.json
data\docling_chunk_out\results\chunk_004_p0031_0040.txt
data\docling_chunk_out\results\chunk_005_p0041_0050.json
data\docling_chunk_out\results\chunk_005_p0041_0050.txt
data\docling_chunk_out\results\chunk_006_p0051_0060.json
data\docling_chunk_out\results\chunk_006_p0051_0060.txt
data\docling_chunk_out\results\chunk_007_p0061_0070.json
data\docling_chunk_out\results\chunk_007_p0061_0070.txt
data\docling_chunk_out\results\chunk_008_p0071_0080.json
data\docling_chunk_out\results\chunk_008_p0071_0080.txt
data\docling_chunk_out\results\chunk_009_p0081_0090.json
data\docling_chunk_out\results\chunk_009_p0081_0090.txt
data\docling_chunk_out\results\chunk_010_p0091_0100.json
data\docling_chunk_out\results\chunk_010_p0091_0100.txt
data\docling_chunk_out\results\chunk_011_p0101_0110.json
data\docling_chunk_out\results\chunk_011_p0101_0110.txt
data\docling_chunk_out\results\chunk_012_p0111_0120.json
data\docling_chunk_out\results\chunk_012_p0111_0120.txt
data\docling_chunk_out\results\chunk_013_p0121_0130.json
data\docling_chunk_out\results\chunk_013_p0121_0130.txt
data\docling_chunk_out\results\chunk_014_p0131_0140.json
data\docling_chunk_out\results\chunk_014_p0131_0140.txt
data\docling_chunk_out\results\chunk_015_p0141_0148.json
data\docling_chunk_out\results\chunk_015_p0141_0148.txt
devA\.git\COMMIT_EDITMSG
devA\.git\config
devA\.git\description
devA\.git\HEAD
devA\.git\hooks\applypatch-msg.sample
devA\.git\hooks\commit-msg.sample
devA\.git\hooks\fsmonitor-watchman.sample
devA\.git\hooks\post-update.sample
devA\.git\hooks\pre-applypatch.sample
devA\.git\hooks\pre-commit.sample
devA\.git\hooks\pre-merge-commit.sample
devA\.git\hooks\prepare-commit-msg.sample
devA\.git\hooks\pre-push.sample
devA\.git\hooks\pre-rebase.sample
devA\.git\hooks\pre-receive.sample
devA\.git\hooks\push-to-checkout.sample
devA\.git\hooks\sendemail-validate.sample
devA\.git\hooks\update.sample
devA\.git\index
devA\.git\info\exclude
devA\.git\logs\HEAD
devA\.git\logs\refs\heads\master
devA\.git\logs\refs\remotes\origin\HEAD
devA\.git\logs\refs\remotes\origin\master
devA\.git\objects\07\6d1547350d65a2c7678a0cfcb42f63f83cb2af
devA\.git\objects\13\eddb290cb021896a3b075f70d26ed22b216e51
devA\.git\objects\29\b879658ac43d20910fa8f48615703eb421ace4
devA\.git\objects\2d\b8731da96c9baab784e80f69b0dd48569f1ff5
devA\.git\objects\4e\f0d733efdb05d61246368a97ae1a67ca5c8fd1
devA\.git\objects\4f\4cd8151c67e0de1eefb17b327804ba4dc32054
devA\.git\objects\50\6812d383b8ab761d1b92579386191aef790ae1
devA\.git\objects\6b\bf32e84517bb1ceb198293d9f9d2b03cdb1f9f
devA\.git\objects\6d\aa394260c9556b7003636ade722d5d1b70ac7f
devA\.git\refs\heads\master
devA\.git\refs\remotes\origin\HEAD
devA\.git\refs\remotes\origin\master
devA\conflict.txt
devB\.git\COMMIT_EDITMSG
devB\.git\config
devB\.git\description
devB\.git\FETCH_HEAD
devB\.git\HEAD
devB\.git\hooks\applypatch-msg.sample
devB\.git\hooks\commit-msg.sample
devB\.git\hooks\fsmonitor-watchman.sample
devB\.git\hooks\post-update.sample
devB\.git\hooks\pre-applypatch.sample
devB\.git\hooks\pre-commit.sample
devB\.git\hooks\pre-merge-commit.sample
devB\.git\hooks\prepare-commit-msg.sample
devB\.git\hooks\pre-push.sample
devB\.git\hooks\pre-rebase.sample
devB\.git\hooks\pre-receive.sample
devB\.git\hooks\push-to-checkout.sample
devB\.git\hooks\sendemail-validate.sample
devB\.git\hooks\update.sample
devB\.git\index
devB\.git\info\exclude
devB\.git\logs\HEAD
devB\.git\logs\refs\heads\master
devB\.git\logs\refs\remotes\origin\HEAD
devB\.git\logs\refs\remotes\origin\master
devB\.git\objects\07\6d1547350d65a2c7678a0cfcb42f63f83cb2af
devB\.git\objects\0d\f889311439333a5fc5024cd38cc4c39918c523
devB\.git\objects\13\eddb290cb021896a3b075f70d26ed22b216e51
devB\.git\objects\29\b879658ac43d20910fa8f48615703eb421ace4
devB\.git\objects\2d\b8731da96c9baab784e80f69b0dd48569f1ff5
devB\.git\objects\34\ef65fb4a843165201ed57f6cec9527cb82f66b
devB\.git\objects\4e\f0d733efdb05d61246368a97ae1a67ca5c8fd1
devB\.git\objects\4f\4cd8151c67e0de1eefb17b327804ba4dc32054
devB\.git\objects\50\6812d383b8ab761d1b92579386191aef790ae1
devB\.git\objects\6b\bf32e84517bb1ceb198293d9f9d2b03cdb1f9f
devB\.git\objects\6d\aa394260c9556b7003636ade722d5d1b70ac7f
devB\.git\objects\86\6076ef209fd9cb561b64d2505d6c63cc3ba76f
devB\.git\objects\a8\fa0d1c29ef10b6f7e00c592969239f820efc14
devB\.git\objects\b8\c99c3ffdec9aee68a3ba41453040734d7e7ea5
devB\.git\ORIG_HEAD
devB\.git\REBASE_HEAD
devB\.git\refs\heads\master
devB\.git\refs\remotes\origin\HEAD
devB\.git\refs\remotes\origin\master
devB\conflict.txt
docs\data\daily_ai_brief_2026-03-10.json
docs\data\daily_ai_brief_2026-03-10.md
docs\data\daily_ai_brief_2026-03-11.json
docs\data\daily_ai_brief_2026-03-11.md
docs\data\index.json
docs\data\latest.json
docs\data\latest.md
docs\icons\icon-192.png
docs\icons\icon-512.png
docs\icons\icon-512-maskable.png
docs\index.html
docs\manifest.webmanifest
docs\offline.html
docs\PWA_MOBILE_TEST_CHECKLIST.md
docs\sw.js
EMAIL_AUTOSEND_SETUP.md
ETC\2026 행정업무매뉴얼(챗봇학습용_텍스트화)_최종.pdf
ETC\automation_agent.py
ETC\automation_jobs.json
ETC\chunking_final.py
ETC\docling_test1_revised_default.ipynb
ETC\Embedding_VectorDB.py
ETC\faiss_index_large.bin
ETC\faiss_index_large2.bin
ETC\faiss_mapping_large.json
ETC\faiss_mapping_large2.json
ETC\final_combined_elements.json
ETC\GPT_TEST.py
ETC\json_merge.py
ETC\main.py
ETC\merged.txt
ETC\part1.pdf
ETC\part2.pdf
ETC\Plus_json.py
ETC\semantic_chunks.json
ETC\semantic_chunks.txt
ETC\Shift.py
ETC\Shift.pypart2_result_shifted.json
ETC\step2_chunking.py
ETC\temp_upstage_0.pdf
ETC\upstage_document_parser copy.ipynb
ETC\upstage_document_parser.ipynb
final_chunks\golden_final_chunks.json
final_chunks\golden_final_chunks.txt
final_chunks\smart_final_chunks.json
final_chunks\smart_final_chunks.txt
Final\__pycache__\AgentOCR_Chat copy.cpython-314.pyc
Final\__pycache__\ChatBot_Multiturn_Streamlit.cpython-312.pyc
Final\__pycache__\ChatBot_Multiturn_Streamlit.cpython-314.pyc
Final\2026 행정업무매뉴얼(챗봇학습용_텍스트화)_최종.pdf
Final\AgentOCR_Chat copy.py
Final\AgentOCR_Chat.py
Final\ChatBot_Final.py
Final\ChatBot_Multiturn_Improved.ipynb
Final\ChatBot_Multiturn_Streamlit.py
Final\docling_chunk_out\docling_worker.py
Final\docling_chunk_out\log.json
Final\faiss_index_large2.bin
Final\faiss_mapping_large2.json
Final\final_combined_elements.json
Final\poppler-25.12.0\Library\bin\cairo.dll
Final\poppler-25.12.0\Library\bin\charset.dll
Final\poppler-25.12.0\Library\bin\deflate.dll
Final\poppler-25.12.0\Library\bin\expat.dll
Final\poppler-25.12.0\Library\bin\fontconfig-1.dll
Final\poppler-25.12.0\Library\bin\freetype.dll
Final\poppler-25.12.0\Library\bin\iconv.dll
Final\poppler-25.12.0\Library\bin\jpeg8.dll
Final\poppler-25.12.0\Library\bin\lcms2.dll
Final\poppler-25.12.0\Library\bin\Lerc.dll
Final\poppler-25.12.0\Library\bin\libcrypto-3-x64.dll
Final\poppler-25.12.0\Library\bin\libcurl.dll
Final\poppler-25.12.0\Library\bin\libexpat.dll
Final\poppler-25.12.0\Library\bin\liblzma.dll
Final\poppler-25.12.0\Library\bin\libpng16.dll
Final\poppler-25.12.0\Library\bin\libssh2.dll
Final\poppler-25.12.0\Library\bin\libtiff.dll
Final\poppler-25.12.0\Library\bin\libzstd.dll
Final\poppler-25.12.0\Library\bin\openjp2.dll
Final\poppler-25.12.0\Library\bin\pdfattach.exe
Final\poppler-25.12.0\Library\bin\pdfdetach.exe
Final\poppler-25.12.0\Library\bin\pdffonts.exe
Final\poppler-25.12.0\Library\bin\pdfimages.exe
Final\poppler-25.12.0\Library\bin\pdfinfo.exe
Final\poppler-25.12.0\Library\bin\pdfseparate.exe
Final\poppler-25.12.0\Library\bin\pdftocairo.exe
Final\poppler-25.12.0\Library\bin\pdftohtml.exe
Final\poppler-25.12.0\Library\bin\pdftoppm.exe
Final\poppler-25.12.0\Library\bin\pdftops.exe
Final\poppler-25.12.0\Library\bin\pdftotext.exe
Final\poppler-25.12.0\Library\bin\pdfunite.exe
Final\poppler-25.12.0\Library\bin\pixman-1-0.dll
Final\poppler-25.12.0\Library\bin\poppler.dll
Final\poppler-25.12.0\Library\bin\poppler-cpp.dll
Final\poppler-25.12.0\Library\bin\poppler-glib.dll
Final\poppler-25.12.0\Library\bin\tiff.dll
Final\poppler-25.12.0\Library\bin\zlib.dll
Final\poppler-25.12.0\Library\bin\zstd.dll
Final\poppler-25.12.0\Library\bin\zstd.exe
Final\poppler-25.12.0\Library\include\poppler\Annot.h
Final\poppler-25.12.0\Library\include\poppler\AnnotStampImageHelper.h
Final\poppler-25.12.0\Library\include\poppler\Array.h
Final\poppler-25.12.0\Library\include\poppler\BBoxOutputDev.h
Final\poppler-25.12.0\Library\include\poppler\CachedFile.h
Final\poppler-25.12.0\Library\include\poppler\Catalog.h
Final\poppler-25.12.0\Library\include\poppler\CertificateInfo.h
Final\poppler-25.12.0\Library\include\poppler\CharTypes.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler_cpp_export.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-destination.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-document.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-embedded-file.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-font.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-font-private.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-global.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-image.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-page.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-page-renderer.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-page-transition.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-rectangle.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-toc.h
Final\poppler-25.12.0\Library\include\poppler\cpp\poppler-version.h
Final\poppler-25.12.0\Library\include\poppler\CryptoSignBackend.h
Final\poppler-25.12.0\Library\include\poppler\CurlCachedFile.h
Final\poppler-25.12.0\Library\include\poppler\CurlPDFDocBuilder.h
Final\poppler-25.12.0\Library\include\poppler\DateInfo.h
Final\poppler-25.12.0\Library\include\poppler\Dict.h
Final\poppler-25.12.0\Library\include\poppler\Error.h
Final\poppler-25.12.0\Library\include\poppler\ErrorCodes.h
Final\poppler-25.12.0\Library\include\poppler\FILECacheLoader.h
Final\poppler-25.12.0\Library\include\poppler\FileSpec.h
Final\poppler-25.12.0\Library\include\poppler\fofi\FoFiBase.h
Final\poppler-25.12.0\Library\include\poppler\fofi\FoFiEncodings.h
Final\poppler-25.12.0\Library\include\poppler\fofi\FoFiIdentifier.h
Final\poppler-25.12.0\Library\include\poppler\fofi\FoFiTrueType.h
Final\poppler-25.12.0\Library\include\poppler\fofi\FoFiType1C.h
Final\poppler-25.12.0\Library\include\poppler\FontInfo.h
Final\poppler-25.12.0\Library\include\poppler\Form.h
Final\poppler-25.12.0\Library\include\poppler\Function.h
Final\poppler-25.12.0\Library\include\poppler\Gfx.h
Final\poppler-25.12.0\Library\include\poppler\GfxFont.h
Final\poppler-25.12.0\Library\include\poppler\GfxState.h
Final\poppler-25.12.0\Library\include\poppler\GfxState_helpers.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-action.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-annot.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-attachment.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-date.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-document.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-enums.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-features.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-form-field.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-layer.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-macros.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-media.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-movie.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-page.h
Final\poppler-25.12.0\Library\include\poppler\glib\poppler-structure-element.h
Final\poppler-25.12.0\Library\include\poppler\GlobalParams.h
Final\poppler-25.12.0\Library\include\poppler\goo\gfile.h
Final\poppler-25.12.0\Library\include\poppler\goo\gmem.h
Final\poppler-25.12.0\Library\include\poppler\goo\GooCheckedOps.h
Final\poppler-25.12.0\Library\include\poppler\goo\GooLikely.h
Final\poppler-25.12.0\Library\include\poppler\goo\GooString.h
Final\poppler-25.12.0\Library\include\poppler\goo\GooTimer.h
Final\poppler-25.12.0\Library\include\poppler\goo\grandom.h
Final\poppler-25.12.0\Library\include\poppler\goo\gstrtod.h
Final\poppler-25.12.0\Library\include\poppler\goo\ImgWriter.h
Final\poppler-25.12.0\Library\include\poppler\goo\JpegWriter.h
Final\poppler-25.12.0\Library\include\poppler\goo\PNGWriter.h
Final\poppler-25.12.0\Library\include\poppler\goo\TiffWriter.h
Final\poppler-25.12.0\Library\include\poppler\HashAlgorithm.h
Final\poppler-25.12.0\Library\include\poppler\JPEG2000Stream.h
Final\poppler-25.12.0\Library\include\poppler\JSInfo.h
Final\poppler-25.12.0\Library\include\poppler\Lexer.h
Final\poppler-25.12.0\Library\include\poppler\Link.h
Final\poppler-25.12.0\Library\include\poppler\MarkedContentOutputDev.h
Final\poppler-25.12.0\Library\include\poppler\Movie.h
Final\poppler-25.12.0\Library\include\poppler\NameToUnicodeTable.h
Final\poppler-25.12.0\Library\include\poppler\Object.h
Final\poppler-25.12.0\Library\include\poppler\OptionalContent.h
Final\poppler-25.12.0\Library\include\poppler\Outline.h
Final\poppler-25.12.0\Library\include\poppler\OutputDev.h
Final\poppler-25.12.0\Library\include\poppler\Page.h
Final\poppler-25.12.0\Library\include\poppler\PageTransition.h
Final\poppler-25.12.0\Library\include\poppler\Parser.h
Final\poppler-25.12.0\Library\include\poppler\PDFDoc.h
Final\poppler-25.12.0\Library\include\poppler\PDFDocBuilder.h
Final\poppler-25.12.0\Library\include\poppler\PDFDocEncoding.h
Final\poppler-25.12.0\Library\include\poppler\PDFDocFactory.h
Final\poppler-25.12.0\Library\include\poppler\poppler_private_export.h
Final\poppler-25.12.0\Library\include\poppler\PopplerCache.h
Final\poppler-25.12.0\Library\include\poppler\poppler-config.h
Final\poppler-25.12.0\Library\include\poppler\ProfileData.h
Final\poppler-25.12.0\Library\include\poppler\PSOutputDev.h
Final\poppler-25.12.0\Library\include\poppler\Rendition.h
Final\poppler-25.12.0\Library\include\poppler\SignatureInfo.h
Final\poppler-25.12.0\Library\include\poppler\Sound.h
Final\poppler-25.12.0\Library\include\poppler\splash\Splash.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashBitmap.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashClip.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashErrorCodes.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashFont.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashFontEngine.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashFontFile.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashFontFileID.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashGlyphBitmap.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashMath.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashPath.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashPattern.h
Final\poppler-25.12.0\Library\include\poppler\splash\SplashTypes.h
Final\poppler-25.12.0\Library\include\poppler\SplashOutputDev.h
Final\poppler-25.12.0\Library\include\poppler\Stream.h
Final\poppler-25.12.0\Library\include\poppler\Stream-CCITT.h
Final\poppler-25.12.0\Library\include\poppler\StructElement.h
Final\poppler-25.12.0\Library\include\poppler\StructTreeRoot.h
Final\poppler-25.12.0\Library\include\poppler\TextOutputDev.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeCClassTables.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeCompTables.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeDecompTables.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeMap.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeMapFuncs.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeMapTables.h
Final\poppler-25.12.0\Library\include\poppler\UnicodeTypeTable.h
Final\poppler-25.12.0\Library\include\poppler\UTF.h
Final\poppler-25.12.0\Library\include\poppler\ViewerPreferences.h
Final\poppler-25.12.0\Library\include\poppler\XRef.h
Final\poppler-25.12.0\Library\lib\pkgconfig\poppler.pc
Final\poppler-25.12.0\Library\lib\pkgconfig\poppler-cpp.pc
Final\poppler-25.12.0\Library\lib\pkgconfig\poppler-glib.pc
Final\poppler-25.12.0\Library\lib\poppler.lib
Final\poppler-25.12.0\Library\lib\poppler-cpp.lib
Final\poppler-25.12.0\Library\lib\poppler-glib.lib
Final\poppler-25.12.0\Library\share\man\man1\pdfattach.1
Final\poppler-25.12.0\Library\share\man\man1\pdfdetach.1
Final\poppler-25.12.0\Library\share\man\man1\pdffonts.1
Final\poppler-25.12.0\Library\share\man\man1\pdfimages.1
Final\poppler-25.12.0\Library\share\man\man1\pdfinfo.1
Final\poppler-25.12.0\Library\share\man\man1\pdfseparate.1
Final\poppler-25.12.0\Library\share\man\man1\pdftocairo.1
Final\poppler-25.12.0\Library\share\man\man1\pdftohtml.1
Final\poppler-25.12.0\Library\share\man\man1\pdftoppm.1
Final\poppler-25.12.0\Library\share\man\man1\pdftops.1
Final\poppler-25.12.0\Library\share\man\man1\pdftotext.1
Final\poppler-25.12.0\Library\share\man\man1\pdfunite.1
Final\poppler-25.12.0\share\poppler\cidToUnicode\Adobe-CNS1
Final\poppler-25.12.0\share\poppler\cidToUnicode\Adobe-GB1
Final\poppler-25.12.0\share\poppler\cidToUnicode\Adobe-Japan1
Final\poppler-25.12.0\share\poppler\cidToUnicode\Adobe-Korea1
Final\poppler-25.12.0\share\poppler\CMakeLists.txt
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-1
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-3
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-4
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-6
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-7
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-B5pc
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-ETen-B5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-H-CID
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-H-Host
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-H-Mac
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\Adobe-CNS1-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5pc-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5pc-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5pc-UCS2C
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5pc-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS1-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS1-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\CNS-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETen-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETen-B5-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETen-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETenms-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETenms-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETHK-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\ETHK-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKdla-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKdla-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKdlb-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKdlb-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKgccs-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKgccs-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKm314-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKm314-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKm471-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKm471-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKscs-B5-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\HKscs-B5-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UCS2-B5pc
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UCS2-ETen-B5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UCS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-CNS1\UniCNS-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-1
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-3
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-4
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-GBK-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-GBpc-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-H-CID
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-H-Host
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-H-Mac
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\Adobe-GB1-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GB-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GB-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GB-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBK2K-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBK2K-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBK-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBK-EUC-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBK-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBKp-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBKp-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBpc-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBpc-EUC-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBpc-EUC-UCS2C
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBpc-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBT-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBT-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBT-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBTpc-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBTpc-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GBT-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\GB-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UCS2-GBK-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UCS2-GBpc-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UCS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-GB1\UniGB-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78ms-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78ms-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\78-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\83pv-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90msp-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90msp-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90ms-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90ms-RKSJ-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90ms-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90pv-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90pv-RKSJ-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90pv-RKSJ-UCS2C
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\90pv-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Add-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Add-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Add-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Add-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-1
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-3
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-4
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-6
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-7
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-90ms-RKSJ
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-90pv-RKSJ
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-H-CID
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-H-Host
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-H-Mac
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-PS-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-PS-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Adobe-Japan1-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Ext-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Ext-RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Ext-RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Ext-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hankaku
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hiragana
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hojo-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hojo-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hojo-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Hojo-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Katakana
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\NWP-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\NWP-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\RKSJ-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\RKSJ-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\Roman
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UCS2-90ms-RKSJ
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UCS2-90pv-RKSJ
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UCS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniHojo-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS2004-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISPro-UCS2-HW-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISPro-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISPro-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UCS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UCS2-HW-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UCS2-HW-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJIS-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISX02132004-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISX02132004-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISX0213-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\UniJISX0213-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan1\WP-Symbol
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Japan2\Adobe-Japan2-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-1
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-H-CID
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-H-Host
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-H-Mac
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-KSCms-UHC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-KSCpc-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\Adobe-Korea1-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-Johab-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-Johab-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCms-UHC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCms-UHC-HW-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCms-UHC-HW-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCms-UHC-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCms-UHC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCpc-EUC-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCpc-EUC-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCpc-EUC-UCS2C
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSCpc-EUC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\KSC-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UCS2-KSCms-UHC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UCS2-KSCpc-EUC
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UCS2-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UCS2-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF16-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF32-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF8-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-Korea1\UniKS-UTF8-V
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-0
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-1
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-3
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-4
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-5
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-6
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-7
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-8
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-9
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\Adobe-KR-UCS2
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\UniAKR-UTF16-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\UniAKR-UTF32-H
Final\poppler-25.12.0\share\poppler\cMap\Adobe-KR\UniAKR-UTF8-H
Final\poppler-25.12.0\share\poppler\COPYING
Final\poppler-25.12.0\share\poppler\COPYING.adobe
Final\poppler-25.12.0\share\poppler\COPYING.gpl2
Final\poppler-25.12.0\share\poppler\Makefile
Final\poppler-25.12.0\share\poppler\nameToUnicode\Bulgarian
Final\poppler-25.12.0\share\poppler\nameToUnicode\Greek
Final\poppler-25.12.0\share\poppler\nameToUnicode\Thai
Final\poppler-25.12.0\share\poppler\poppler-data.pc
Final\poppler-25.12.0\share\poppler\poppler-data.pc.in
Final\poppler-25.12.0\share\poppler\README
Final\poppler-25.12.0\share\poppler\unicodeMap\Big5
Final\poppler-25.12.0\share\poppler\unicodeMap\Big5ascii
Final\poppler-25.12.0\share\poppler\unicodeMap\EUC-CN
Final\poppler-25.12.0\share\poppler\unicodeMap\EUC-JP
Final\poppler-25.12.0\share\poppler\unicodeMap\GBK
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-2022-CN
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-2022-JP
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-2022-KR
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-8859-6
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-8859-7
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-8859-8
Final\poppler-25.12.0\share\poppler\unicodeMap\ISO-8859-9
Final\poppler-25.12.0\share\poppler\unicodeMap\KOI8-R
Final\poppler-25.12.0\share\poppler\unicodeMap\Latin2
Final\poppler-25.12.0\share\poppler\unicodeMap\Shift-JIS
Final\poppler-25.12.0\share\poppler\unicodeMap\TIS-620
Final\poppler-25.12.0\share\poppler\unicodeMap\Windows-1255
Final\semantic_chunks.json
Final\semantic_chunks.txt
Final\upstage_batch_results\upstage_full.json
Final\VectorDB.ipynb
git-training\.git\AUTO_MERGE
git-training\.git\COMMIT_EDITMSG
git-training\.git\config
git-training\.git\description
git-training\.git\HEAD
git-training\.git\hooks\applypatch-msg.sample
git-training\.git\hooks\commit-msg.sample
git-training\.git\hooks\fsmonitor-watchman.sample
git-training\.git\hooks\post-update.sample
git-training\.git\hooks\pre-applypatch.sample
git-training\.git\hooks\pre-commit.sample
git-training\.git\hooks\pre-merge-commit.sample
git-training\.git\hooks\prepare-commit-msg.sample
git-training\.git\hooks\pre-push.sample
git-training\.git\hooks\pre-rebase.sample
git-training\.git\hooks\pre-receive.sample
git-training\.git\hooks\push-to-checkout.sample
git-training\.git\hooks\sendemail-validate.sample
git-training\.git\hooks\update.sample
git-training\.git\index
git-training\.git\info\exclude
git-training\.git\logs\HEAD
git-training\.git\logs\refs\heads\feature\login
git-training\.git\logs\refs\heads\master
git-training\.git\objects\0e\b6f3db4b19fe02aa9b14cf82f14e2ca9239ee9
git-training\.git\objects\10\f98ec167a642e5a769b61b94441fa20d0c89c0
git-training\.git\objects\16\692d88b826528c690fc798a2e71494140bdff4
git-training\.git\objects\22\b496de9a6df58b429812e079a6b2f6c8466d2b
git-training\.git\objects\2a\93d00994fbd8c484f38b0423b7c42e87a55d48
git-training\.git\objects\2c\1258e761003f39c96827062ee535b65dc1dc79
git-training\.git\objects\30\a7cb61714fab59df4a3ef930ee916888ee8d39
git-training\.git\objects\33\23f354391b7d5238900363722196567eebfc7d
git-training\.git\objects\40\16e124f6d142ca0315f21780c384948997668f
git-training\.git\objects\6f\e48b40a6c07dd9c3371cd3eb75e454037c9fae
git-training\.git\objects\71\f763dbff68c94f6da6262bd1fd0fd26d1382c1
git-training\.git\objects\83\c79c8716df4e5805ec750ffed144cc12bf0849
git-training\.git\objects\a0\5a62b506e392bb81cf86cfaf830ae0328dfaa9
git-training\.git\objects\a7\74be4e093e927c4b873c20a3104c691a0056cd
git-training\.git\objects\bb\47cee05826ced94afbd3cb151956f8ae45532e
git-training\.git\objects\cb\62a003cf7c6d2ea3319b3a4e1d9fdcd333f216
git-training\.git\objects\da\0b7bcc076b952f8ef5665679843b538fa46f6a
git-training\.git\objects\f5\a6280e9852dab12a6d194be85bcbda4fd84ccb
git-training\.git\ORIG_HEAD
git-training\.git\refs\heads\feature\login
git-training\.git\refs\heads\master
git-training\a.txt
git-training\app.txt
git-training\login.txt
main.py_results\1_pymupdf_result.json
main.py_results\1_pymupdf_result.txt
main.py_results\2_pypdf_result.json
main.py_results\2_pypdf_result.txt
main.py_results\2_simple_dir_result.json
main.py_results\2_simple_dir_result.txt
main.py_results\3_docling_result.json
main.py_results\3_docling_result.txt
main.py_results\3_simple_dir_result.json
main.py_results\3_simple_dir_result.txt
main.py_results\4_docling_result.json
main.py_results\4_docling_result.txt
main.py_results\4_llamaparse_result.json
main.py_results\4_llamaparse_result.txt
main.py_results\5_docling_result.json
main.py_results\5_docling_result.txt
main.py_results\pymupdf_result.json
main.py_results\simple_dir_result.json
PRECOMMIT_SECRET_SCAN.md
README.md
remote.git\config
remote.git\description
remote.git\HEAD
remote.git\hooks\applypatch-msg.sample
remote.git\hooks\commit-msg.sample
remote.git\hooks\fsmonitor-watchman.sample
remote.git\hooks\post-update.sample
remote.git\hooks\pre-applypatch.sample
remote.git\hooks\pre-commit.sample
remote.git\hooks\pre-merge-commit.sample
remote.git\hooks\prepare-commit-msg.sample
remote.git\hooks\pre-push.sample
remote.git\hooks\pre-rebase.sample
remote.git\hooks\pre-receive.sample
remote.git\hooks\push-to-checkout.sample
remote.git\hooks\sendemail-validate.sample
remote.git\hooks\update.sample
remote.git\info\exclude
remote.git\objects\07\6d1547350d65a2c7678a0cfcb42f63f83cb2af
remote.git\objects\13\eddb290cb021896a3b075f70d26ed22b216e51
remote.git\objects\29\b879658ac43d20910fa8f48615703eb421ace4
remote.git\objects\2d\b8731da96c9baab784e80f69b0dd48569f1ff5
remote.git\objects\4e\f0d733efdb05d61246368a97ae1a67ca5c8fd1
remote.git\objects\4f\4cd8151c67e0de1eefb17b327804ba4dc32054
remote.git\objects\50\6812d383b8ab761d1b92579386191aef790ae1
remote.git\objects\6b\bf32e84517bb1ceb198293d9f9d2b03cdb1f9f
remote.git\objects\6d\aa394260c9556b7003636ade722d5d1b70ac7f
remote.git\refs\heads\master
requirements_daily_agent.txt
requirements-dev.txt
scripts\__pycache__\publish_latest_report.cpython-314.pyc
scripts\__pycache__\send_daily_report_email.cpython-314.pyc
scripts\publish_latest_report.py
scripts\secret_scan.py
scripts\send_daily_report_email.py
upstage_batch_results\upstage_final_merged.html
upstage_batch_results\upstage_final_merged.json
upstage_batch_results\upstage_final_merged.txt
upstage_batch_results2\upstage_final_merged.html
upstage_batch_results2\upstage_final_merged.json
upstage_batch_results2\upstage_final_merged.txt
upstage_batch_results2\upstage_final_merged_clean.json
upstage_results\part2_result.html
upstage_results\part2_result.json
upstage_results\part2_result.txt
```
