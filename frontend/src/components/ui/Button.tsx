import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    loading?: boolean
    /** Shown under the button when disabled, so a doctor never sees a mystery-grey control. */
    disabledReason?: string
}

const VARIANT_CLASSES: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'bg-accent text-on-accent hover:bg-accent-hover disabled:bg-accent',
    secondary: 'bg-surface-sunken text-fg border border-border-strong hover:bg-surface-hover',
    ghost: 'text-accent-fg hover:bg-accent-soft',
    danger: 'bg-danger-solid text-on-accent hover:bg-danger-solid-hover',
}

const SIZE_CLASSES: Record<NonNullable<ButtonProps['size']>, string> = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
}

const Button: React.FC<ButtonProps> = ({
    variant = 'primary',
    size = 'md',
    loading = false,
    disabledReason,
    disabled,
    className = '',
    children,
    ...rest
}) => {
    const isDisabled = disabled || loading
    return (
        <div className="inline-flex flex-col items-start gap-1">
            <button
                type="button"
                disabled={isDisabled}
                className={`rounded-control font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
                {...rest}
            >
                {loading ? 'Working…' : children}
            </button>
            {isDisabled && disabledReason && (
                <span className="text-[11px] text-fg-faint">{disabledReason}</span>
            )}
        </div>
    )
}

export default Button
