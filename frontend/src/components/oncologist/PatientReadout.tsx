import React, { useMemo } from 'react'
import { PredictResponse, ReferenceKMCurve } from '../../services/api'
import { GROUP_COLORS } from '../../utils/signatureViz'
import KaplanMeierChart, { KMChartCurve } from '../KaplanMeierChart'
import TherapyDirections from './TherapyDirections'
import PatientReport from './PatientReport'
import { RuoNotice } from '../ui'

interface PatientReadoutProps {
    prediction: PredictResponse
    modelId: string
    cancerLabel: string
    modelIsDemo?: boolean
    /** All risk-group reference curves (for the highlighted multi-group KM). Falls
     *  back to the prediction's single assigned-group curve when absent. */
    referenceCurves?: ReferenceKMCurve[]
    timeUnit?: string
    /** The patient's scored tumour profile — forwarded to "Treatments to
     *  consider" so each drug's cohort-reference curve can be picked by
     *  scoring the patient against that treatment-specific model. */
    expression?: Record<string, number>
    clinical?: Record<string, string>
}

/**
 * Shared predictive readout for a single scored patient — used by both the
 * in-results patient panel and Oncologist Mode. Predicts an outcome risk group
 * and surfaces advisory treatment suggestions. Advisory, research use only.
 */
