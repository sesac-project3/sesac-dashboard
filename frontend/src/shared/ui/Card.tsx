import type { ReactNode } from "react";

// DESIGN_SPEC.md §12.1 Standard Card.
export default function Card({
  children,
  className = "",
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <div id={id}
      className={`rounded-lg border border-border-soft bg-white p-4 shadow-card ${className}`}
    >
      {children}
    </div>
  );
}
