import React from 'react'
import { RiskBadge } from '../ui'
import { PredictResponse } from '../../services/api'
import { ChartSource } from './types'

interface ChartSummaryProps {
    source: ChartSource
    cancerIcon: string | null
    geneCount: number
    covariateCount: number
    prediction: PredictResponse | null
    modelIsDemo: boolean
    onClear: () => void
    /** Scrolls the thread to the live intake card — editing happens there, not here. */
    onEdit: () => void
}

const SOURCE_NOTE: Record<ChartSource['kind'], string> = {
    none: '',
    curated: 'curated model',
    pending: 'no model yet',
    cohort: 'model built from your query',
}

/**
 * The chart, read-only.
 *
 * Every control that CHANGES patient data now lives in the conversation (see
 * entries/CaseSetupCard and entries/IntakeCard) — the console previously had two
 * editable surfaces for the same state, which is what made the chat and the
 * profile feel like separate apps. This panel only reports.
 */
const ChartSummary: React.FC<ChartSummaryProps> = ({
    source, cancerIcon, geneCount, covariateCount, prediction, modelIsDemo, onClear, onEdit,
}) => {
    if (source.kind === 'none') {
        return (
            <div className="rounded-card border border-dashed border-border px-3 py-2.5">
                <p className="text-[11px] text-fg-faint">
                    No patient yet. Describe the case in the conversation — it is parsed in your browser and only a
                    de-identified summary is ever sent.
                </p>
            </div>
        )
    }

    return (
        <div className="rounded-card border border-border bg-surface px-3 py-2.5">
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <div className="flex items-center gap-1.5 min-w-0">
                        {cancerIcon && <span aria-hidden>{cancerIcon}</span>}
                        <span className="text-sm font-medium text-fg-strong truncate">{source.label}</span>
                    </div>
                    <p className="text-[11px] text-fg-faint mt-0.5">
                        {SOURCE_NOTE[source.kind]}
                        {modelIsDemo && ' · synthetic demo'}
                    </p>
                </div>
                <button type="button" onClick={onClear} className="flex-shrink-0 text-[11px] text-fg-faint hover:text-danger">
                    Clear
                </button>
            </div>

            <dl className="mt-2 pt-2 border-t border-border grid grid-cols-2 gap-y-1 text-[11px]">
                <dt className="text-fg-faint">Profile</dt>
                <dd className="text-fg text-right">{geneCount > 0 ? `${geneCount} genes` : 'not provided'}</dd>
                <dt className="text-fg-faint">Covariates</dt>
                <dd className="text-fg text-right">{covariateCount > 0 ? `${covariateCount} supplied` : 'none'}</dd>
            </dl>

            {prediction && (
                <div className="mt-2 pt-2 border-t border-border flex items-center gap-2 flex-wrap">
                    <RiskBadge group={prediction.risk_group} percentile={prediction.risk_percentile} size="sm" />
                    <span className="text-[11px] text-fg-muted">C-index {prediction.pooled_c_index.toFixed(2)}</span>
                </div>
            )}

            <button
                type="button"
                onClick={onEdit}
                className="mt-2 text-[11px] text-accent-fg hover:underline"
            >
                Edit in the conversation ↓
            </button>
        </div>
    )
}

export default ChartSummary
