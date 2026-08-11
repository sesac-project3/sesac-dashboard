# z-invest/backend 구조 분석 (FastAPI 이전용)

> 분석 대상: `z-invest/backend` (Spring Boot 3.4.1 / Java 17 / Gradle)
> sesac-dashbaord에는 아직 backend가 없어, 워크스페이스에서 유일하게 실제 코드가 있는 이 프로젝트를 분석했다.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 프레임워크 | Spring Boot 3.4.1, Java 17 |
| DB | PostgreSQL + Spring Data JPA (`open-in-view=false`) |
| 캐시 | Redis (`spring-boot-starter-data-redis`) |
| 인증 | Spring Security + JWT (jjwt 0.12.6), Stateless |
| 실시간 | WebSocket + STOMP (`/ws`, `/ws-sockjs`), Redis 미사용 브로커(SimpleBroker) |
| 파일 저장 | AWS S3 (presigned URL 업로드 방식) |
| 푸시 알림 | Firebase Admin SDK (FCM) |
| 문서화 | springdoc-openapi (Swagger UI) |
| 모니터링 | Actuator + Micrometer Prometheus |
| 외부 HTTP | RestTemplate + OkHttp |
| 배치 | `@Scheduled` cron 기반 (주식 시세 배치) |

## 폴더 구조

```
backend/src/main/java/com/ssafy/backend/
├── BackendApplication.java
├── domain/               # 도메인별 controller / service / repository / entity / dto
│   ├── account/          # 수시입출금 계좌 (SSAFY 금융망 연동)
│   ├── admin/            # 관리자 로그인
│   ├── aireport/         # AI 리포트 생성 (외부 AI 서버 연동)
│   ├── auth/             # SSAFY OAuth 로그인, JWT 발급
│   ├── faq/               # FAQ (조회/관리자 CRUD)
│   ├── group/             # 모임 투자(계 형태), 투표
│   ├── invest/            # 투자 계좌/보유종목/즐겨찾기/투자성향테스트/주문/최근조회
│   ├── member/            # 회원 (SSAFY 연동)
│   ├── notification/      # 알림 설정, FCM 푸시 토큰
│   ├── profile/           # 프로필, 팔로우
│   ├── quiz/               # 데일리 퀴즈
│   ├── shortform/          # 숏폼 영상 (업로드/피드/좋아요/STT)
│   └── stock/              # 종목/시세/차트/호가/배치 (KIS, DART 연동)
└── global/
    ├── config/            # CORS, Security, S3, Firebase, KIS/DART/SSAFY properties, WebSocket 등
    ├── exception/         # 커스텀 예외 + GlobalExceptionHandler
    ├── response/          # 공통 응답 포맷 (ApiResponse, ErrorResponse)
    ├── s3/                # S3Uploader
    ├── security/          # JwtTokenProvider, JwtAuthenticationFilter, 핸들러
    └── util/               # 헤더/거래번호 생성 유틸
```

각 도메인은 `controller / service / repository / entity(+enums) / dto` 로 통일된 계층 구조. 이 패턴은 FastAPI로 옮길 때 `router / service / models(SQLAlchemy) / schemas(Pydantic)` 로 1:1 매핑하기 좋다.

## 도메인별 기능 요약

### 1. auth — 로그인/인증
- `GET /api/v1/auth/ssafy/authorize`, `GET /api/v1/auth/ssafy/callback` — SSAFY OAuth 인가코드 플로우
- `POST /api/v1/auth/refresh` — 리프레시 토큰으로 액세스 토큰 재발급
- `GET /api/v1/auth/me` — 내 정보
- `POST /api/v1/finance/userkey`, `GET /api/v1/finance/me` — SSAFY 금융망 계좌 연동(userKey 발급)
- JWT는 access/refresh 2종, HMAC 서명, subject=userId. `JwtAuthenticationFilter`가 매 요청 검증 후 SecurityContext에 세팅.
- **주의**: `SecurityConfig`가 현재 `anyRequest().permitAll()`로 전체 개방 상태 (주석: "API 테스트 때만 일단 열어둠, 추후 인증 필수로 변경 필요"). 이전 시 인증 필수 정책을 어떻게 할지 결정 필요.

