import clsx from "clsx";
import * as React from "react";

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "soft";
}

export function Badge({
  variant = "default",
  className,
  children,
  ...props
}: BadgeProps) {
  const base =
    "inline-flex items-center rounded-full text-[10px] font-semibold tracking-wide uppercase px-2.5 py-1";
  const styles =
    variant === "default"
      ? "bg-black text-white"
      : "bg-white border border-border text-text-secondary shadow-sm";

  return (
    <span className={clsx(base, styles, className)} {...props}>
      {children}
    </span>
  );
}

