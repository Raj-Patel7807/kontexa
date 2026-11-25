import * as React from "react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:opacity-50 disabled:pointer-events-none select-none";

    const variantStyles = {
      primary:
        "bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white shadow-sm focus-visible:ring-indigo-500",
      secondary:
        "bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-slate-100 border border-slate-700 focus-visible:ring-slate-400",
      outline:
        "border border-slate-700 hover:border-slate-600 hover:bg-slate-800/60 text-slate-200 focus-visible:ring-slate-400",
      danger:
        "bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white shadow-sm focus-visible:ring-rose-500",
      ghost:
        "hover:bg-slate-800/60 text-slate-300 hover:text-white focus-visible:ring-slate-400",
    };

    const sizeStyles = {
      sm: "px-2.5 py-1 text-xs gap-1.5",
      md: "px-3.5 py-2 text-sm gap-2",
      lg: "px-5 py-2.5 text-base gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-0.5 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