### 2. account — 수시입출금 계좌 (SSAFY 금융망 API 프록시)
- `DemandDepositController` (`/api/demand-deposit/**`) — 상품 생성/조회, 계좌 생성/조회/상세/잔액/입출금/이체/이체한도/거래내역/해지, PIN 검증/변경, 닉네임 변경 등 약 20개 엔드포인트. 대부분 SSAFY 오픈뱅킹 실습 API(`SsafyDemandDepositClient`)를 그대로 감싸는 프록시.
- `TransferController` (`/api/v1/transfers/**`) — 이체 설정 조회, 수취인 검증, 이체 실행 (`TransferFacadeService`가 오케스트레이션).
- Entity: `Account`, `RecentTransferRecipient`.

### 3. invest — 투자(모의투자) 도메인
- `InvestmentAccountController` — 투자계좌 조회/입출금 (`/api/v1/me/accounts`, `/me/invest/account/**`)
- `StockOrderController` (`/api/v1/invest/orders/**`) — 주문 목록/체결내역/개요, 매수/매도 미리보기·생성·수정·취소
- `HoldingController` — 보유종목, 포트폴리오 요약/대시보드
- `FavoriteStockController` — 관심종목 등록/삭제/조회
- `RecentViewedStockController` — 최근 본 종목
- `InvestmentTestController` — 투자성향 테스트 문항/제출/내 결과
- Entity: `InvestmentAccount`, `Holding`, `StockOrder`, `StockOrderExecution`, `FavoriteStock`, `RecentViewedStock`, `InvestmentPropensity`, `InvestmentQuestion`, `InvestmentOption`

### 4. stock — 종목/시세/차트/호가
- `StockController` (`/api/v1/stocks/**`) — 종목 목록/검색, 상세, 현재가, 캔들(차트)
- `OrderBookController` (`/api/market/**`) — 실시간 호가 구독/해제, KIS 웹소켓 상태, mock 모드 토글, 승인키 발급 (내부적으로 KIS 실시간 시세 연동 + STOMP 브로드캐스트로 추정)
- `StockBatchController` (`/api/v1/stocks/admin/**`) — 종목마스터 임포트, 일/분봉 백필, 재무데이터(DART) 동기화 — 관리자/배치 트리거용
- 외부 연동: `KisStockClient`(한국투자증권 Open API, 시세/차트), `DartFinancialClient`(DART 공시 재무정보), `SsafyMemberClient`
- `StockScheduler`: cron으로 마스터/일봉/분봉/재무데이터 배치 자동 실행 (기본은 모두 `enabled=false`, properties로 on/off)
- Entity: `Stock`, `StockDailyCandle`, `StockMinuteCandle`, `StockBatchJobState`

### 5. group — 모임 투자(계모임)
- `GroupController` (`/api/group/**`) — 모임 생성/조회/상세, 계좌, 이미지 presign/업로드, 초대(생성/수락/거절/취소), 펀딩, 해산 및 해산투표
- `InvestVoteController` — 모임 내 투자 제안/투표/확정/조회
- Entity: `Group`, `GroupMember`, `GroupInvitation`, `InvestVote`, `InvestVoteRecord`, `DissolutionVote`, `DissolutionVoteRecord`
- S3 presigned URL 업로드 패턴 재사용 (프로필 이미지와 동일 방식)

### 6. shortform — 숏폼 영상 피드
- `ShortformUploadController` — 업로드 init(presigned)/confirm
- `ShortformController` (`/api/v1/shortforms/**`) — 검색, 피드(커서 페이지네이션), 조회수 기록, 좋아요, 삭제
- `ShortformProfileController` — 특정 유저의 숏폼 목록
- STT(`AiSttClient`) 로 영상 음성 텍스트 추출 → 종목 태깅(`StockTag`)에 활용 추정
- Entity: `Shortform`, `ShortformLike`, `ShortformView`, `ShortformStock`, `ShortformSttResult`, `UserTagWeight`(추천 가중치)

