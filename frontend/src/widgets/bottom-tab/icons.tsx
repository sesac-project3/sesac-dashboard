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
      <path d="M12 20s-7.5-4.6-10-9.1C.5 7.7 2 4.5 5.3 4.1c1.9-.2 3.6.8 4.7 2.4 1.1-1.6 2.8-2.6 4.7-2.4 3.3.4 4.8 3.6 3.3 6.8C19.5 15.4 12 20 12 20Z" />
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
