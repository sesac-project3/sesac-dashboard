# DESIGN_SPEC.md — Z멋대로 (Z-Invest) UI/UX 구현 명세

> **목적**
>
> 이 문서는 Z멋대로(Z-Invest)의 기존 디자인 시스템과 제공된 화면 레퍼런스를 기준으로,
> **Claude Code가 Next.js/React 화면을 구현할 때 직접 참조할 수 있는 실행 가능한 디자인 명세**다.
>
> 기능/API 요구사항은 `PRODUCT.md`를 기준으로 하고, 이 문서는 **화면의 시각적 표현, 레이아웃,
> 컴포넌트, 상태, 반응형, 인터랙션 및 디자인 구현 규칙**을 정의한다.
>
> **중요:** 이 문서에 정의되지 않은 시각적 결정을 임의로 추가하지 않는다.
> 기존 컴포넌트/토큰을 먼저 재사용하고, 새 컴포넌트가 필요하면 이 문서의 디자인 원칙을 따른다.

---

## 0. Claude Code용 최우선 규칙

### 0.1 구현 우선순위

화면을 구현할 때 다음 순서를 따른다.

1. 기존 프로젝트의 디자인 토큰/컴포넌트 확인
2. 이 문서의 Design Token 적용
3. 기존 컴포넌트 재사용
4. 페이지별 레이아웃 규칙 적용
5. 상태(loading/empty/error/disabled) 구현
6. 모바일 viewport에서 시각적 검수
7. 임의의 색상/spacing/radius/shadow 추가 금지

### 0.2 절대 변경하지 않는 규칙

- 국내 주식 등락 색상: **상승 = 빨강 / 하락 = 파랑**
- 브랜드 기본 액센트: **Deep Indigo `#542BE9`**
- 대시보드형 화면의 Soft Lavender: **`#7C78E8` 계열**
- 카드 radius: **최소 16px**
- 버튼/입력 radius: **최소 12px**
- 순수 검정 shadow 사용 금지
- Pretendard 중심의 단일 타이포그래피
- 모바일 우선, 기본 콘텐츠 max-width `480px`
- 고정 Header `56px`
- 고정 Bottom Tab Bar `72px`
- 화면당 브랜드 인디고 액센트는 핵심 영역에 제한적으로 사용
- 각진 0px radius 컴포넌트를 새로 만들지 않는다.

---

# 1. Product UI Direction

## 1.1 Creative North Star

### The Approachable Vault

Z-Invest는 금융 서비스를 딱딱하게 표현하지 않는다.

핵심 시각 언어는:

- 부드러운 카드
- 큰 radius
- 낮은 채도의 ambient shadow
- 넓은 여백
- 큰 숫자
- 명확한 정보 hierarchy
- 진한 indigo CTA
- Soft Lavender 대시보드
- 빨강/파랑 국내 증시 등락 색상

이다.

사용자가 느껴야 하는 인상:

> **"돈을 다루는 서비스지만 어렵거나 무겁지 않다."**

---

# 2. Platform & Viewport

## 2.1 Primary Target

모바일 PWA / 네이티브 앱 셸을 기본으로 한다.

```text
Primary viewport
┌──────────────────────────┐
│        Header 56px       │
├──────────────────────────┤
│                          │
│      Scroll Content      │
│      max-width 480px     │
│      horizontal 16px     │
│                          │
├──────────────────────────┤
│   Bottom Tab 72px        │
└──────────────────────────┘
```

## 2.2 Content Width

- 기본 content max-width: `480px`
- 기본 horizontal padding: `16px`
- 카드가 화면 전체에 가까운 경우에도 콘텐츠 안전 여백 `16px` 유지
- modal/bottom-sheet 내부 콘텐츠 max-width: `360px` 기준
- 넓은 desktop viewport에서는 모바일 앱 화면을 중앙에 배치할 수 있다.

## 2.3 Safe Area

고정 요소는 반드시 safe-area를 고려한다.

```css
padding-top: env(safe-area-inset-top);
padding-bottom: env(safe-area-inset-bottom);
```

---

# 3. Design Tokens

## 3.1 Color Tokens

### Brand

| Token | Value | Usage |
|---|---|---|
| `--color-primary` | `#542BE9` | 기본 CTA, active, focus |
| `--color-primary-soft` | `#7C78E8` | dashboard hero, dashboard accent |
| `--color-primary-soft-alt` | `#7D7BEF` | dashboard variation |

