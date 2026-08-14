import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "text" | "icon" | "pill";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "inline-flex h-10 items-center justify-center gap-1 rounded-sm bg-primary px-5 text-[14px] font-medium text-white transition active:scale-[0.98]",
  secondary:
    "inline-flex h-[52px] items-center justify-center gap-1 rounded-sm border border-border bg-white px-5 text-[14px] font-medium text-heading transition active:scale-[0.98]",
  text: "inline-flex items-center justify-center text-[14px] font-medium transition-colors",
  icon: "inline-flex items-center justify-center transition-colors",
  pill:
    "inline-flex h-[52px] items-center justify-center gap-1 rounded-full border border-border bg-white px-5 text-[14px] font-medium text-heading transition active:scale-[0.98]",
};

export default function Button({
  variant = "primary",
  type = "button",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      {...props}
      className={`focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${variantClasses[variant]} ${className}`}
    />
  );
}
