-- ============================================================
-- sesac-dashboard DB 스키마 (PostgreSQL)
-- 근거 문서: PRODUCT.md, PRD.md, docs/data/raw/*.csv
-- 상세 설명: ../../SCHEMA.md
-- ============================================================

-- 모든 테이블의 updated_at 자동 갱신용 공통 트리거 함수
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 1. stocks — 종목 마스터 (ISSUE-000 5종목 시딩 대상)
-- ============================================================
CREATE TABLE stocks (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) NOT NULL UNIQUE,               -- 종목코드 (예: 005930)
    name        VARCHAR(50) NOT NULL UNIQUE,               -- 종목명 (예: 삼성전자)
    market      VARCHAR(10) NOT NULL CHECK (market IN ('KOSPI', 'KOSDAQ')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_stocks_updated_at
    BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 2. stock_daily_candles — 일봉 (F-01, ISSUE-A2/A3)
-- ============================================================
CREATE TABLE stock_daily_candles (
    id          BIGSERIAL PRIMARY KEY,
    stock_id    INTEGER NOT NULL REFERENCES stocks(id),
    trade_date  DATE NOT NULL,
    open_price  NUMERIC(15,2) NOT NULL,
    high_price  NUMERIC(15,2) NOT NULL,
    low_price   NUMERIC(15,2) NOT NULL,
    close_price NUMERIC(15,2) NOT NULL,
    volume      BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stock_id, trade_date)
);

CREATE TRIGGER trg_stock_daily_candles_updated_at
    BEFORE UPDATE ON stock_daily_candles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 3. stock_minute_candles — 분봉 (F-01, ISSUE-A2/A3, 장중 5분 저장)
-- ============================================================
CREATE TABLE stock_minute_candles (
    id          BIGSERIAL PRIMARY KEY,
    stock_id    INTEGER NOT NULL REFERENCES stocks(id),
    traded_at   TIMESTAMPTZ NOT NULL,
    open_price  NUMERIC(15,2) NOT NULL,
    high_price  NUMERIC(15,2) NOT NULL,
    low_price   NUMERIC(15,2) NOT NULL,
    close_price NUMERIC(15,2) NOT NULL,
    volume      BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stock_id, traded_at)
);

CREATE TRIGGER trg_stock_minute_candles_updated_at
    BEFORE UPDATE ON stock_minute_candles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 4. market_indices — 코스피/코스닥 지수, 원/달러 환율 (ISSUE-A4)
-- ============================================================
CREATE TABLE market_indices (
    id           BIGSERIAL PRIMARY KEY,
    index_type   VARCHAR(20) NOT NULL CHECK (index_type IN ('KOSPI', 'KOSDAQ', 'USD_KRW')),
    value        NUMERIC(15,4) NOT NULL,
    recorded_at  TIMESTAMPTZ NOT NULL,                     -- 조회 시각 (실패 시 마지막 캐시값 판단 기준, PRD §8)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (index_type, recorded_at)
);

CREATE TRIGGER trg_market_indices_updated_at
    BEFORE UPDATE ON market_indices
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 5. data_source — 뉴스 + 토스 커뮤니티 통합 (F-03-4, F-05)
--    실제 배포명은 data_source (news는 설계 당시 가칭)
--    종류가 '토스_커뮤니티'면 url은 항상 NULL
--    raw 데이터 매핑은 SCHEMA.md 참고
-- ============================================================
CREATE TABLE data_source (
    id           BIGSERIAL PRIMARY KEY,
    date         DATE NOT NULL,                            -- 날짜
    stock_id     INTEGER NOT NULL REFERENCES stocks(id),   -- 종목명
    source_type  VARCHAR(20) NOT NULL CHECK (source_type IN ('뉴스', '토스_커뮤니티')), -- 종류
    headline     TEXT NOT NULL,                             -- 뉴스 헤드라인 (토스는 게시글 제목/본문)
    url          TEXT,                                      -- 뉴스_URL (토스_커뮤니티면 NULL)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_news_toss_url_null
        CHECK (source_type <> '토스_커뮤니티' OR url IS NULL)
);

CREATE INDEX idx_data_source_stock_date ON data_source (stock_id, date);

CREATE TRIGGER trg_data_source_updated_at
    BEFORE UPDATE ON data_source
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 6. sentiment_analysis — (날짜, 종목) 단위 감성 라벨 (F-03-4, F-05)
--    data_source와 (stock_id, date)로 조인해서 사용
-- ============================================================
CREATE TABLE sentiment_analysis (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL,                             -- 날짜
    stock_id    INTEGER NOT NULL REFERENCES stocks(id),    -- 종목명
    sentiment   VARCHAR(10) NOT NULL CHECK (sentiment IN ('긍정', '부정', '중립')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (date, stock_id)
);

CREATE TRIGGER trg_sentiment_analysis_updated_at
    BEFORE UPDATE ON sentiment_analysis
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 7. financial_statements — DART 연도별 재무 (F-03-2, ISSUE-C2)
-- ============================================================
CREATE TABLE financial_statements (
    id                BIGSERIAL PRIMARY KEY,
    stock_id          INTEGER NOT NULL REFERENCES stocks(id),
    fiscal_year       SMALLINT NOT NULL,
    revenue           BIGINT NOT NULL,                     -- 매출액 (원)
    operating_profit  BIGINT NOT NULL,                     -- 영업이익 (원)
    operating_margin  NUMERIC(6,2),                        -- 영업이익률 (%)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stock_id, fiscal_year)
);

CREATE TRIGGER trg_financial_statements_updated_at
    BEFORE UPDATE ON financial_statements
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 8. stock_reports — AI 종목 리포트 1일 1회 배치 캐시 (F-03, ISSUE-C1~C4/D1~D3)
--    블록4(최신뉴스)는 data_source + sentiment_analysis 조인으로 별도 조회, 여기엔 저장하지 않음
-- ============================================================
CREATE TABLE stock_reports (
    id                       BIGSERIAL PRIMARY KEY,
    stock_id                 INTEGER NOT NULL REFERENCES stocks(id),
    report_date              DATE NOT NULL,

    -- F-03-1 투자 판단 요약 (근거 없으면 judgement/judgement_reasons NULL → 블록 비노출)
    judgement                VARCHAR(10) CHECK (judgement IN ('매수', '중립', '매도')),
    judgement_reasons        JSONB,                        -- 근거 3가지 텍스트 배열

    -- F-03-2 매출/영업이익 분석
    revenue_trend            VARCHAR(10) CHECK (revenue_trend IN ('증가', '감소')),
    operating_profit_trend   VARCHAR(10) CHECK (operating_profit_trend IN ('증가', '감소')),
    operating_margin_trend   VARCHAR(10) CHECK (operating_margin_trend IN ('개선', '악화')),
    growth_grade             VARCHAR(10) CHECK (growth_grade IN ('양호', '보통', '낮음')),
    profitability_grade      VARCHAR(10) CHECK (profitability_grade IN ('양호', '보통', '낮음')),

    -- F-03-3 리스크 체크 (시장변동성/실적신뢰도/경쟁강도 0~100 + 산출근거)
    risk_scores               JSONB,

    -- F-03-5 동종 업계 비교 (PER/PBR/ROE 목록)
    peer_comparison            JSONB,

    -- F-03-6 밸류에이션 (52주 밴드)
    week52_high                NUMERIC(15,2),
    week52_low                 NUMERIC(15,2),
    current_price               NUMERIC(15,2),

    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stock_id, report_date)
);

CREATE TRIGGER trg_stock_reports_updated_at
    BEFORE UPDATE ON stock_reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 9. shortforms — 종목당 긍정 1건 + 부정 1건 숏폼 (F-02, ISSUE-E2/E3)
-- ============================================================
CREATE TABLE shortforms (
    id              BIGSERIAL PRIMARY KEY,
    stock_id        INTEGER NOT NULL REFERENCES stocks(id),
    sentiment       VARCHAR(10) NOT NULL CHECK (sentiment IN ('긍정', '부정')),
    video_url       TEXT NOT NULL,                          -- S3 사전 저장 배경 영상
    subtitle_text   TEXT NOT NULL,                           -- LLM 생성 자막 (접근성 병행 노출, PRD §8)
    ai_insight      TEXT,                                    -- AI INSIGHT 패널 핵심 포인트 3줄
    news_id         BIGINT REFERENCES data_source(id),       -- 자막 원문 뉴스 (사실관계 추적용, PRD §9.3)
    view_count      INTEGER NOT NULL DEFAULT 0,
    like_count      INTEGER NOT NULL DEFAULT 0,
    published_date  DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stock_id, sentiment, published_date)
);

CREATE TRIGGER trg_shortforms_updated_at
    BEFORE UPDATE ON shortforms
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 10. users — 사용자. 카카오 OAuth로 확정(ISSUE-001)되어 kakao_tokens가 진짜 신원.
--     device_id는 로그인 전 임시 식별용 흔적만 남겨두며 NULL 허용.
-- ============================================================
CREATE TABLE users (
    id                BIGSERIAL PRIMARY KEY,
    device_id         TEXT UNIQUE,                           -- 로그인 전 디바이스 쿠키(옵션), 로그인 후엔 kakao_tokens가 신원 담당
    telegram_chat_id  TEXT UNIQUE,                            -- F-04 연동 후 저장, 개인정보 취급 (PRD §8)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 11. watchlists — 관심종목 (F-04 브리핑/시그널 대상)
-- ============================================================
CREATE TABLE watchlists (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    stock_id    INTEGER NOT NULL REFERENCES stocks(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, stock_id)
);

CREATE TRIGGER trg_watchlists_updated_at
    BEFORE UPDATE ON watchlists
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 12. shortform_likes — 숏폼 좋아요 토글 (ISSUE-E2, 사용자당 1회)
-- ============================================================
CREATE TABLE shortform_likes (
    id            BIGSERIAL PRIMARY KEY,
    shortform_id  BIGINT NOT NULL REFERENCES shortforms(id),
    user_id       BIGINT NOT NULL REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (shortform_id, user_id)
);

CREATE TRIGGER trg_shortform_likes_updated_at
    BEFORE UPDATE ON shortform_likes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 13. telegram_link_codes — 일회용 연동 코드 (F-04, PRD §"미확정" 제안안)
-- ============================================================
CREATE TABLE telegram_link_codes (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    code        VARCHAR(20) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_telegram_link_codes_updated_at
    BEFORE UPDATE ON telegram_link_codes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 14. telegram_notifications — 발송 로그 (F-04, 중복 발송 방지가 핵심 제약)
--     브리핑(종목 무관)과 시그널(종목별)의 중복 방지 조건이 달라 부분 유니크 인덱스 2개로 분리
-- ============================================================
CREATE TABLE telegram_notifications (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id),
    stock_id            INTEGER REFERENCES stocks(id),      -- 브리핑=NULL, 시그널=종목 지정
    notification_type   VARCHAR(20) NOT NULL CHECK (notification_type IN ('조간_브리핑', '마감_브리핑', '시그널')),
    sent_date           DATE NOT NULL,
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 브리핑: 사용자당 유형/날짜별 1건만 (stock_id가 NULL이라 일반 UNIQUE 제약으로는 중복 방지 안 됨)
CREATE UNIQUE INDEX uq_telegram_notif_briefing
    ON telegram_notifications (user_id, notification_type, sent_date)
    WHERE stock_id IS NULL;

-- 시그널: 사용자/종목당 유형/날짜별 1건만
CREATE UNIQUE INDEX uq_telegram_notif_signal
    ON telegram_notifications (user_id, notification_type, sent_date, stock_id)
    WHERE stock_id IS NOT NULL;

CREATE TRIGGER trg_telegram_notifications_updated_at
    BEFORE UPDATE ON telegram_notifications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 15. kakao_tokens — 카카오 OAuth 토큰, users와 1:1 (user_id UNIQUE)
-- ============================================================
CREATE TABLE kakao_tokens (
    id                          BIGSERIAL PRIMARY KEY,
    user_id                     BIGINT NOT NULL UNIQUE REFERENCES users(id), -- 1:1 매핑
    kakao_user_id               BIGINT NOT NULL UNIQUE,   -- 카카오 고유 회원번호 (로그인 콜백 시 유저 조회용)
    access_token                TEXT NOT NULL,
    refresh_token               TEXT NOT NULL,
    token_type                  VARCHAR(20) NOT NULL DEFAULT 'bearer',
    scope                       TEXT,
    expires_at                  TIMESTAMPTZ NOT NULL,      -- access_token 만료 시각
    refresh_token_expires_at    TIMESTAMPTZ NOT NULL,      -- refresh_token 만료 시각 (카카오는 refresh token도 만료됨)
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_kakao_tokens_updated_at
    BEFORE UPDATE ON kakao_tokens
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
