import React from 'react'

interface CardHeaderProps {
    icon?: React.ReactNode
    title: React.ReactNode
    actions?: React.ReactNode
    className?: string
}

export const CardHeader: React.FC<CardHeaderProps> = ({ icon, title, actions, className = '' }) => (
    <div className={`flex items-center justify-between gap-2 ${className}`}>
        <div className="flex items-center gap-2 min-w-0">
            {icon && <span className="flex-shrink-0">{icon}</span>}
            <div className="min-w-0 font-semibold text-fg-strong truncate">{title}</div>
        </div>
        {actions && <div className="flex-shrink-0 flex items-center gap-2">{actions}</div>}
    </div>
)

interface CardProps {
    tone?: 'default' | 'clinical' | 'warning' | 'muted'
    dense?: boolean
    className?: string
    children: React.ReactNode
}

const TONE_CLASSES: Record<NonNullable<CardProps['tone']>, string> = {
    default: 'bg-surface border-border',
    clinical: 'bg-surface-accent border-accent-soft',
    warning: 'bg-ruo-bg border-ruo-border',
    muted: 'bg-surface-sunken border-border',
}

const Card: React.FC<CardProps> = ({ tone = 'default', dense = false, className = '', children }) => (
    <div
        className={`rounded-card border shadow-[var(--shadow-card)] ${dense ? 'p-3' : 'p-4'} ${TONE_CLASSES[tone]} ${className}`}
    >
        {children}
    </div>
)

export default Card
