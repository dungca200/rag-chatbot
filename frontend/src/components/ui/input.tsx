import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, type = 'text', id, ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="space-y-2">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-foreground"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            type={type}
            className={cn(
              'block w-full rounded-xl px-4 py-3 text-sm',
              'bg-background-secondary border border-border',
              'transition-all duration-300',
              'text-foreground',
              'placeholder-muted-foreground',
              'focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent',
              error && 'border-error focus:border-error',
              className
            )}
            {...props}
          />
          {/* Focus glow effect */}
          <div className="absolute inset-0 rounded-xl opacity-0 focus-within:opacity-100 bg-accent/5 blur-xl -z-10 transition-opacity pointer-events-none" />
        </div>
        {error && (
          <p className="text-sm text-error flex items-center gap-1">
            <span className="w-1 h-1 rounded-full bg-error" />
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
