import clsx from "clsx";
import * as React from "react";

type Variant = "primary" | "secondary" | "accent" | "ghost";
type Size = "sm" | "md" | "lg";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const baseClasses =
  "inline-flex items-center justify-center rounded-full font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-accent disabled:opacity-50 disabled:cursor-not-allowed";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-text-primary text-bg-primary hover:opacity-90 shadow-sm",
  secondary:
    "bg-bg-primary text-text-primary border border-border hover:bg-bg-secondary shadow-sm",
  accent:
    "bg-accent text-white hover:opacity-90 shadow-sm",
  ghost:
    "bg-transparent text-text-secondary hover:text-text-primary hover:bg-bg-secondary",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