### Semantic

| Token | Value | Usage |
|---|---|---|
| `--color-market-up` | `#EF4444` 계열 | 국내 증시 상승 |
| `--color-market-down` | `#3B82F6` 계열 | 국내 증시 하락 |
| `--color-positive` | `#2DC98E` | 포트폴리오 집계 positive |
| `--color-danger` | `#EF4444` 계열 | destructive/error |
| `--color-info` | `#3B82F6` 계열 | information |

> 실제 프로젝트에 이미 semantic color token이 있다면 기존 token을 우선 사용한다.
> 위 값은 새 token을 만들 때의 기준이다.

### Neutral

| Token | Value |
|---|---|
| `--color-ink` | `#111111` |
| `--color-heading` | `#1F2435` |
| `--color-heading-alt` | `#20253A` |
| `--color-caption` | `#8B90A0` |
| `--color-caption-alt` | `#9AA1B4` |
| `--color-surface` | `#F5F5F7` |
| `--color-white` | `#FFFFFF` |
| `--color-border` | `#E5E7EB` |
| `--color-border-soft` | `#E7E8F2` |

---

# 4. Named Color Rules

## 4.1 Market Color Rule

국내 주식 시장의 관례를 따른다.

```text
상승 → 빨강
하락 → 파랑
```

절대로 미국식 금융 UI처럼:

```text
상승 → green
하락 → red
```

으로 바꾸지 않는다.

적용 대상:

- 현재가 등락
- 등락률
- 보유 종목 수익률
- 보유 종목 수익금
- 목표가 대비 상승/하락
- 차트의 시장 방향 표시

## 4.2 Portfolio Positive Rule

`Mint Green #2DC98E`는 **포트폴리오 집계 상태**에 사용한다.

예:

- 그룹 총 수익률
- 잔액 positive 상태
- 포트폴리오 aggregate badge

개별 종목 등락에는 사용하지 않는다.

## 4.3 One Accent Rule

한 화면에서 브랜드 indigo를 과도하게 사용하지 않는다.

권장:

```text
Background       neutral
Card             white
Text             navy/gray
Primary CTA      indigo
Active           indigo
One key visual   soft lavender
```

금지:

```text
전체 카드 → indigo
전체 텍스트 → indigo
전체 border → indigo
전체 icon → indigo
```

---

# 5. Typography

## 5.1 Font

Primary:

```text
Pretendard
```

Fallback:

```text
ui-sans-serif, system-ui, sans-serif
```

장식용 serif / mono font를 사용하지 않는다.

## 5.2 Type Scale

| Name | Size | Weight | Line Height | Usage |
|---|---:|---:|---:|---|
| Display | 38px | 700 | 1.1 | 총자산/현재가 등 핵심 숫자 |
| Headline | 22px | 500 | 1.25 | 페이지/모달 제목 |
| Title | 18px | 600 | 1.3 | 섹션 제목 |
| Body Large | 16px | 400~500 | 1.5 | 설명/중요 본문 |
| Body | 14px | 400 | 1.5 | 일반 본문 |
| Label | 11~13px | 500 | 1.3 | 캡션/배지 |

## 5.3 Letter Spacing

- Display: `-0.03em`
- Headline: `-0.04em`
- Title: `-0.03em`
- Body: `-0.02em` ~ `-0.03em`
- 숫자 Display: 가능한 경우 `-0.03em`

## 5.4 Bold Number Rule

금액/가격/수익률처럼 사용자가 가장 먼저 확인해야 하는 숫자는:

```text
font-weight: 700
```

설명 텍스트는 한 단계 낮은 weight/color를 사용한다.

---

# 6. Spacing System

기본 spacing 단위는 4px 계열을 사용한다.

권장:

```text
4   xs
8   sm
12  md
16  lg
20  xl
24  2xl
32  3xl
40  4xl
48  5xl
```

## Section Rhythm

- section vertical padding: `24px`
- card gap: `12px`
- 주요 block gap: `16px`
- 큰 섹션 간 gap: `24px~32px`

기본:

```css
gap: 12px;
padding: 16px;
```

---

# 7. Radius System

