import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles = cn(
      'relative inline-flex items-center justify-center font-medium rounded-xl',
      'transition-all duration-300',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'overflow-hidden'
    );

    const variants = {
      primary: cn(
        'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground',
        'hover:shadow-lg hover:shadow-accent/25',
        'hover:scale-[1.02] active:scale-[0.98]'
      ),
      secondary: cn(
        'glass text-foreground',
        'hover:glow-sm'
      ),
      outline: cn(
        'border border-border bg-transparent text-foreground',
        'hover:bg-accent/5 hover:border-accent/50',
        'hover:glow-sm'
      ),
      ghost: cn(
        'text-foreground hover:bg-accent/5',
        'hover:text-accent'
      ),
      danger: cn(
        'bg-error text-white',
        'hover:bg-red-700 hover:shadow-lg hover:shadow-error/25'
      ),
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-5 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
      icon: 'h-10 w-10 p-0',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {/* Shimmer effect on hover */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full hover:translate-x-full transition-transform duration-700 pointer-events-none" />

        {isLoading ? (
          <span className="relative z-10 flex items-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Loading...
          </span>
        ) : (
          <span className="relative z-10">{children}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
