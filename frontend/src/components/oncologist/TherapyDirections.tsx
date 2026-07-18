import React, { useEffect, useRef, useState } from 'react'
import {
    getTherapyRationale, getCohortKM, getTreatmentContext,
    TherapyRationaleResponse, TreatmentKMEvidence, TreatmentComparisonResult, ReferenceKMCurve,
} from '../../services/api'
import KaplanMeierChart, { KMChartCurve } from '../KaplanMeierChart'
import { GROUP_COLORS, TREATMENT_COLORS, fiveYearSurvival, treatmentComparisonCurves } from '../../utils/signatureViz'

interface TherapyDirectionsProps {
    modelId: string
    riskGroup?: string | null
    genes?: string[]
    /** Cancer type key (e.g. "breast") — enables the always-on cohort treatment-outcome chart. */
    cancerType?: string | null
    /** The scored patient's tumour expression — required (>=10 genes) for the cohort chart. */
    expression?: Record<string, number>
    clinical?: Record<string, string | number> | null
    /** The patient's own predicted curve (from the base model) — overlaid on the
     *  cohort treatment chart as a reference line so treatment outcomes are directly
     *  comparable against the patient's current predicted trajectory. */
    baselineCurve?: ReferenceKMCurve | null
}

const POLL_INTERVAL_MS = 15_000

function cohortKmCurves(km: TreatmentKMEvidence): KMChartCurve[] {
    if (km.tier === 'arm_comparison') {
        return (km.arms ?? []).map((a, i) => ({
            key: a.name,
            label: `${a.name} (n=${a.n_samples})`,
            times: a.km_curve.times,
            survival_probabilities: a.km_curve.survival_probabilities,
            ci_lower: a.km_curve.ci_lower,
            ci_upper: a.km_curve.ci_upper,
            color: i === 0 ? '#9ca3af' : '#6366f1',
        }))
    }
    return (km.reference_km ?? []).map((c) => ({
        key: c.group,
        label: c.group,
        times: c.times,
        survival_probabilities: c.survival_probabilities,
        color: GROUP_COLORS[c.group] ?? '#6b7280',
        dashed: true,
    }))
}

const CohortKmPanel: React.FC<{ km: TreatmentKMEvidence }> = ({ km }) => {
    if (km.is_building) {
        return (
            <div className="mt-1 text-[11px] text-indigo-600 flex items-center gap-1.5">
                <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                Building cohort model for {km.drug}… (~2 min, auto-refreshing)
            </div>
        )
    }
    if (km.tier === 'not_checked') {
        return (
            <div className="mt-1 text-[11px] text-gray-400">
                Not checked for GEO cohort data this round.
            </div>
        )
    }
    if (km.tier === 'unavailable') {
        return (
            <div className="mt-1 text-[11px] text-gray-400">
                No matching GEO cohort data available for {km.drug}.
            </div>
        )
    }

    const curves = cohortKmCurves(km)
    if (curves.length === 0) return null

    return (
        <div className="mt-2 border border-gray-200 rounded p-2 bg-white">
            <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-[11px] font-medium text-gray-600">{km.drug} — GEO cohort survival</span>
                <span
                    className={`text-[10px] px-1.5 py-0.5 rounded ${
                        km.tier === 'arm_comparison' ? 'bg-indigo-50 text-indigo-700' : 'bg-gray-100 text-gray-500'
                    }`}
                >
                    {km.tier === 'arm_comparison' ? 'Cohort comparison' : 'Cohort reference'}
                </span>
            </div>
            <KaplanMeierChart curves={curves} height={160} />
            <p className="text-[10px] text-gray-400 mt-1">{km.caveat}</p>
        </div>
    )
}

/**
 * Curated per-cancer-type treatment cohort comparison (F24) — real GEO cohort
 * KM curves for standard-of-care treatments, independent of whether any
 * specific gene-drug literature association was found. Renders every time
 * Generate is clicked and a supported cancer type is resolved, so a chart is
 * never gated on CIViC/DGIdb coverage (which is often sparse for a given
 * gene set).
 */