| Token | Value | Usage |
|---|---:|---|
| `radius-sm` | 12px | button/input |
| `radius-md` | 16px | small card |
| `radius-lg` | 20px | standard card |
| `radius-xl` | 24px | large card |
| `radius-hero` | 28px | hero/modal |
| `radius-full` | 9999px | pill/avatar |

### Shape Rule

요소의 중요도가 높고 크기가 클수록 radius를 크게 한다.

```text
Input / Button       12px
Small Card           16px
Card                 16~24px
Hero                 24~28px
Bottom Sheet         28px top
Pill                 full
```

---

# 8. Shadow System

순수 black shadow를 사용하지 않는다.

## 8.1 Ambient Card

```css
box-shadow: 0 10px 24px rgba(51, 65, 85, 0.05);
```

또는:

```css
box-shadow: 0 8px 24px rgba(44, 49, 67, 0.04);
```

## 8.2 Elevated Hero

```css
box-shadow: 0 12px 32px rgba(70, 72, 212, 0.08);
```

## 8.3 CTA Glow

```css
box-shadow: 0 10px 18px rgba(130, 154, 233, 0.28);
```

## 8.4 Modal

```css
box-shadow: 0 24px 48px rgba(22, 26, 38, 0.24);
```

## 8.5 Interaction

hover/active 가능한 card:

```css
transform: translateY(-2px);
```

정도만 사용한다.

과도한 scale/translate 금지.

---

# 9. Global App Shell

## 9.1 Header

### Dimensions

```text
height: 56px
```

### Structure

```text
┌──────────────────────────────┐
│ ←       Page Title       ♥   │
└──────────────────────────────┘
```

가능한 경우:

- left: back / navigation
- center: title
- right: action

### Visual

- white 또는 반투명 white
- bottom border
- scroll 시 backdrop blur
- title: `18~22px`, semibold
- icon은 Ink/Navy 계열
- active favorite: red 계열

### Stock Detail Header Example

```text
←           삼성전자          ♥
            KOSPI | 005930
```

title:

```text
22px / 600
```

subtitle:

```text
14~16px / 400
caption gray
```

---

# 10. Bottom Navigation

## 10.1 Dimensions

```text
height: 72px
border-radius: 24px 24px 0 0
```

safe-area-bottom 적용.

## 10.2 Structure

Z-Invest의 주요 navigation:

```text
모임 투자 | 투자 | 피드 | 포트폴리오 | 프로필
```

필요한 경우 중앙 FAB를 navigation 위로 띄운다.

### Active

- indigo text/icon
- label semibold
- 약간의 scale 강조

### Inactive

- gray
- normal weight

### FAB

- circular
- brand indigo
- colored glow shadow
- bottom tab bar보다 약 `32px` 위로 돌출

---

# 11. Buttons

## 11.1 Primary

```text
background: #542BE9
color: white
height: 52px
radius: 12px
```

interaction:

```css
active:scale(0.98)
active:brightness(0.9)
```

## 11.2 Dashboard Pill CTA

대시보드의 핵심 CTA에는 pill 형태 허용.

```text
radius: 9999px
background: lavender/brand tone
shadow: colored glow
```

## 11.3 Buy / Sell

국내 증시 convention을 유지한다.

```text
매수 → red
매도 → blue
```

단, 브랜드 CTA가 필요한 일반 행동 버튼은 primary indigo를 사용한다.

## 11.4 Secondary

- white / light gray background
- border
- dark text

## 11.5 Disabled

```css
opacity: 0.5;
```

---

# 12. Cards

## 12.1 Standard Card

```text
background: white
radius: 16~24px
padding: 16~20px
border: 1px solid #E5E7EB 또는 #E7E8F2
shadow: Ambient
```

## 12.2 Hero Card

```text
radius: 24~28px
padding: 20~24px
gradient: soft lavender / indigo
shadow: Elevated
```

## 12.3 Stat Card

예:

```text
┌──────────────┐
│ 시가총액     │
│              │
│ 1088.0조     │
│ 원           │
└──────────────┘
```

규칙:

- label: 13~16px, caption gray
- value: 24~28px, bold
- 카드끼리 동일 높이
- 모바일에서 3-column 가능
- 좁은 viewport에서는 overflow가 발생하지 않도록 숫자 wrapping 고려

---

# 13. Stock Detail Screen

## 13.1 Screen Goal

종목 상세 화면에서 사용자가 다음 정보를 빠르게 확인할 수 있어야 한다.

