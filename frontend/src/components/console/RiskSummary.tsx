import React from 'react'
import { RiskBadge, StatTile, RuoNotice } from '../ui'
import KaplanMeierChart from '../KaplanMeierChart'
import { PredictResponse } from '../../services/api'
import { GROUP_COLORS } from '../../utils/signatureViz'

interface RiskSummaryProps {
    prediction: PredictResponse
    modelIsDemo: boolean
    timeUnit: string
    /** Scrolls the thread to the full PatientReadout entry. */
    onOpenFullReadout: () => void
    /** Sends a grounded follow-up question about this readout to the assistant. */
    onAsk: (question: string) => void
}

/**
 * The scored chart, condensed for the rail. Deliberately NOT the whole readout —
 * the full PatientReadout (driver bars, treatment evidence, print report) stays
 * in the thread where it was produced; this is the persistent "where does this
 * patient stand" state that must not scroll away.
 *
 * The caveat block is not optional. Which C-index is being quoted, whether the
 * profile was quantile-normalized or fell back to per-gene ranking, and whether
 * the model is synthetic all change how a risk group should be read.
 */
const RiskSummary: React.FC<RiskSummaryProps> = ({ prediction, modelIsDemo, timeUnit, onOpenFullReadout, onAsk }) => {
    const horizons = prediction.predicted_survival.slice(0, 2)
    const km = prediction.reference_km
    const perYearUnit = timeUnit === 'days' ? 'days' : timeUnit === 'months' ? 'months' : 'years'

    return (
        <section className="rounded-card border border-border bg-surface p-3">
            <div className="flex items-center justify-between gap-2">
                <RiskBadge group={prediction.risk_group} percentile={prediction.risk_percentile} size="sm" />
                <button type="button" onClick={onOpenFullReadout} className="text-[11px] text-accent-fg hover:underline">
                    Full readout ↓
                </button>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2">
                {horizons.map((h) => (
                    <StatTile
                        key={h.horizon_label}
                        label={h.horizon_label}
                        value={`${Math.round(h.survival_probability * 100)}%`}
                    />
                ))}
            </div>

            {km?.times?.length > 0 && (
                <div className="mt-2">
                    <KaplanMeierChart
                        curves={[{
                            key: 'reference',
                            label: `${prediction.risk_group} risk (reference cohort)`,
                            times: km.times,
                            survival_probabilities: km.survival_probabilities,
                            color: GROUP_COLORS[prediction.risk_group] ?? GROUP_COLORS.intermediate,
                        }]}
                        timeUnit={perYearUnit as 'days' | 'months' | 'years'}
                        height={130}
                    />
                </div>
            )}

            <dl className="mt-2 space-y-0.5 text-[11px]">
                <div className="flex justify-between gap-2">
                    <dt className="text-fg-faint">Discrimination</dt>
                    <dd className="text-fg-muted">
                        {prediction.c_index_combined != null
                            ? `C ${prediction.c_index_combined.toFixed(2)} (expression + clinical)`
                            : `C ${prediction.pooled_c_index.toFixed(2)} (pooled, cross-cohort)`}
                    </dd>
                </div>
                <div className="flex justify-between gap-2">
                    <dt className="text-fg-faint">Genes matched</dt>
                    <dd className="text-fg-muted">{prediction.genes_used} of {prediction.genes_total}</dd>
                </div>
                <div className="flex justify-between gap-2">
                    <dt className="text-fg-faint">Normalization</dt>
                    <dd className="text-fg-muted">{prediction.normalization}</dd>
                </div>
            </dl>

            {(modelIsDemo || prediction.warnings.length > 0) && (
                <ul className="mt-2 space-y-1">
                    {modelIsDemo && (
                        <li className="text-[11px] text-warn">
                            ⚠ Synthetic demo model — this risk group is illustrative only, not an estimate for a real patient.
                        </li>
                    )}
                    {prediction.warnings.map((w) => (
                        <li key={w} className="text-[11px] text-warn">⚠ {w}</li>
                    ))}
                </ul>
            )}

            <div className="mt-2 flex flex-wrap gap-1.5">
                <button
                    type="button"
                    onClick={() => onAsk(`How should I read a ${prediction.risk_group}-risk call at the ${Math.round(prediction.risk_percentile)}th percentile with a pooled C-index of ${prediction.pooled_c_index.toFixed(2)}?`)}
                    className="px-2 py-0.5 rounded-full text-[10px] bg-surface-sunken text-fg-muted border border-border hover:text-accent-fg hover:border-border-accent transition-colors"
                >
                    Ask about this score
                </button>
            </div>

            <RuoNotice variant="footnote" className="mt-2" />
        </section>
    )
}

export default RiskSummary