### 7. aireport — AI 리포트
- `POST /api/v1/ai-reports/trade` — 매매 리포트 생성
- `GET /api/v1/ai-reports/shortforms/{id}` — 숏폼 리포트
- `GET /api/v1/ai-reports/stocks/{stockCode}` — 종목 상세 리포트
- 외부 AI 리포트 서버(`AiReportClient`, `aireport.base-url`)에 위임하는 프록시 성격

### 8. profile — 프로필/팔로우
- 내 프로필 조회/수정, 프로필 이미지 presign, 유저 프로필/팔로워/팔로잉/검색, 보유종목·포트폴리오 요약/대시보드(공개용), 팔로우/언팔로우

### 9. member / admin — 회원 및 관리자
- `MemberController` (`/api/member`) — SSAFY 연동 회원가입, 검색, 조회
- `AdminController`, `AdminFaqController` — 관리자 로그인/가입, FAQ 관리(CRUD)

### 10. notification — 알림
- 알림 설정 조회/수정, FCM 푸시 토큰 등록/삭제 (`PushNotificationService`가 실제 발송 담당)

### 11. quiz — 데일리 퀴즈
- 오늘의 퀴즈, 응시 상태, 제출 — `QuizDataInitializer`로 초기 데이터 시딩

### 12. faq
- 공개 FAQ 목록/상세, 관리자 CRUD

## 공통 인프라 (global/)
- **예외 처리**: `BusinessException` 계열(BadRequest/Conflict/Forbidden/NotFound/ServiceUnavailable/Unauthorized/UnprocessableEntity) + `ErrorCode` enum + `GlobalExceptionHandler`(`@RestControllerAdvice` 추정)로 통일된 에러 응답.
- **공통 응답**: `ApiResponse`/`ApiResponses` 래퍼 + `SuccessCode` enum — 모든 API가 동일한 success/data 포맷 사용.
- **설정 프로퍼티 클래스**: `AiReportProperties`, `AwsProperties`, `DartProperties`, `FirebaseProperties`, `KisProperties`, `SsafyApiProperties`, `SsafyOAuthProperties`, `StockMasterProperties`, `StockScheduleProperties`, `CorsProperties`, `AuthProperties` — 전부 `@ConfigurationProperties` 기반, `.env`/`application.properties`로 주입.
- **CORS**: `localhost:3000`, `:5173`, 사내망 IP 대역 허용, 모든 메서드/헤더 허용 + credential 허용.

## 데이터베이스
- PostgreSQL, JPA/Hibernate (`ddl-auto` 명시 안 됨 → 프로필별 설정 확인 필요, `application-prod.properties`도 존재)
- 배치 fetch size 100, `open-in-view=false` → 트랜잭션 경계 명확 (FastAPI+SQLAlchemy로 옮길 때도 요청 스코프 세션 패턴 유지 권장)

## FastAPI 이전 시 참고 포인트 (요청 범위 밖이지만 짧게 메모)
- 도메인 구조(`domain/*/{controller,service,repository,entity,dto}`)를 그대로 `app/*/{router,service,repository,models,schemas}` 로 옮기면 매핑이 쉬움.
- JWT/Security → `fastapi-users` 또는 직접 `PyJWT` + `Depends` 인증 미들웨어로 대체 가능.
- WebSocket(STOMP)은 FastAPI 네이티브 WebSocket + 직접 pub/sub(Redis 등)로 재설계 필요 (STOMP 프로토콜 자체는 FastAPI에 없음).
- `@Scheduled` 배치 → APScheduler 또는 별도 워커/Celery beat.
- SSAFY/KIS/DART/AI리포트/STT 등 외부 API 클라이언트는 로직 이식 대상이지, 이전 자체와 무관 (그대로 httpx로 재작성).