1. 어떤 종목인지
2. 현재 가격
3. 등락
4. 가격 흐름
5. AI 분석 요약
6. 핵심 통계
7. 보유 상태
8. 전체 AI 리포트 접근

---

## 13.2 Stock Header

```text
←        삼성전자        ♥
         KOSPI | 005930
```

center aligned.

---

## 13.3 Price Hero

화면에서 가장 큰 숫자.

```text
183,800원
▲ 3.03%   (5,400원)   전일 대비
```

### Rules

- price: Display, bold
- 상승: red
- 하락: blue
- change amount/rate: 동일 semantic color
- "전일 대비": caption gray

---

# 14. Stock Chart

## 14.1 Time Selector

```text
1분   5분   15분   [일]   주   월
```

active:

```text
background: #542BE9
color: white
radius: full
```

inactive:

```text
background: transparent
color: caption gray
```

## 14.2 Chart

기본 chart library:

```text
Recharts
```

### Visual

- line: indigo/soft lavender
- area fill: very light lavender
- grid: light neutral
- axis label: caption gray
- current price marker: accent color
- tooltip: rounded card

### Chart behavior

- time range 변경 가능
- line/candle mode가 요구되는 화면에서는 toggle 제공
- 장중 갱신
- 데이터가 없는 경우 empty state
- loading 시 skeleton

---

# 15. AI Analysis Summary

## 15.1 Section Header

```text
✦ AI 분석 리포트 요약                    Updated 방금 전
```

### Rules

- AI icon: indigo/lavender
- title: 18px semibold
- update time: caption gray/blue
- section spacing: 16~24px

---

## 15.2 Summary Card

세 가지 핵심 AI 분석 상태를 vertical list로 보여준다.

```text
① AI 종합 의견 준비 중
   종목 분석이 끝나면 핵심 투자 관점을 이곳에 요약해 보여줍니다.

② 정상 포인트 확인 중
   수급, 실적, 가격 흐름을 바탕으로 성장 요인을 정리하고 있습니다.

③ 리스크 체크 준비 중
   변동성과 최신 뉴스 흐름을 분석해 주의 포인트를 곧 반영합니다.
```

### Item

- circular numbered badge
- badge background: semantic soft tone
- title: 18px semibold
- description: 16px body
- item gap: 24px 이상

### Badge tone

```text
1 → soft indigo
2 → soft mint
3 → soft red/pink
```

---

## 15.3 Report CTA

```text
리포트 전체 보기  →
```

- outline/light surface
- full width
- pill
- height 약 52~56px
- dark navy text
- arrow icon right

---

# 16. Stock Statistics

3-column stat cards:

```text
┌─────────┬─────────┬─────────┐
│ 시가총액 │  PER    │  PBR    │
│1088.0조  │   28    │  2.87   │
│   원     │         │         │
└─────────┴─────────┴─────────┘
```

Rules:

- 동일한 card height
- label: caption gray
- value: bold
- card gap: 12px
- radius: 16~20px

---

# 17. Holding Stock Card

사용자가 해당 종목을 보유한 경우 노출한다.

```text
보유 중인 종목입니다                         보유 1주

┌──────────┬──────────┬──────────┐
│ 평균단가 │  수익률  │  수익금  │
│189,700원 │ -3.11%  │ -5,900원 │
└──────────┴──────────┴──────────┘
```

### Rules

- 전체 card: white / very light lavender surface
- radius: 24px
- title: 20~22px semibold
- holding count: caption/medium
- metric sub-card: white
- negative return: blue
- positive return: red
- aggregate positive status가 필요한 경우에만 mint 사용

---

# 18. Fixed Trade Action Bar

Stock detail 화면에서 하단에 고정되는 행동 영역.

```text
┌──────────────────────────────────┐
│       [ 매도 ]     [ 매수하기 ]  │
└──────────────────────────────────┘
```

### Layout

- fixed bottom
- safe-area-bottom
- white/blur surface
- top shadow
- large horizontal padding
- two equal/near-equal buttons

### Buy

- red
- white text
- pill
- height 약 56px

### Sell

- blue 또는 light-blue background
- blue text
- pill
- height 약 56px

> 화면 캡처처럼 매수 버튼을 red, 매도 버튼을 blue 계열로 유지한다.

---

