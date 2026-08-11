# PRODUCT.md — Next.js + FastAPI 재구축 실행 계획

> 기준 문서: [`PRD.md`](./PRD.md) (AI 기반 국내주식 투자 인사이트 플랫폼)
> 목적: `z-invest`(Spring Boot backend + FastAPI ai 서비스)의 기존 자산 중 PRD 요구사항에 맞는 부분을 식별하고, Next.js + FastAPI 스택으로 **5명 / 2.5일** 안에 만들 수 있도록 이슈 단위로 쪼갠다.
> 이 문서는 산출물(코드) 분석이 아니라 **실행 계획**이다 — "무엇을 그대로 옮기고, 무엇을 새로 짜는지"와 "누가 언제 할지"만 다룬다.

---

## 1. 재사용 자산 매핑 (z-invest → 이번 프로젝트)

PRD의 기능 요구사항(F-01~F-05) 기준으로, `z-invest/backend`(Spring Boot)와 `z-invest/ai`(이미 FastAPI)에서 가져올 수 있는 것과 새로 만들어야 하는 것을 나눈다.

| PRD 기능 | z-invest 소스 | 상태 | 이전 방식 |
| --- | --- | --- | --- |
| F-01 실시간 차트 `P0` | `backend/domain/stock/kis/KisStockClient.java`, `StockController`, `StockScheduler`, `StockDailyCandle`/`StockMinuteCandle` 엔티티 | Java, 포팅 필요 | KIS REST 연동 로직을 `httpx` 기반 Python 클라이언트로 재작성. 엔티티 → SQLAlchemy 모델. cron 스케줄 로직은 그대로 이식(APScheduler) |
| F-02 AI 숏폼 `P1` | `ai/stt/*` (STT 전사+3줄 요약, **이미 FastAPI**) + `backend/domain/shortform/*` (피드/좋아요/조회수/태깅 로직) | STT는 재사용 가능, 나머지는 참고만 | `ai/stt` 라우터·서비스는 그대로 이식. 숏폼 피드/좋아요 API는 Java 로직을 FastAPI 라우터로 재작성. **영상 합성 파이프라인(S3 사전 저장 + 자막 오버레이)은 z-invest에 없음 → 신규 개발** |
| F-03 AI 심층 리포트 `P0` | `ai/reports/*` (trade/shortform/stock-detail 3종 리포트, **이미 FastAPI + Pydantic 스키마 완비**) + `backend/domain/stock/dart/DartFinancialClient.java`(재무데이터) + `backend/domain/aireport/*` | 스캐폴딩 재사용 가능 | `ai/reports/router.py`, `schemas.py`, `scoring.py`, `service.py` 그대로 이식. 현재는 프론트/백엔드가 계산한 값(캔들 지표, 재무 등)을 입력으로 받는 구조라 **DART/KIS 실데이터 연동 → 입력 조립 로직만 신규 작성**하면 됨 |
| F-04 텔레그램 시그널/브리핑 `보류` | 없음 (z-invest 전체에 텔레그램 코드 없음). `backend/domain/notification/*`(FCM 푸시)는 구조만 참고 가능 | 전량 신규, 이번 스프린트 스코프 아웃 | ⏸️ **후순위로 연기**: 정기 브리핑("오늘의 리포트")·임계값 시그널("시세 알림") 둘 다 보류. 상세는 ISSUE-E4 |
| F-05 커뮤니티 민심(날씨) `P2` | `ai/news/*` (네이버 뉴스 감성분석 + SQLite 캐시, **이미 FastAPI**) | 파이프라인 구조만 재사용 | `ai/news`는 "뉴스" 감성분석이지 "커뮤니티"가 아님. 캐시·LLM 분류 파이프라인 패턴(`cache.py`, `sentiment.py`)만 그대로 따라가고, 커뮤니티 크롤러 자체는 신규 (PRD상 P2, 여유 시 구현) |
| 인증/관심종목 저장 주체 | `backend/global/security/*`(JWT), `domain/invest/favorite/*` | ✅ 결정됨 | **카카오 OAuth 로그인 + 자체 발급 JWT**로 확정. `users`·`kakao_tokens`(1:1) 스키마는 [`SCHEMA.md`](./SCHEMA.md) 참고. JWT access token은 짧은 수명 stateless 검증, refresh token은 **Redis**에 저장(DB 미저장) — 상세는 ISSUE-001 |