const PatientReadout: React.FC<PatientReadoutProps> = ({
    prediction: result, modelId, cancerLabel, modelIsDemo, referenceCurves, timeUnit = 'days',
    expression, clinical,
}) => {
    const curves = referenceCurves && referenceCurves.length ? referenceCurves : [result.reference_km]
    const kmCurves: KMChartCurve[] = useMemo(() => curves.map((c) => ({
        key: c.group,
        label: c.group,
        times: c.times,
        survival_probabilities: c.survival_probabilities,
        color: GROUP_COLORS[c.group] ?? '#6b7280',
        strokeWidth: c.group === result.risk_group ? 3.5 : 1.5,
        strokeOpacity: c.group === result.risk_group ? 1 : 0.45,
    })), [curves, result.risk_group])
    const hasKmData = curves.some((c) => c.times.length > 0)
    const perYear = timeUnit.toLowerCase().startsWith('month') ? 12 : 365
    const maxAbs = Math.max(1e-9, ...result.contributions.map((c) => Math.abs(c.contribution)))

    return (
        <div className="mt-6 space-y-4">
            <h2 className="text-lg font-semibold text-fg-strong">Predictive readout</h2>

            <div className="flex flex-wrap items-center gap-3">
                <span
                    className="px-3 py-1 rounded-full text-sm font-semibold text-on-accent"
                    style={{ backgroundColor: GROUP_COLORS[result.risk_group] ?? '#6b7280' }}
                >
                    {result.risk_group.toUpperCase()} RISK
                </span>
                <span className="text-sm text-fg-muted">{result.risk_percentile.toFixed(0)}th percentile vs reference</span>
                <span className="text-xs text-fg-faint">scored on {result.scored_on}</span>
                <span className="text-xs text-fg-faint ml-auto">{result.genes_used}/{result.genes_total} signature genes matched</span>
            </div>

            <p className="text-[11px] text-fg-faint">Normalization: {result.normalization}</p>

            {result.warnings.length > 0 && (
                <div className="text-xs text-warn bg-warn-soft border border-warn-border rounded p-2 space-y-1">
                    {result.warnings.map((w, i) => (
                        <div key={i}>⚠ {w}</div>
                    ))}
                </div>
            )}

            {result.predicted_survival.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                    {result.predicted_survival.map((s) => (
                        <div key={s.horizon_label} className="text-center bg-surface-sunken rounded p-2">
                            <div className="text-xl font-bold text-fg-strong">{(s.survival_probability * 100).toFixed(0)}%</div>
                            <div className="text-xs text-fg-muted">{s.horizon_label} survival</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Incremental-value C-index trio */}
            {(result.c_index_combined != null || result.c_index_expression_only != null) && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                    <CIdx label="Expression" value={result.c_index_expression_only} />
                    <CIdx label="Clinical" value={result.c_index_clinical_only} />
                    <CIdx label="Combined" value={result.c_index_combined ?? result.pooled_c_index} highlight />
                    <CIdx label="Δ vs expression" value={result.delta_c_index} signed />
                </div>
            )}

            {hasKmData && (
                <div>
                    <h3 className="text-sm font-medium text-fg mb-1">
                        Reference survival by risk group <span className="text-fg-faint font-normal">(patient's group highlighted)</span>
                    </h3>
                    <KaplanMeierChart curves={kmCurves} timeUnit={perYear === 12 ? 'months' : 'days'} height={260} />
                </div>
            )}

            {result.contributions.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-fg mb-1">What drove this score</h3>
                    <div className="space-y-1">
                        {result.contributions.map((c, i) => {
                            const pct = (Math.abs(c.contribution) / maxAbs) * 50
                            const positive = c.contribution >= 0
                            return (
                                <div key={i} className="flex items-center gap-2 text-xs">
                                    <span className="w-40 truncate text-fg-muted" title={c.label}>{c.label}</span>
                                    <div className="flex-1 flex items-center">
                                        <div className="w-1/2 flex justify-end">
                                            {!positive && <div className="h-3 rounded-l bg-ok" style={{ width: `${pct}%` }} />}
                                        </div>
                                        <div className="w-px h-3 bg-surface-hover" />
                                        <div className="w-1/2">
                                            {positive && <div className="h-3 rounded-r bg-danger" style={{ width: `${pct}%` }} />}
                                        </div>
                                    </div>
                                    <span className={`w-14 text-right ${positive ? 'text-danger' : 'text-ok'}`}>
                                        {positive ? '+' : ''}{c.contribution.toFixed(3)}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                    <p className="text-[11px] text-fg-faint mt-1">
                        Right (red) = increases estimated risk; left (green) = protective. The combined model adds
                        clinical covariates on top of the expression signature.
                    </p>
                </div>
            )}

            <RuoNotice scope="prediction" text={result.disclaimer} />

            {/* Advisory treatment recommendation — promoted to a primary section */}
            <div className="pt-2 border-t border-border">
                <h3 className="text-base font-semibold text-fg-strong">
                    Treatments to consider <span className="font-normal text-fg-faint text-sm">(advisory)</span>
                </h3>
                <p className="text-[11px] text-fg-muted mb-2">
                    Suggestions to discuss with the tumour board, grounded in documented biomarker–therapy
                    evidence and historical GEO cohort outcomes. Not a prescription or a prediction that this
                    patient will respond.
                </p>

                <TherapyDirections
                    modelId={modelId}
                    riskGroup={result.risk_group}
                    baselineCurve={result.reference_km}
                    expression={expression}
                    clinical={clinical}
                    timeUnit={timeUnit}
                />
            </div>

            <button
                onClick={() => window.print()}
                className="px-4 py-2 text-sm bg-inverse text-on-inverse rounded hover:bg-inverse-hover"
            >
                Print patient report
            </button>

            <PatientReport
                cancerLabel={cancerLabel}
                modelId={modelId}
                modelIsDemo={!!modelIsDemo}
                prediction={result}
            />
        </div>
    )
}

const CIdx: React.FC<{ label: string; value: number | null | undefined; highlight?: boolean; signed?: boolean }> = ({
    label, value, highlight, signed,
}) => (
    <div className={`rounded p-2 ${highlight ? 'bg-accent-soft border border-border-accent' : 'bg-surface-sunken'}`}>
        <div className="text-sm font-bold text-fg-strong">
            {value == null ? '—' : `${signed && value >= 0 ? '+' : ''}${value.toFixed(3)}`}
        </div>
        <div className="text-[10px] text-fg-muted">{label} C-index</div>
    </div>
)

export default PatientReadout