# 19. AI Report Detail Modal / Bottom Sheet

## 19.1 Behavior

사용자가 "리포트 전체 보기"를 선택하면 현재 화면 위에 AI 리포트 상세 sheet/modal을 띄운다.

background:

```text
rgba(0,0,0,0.5) 수준의 dim overlay
```

단, overlay 자체는 black shadow 규칙과 별개인 modal backdrop이다.

## 19.2 Sheet

- top radius: `28px`
- white/light background
- viewport 높이를 크게 사용할 수 있음
- 내부 scroll
- drag handle
- close button
- shadow: Modal shadow

Structure:

```text
┌─────────────────────────────┐
│            ───              │
│ ✦ AI 리포트 상세          × │
├─────────────────────────────┤
│                             │
│       Hero Report Card      │
│                             │
│       Report Section 1      │
│                             │
│       Report Section 2      │
│                             │
│       Report Section 3      │
│                             │
└─────────────────────────────┘
```

---

# 20. AI Report Hero Card

제공된 화면처럼 리포트의 가장 중요한 한 문장을 큰 gradient card로 보여준다.

## Visual

```text
background:
linear-gradient(...)
```

- blue/indigo 계열 gradient
- radius: 24px
- white text
- strong shadow
- padding: 20~24px

Content:

```text
삼성전자 (005930)

삼성전자는 실적 모멘텀
부담이 커진 구간

2026.04.03 09:40 기준 분석
```

### Hierarchy

- stock badge: 13~14px
- main insight: 28~36px, bold
- timestamp: 14~16px
- decorative icon: low opacity

---

# 21. AI Report Section Card

각 report section은 white card.

예:

```text
┌──────────────────────────────┐
│ ▣  1. 투자 판단 요약         │
│                              │
│ ┌────────────┬─────────────┐ │
│ │ AI 종합 의견│ 목표 주가   │ │
│ │ 매도 (Sell) │ 159,800원  │ │
│ │             │ -13.1%     │ │
│ └────────────┴─────────────┘ │
│                              │
│ 설명 본문...                 │
└──────────────────────────────┘
```

### Rules

- section card radius: 20~24px
- section title: 20~22px semibold
- icon: indigo/blue
- key decision: semantic market color
- explanatory text: 16px
- line-height: 1.6~1.8

---

# 22. Report Content Blocks

PRODUCT 요구사항에 맞는 종목 상세 리포트는 다음 영역을 지원한다.

1. 투자 판단
2. 성장성 분석
3. 밸류에이션
4. 리스크 체크
5. 뉴스
6. 동종업계 비교

각 block은 독립적으로 렌더링 가능해야 한다.

### Missing Data Rule

근거 데이터가 없으면:

- 억지로 placeholder 값을 표시하지 않는다.
- 해당 block을 숨길 수 있다.
- API가 empty를 반환하면 empty state를 사용한다.

---

# 23. Empty / Loading / Error States

## 23.1 Loading

Skeleton은 실제 콘텐츠와 비슷한 형태를 유지한다.

예:

```text
████████████████
██████████
████████████████████
```

- neutral surface
- rounded shape
- 과도한 shimmer 금지

## 23.2 Empty

문구:

```text
아직 분석할 데이터가 없어요.
```

스타일:

- center aligned
- caption gray
- 작은 supporting icon
- CTA가 필요한 경우 primary indigo

## 23.3 Error

```text
데이터를 불러오지 못했어요.
잠시 후 다시 시도해주세요.

[ 다시 시도 ]
```

CTA는 primary indigo.

---

# 24. Group Investment Screen

제공된 레퍼런스의 "모임 투자" 화면을 기준으로 한다.

## 24.1 Header

```text
              모임 투자                     ⚙
```

- center title
- right settings icon
- height 56px
- bottom border

---

## 24.2 Group Hero Card

큰 rounded gradient card.

```text
┌──────────────────────────────────┐
│ 모임 계좌                         │
│                                  │
│ c101 여행 자금                    │
│ 092-630-6354184-963              │
│                                  │
│                     해산 투표중   │
└──────────────────────────────────┘
```

### Visual

- radius: 28px
- lavender/indigo gradient
- white text
- subtle background illustration allowed
- no hard border
- elevated shadow

---

## 24.3 Carousel Indicator

```text
● ● ━ ● ●
```

- inactive: light gray
- active: mint green
- active indicator can be elongated pill

