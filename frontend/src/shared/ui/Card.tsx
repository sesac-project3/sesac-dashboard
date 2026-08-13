import type { ReactNode } from "react";

// DESIGN_SPEC.md §12.1 Standard Card.
export default function Card({
  children,
  className = "",
  id,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
  onClick?: () => void;
}) {
  return (
    <div id={id} onClick={onClick}
      className={`rounded-lg border border-border-soft bg-white p-4 shadow-card ${className}`}
    >
      {children}
    </div>
  );
}