**결론**: `ai/reports`, `ai/news`, `ai/stt` 세 모듈은 이미 FastAPI라 **거의 그대로 이식**된다. 가장 무거운 신규 작업은 ① KIS 실시간 시세/차트 Python 포팅, ② 숏폼 영상 합성 파이프라인이다. ③ 텔레그램 봇(브리핑/시그널)은 이번 스프린트에서 **보류**로 변경.

---

## 2. 시스템 구성

```
Next.js (App Router, TS)  ──REST──▶  FastAPI
  - 대시보드(지수/환율)                - auth: 카카오 로그인/JWT 발급·재발급 (신규)
  - 숏폼 피드                          - stocks: 시세/차트 (F-01)
  - 종목 상세 리포트                    - reports: AI 리포트 (F-03, ai/reports 이식)
  - 텔레그램 연동 안내(보류)             - news: 뉴스 감성 (ai/news 이식)
                                       - shortforms: 피드/좋아요/업로드 (F-02)
                                       - stt: 영상 전사 (ai/stt 이식)
                                       - telegram: 봇 웹훅/브리핑 (F-04, 보류)
                                       - community: 민심 분석 (F-05, 신규, P2)
                    │
                    ▼
         PostgreSQL (종목/캔들/뉴스/리포트캐시/카카오 토큰) + Redis (시세/LLM 캐시 + JWT refresh token)
                    │
                    ▼
   외부: KIS Open API / DART / Naver News / OpenAI / Telegram Bot API / 카카오 로그인
```

기존 `z-invest/ai`는 독립 FastAPI 앱(`ai/app.py`)이었지만, 이번 프로젝트는 이를 **단일 FastAPI 앱의 라우터**로 흡수한다 (`app/routers/{auth,stocks,reports,news,shortforms,stt,telegram,community}.py`).

---

## 3. 팀 구성 및 일정 (5명 × 2.5일)

2.5일 = Day 1(풀데이) + Day 2(풀데이) + Day 3(반나절)로 가정. Day 1 오전은 **전원 공통 셋업**에 투입하고, 이후 각자 트랙을 세로로(FE+BE 모두) 담당해 결합 지점을 최소화한다.

| 트랙 | 담당 | 커버 기능 | 우선순위 |
| --- | --- | --- | --- |
| A. 플랫폼/시세 | 1명 | 공통 인프라 + F-01(차트) 백엔드 | P0 |
| B. 대시보드/차트 UI | 1명 | 공통 인프라 + F-01(차트) 프론트 | P0 |
| C. AI 리포트 백엔드 | 1명 | F-03 백엔드 (ai/reports 이식 + DART/KIS 연동) | P0 |
| D. AI 리포트 프론트 + 민심 | 1명 | F-03 프론트 + F-05(여유 시) | P0 → P2 |
| E. 숏폼 + 텔레그램 | 1명 | F-02(ai/stt 이식 포함) + F-04(봇 연동 골격만, 브리핑·시그널 보류) | P1 → 보류 |

```
Day 1 AM  ── 전원: 공통 셋업 (ISSUE-000)
Day 1 PM  ┬─ A: KIS 연동/캐시        ┬─ B: 레이아웃/디자인시스템/대시보드
          ├─ C: ai/reports 이식      ├─ D: 리포트 페이지 스켈레톤
          └─ E: ai/stt 이식
Day 2 AM  ┬─ A: 캔들 백필/스케줄러    ┬─ B: 실시간 차트 컴포넌트
          ├─ C: DART 연동/스코어링   ├─ D: 6개 블록 UI 연결
          └─ E: 숏폼 피드 API + 영상 합성
Day 2 PM  ┬─ A: 지수/환율 API        ┬─ B: 숏폼 피드 UI
          ├─ C: 리포트 캐싱/배치     ├─ D: (여유) F-05 착수
          └─ E: 숏폼 QA/버퍼 (텔레그램 브리핑·시그널 보류로 확보된 시간, 여유 시 ISSUE-E4 연동 골격만)
Day 3 AM  ── 전원: 통합 테스트, 5종목 데이터 채우기, 배포, 발표 자료
```

