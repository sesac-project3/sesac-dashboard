import type { ReactNode } from "react";

// DESIGN_SPEC.md §12.1 Standard Card.
export default function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-border-soft bg-white p-4 shadow-card ${className}`}
    >
      {children}
    </div>
  );
}
