import React from 'react'

interface StepHeaderProps {
    index: number
    title: string
    status: 'todo' | 'active' | 'done'
    hint?: string
    className?: string
}

const STATUS_STYLES: Record<StepHeaderProps['status'], string> = {
    todo: 'bg-surface-sunken text-fg-faint border-border',
    active: 'bg-accent text-on-accent border-accent',
    done: 'bg-ok-soft text-ok border-ok-border',
}

const StepHeader: React.FC<StepHeaderProps> = ({ index, title, status, hint, className = '' }) => (
    <div className={`flex items-center gap-2 ${className}`}>
        <span
            className={`flex-shrink-0 w-5 h-5 rounded-full border flex items-center justify-center text-[11px] font-semibold ${STATUS_STYLES[status]}`}
        >
            {status === 'done' ? '✓' : index}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-fg-muted">{title}</span>
        {hint && <span className="text-[11px] text-fg-faint">{hint}</span>}
    </div>
)

export default StepHeader
