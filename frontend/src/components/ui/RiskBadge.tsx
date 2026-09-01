import React from 'react'

interface RiskBadgeProps {
    group: string
    percentile?: number
    size?: 'sm' | 'md'
    className?: string
}

// Mirrors GROUP_COLORS in utils/signatureViz.ts and --color-risk-* in index.css.
const GROUP_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
    low: { bg: 'bg-ok-soft', text: 'text-ok', dot: 'bg-risk-low', label: 'LOW RISK' },
    intermediate: { bg: 'bg-warn-soft', text: 'text-warn', dot: 'bg-risk-intermediate', label: 'INTERMEDIATE RISK' },
    high: { bg: 'bg-danger-soft', text: 'text-danger', dot: 'bg-risk-high', label: 'HIGH RISK' },
}

const RiskBadge: React.FC<RiskBadgeProps> = ({ group, percentile, size = 'md', className = '' }) => {
    const style = GROUP_STYLES[group] ?? GROUP_STYLES.intermediate
    const padding = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-3 py-1 text-sm'
    return (
        <span
            className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${style.bg} ${style.text} ${padding} ${className}`}
        >
            <span className={`w-2 h-2 rounded-full ${style.dot}`} />
            {style.label}
            {percentile != null && (
                <span className="font-normal opacity-75">· {Math.round(percentile)}th pct</span>
            )}
        </span>
    )
}

export default RiskBadge
