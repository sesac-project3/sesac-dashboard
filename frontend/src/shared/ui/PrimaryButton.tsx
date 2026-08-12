import type { ButtonHTMLAttributes } from "react";

// DESIGN_SPEC.md §11.1 Primary Button.
export default function PrimaryButton({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`h-[52px] rounded-sm bg-primary font-medium text-white transition active:scale-[0.98] active:brightness-90 disabled:opacity-50 ${className}`}
    />
  );
}