---

## 4. 이슈 목록

### 공통 (Day 1 오전, 전원 참여)

**ISSUE-000. 프로젝트 스캐폴딩 & 계약 확정** `P0`
- Next.js(App Router) / FastAPI 레포 초기화, Docker Compose(Postgres+Redis)
- 5종목 마스터 데이터 시딩 (삼성전자, SK하이닉스, 현대자동차, LG에너지솔루션, 한화오션)
- 공통 응답 포맷(`ApiResponse`) + 에러 핸들러 (`backend/global/response`, `global/exception` 참고)
- API 계약: 각 트랙이 만들 엔드포인트의 요청/응답 스키마를 이 시점에 합의 (뒤 이슈들의 스키마는 이 합의를 전제로 함)
- 사용자 식별 방식: **카카오 OAuth + 자체 JWT**로 결정 (ISSUE-001에서 구현). `users`/`kakao_tokens` 스키마는 [`SCHEMA.md`](./SCHEMA.md) 참고
- **완료 기준**: `docker compose up`으로 FE/BE/DB/Redis 기동, 5종목 시드 데이터 확인

---

**ISSUE-001. 카카오 OAuth 로그인 + JWT 인증/인가** `P0`
- 참고: `backend/global/security/*`(JWT 발급/검증 필터 구조), [`SCHEMA.md`](./SCHEMA.md#33-카카오-oauth--kakao_tokens)(`users` 1:1 `kakao_tokens`)
- **로그인 플로우**: 프론트가 카카오 인가 URL로 리다이렉트 → `GET /auth/kakao/callback?code=`에서 인가코드를 카카오 토큰으로 교환 → `/v2/user/me`로 `kakao_user_id` 조회 → `kakao_tokens.kakao_user_id`로 기존 유저 조회, 없으면 `users` + `kakao_tokens` 신규 생성, 있으면 카카오 access/refresh token 갱신(upsert)
- **JWT 발급**: 로그인 성공 시 서비스 자체 access token(짧은 수명, 예 1시간, 서명 검증만으로 stateless 인가) + refresh token(예 14일) 발급
- **refresh token 저장 = Redis** (`refresh:{user_id}` 키, TTL을 refresh token 수명과 동일하게 설정, DB에는 저장하지 않음)
  - 재발급(`POST /auth/refresh`): 클라이언트가 보낸 refresh token을 Redis에 저장된 값과 대조 → 일치 시 새 access token 발급(+ rotation으로 refresh token도 재발급하며 Redis 키 값 교체)
  - 로그아웃/탈퇴: Redis 키 삭제로 즉시 무효화 (DB 방식 대비 별도 만료/블랙리스트 정리 배치 불필요)
- **인가**: 관심종목(watchlist)·텔레그램 연동 등 로그인 필요 라우트는 FastAPI `Depends`로 access token 검증 공용 미들웨어 적용, 미인증 시 401
- **완료 기준**: 카카오 로그인 → JWT 발급 → 보호된 엔드포인트 접근 → refresh token으로 재발급 → 로그아웃(Redis 키 삭제 확인) 전체 플로우 동작

---

### 트랙 A — 플랫폼/시세 (F-01 백엔드)

**ISSUE-A1. KIS Open API 클라이언트 포팅** `P0`
- 참고: `backend/domain/stock/kis/KisStockClient.java`, `KisTokenService.java`
- 현재가/차트 조회 + 토큰 자동 갱신(24h 만료) 로직을 `httpx` 기반 Python 클라이언트로 재작성
- **완료 기준**: 5종목 현재가/일봉/분봉 조회 성공

**ISSUE-A2. 시세 DB 스키마 + 캐시 전략** `P0`
- 참고: `StockDailyCandle`, `StockMinuteCandle`, `StockBatchJobState` 엔티티
- SQLAlchemy 모델 설계, "DB 우선 조회 → 없으면 KIS 호출" 로직 (PRD §F-01 차트 값 갱신 기준)
- Redis에 최신가 단기 캐시
- **완료 기준**: DB에 캔들 있으면 KIS 미호출, 없으면 호출 후 저장

**ISSUE-A3. 배치 스케줄러 (장중 5분 분봉 / 17시 일봉)** `P0`
- 참고: `StockScheduler.java` (cron 패턴 그대로 이식)
- APScheduler로 재구현, on/off 플래그는 환경변수
- **완료 기준**: 스케줄 트리거 시 5종목 캔들 저장 확인 (로컬은 수동 트리거 엔드포인트로 검증)

**ISSUE-A4. 지수/환율 API** `P0`
- 코스피/코스닥 지수, 원/달러 환율 조회 엔드포인트 (KIS 지수 API 또는 대체 소스)
- **완료 기건**: `GET /api/v1/market/indices` 가 3개 지표 반환

---

### 트랙 B — 대시보드/차트 UI (F-01 프론트)

**ISSUE-B1. 레이아웃 & 디자인 시스템 셋업** `P0`
- 공통 헤더/하단 탭(홈·숏폼·검색), 반응형 그리드, Recharts 셋업
- **완료 기준**: 빈 페이지라도 홈/숏폼/리포트 3개 라우트 이동 가능

**ISSUE-B2. 홈 대시보드 (지수/환율 카드)** `P0`
- ISSUE-A4 연동, 실패 시 마지막 캐시값+타임스탬프 표시 (§8 가용성 요구사항)
- **완료 기준**: 코스피/코스닥/환율 3개 카드 렌더링

**ISSUE-B3. 실시간 차트 컴포넌트** `P0`
- 60분/1일/1주/1월 토글, 캔들/라인 토글, 장중 갱신
- ISSUE-A1~A2 연동
- **완료 기준**: 4개 단위 전환 1초 내 렌더링 (PRD 수용 기준)

---

### 트랙 C — AI 리포트 백엔드 (F-03)

**ISSUE-C1. `ai/reports` 라우터 이식** `P0`
- `z-invest/ai/reports/{router,schemas,service,scoring,cache}.py` 그대로 복사 후 프로젝트 구조에 맞게 통합
- **완료 기준**: `/ai/reports/stock-detail` 등 3개 엔드포인트가 목업 입력으로 정상 응답

**ISSUE-C2. DART 재무데이터 연동** `P0`
- 참고: `backend/domain/stock/dart/DartFinancialClient.java` (기업코드 매핑, 영업이익률/연도별 매출)
- Python으로 재작성, F-03-2(매출·영업이익 분석) 입력 조립
- **완료 기준**: 5종목 연도별 매출/영업이익 조회 성공

**ISSUE-C3. 리스크 체크 정량 스코어링** `P0`
- 참고: `ai/reports/scoring.py` (있으면 확장, 없으면 신규)
- 시장변동성(60일 표준편차) / 실적신뢰도 / 경쟁강도 공식화 (§F-03-3)
- **완료 기준**: 3개 축 점수가 0~100 범위로 산출되고 산출 근거가 응답에 포함

**ISSUE-C4. 리포트 배치 생성 + 캐싱** `P0`
- 장 마감 후 1일 1회 5종목 리포트 사전 생성, Redis/DB 캐시로 응답 속도 확보 (15초 이내 요구사항은 캐시 히트 시 무의미하므로 **배치 생성이 핵심**)
- **완료 기준**: 캐시 히트 시 응답 1초 이내, 미스 시 15초 이내

---

### 트랙 D — 리포트 프론트 + 민심 (F-03 프론트, F-05)

**ISSUE-D1. 종목 상세 리포트 페이지 스켈레톤** `P0`
- `StockDetailReportResponse` 스키마(`ai/reports/schemas.py`) 기준으로 6개 블록 레이아웃
- **완료 기준**: 목업 데이터로 6블록 모두 렌더링

**ISSUE-D2. 투자판단/성장성/밸류에이션 블록 연동** `P0`
- F-03-1(매수/중립/매도 + 근거 3가지, 근거 없으면 블록 비노출), F-03-2(매출·영업이익 차트), F-03-6(52주 밴드)
- ISSUE-C1~C4 연동
- **완료 기준**: 근거 누락 시 블록 자동 숨김 동작 확인

**ISSUE-D3. 리스크체크/뉴스/동종비교 블록 연동** `P0`
- F-03-3(레이더/게이지), F-03-4(뉴스 카드, `ai/news` 연동), F-03-5(동종업계 비교 표)
- **완료 기준**: 뉴스 7개 매체 소스 중 수집된 것만 정상 노출, 없으면 빈 상태 처리

**ISSUE-D4. (여유 시) 커뮤니티 민심 위젯** `P2`
- 참고: `ai/news/{cache,sentiment}.py` 구조를 커뮤니티 소스로 변형
- ☀️/🌤️/🌧️ 날씨 메타포 + 24시간 언급량 추이
- **완료 기준**: 시간 남을 때만 착수, 없어도 배포 가능해야 함

---

### 트랙 E — 숏폼 + 텔레그램 (F-02, F-04)

**ISSUE-E1. `ai/stt` 이식** `P1`
- `z-invest/ai/stt/*` 그대로 복사, faster-whisper 모델은 CPU(int8)로 기본 설정
- **완료 기준**: 영상 업로드 → 전사 텍스트 + 3줄 요약 응답

**ISSUE-E2. 숏폼 피드 API (좋아요/조회수/커서 페이지네이션)** `P1`
- 참고: `backend/domain/shortform/{controller,service,entity}` (Java 로직 → FastAPI 라우터로 재작성)
- **완료 기준**: 피드 커서 페이지네이션, 좋아요 토글 동작

**ISSUE-E3. 숏폼 영상 합성 파이프라인 (신규)** `P1`
- PRD §9.4 폴백 전략 적용: **A안(정적 배경 + 자막 애니메이션) 먼저 구현**, S3에 종목별 긍/부정 배경 사전 업로드
- ISSUE-E1(자막 텍스트) 결과를 오버레이
- **완료 기준**: 5종목 × 2건(긍/부정) = 10개 영상 항상 존재 (PRD 수용 기준)

**ISSUE-E4. 텔레그램 봇 연동 (신규)** `보류`
- ⏸️ **보류**: 정기 브리핑("오늘의 리포트", 08:00/16:30)과 임계값 시그널("시세 알림", 지수 대비 3~5%p·당일 등락 ±5%) 발송 기능 둘 다 이번 스프린트에서 제외
- 일회용 연동 코드 발급 → 사용자가 봇에 전송 → `chat_id` 매핑 저장(`telegram_link_codes`, `users.telegram_chat_id`)까지는 스키마가 이미 준비돼 있으므로, 시간이 남으면 연동 골격(코드 발급~매핑)만 구현하고 발송 로직(브리핑/시그널)은 다음 스프린트로 넘긴다
- **완료 기준(재개 시)**: 예약 시각 ±1분 내 발송, 중복 발송 없음 (PRD 수용 기준) — 이번 스프린트에는 해당 없음

---

## 5. Day 3 오전 — 통합 및 마감 (전원)

- 5종목 × 전체 기능 수동 검수 (PRD §2.2 기능 완결성 100% 목표)
- AI 리포트 사실 오류 수동 체크 (종목당 0건 목표)
- 배포 (Docker Compose 단일 서버, PRD §7.2 제안)
- 발표 자료 정리

## 6. 이슈 작성 시 유의사항

- 모든 P0 이슈는 데모 필수. P1은 시간이 부족하면 F-02(숏폼)의 ISSUE-E3(영상 합성)부터 스코프를 줄인다 (자막 텍스트만 노출하는 정적 카드로 축소 가능).
- F-04(텔레그램 정기 브리핑·임계값 시그널, ISSUE-E4)는 **이번 스프린트에서 보류 확정** — 후순위로 미루며, 재개 시를 대비해 스키마(`telegram_link_codes`, `telegram_notifications`)만 유지한다.
- F-05(민심)는 처음부터 스코프 아웃 후보로 간주하고 다른 트랙이 밀리면 가장 먼저 버린다.
- `z-invest/backend`의 Java 코드는 **로직 참고용**이지 직접 실행 대상이 아니다 — 포팅 시 SSAFY 금융망 특화 로직(계좌/이체 등)은 이번 PRD 범위(§4.2 Out of Scope: 실제 주문 체결)에 없으므로 가져오지 않는다.
