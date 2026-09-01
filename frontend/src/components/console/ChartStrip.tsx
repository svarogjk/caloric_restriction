import React from 'react'
import { RiskBadge } from '../ui'
import { PredictResponse } from '../../services/api'

interface ChartStripProps {
    cancerLabel: string | null
    cancerIcon: string | null
    genesProvided: number
    prediction: PredictResponse | null
    modelIsDemo: boolean
    onClear: () => void
    /** Whether the collapsed rail is currently expanded beneath this strip. */
    expanded: boolean
    onToggle: () => void
}

/** The chart in one line. On wide screens the full PatientRail is always
 *  visible and this is hidden; below lg it is the rail's collapsed state, and
 *  tapping it opens the chart. */
const ChartStrip: React.FC<ChartStripProps> = ({
    cancerLabel, cancerIcon, genesProvided, prediction, modelIsDemo, onClear, expanded, onToggle,
}) => (
    <div className="sticky top-0 z-10 bg-surface border-b border-border px-4 py-2 flex items-center justify-between gap-3 text-xs">
        <button type="button" onClick={onToggle} className="flex items-center gap-2 min-w-0 flex-wrap text-left">
            <span className="text-fg-faint" aria-hidden>{expanded ? '▾' : '▸'}</span>
            {cancerLabel ? (
                <>
                    {cancerIcon && <span aria-hidden>{cancerIcon}</span>}
                    <span className="font-medium text-fg-strong">{cancerLabel}</span>
                    {modelIsDemo && (
                        <span className="text-[10px] text-warn border border-warn-border bg-warn-soft rounded-full px-1.5">
                            demo model
                        </span>
                    )}
                    {genesProvided > 0 && <span className="text-fg-muted">· {genesProvided} genes</span>}
                    {prediction && (
                        <>
                            <RiskBadge group={prediction.risk_group} percentile={prediction.risk_percentile} size="sm" />
                            <span className="text-fg-muted">· C {prediction.pooled_c_index.toFixed(2)}</span>
                        </>
                    )}
                </>
            ) : (
                <span className="text-fg-faint">No patient chart open yet — tap to start one.</span>
            )}
        </button>
        {cancerLabel && (
            <button type="button" onClick={onClear} className="flex-shrink-0 text-fg-faint hover:text-danger">
                Clear chart
            </button>
        )}
    </div>
)

export default ChartStrip
