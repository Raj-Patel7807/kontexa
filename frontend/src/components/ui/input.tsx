import * as React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, helperText, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full flex flex-col gap-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-semibold uppercase tracking-wider text-slate-300 select-none"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={`w-full rounded-lg bg-slate-900 border px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 transition-colors ${
            error
              ? "border-rose-500/80 focus:ring-rose-500 text-rose-100"
              : "border-slate-800 focus:border-indigo-500 focus:ring-indigo-500"
          } ${className}`}
          {...props}
        />
        {error && (
          <span id={`${inputId}-error`} className="text-xs text-rose-400 font-medium">
            {error}
          </span>
        )}
        {!error && helperText && (
          <span className="text-xs text-slate-400">{helperText}</span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
