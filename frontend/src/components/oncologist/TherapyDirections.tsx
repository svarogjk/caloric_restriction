import React, { useEffect, useRef, useState } from 'react'
import { getTherapyRationale, getCohortKM, TherapyRationaleResponse, TreatmentKMEvidence } from '../../services/api'
import KaplanMeierChart, { KMChartCurve } from '../KaplanMeierChart'
import { GROUP_COLORS } from '../../utils/signatureViz'

interface TherapyDirectionsProps {
    modelId: string
    riskGroup?: string | null
    genes?: string[]
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
 * Grounded "treatments to consider" (Oncologist Mode). On demand, the AI writes
 * advisory suggestions over REAL CIViC/DGIdb evidence for the risk-driving genes —
 * advisory, not a prescription. The cited associations are always shown alongside
 * the prose, and a prominent banner keeps the framing honest.
 *
 * For the top few highest-confidence suggestions, real GEO cohort survival
 * curves (F24b) are auto-built alongside generation and rendered inline once
 * ready — see cohortKmCurves for the tiered arm-comparison vs cohort-reference
 * framing.
 */
const TherapyDirections: React.FC<TherapyDirectionsProps> = ({ modelId, riskGroup, genes }) => {
    const [data, setData] = useState<TherapyRationaleResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [cohortKm, setCohortKm] = useState<Record<string, TreatmentKMEvidence>>({})
    const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => () => {
        if (pollRef.current) clearTimeout(pollRef.current)
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

    const generate = async () => {
        setLoading(true)
        setError(null)
        if (pollRef.current) {
            clearTimeout(pollRef.current)
            pollRef.current = null
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

            {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
            )}

            {!data && !loading && !error && (
                <p className="text-sm text-gray-500">
                    Surface documented CIViC/DGIdb drug–biomarker associations for this patient's
                    risk-driving genes, with an AI-written summary framed as research hypotheses.
                </p>
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
