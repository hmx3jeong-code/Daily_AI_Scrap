# Daily AI News Agent

## 1) 실행

사전 준비(최초 1회):

```powershell
pip install openai python-dotenv
$env:GEMINI_API_KEY=""
```

```powershell
python daily_ai_news_agent.py --config daily_ai_agent_config.json
```

생성 파일:

- `daily_ai_reports/daily_ai_brief_YYYY-MM-DD.md`
- `daily_ai_reports/daily_ai_brief_YYYY-MM-DD.json`

결과 규칙:

- 기사 제목/요약/키워드를 자연스러운 한국어로 변환해서 저장
- 기본으로 최근 7일 범위에서 수집하고, 기사 수가 부족하면 오래된 기사로 보충해 약 10개를 맞춤
- 요약은 4~6문장 상세 요약으로 생성

## 2) 빠른 점검 (네트워크 없이)

```powershell
python daily_ai_news_agent.py --dry-run
```

## 3) LLM 요약 켜기 (Gemini 무료 기본값)

현재 기본 설정은 이미 Gemini 무료 모델로 되어 있습니다:

- `"llm.enabled": true`
- `"llm.provider": "gemini"`
- `"llm.model": "gemini-3.1-flash-lite-preview"`

필수 환경 변수:

- `GEMINI_API_KEY` (권장)
- `GOOGLE_API_KEY` (`GEMINI_API_KEY`가 없을 때 대체로 사용 가능)

주의:

- `daily_ai_agent_config.json`의 `llm.api_key_env`에는 실제 키가 아니라 환경 변수 이름(예: `GEMINI_API_KEY`)을 넣어야 함

## 4) 소스/키워드 커스터마이징

- 권위 있는 출처 추가/삭제: `sources`
- 주제 분류 정확도 조정: `topic_rules`
- 주요 이슈 추출 조정: `issue_rules`
- 기사 개수/기간 조정: `report_options` (`default_lookback_days`, `target_articles`, `max_total_articles`)

## 5) 매일 자동 실행 (Windows 작업 스케줄러 예시)

```powershell
schtasks /Create /SC DAILY /TN "DailyAIBrief" /TR "powershell -NoProfile -ExecutionPolicy Bypass -Command cd 'C:\Users\JS-JEONG\Desktop\test3'; python daily_ai_news_agent.py --config daily_ai_agent_config.json" /ST 09:00
```

## 6) URL 있는 UI 서비스로 배포 (GitHub Pages + Actions)

이 프로젝트에는 아래 파일이 이미 추가되어 있습니다:

- `.github/workflows/publish_daily_ai_brief.yml` : 평일 오전 9시(KST) 자동 실행
- `docs/index.html` : 웹 UI
- `scripts/publish_latest_report.py` : `latest.json`, `index.json` 생성

설정 순서:

1. GitHub 저장소에 푸시
2. GitHub 저장소 `Settings > Secrets and variables > Actions`에서 `GEMINI_API_KEY` 등록
3. `Settings > Pages`에서 배포 소스를 `GitHub Actions`로 설정
4. `Actions` 탭에서 `Publish Daily AI Brief`를 `Run workflow`로 1회 수동 실행

완료 후 URL:

- `https://<github-id>.github.io/<repo-name>/`

스케줄 기준:

- GitHub Actions cron `0 0 * * 1-5` = 한국시간 평일 오전 9시
