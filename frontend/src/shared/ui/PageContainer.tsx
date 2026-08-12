import type { ReactNode } from "react";

// DESIGN_SPEC.md §2.2: content max-width 480px, horizontal padding 16px.
export default function PageContainer({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-[480px] px-4">{children}</div>;
}
