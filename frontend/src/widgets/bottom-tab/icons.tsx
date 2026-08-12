// BottomTabBar 전용 line 아이콘. 별도 아이콘 라이브러리 없이 4개만 필요해서 인라인 SVG로 둔다
// (Ink/Navy 계열 line icon, DESIGN_SPEC.md AppHeader 아이콘 규칙과 통일). 색은 currentColor로
// 받아서 active(indigo)/inactive(gray) 상태를 부모 className이 그대로 결정한다.

type IconProps = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function HomeIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9" />
    </svg>
  );
}

export function ShortformIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
      <path d="M10 8.3v7.4l6-3.7-6-3.7Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function WatchlistIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
    </svg>
  );
}

export function ProfileIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M5 20c0-3.6 3.13-6 7-6s7 2.4 7 6" />
    </svg>
  );
}