---

## 24.4 Group Deposit Card

```text
모임 예수금

₩0

┌─────────────────────────────┐
│ 개설일              2026.03.30 │
│ 대표 개인계좌        ********  │
│ 내 역할                 방장   │
└─────────────────────────────┘
```

Rules:

- outer card: white
- radius: 24px
- inner information area: `#F5F5F7`
- inner radius: 24px
- labels: gray
- values: navy/bold

---

# 25. Landing / Web Entry Screen

제공된 웹 레퍼런스의 방향을 따른다.

## 25.1 Desktop Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Z멋대로                              웹으로 계속하기  [앱 시작] │
│                                                              │
│  [badge]                                                     │
│  보고, 따라하고,                                              │
│  함께 투자하세요                                              │
│                                                              │
│  Scroll, Tap, Invest                                          │
│                                                              │
│  설명                                                         │
│                                                              │
│  [앱으로 시작하기] [웹으로 계속하기]         [Phone Mockups]  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 25.2 Hero

headline:

```text
보고, 따라하고,
함께 투자하세요
```

강조 문구:

```text
함께 투자하세요
```

에는 brand gradient 또는 primary/secondary accent를 사용할 수 있다.

단, gradient는 hero와 같은 핵심 영역에서만 사용한다.

## 25.3 Hero CTA

Primary:

```text
앱으로 시작하기
```

Secondary:

```text
웹으로 계속하기
```

Primary:

```text
#542BE9
white
```

Secondary:

```text
white
border
navy text
```

---

# 26. Shortform Feed Direction

PRODUCT의 숏폼 기능과 기존 레퍼런스 화면을 따른다.

## Card

영상이 가장 큰 시각 요소가 된다.

```text
┌────────────────────┐
│                    │
│      VIDEO         │
│                    │
│                    │
│       ♥           │
│       ↗           │
│                    │
├────────────────────┤
│ 종목명 / 코드       │
│ 제목                │
│ [소액 투자하기]     │
└────────────────────┘
```

### Rules

- full-height video 우선
- overlay text는 높은 대비
- interaction icon은 right rail
- bottom CTA는 pill
- 좋아요/조회수는 작은 label
- bottom navigation은 앱 shell과 동일하게 유지

---

# 27. Navigation Rules

주요 앱 navigation:

```text
모임 투자
투자
피드
포트폴리오
프로필
```

새 페이지를 추가할 때:

- 기존 navigation 구조를 유지
- 새로운 top-level tab을 임의로 만들지 않는다.
- active 상태는 indigo
- inactive 상태는 gray

---

# 28. Component Naming Convention

컴포넌트는 역할 중심으로 명명한다.

권장:

```text
AppHeader
BottomTabBar
PrimaryButton
PillButton
MarketIndexCard
StockPriceHeader
StockChart
TimeRangeSelector
AIReportSummary
AIReportSummaryItem
AIReportHero
AIReportSection
StockStatCard
HoldingStockCard
TradeActionBar
GroupHeroCard
GroupDepositCard
ShortformCard
```

피해야 할 이름:

```text
Box1
PurpleCard
NewCard
TestComponent
BigCard
```

색상이 아닌 역할을 기준으로 이름을 짓는다.

---

# 29. Component Architecture

권장 구조:

```text
components/
├── ui/
│   ├── Button
│   ├── Card
│   ├── Badge
│   ├── IconButton
│   └── Skeleton
│
├── layout/
│   ├── AppHeader
│   ├── BottomTabBar
│   └── PageContainer
│
├── stock/
│   ├── StockHeader
│   ├── StockPrice
│   ├── StockChart
│   ├── TimeRangeSelector
│   ├── StockStats
│   └── HoldingStockCard
│
├── ai-report/
│   ├── AIReportSummary
│   ├── AIReportHero
│   ├── AIReportSection
│   ├── RiskRadar
│   └── PeerComparison
│
├── group/
│   ├── GroupHeroCard
│   └── GroupDepositCard
│
└── shortform/
    └── ShortformCard
```

실제 repository 구조가 이미 존재한다면 기존 구조를 우선한다.

---

# 30. Data/UI Separation

디자인 컴포넌트 내부에 API 호출 로직을 직접 넣지 않는다.

권장:

```text
Page
 ↓
Container / Hook
 ↓
API data
 ↓
Presentation Component
```

