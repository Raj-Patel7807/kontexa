import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
}

export function Badge({
  className = "",
  variant = "default",
  children,
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-800 text-slate-300 border-slate-700",
    success: "bg-emerald-950/60 text-emerald-400 border-emerald-800/50",
    warning: "bg-amber-950/60 text-amber-400 border-amber-800/50",
    danger: "bg-rose-950/60 text-rose-400 border-rose-800/50",
    info: "bg-indigo-950/60 text-indigo-400 border-indigo-800/50",
    outline: "bg-transparent text-slate-300 border-slate-700",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border uppercase tracking-wider select-none font-mono ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