const TreatmentComparisonPanel: React.FC<{
    cancerType?: string | null
    hasEnoughExpression: boolean
    loading: boolean
    error: string | null
    data: TreatmentComparisonResult | null
    baselineCurve?: ReferenceKMCurve | null
}> = ({ cancerType, hasEnoughExpression, loading, error, data, baselineCurve }) => {
    if (!cancerType) {
        return (
            <p className="text-[11px] text-gray-400">
                Cohort outcome curves aren't available for this cancer type yet.
            </p>
        )
    }
    if (!hasEnoughExpression) {
        return (
            <p className="text-[11px] text-gray-400">
                Add the full tumour expression profile (≥10 genes) to enable cohort treatment-outcome curves.
            </p>
        )
    }
    if (error) {
        return <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
    }
    if (!data && loading) {
        return (
            <div className="flex items-center gap-2 text-xs text-gray-500">
                <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                Loading treatment cohort data…
            </div>
        )
    }
    if (!data) return null

    const patientRiskGroup = data.treatments.find((t) => t.risk_group)?.risk_group ?? null
    const building = data.treatments.filter((t) => t.is_building)
    const failed = data.treatments.filter((t) => t.build_error)
    const curves = treatmentComparisonCurves(data.treatments, patientRiskGroup, baselineCurve)

    return (
        <div className="space-y-2">
            {building.length > 0 && (
                <div className="text-[11px] text-indigo-700 bg-indigo-50 border border-indigo-200 rounded p-2 flex items-center gap-2">
                    <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                    Building cohort models for {building.map((t) => t.name).join(', ')}… (~2 min each, auto-refreshing)
                </div>
            )}

            {curves.length > 0 && <KaplanMeierChart curves={curves} height={220} />}

            <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                    <thead>
                        <tr className="bg-gray-50 text-gray-500 text-left">
                            <th className="px-2 py-1.5 font-medium border-b border-gray-200">Treatment</th>
                            <th className="px-2 py-1.5 font-medium border-b border-gray-200">Your risk group</th>
                            <th className="px-2 py-1.5 font-medium border-b border-gray-200">5-yr survival</th>
                            <th className="px-2 py-1.5 font-medium border-b border-gray-200">C-index</th>
                            <th className="px-2 py-1.5 font-medium border-b border-gray-200">Cohorts</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.treatments.map((t, i) => (
                            <tr key={t.slug} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                                <td className="px-2 py-2 font-medium text-gray-700 border-b border-gray-100">
                                    <div className="flex items-center gap-2">
                                        {!t.is_building && !t.build_error && (
                                            <span
                                                className="w-2 h-2 rounded-full flex-shrink-0"
                                                style={{ backgroundColor: TREATMENT_COLORS[i % TREATMENT_COLORS.length] }}
                                            />
                                        )}
                                        {t.name}
                                    </div>
                                </td>
                                <td className="px-2 py-2 border-b border-gray-100">
                                    {t.is_building ? (
                                        <span className="text-indigo-500 italic">Building…</span>
                                    ) : t.build_error ? (
                                        <span className="text-red-400">Error</span>
                                    ) : (
                                        <span
                                            className="px-2 py-0.5 rounded-full text-white text-[11px] font-semibold"
                                            style={{ backgroundColor: GROUP_COLORS[t.risk_group ?? 'low'] ?? '#6b7280' }}
                                        >
                                            {t.risk_group?.toUpperCase() ?? '—'}
                                        </span>
                                    )}
                                </td>
                                <td className="px-2 py-2 border-b border-gray-100 tabular-nums">
                                    {t.is_building ? '—' : fiveYearSurvival(t)}
                                </td>
                                <td className="px-2 py-2 border-b border-gray-100 tabular-nums text-gray-500">
                                    {t.pooled_c_index != null ? t.pooled_c_index.toFixed(2) : '—'}
                                </td>
                                <td className="px-2 py-2 border-b border-gray-100 text-gray-500">
                                    {t.n_cohorts != null ? `${t.n_cohorts} (n=${t.n_patients ?? '?'})` : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {failed.length > 0 && (
                <p className="text-[11px] text-gray-400">
                    Could not build models for: {failed.map((t) => t.name).join(', ')}.
                    These treatments may not have enough matching GEO datasets.
                </p>
            )}

            <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-2">
                {data.treatments[0]?.disclaimer}
            </p>
        </div>
    )
}

/**
 * Grounded "treatments to consider" (Oncologist Mode). On demand, the AI writes
 * advisory suggestions over REAL CIViC/DGIdb evidence for the risk-driving genes —
 * advisory, not a prescription. The cited associations are always shown alongside
 * the prose, and a prominent banner keeps the framing honest.
 *
 * Two independent, real-GEO-cohort chart sources are drawn on every Generate click:
 * - Per-drug KM (F24b) for the top few highest-confidence CIViC/DGIdb suggestions,
 *   see cohortKmCurves for the tiered arm-comparison vs cohort-reference framing.
 * - A curated per-cancer-type treatment comparison (F24, TreatmentComparisonPanel)
 *   that does NOT depend on any biomarker-drug literature match existing — so a
 *   chart still renders even when CIViC/DGIdb has no coverage for these genes.
 */
const TherapyDirections: React.FC<TherapyDirectionsProps> = ({
    modelId, riskGroup, genes, cancerType, expression, clinical, baselineCurve,
}) => {
    const [data, setData] = useState<TherapyRationaleResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [cohortKm, setCohortKm] = useState<Record<string, TreatmentKMEvidence>>({})
    const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    const [treatmentContext, setTreatmentContext] = useState<TreatmentComparisonResult | null>(null)
    const [tcLoading, setTcLoading] = useState(false)
    const [tcError, setTcError] = useState<string | null>(null)
    const tcPollRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const hasEnoughExpression = Object.keys(expression ?? {}).length >= 10

    useEffect(() => () => {
        if (pollRef.current) clearTimeout(pollRef.current)
        if (tcPollRef.current) clearTimeout(tcPollRef.current)
    }, [])

    const pollCohortKm = async (drugs: string[]) => {
        if (drugs.length === 0) return
        try {
            const results = await getCohortKM({ modelId, drugs })
            setCohortKm((prev) => {
                const next = { ...prev }
                for (const r of results) next[r.drug.toLowerCase()] = r
                return next
            })
            const stillBuilding = results.filter((r) => r.is_building).map((r) => r.drug)
            if (stillBuilding.length > 0) {
                pollRef.current = setTimeout(() => pollCohortKm(stillBuilding), POLL_INTERVAL_MS)
            }
        } catch {
            // Network hiccup — stop polling silently; Regenerate will retry.
        }
    }

    const fetchTreatmentContext = async () => {
        if (!cancerType || !hasEnoughExpression) return
        try {
            const result = await getTreatmentContext({
                cancer_type: cancerType, expression: expression ?? {}, clinical,
            })
            setTreatmentContext(result)
            setTcError(null)
            if (result.treatments.some((t) => t.is_building)) {
                tcPollRef.current = setTimeout(() => { void fetchTreatmentContext() }, POLL_INTERVAL_MS)
            }
        } catch (err) {
            setTcError(err instanceof Error ? err.message : 'Failed to load treatment cohort data')
        } finally {
            setTcLoading(false)
        }
    }

    const generate = async () => {
        setLoading(true)
        setError(null)
        if (pollRef.current) {
            clearTimeout(pollRef.current)
            pollRef.current = null
        }
        if (tcPollRef.current) {
            clearTimeout(tcPollRef.current)
            tcPollRef.current = null
        }
        setTreatmentContext(null)
        setTcError(null)
        if (cancerType && hasEnoughExpression) {
            setTcLoading(true)
            void fetchTreatmentContext()
        }

        try {
            const r = await getTherapyRationale({ modelId, riskGroup, genes })
            setData(r)

            const initial: Record<string, TreatmentKMEvidence> = {}
            const building: string[] = []
            for (const e of r.evidence) {
                if (e.cohort_km) {
                    initial[e.drug.toLowerCase()] = e.cohort_km
                    if (e.cohort_km.is_building) building.push(e.cohort_km.drug)
                }
            }
            setCohortKm(initial)
            if (building.length > 0) {
                pollRef.current = setTimeout(() => pollCohortKm(building), POLL_INTERVAL_MS)
            }
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Could not generate therapeutic directions.')
        } finally {
            setLoading(false)
        }
    }

    // Only render the cohort-KM chart under the FIRST evidence row for a given
    // drug — multiple rows (different genes) can share one drug suggestion.
    const firstRowForDrug = new Set<string>()
    const hasGenerated = data !== null || loading || error !== null

    return (
        <div className="border border-purple-200 rounded-lg p-4 bg-purple-50/40">
            <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-semibold text-gray-800">Treatments to consider</h3>
                <button
                    onClick={generate}
                    disabled={loading}
                    className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
                >
                    {loading ? 'Generating…' : data ? 'Regenerate' : 'Generate'}
                </button>
            </div>

            <div className="text-xs font-semibold text-purple-900 bg-purple-100 border border-purple-200 rounded p-2 mb-3">
                Advisory only — treatments to CONSIDER and discuss with the tumour board, grounded in
                documented biomarker–therapy associations from public knowledge bases. Hypothesis-generating
                and research use only; not a prescription and not a guarantee that this patient will respond.
            </div>

            {!hasGenerated && (
                <p className="text-sm text-gray-500">
                    Surface real GEO cohort survival curves for standard-of-care treatments, plus any
                    documented CIViC/DGIdb drug–biomarker associations for this patient's risk-driving
                    genes, with an AI-written summary framed as research hypotheses.
                </p>
            )}

            {hasGenerated && (
                <div className="mb-4 border border-gray-200 rounded-lg p-3 bg-white">
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Cohort survival by treatment</h4>
                    <p className="text-[11px] text-gray-500 mb-2">
                        Historical outcomes from GEO cohorts receiving each treatment — patients in the same
                        risk group as yours — plotted alongside your currently predicted survival (bold gray,
                        dashed) so each option is directly comparable to your current trajectory. Advisory, not
                        a prescription or a prediction that you will respond.
                    </p>
                    <TreatmentComparisonPanel
                        cancerType={cancerType}
                        hasEnoughExpression={hasEnoughExpression}
                        loading={tcLoading}
                        error={tcError}
                        data={treatmentContext}
                        baselineCurve={baselineCurve}
                    />
                </div>
            )}

            {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
            )}

            {data && (
                <div className="space-y-3">
                    <p className="text-sm text-gray-700 whitespace-pre-line">{data.rationale}</p>

                    {data.evidence.length > 0 && (
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs border-collapse">
                                <thead>
                                    <tr className="text-left text-gray-500 border-b border-gray-200">
                                        <th className="py-1 pr-2">Gene</th>
                                        <th className="py-1 pr-2">Drug / therapy</th>
                                        <th className="py-1 pr-2">Evidence</th>
                                        <th className="py-1 pr-2">Source</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.evidence.map((e, i) => {
                                        const drugKey = e.drug.toLowerCase()
                                        const showChart = !firstRowForDrug.has(drugKey)
                                        firstRowForDrug.add(drugKey)
                                        const km = cohortKm[drugKey]
                                        return (
                                            <React.Fragment key={i}>
                                                <tr className="border-b border-gray-100">
                                                    <td className="py-1 pr-2 font-medium text-gray-800">{e.gene}</td>
                                                    <td className="py-1 pr-2">{e.drug}</td>
                                                    <td className="py-1 pr-2 text-gray-600">
                                                        {e.source === 'CIViC'
                                                            ? [e.evidence_type, e.significance, e.evidence_level && `level ${e.evidence_level}`]
                                                                  .filter(Boolean)
                                                                  .join(' · ')
                                                            : [e.interaction_type, e.approved ? 'approved' : 'investigational']
                                                                  .filter(Boolean)
                                                                  .join(' · ')}
                                                    </td>
                                                    <td className="py-1 pr-2">
                                                        {e.url ? (
                                                            <a
                                                                href={e.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-indigo-600 hover:underline"
                                                            >
                                                                {e.source}
                                                            </a>
                                                        ) : (
                                                            <span className="text-gray-500">{e.source}{e.source_db ? ` (${e.source_db})` : ''}</span>
                                                        )}
                                                    </td>
                                                </tr>
                                                {showChart && km && (
                                                    <tr>
                                                        <td colSpan={4} className="pb-2">
                                                            <CohortKmPanel km={km} />
                                                        </td>
                                                    </tr>
                                                )}
                                            </React.Fragment>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default TherapyDirections
