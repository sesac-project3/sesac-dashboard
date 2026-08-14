import type { AnchorHTMLAttributes } from "react";

// DESIGN_SPEC.md §15.3 Report CTA — outline pill, full width.
export default function PillButton({
  className = "",
  children,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a
      {...props}
      className={`flex h-[52px] w-full items-center justify-center gap-1 rounded-full border border-border bg-white text-[15px] font-medium text-heading transition active:scale-[0.98] ${className}`}
    >
      {children}
    </a>
  );
}
