import React from 'react'

interface FieldProps {
    label: string
    hint?: string
    error?: string
    optional?: boolean
    className?: string
    children: React.ReactNode
}

export const Field: React.FC<FieldProps> = ({ label, hint, error, optional, className = '', children }) => (
    <div className={className}>
        <label className="block text-sm font-medium text-fg mb-1">
            {label}
            {optional && <span className="font-normal text-fg-faint"> (optional)</span>}
        </label>
        {children}
        {hint && !error && <p className="text-[11px] text-fg-faint mt-1">{hint}</p>}
        {error && <p className="text-[11px] text-danger mt-1">{error}</p>}
    </div>
)

interface FieldGridProps {
    columns?: 1 | 2 | 3
    className?: string
    children: React.ReactNode
}

export const FieldGrid: React.FC<FieldGridProps> = ({ columns = 2, className = '', children }) => {
    const cols = columns === 1 ? 'grid-cols-1' : columns === 2 ? 'grid-cols-2 sm:grid-cols-2' : 'grid-cols-2 sm:grid-cols-3'
    return <div className={`grid ${cols} gap-3 ${className}`}>{children}</div>
}

export default Field