예:

```tsx
<StockDetailPage>
  <StockHeader />
  <StockPrice />
  <StockChart />
  <AIReportSummary />
  <StockStats />
  <HoldingStockCard />
  <TradeActionBar />
</StockDetailPage>
```

각 presentation component는 받은 data를 시각적으로 표현하는 데 집중한다.

---

# 31. Responsive Rules

## 31.1 Mobile First

기본 target:

```text
360px ~ 480px
```

특히 360px viewport에서:

- text overflow 금지
- 숫자 overflow 금지
- 버튼 label clipping 금지
- chart가 화면 밖으로 튀어나가지 않도록 한다.

## 31.2 Wider Viewport

`480px` 이상에서는:

```text
body
  └── mobile app shell
        └── max-width: 480px
```

형태로 중앙 정렬할 수 있다.

Landing page는 별도의 desktop layout을 허용한다.

---

# 32. Interaction Rules

## Tap

- button: `active:scale-[0.98]`
- card: subtle elevation
- navigation: immediate active feedback

## Hover

desktop에서만 사용:

```text
translateY(-2px)
shadow 증가
```

과도한 animation 금지.

## Animation

권장:

```text
150~250ms
ease-out
```

페이지의 정보 전달을 방해하는 장시간 animation 금지.

---

# 33. Accessibility

반드시:

- 버튼에 accessible name 제공
- icon-only button에 `aria-label`
- color만으로 상승/하락을 구분하지 않도록 텍스트/기호도 함께 표시
- keyboard focus visible
- modal open 시 focus 관리
- 이미지에 적절한 alt
- text contrast 확보

특히:

```text
▲ 3.03%
▼ -3.11%
```

처럼 기호 + 텍스트를 함께 사용한다.

---

# 34. Do / Don't

## DO

- 16px 이상 radius
- soft ambient shadow
- indigo를 핵심 액션에만 사용
- Soft Lavender를 dashboard hero에 사용
- 큰 숫자를 bold로 표시
- Pretendard 사용
- 카드 기반 정보 구조
- 국내 증시 상승 빨강 / 하락 파랑
- 모바일 first
- loading/empty/error 상태 구현
- 기존 컴포넌트 재사용

## DON'T

- black shadow 사용
- 0px square card 신규 생성
- 화면 전체를 indigo로 채우기
- 미국식 green/red market convention 사용
- arbitrary Tailwind color를 컴포넌트마다 새로 만들기
- 같은 컴포넌트에서 `gray`와 `slate` token을 무분별하게 혼용
- 새로운 radius 값을 무작위로 추가
- 숫자를 regular weight로 표현
- desktop을 기준으로 모바일을 축소하는 방식으로 구현
- API 데이터가 없는데 임의의 금융 수치를 생성
- 기존 디자인 컴포넌트를 무시하고 유사 컴포넌트를 중복 생성

---

# 35. Existing Design Inconsistency Resolution

현재 디자인에는 다음과 같은 기존 차이가 존재할 수 있다.

### Primary

```text
#542BE9
```

와

```text
#7C78E8 / #7D7BEF
```

가 모두 primary 역할을 수행한다.

### 신규 구현 규칙

한 화면에서는 의도적으로 하나를 선택한다.

```text
Form / onboarding / CTA-heavy
→ #542BE9

Dashboard / portfolio / statistics
→ #7C78E8 계열
```

두 색을 한 화면에서 동시에 primary로 사용하지 않는다.

---

# 36. Tailwind Implementation Guidance

프로젝트가 Tailwind를 사용한다면 arbitrary value를 반복 작성하지 말고 가능한 경우 design token으로 승격한다.

예:

```text
primary
primary-soft
surface
heading
caption
market-up
market-down
positive
border-soft
```

권장:

```tsx
className="rounded-2xl shadow-card"
```

비권장:

```tsx
className="rounded-[19px] shadow-[0_11px_27px_rgba(...)]"
```

동일한 값이 2회 이상 반복된다면 token/component로 만든다.

---

# 37. Page-level Acceptance Checklist

Claude Code가 페이지 구현을 완료하기 전에 확인한다.

## Visual

