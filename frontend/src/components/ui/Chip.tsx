import React from 'react'

interface ChipProps {
    tone?: 'default' | 'confirmed' | 'warning' | 'accent'
    onEdit?: () => void
    onDismiss?: () => void
    className?: string
    children: React.ReactNode
}

const TONE_CLASSES: Record<NonNullable<ChipProps['tone']>, string> = {
    default: 'bg-surface-sunken text-fg border-border',
    confirmed: 'bg-ok-soft text-ok border-ok-border',
    warning: 'bg-ruo-bg text-ruo border-ruo-border',
    accent: 'bg-accent-soft text-accent-fg border-border-accent',
}

const Chip: React.FC<ChipProps> = ({ tone = 'default', onEdit, onDismiss, className = '', children }) => (
    <span
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONE_CLASSES[tone]} ${className}`}
    >
        {children}
        {onEdit && (
            <button type="button" onClick={onEdit} className="opacity-60 hover:opacity-100" aria-label="Edit">
                ✎
            </button>
        )}
        {onDismiss && (
            <button type="button" onClick={onDismiss} className="opacity-60 hover:opacity-100" aria-label="Remove">
                ×
            </button>
        )}
    </span>
)

export default Chip
