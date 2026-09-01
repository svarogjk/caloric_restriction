import React from 'react'

interface EmptyStateProps {
    title: string
    body?: React.ReactNode
    action?: React.ReactNode
    className?: string
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, body, action, className = '' }) => (
    <div className={`text-sm text-fg-muted border border-dashed border-border-strong rounded-card p-4 ${className}`}>
        <p className="font-medium text-fg-muted">{title}</p>
        {body && <p className="mt-1 text-fg-muted">{body}</p>}
        {action && <div className="mt-2">{action}</div>}
    </div>
)

export default EmptyState
