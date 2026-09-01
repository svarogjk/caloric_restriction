import React from 'react'

interface StatTileProps {
    label: string
    value: React.ReactNode
    tone?: 'default' | 'good' | 'bad'
    highlight?: boolean
    tooltip?: React.ReactNode
    className?: string
}

const TONE_CLASSES: Record<NonNullable<StatTileProps['tone']>, string> = {
    default: 'text-fg-strong',
    good: 'text-ok',
    bad: 'text-danger',
}

/** Replaces the duplicated survival-tile / CIdx / Stat markup in PatientReadout and SignaturePanel. */
const StatTile: React.FC<StatTileProps> = ({ label, value, tone = 'default', highlight = false, tooltip, className = '' }) => (
    <div
        className={`rounded-card border p-3 text-center ${highlight ? 'border-border-accent bg-surface-accent' : 'border-border bg-surface-sunken'} ${className}`}
    >
        <div className="flex items-center justify-center gap-1 text-[11px] text-fg-muted uppercase tracking-wide">
            {label}
            {tooltip}
        </div>
        <div className={`text-metric font-semibold mt-0.5 ${TONE_CLASSES[tone]}`}>{value}</div>
    </div>
)

export default StatTile
