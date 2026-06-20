import React, { useMemo } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { PredictResponse, ReferenceKMCurve } from '../../services/api'
import { GROUP_COLORS, buildKMChartData } from '../../utils/signatureViz'
import TherapyDirections from './TherapyDirections'
import PatientReport from './PatientReport'
import { TreatmentContextToggle } from './TreatmentContext'

interface PatientReadoutProps {
    prediction: PredictResponse
    modelId: string
    cancerLabel: string
    modelIsDemo?: boolean
    /** All risk-group reference curves (for the highlighted multi-group KM). Falls
     *  back to the prediction's single assigned-group curve when absent. */
    referenceCurves?: ReferenceKMCurve[]
    timeUnit?: string
    /** Cancer type key (e.g. "breast") — enables the treatment context toggle. */
    cancerType?: string | null
    /** Raw "GENE value" expression string for the scored patient. */
    expressionRaw?: string
    /** Clinical covariates supplied by the user. */
    clinicalValues?: Record<string, string | number> | null
}

/**
 * Shared predictive readout for a single scored patient — used by both the
 * in-results patient panel and Oncologist Mode. Predicts an outcome risk group
 * and surfaces advisory treatment suggestions. Advisory, research use only.
 */
const PatientReadout: React.FC<PatientReadoutProps> = ({
    prediction: result, modelId, cancerLabel, modelIsDemo, referenceCurves, timeUnit = 'days',
    cancerType, expressionRaw, clinicalValues,
}) => {
    const curves = referenceCurves && referenceCurves.length ? referenceCurves : [result.reference_km]
    const kmData = useMemo(() => buildKMChartData(curves), [curves])
    const groupsPresent = curves.map((c) => c.group)
    const perYear = timeUnit.toLowerCase().startsWith('month') ? 12 : 365
    const maxAbs = Math.max(1e-9, ...result.contributions.map((c) => Math.abs(c.contribution)))

    return (
        <div className="mt-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">Predictive readout</h2>

            <div className="flex flex-wrap items-center gap-3">
                <span
                    className="px-3 py-1 rounded-full text-sm font-semibold text-white"
                    style={{ backgroundColor: GROUP_COLORS[result.risk_group] ?? '#6b7280' }}
                >
                    {result.risk_group.toUpperCase()} RISK
                </span>
                <span className="text-sm text-gray-600">{result.risk_percentile.toFixed(0)}th percentile vs reference</span>
                <span className="text-xs text-gray-400">scored on {result.scored_on}</span>
                <span className="text-xs text-gray-400 ml-auto">{result.genes_used}/{result.genes_total} signature genes matched</span>
            </div>

            <p className="text-[11px] text-gray-400">Normalization: {result.normalization}</p>

            {result.warnings.length > 0 && (
                <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2 space-y-1">
                    {result.warnings.map((w, i) => (
                        <div key={i}>⚠ {w}</div>
                    ))}
                </div>
            )}

            {result.predicted_survival.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                    {result.predicted_survival.map((s) => (
                        <div key={s.horizon_label} className="text-center bg-gray-50 rounded p-2">
                            <div className="text-xl font-bold text-gray-800">{(s.survival_probability * 100).toFixed(0)}%</div>
                            <div className="text-xs text-gray-500">{s.horizon_label} survival</div>
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

            {kmData.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-1">
                        Reference survival by risk group <span className="text-gray-400 font-normal">(patient's group highlighted)</span>
                    </h3>
                    <div style={{ width: '100%', height: 260 }}>
                        <ResponsiveContainer>
                            <LineChart data={kmData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                    dataKey="time"
                                    tickFormatter={(t) => (t / perYear).toFixed(0)}
                                    label={{ value: 'Years', position: 'insideBottom', offset: -10 }}
                                />
                                <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                                <Tooltip
                                    formatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                                    labelFormatter={(t: number) => `${(t / perYear).toFixed(1)} yr`}
                                />
                                <Legend />
                                {groupsPresent.map((grp) => (
                                    <Line
                                        key={grp}
                                        type="stepAfter"
                                        dataKey={grp}
                                        stroke={GROUP_COLORS[grp] ?? '#6b7280'}
                                        strokeWidth={grp === result.risk_group ? 3.5 : 1.5}
                                        strokeOpacity={grp === result.risk_group ? 1 : 0.45}
                                        dot={false}
                                        connectNulls
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {result.contributions.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-1">What drove this score</h3>
                    <div className="space-y-1">
                        {result.contributions.map((c, i) => {
                            const pct = (Math.abs(c.contribution) / maxAbs) * 50
                            const positive = c.contribution >= 0
                            return (
                                <div key={i} className="flex items-center gap-2 text-xs">
                                    <span className="w-40 truncate text-gray-600" title={c.label}>{c.label}</span>
                                    <div className="flex-1 flex items-center">
                                        <div className="w-1/2 flex justify-end">
                                            {!positive && <div className="h-3 rounded-l bg-emerald-400" style={{ width: `${pct}%` }} />}
                                        </div>
                                        <div className="w-px h-3 bg-gray-300" />
                                        <div className="w-1/2">
                                            {positive && <div className="h-3 rounded-r bg-red-400" style={{ width: `${pct}%` }} />}
                                        </div>
                                    </div>
                                    <span className={`w-14 text-right ${positive ? 'text-red-600' : 'text-emerald-600'}`}>
                                        {positive ? '+' : ''}{c.contribution.toFixed(3)}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-1">
                        Right (red) = increases estimated risk; left (green) = protective. The combined model adds
                        clinical covariates on top of the expression signature.
                    </p>
                </div>
            )}

            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                <strong>Predictive risk estimate — advisory, research use only.</strong> This predicts an
                outcome risk group from tumour expression{result.scored_on.startsWith('combined') ? ' and clinical covariates' : ''} and,
                below, surfaces treatments worth discussing — grounded in documented evidence and historical
                cohort outcomes. It is not a prescription or a guarantee of response. Single-sample estimates
                are uncertain and cross-platform normalization is approximate. Discuss with the care team.
            </div>

            {/* Advisory treatment recommendation — promoted to a primary section */}
            <div className="pt-2 border-t border-gray-100">
                <h3 className="text-base font-semibold text-gray-800">
                    Treatments to consider <span className="font-normal text-gray-400 text-sm">(advisory)</span>
                </h3>
                <p className="text-[11px] text-gray-500 mb-2">
                    Suggestions to discuss with the tumour board, grounded in documented biomarker–therapy
                    evidence and historical GEO cohort outcomes. Not a prescription or a prediction that this
                    patient will respond.
                </p>

                <TreatmentContextToggle
                    cancerType={cancerType ?? null}
                    expressionRaw={expressionRaw ?? ''}
                    clinical={clinicalValues}
                />

                <TherapyDirections modelId={modelId} riskGroup={result.risk_group} />
            </div>

            <button
                onClick={() => window.print()}
                className="px-4 py-2 text-sm bg-gray-800 text-white rounded hover:bg-gray-900"
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
    <div className={`rounded p-2 ${highlight ? 'bg-indigo-50 border border-indigo-200' : 'bg-gray-50'}`}>
        <div className="text-sm font-bold text-gray-800">
            {value == null ? '—' : `${signed && value >= 0 ? '+' : ''}${value.toFixed(3)}`}
        </div>
        <div className="text-[10px] text-gray-500">{label} C-index</div>
    </div>
)

export default PatientReadout