- [ ] Pretendard가 적용되어 있다.
- [ ] 모바일 viewport에서 레이아웃이 깨지지 않는다.
- [ ] 카드 radius가 최소 16px이다.
- [ ] shadow가 검정이 아니다.
- [ ] primary color가 과도하게 사용되지 않았다.
- [ ] 숫자 hierarchy가 명확하다.

## Market

- [ ] 상승은 red
- [ ] 하락은 blue
- [ ] portfolio aggregate positive에는 mint 사용 가능
- [ ] market color convention이 미국식으로 바뀌지 않았다.

## Layout

- [ ] content max-width 480px
- [ ] horizontal padding 16px
- [ ] header 56px
- [ ] bottom navigation 72px
- [ ] safe-area 적용
- [ ] fixed action bar가 콘텐츠를 가리지 않는다.

## Components

- [ ] 기존 컴포넌트를 우선 재사용했다.
- [ ] 동일한 UI가 중복 구현되지 않았다.
- [ ] component 이름이 역할 중심이다.

## States

- [ ] loading
- [ ] empty
- [ ] error
- [ ] disabled
- [ ] success/positive
- [ ] negative

상태가 필요한 컴포넌트에 구현되어 있다.

---

# 38. Claude Code Execution Prompt

Claude Code에서 디자인 구현을 시작할 때 다음 원칙을 적용한다.

```text
You are implementing the Z-Invest (Z멋대로) UI.

Before writing UI code:

1. Inspect the existing repository.
2. Identify existing design tokens and reusable components.
3. Do not replace existing working components without a reason.
4. Read DESIGN_SPEC.md and PRODUCT.md.
5. Follow DESIGN_SPEC.md for all visual decisions.
6. Follow PRODUCT.md for product/API requirements.

Design rules:

- Mobile-first.
- Main content max-width: 480px.
- Horizontal page padding: 16px.
- Header: 56px.
- Bottom navigation: 72px.
- Cards: 16~28px radius.
- Buttons/inputs: minimum 12px radius.
- Use Pretendard.
- Primary: #542BE9.
- Dashboard accent: #7C78E8 / #7D7BEF.
- Market up: red.
- Market down: blue.
- Portfolio aggregate positive: mint #2DC98E.
- Never use pure black shadows.
- Use soft slate/indigo ambient shadows.
- Do not introduce arbitrary colors, radius, spacing, or shadows.
- Do not use square cards.
- Do not use US stock market green/red conventions.
- Preserve the existing Z-Invest visual language.

Implementation rules:

- Reuse existing components first.
- Create a new component only when an existing one cannot satisfy the requirement.
- Keep API/data logic separate from presentation.
- Implement loading, empty, and error states.
- Make icon-only buttons accessible.
- Ensure 360px viewport compatibility.
- Do not invent financial values when API data is unavailable.
- If the design requirement is ambiguous, prefer the existing repository pattern and this DESIGN_SPEC over inventing a new style.

Before finishing:

- Run the relevant lint/typecheck/build/test commands.
- Inspect the page at mobile width.
- Check overflow.
- Check fixed header/bottom navigation.
- Check color semantics.
- Check spacing/radius/shadow consistency.
```

---

# 39. Relationship With PRODUCT.md

`PRODUCT.md`는 기능/구현 범위를 정의한다.

```text
PRODUCT.md
    ↓
무엇을 만들어야 하는가
```

`DESIGN_SPEC.md`는 화면 표현을 정의한다.

```text
DESIGN_SPEC.md
    ↓
그것을 어떻게 보여줘야 하는가
```

두 문서가 충돌할 경우:

1. 기능/API/데이터 계약 → `PRODUCT.md`
2. UI/visual/layout → `DESIGN_SPEC.md`
3. 기존 코드의 재사용 가능 컴포넌트 → repository 우선 확인
4. 새로운 visual decision → `DESIGN_SPEC.md`의 token/rule 준수

---

# 40. Final Design Principle

Z-Invest의 화면은 금융 정보를 많이 보여주더라도 **금융 시스템처럼 보이지 않아야 한다.**

핵심은:

```text
큰 숫자
+
부드러운 카드
+
넓은 여백
+
Indigo CTA
+
Soft Lavender Dashboard
+
국내 증시 Red/Blue
+
낮은 대비의 그림자
+
명확한 정보 hierarchy
```

이다.

새로운 화면을 만들 때도 이 언어를 유지한다.

**Do not redesign the product per page.**
**Extend the existing Z-Invest design language consistently.**
