import React, { useEffect, useRef, useState } from 'react'
import {
    getTherapyRationale, getCohortKM,
    TherapyRationaleResponse, TreatmentKMEvidence, ReferenceKMCurve,
} from '../../services/api'
import KaplanMeierChart from '../KaplanMeierChart'
import { TREATMENT_COLORS, topTreatmentCurves } from '../../utils/signatureViz'

interface TherapyDirectionsProps {
    modelId: string
    riskGroup?: string | null
    genes?: string[]
    /** The patient's own predicted curve (from the base model) — overlaid on the
     *  treatment comparison chart as a reference line so each drug's cohort
     *  outcome is directly comparable against the patient's current predicted
     *  trajectory. */
    baselineCurve?: ReferenceKMCurve | null
}

const POLL_INTERVAL_MS = 15_000
const POLL_TIMEOUT_MS = 10 * 60_000
const PRESET_TOP_N = [5, 10]
const DEFAULT_TOP_N = 5
// Mirrors backend `_MAX_COHORT_KM_DRUGS` — the generate() call auto-resolves
// this many; requesting a batch of MORE is capped the same way server-side, so
// keep on-demand "check more" requests within one call's worth at a time.
const COHORT_KM_BATCH = 8

/**
 * Grounded "treatments to consider" (Oncologist Mode). On demand, the AI writes
 * advisory suggestions over REAL CIViC/DGIdb evidence for the risk-driving genes —
 * advisory, not a prescription. The cited associations are always shown alongside
 * the prose.
 *
 * The chart/table selection is driven by `ranked_drugs` from the backend — the
 * SAME round-robin-across-genes + evidence-level ranking used to decide which
 * drugs get an eager cohort-KM lookup at generate() time, with documented
 * CIViC resistance/adverse-outcome rows already excluded (see
 * `_rank_drugs_by_gene_priority` in chat_routes.py). N adjustable via the
 * control above the chart. Only the first `COHORT_KM_BATCH` drugs are
 * auto-resolved; raising N past that surfaces an explicit "check more" action
 * rather than firing background builds the user didn't ask to see. The table
 * below the chart is filtered to the same N drugs so plot and table always
 * describe the same data; any drug excluded from ranking for documented
 * resistance/adverse evidence is still disclosed separately, unplotted.
 */
const TherapyDirections: React.FC<TherapyDirectionsProps> = ({
    modelId, riskGroup, genes, baselineCurve,
}) => {
    const [data, setData] = useState<TherapyRationaleResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [cohortKm, setCohortKm] = useState<Record<string, TreatmentKMEvidence>>({})
    const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const pollStartRef = useRef<number | null>(null)
    const [topN, setTopN] = useState<number | 'all'>(DEFAULT_TOP_N)
    const [checkingMore, setCheckingMore] = useState(false)
    const [pollTimedOut, setPollTimedOut] = useState(false)

    useEffect(() => () => {
        if (pollRef.current) clearTimeout(pollRef.current)
    }, [])

    const mergeCohortKm = (results: TreatmentKMEvidence[]) => {
        setCohortKm((prev) => {
            const next = { ...prev }
            for (const r of results) next[r.drug.toLowerCase()] = r
            return next
        })
        return results.filter((r) => r.is_building).map((r) => r.drug)
    }

    const pollCohortKm = async (drugs: string[]) => {
        if (drugs.length === 0) return
        try {
            const results = await getCohortKM({ modelId, drugs })
            const stillBuilding = mergeCohortKm(results)
            if (stillBuilding.length === 0) {
                pollStartRef.current = null
                return
            }
            const elapsed = Date.now() - (pollStartRef.current ?? Date.now())
            if (elapsed > POLL_TIMEOUT_MS) {
                pollStartRef.current = null
                setPollTimedOut(true)
                return
            }
            pollRef.current = setTimeout(() => pollCohortKm(stillBuilding), POLL_INTERVAL_MS)
        } catch {
            // Network hiccup — stop polling silently; Regenerate will retry.
        }
    }

    const generate = async () => {
        setLoading(true)
        setError(null)
        setPollTimedOut(false)
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
                pollStartRef.current = Date.now()
                pollRef.current = setTimeout(() => pollCohortKm(building), POLL_INTERVAL_MS)
            }
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Could not generate therapeutic directions.')
        } finally {
            setLoading(false)
        }
    }

    const hasGenerated = data !== null || loading || error !== null
    const rankedDrugs = data?.ranked_drugs ?? []
    const displayedDrugs = topN === 'all' ? rankedDrugs : rankedDrugs.slice(0, topN)
    const displayedDrugKeys = new Set(displayedDrugs.map((d) => d.toLowerCase()))
    const drugColor: Record<string, string> = {}
    displayedDrugs.forEach((d, i) => { drugColor[d.toLowerCase()] = TREATMENT_COLORS[i % TREATMENT_COLORS.length] })

    const { curves, insufficientN } = topTreatmentCurves(displayedDrugs, cohortKm, riskGroup ?? null, baselineCurve)
    const chartedDrugKeys = new Set(curves.filter((c) => c.key !== '__baseline').map((c) => c.key.toLowerCase()))

    const buildingDrugs = displayedDrugs.filter((d) => cohortKm[d.toLowerCase()]?.is_building)
    const notCheckedDrugs = displayedDrugs.filter((d) => cohortKm[d.toLowerCase()]?.tier === 'not_checked')
    const unavailableDrugs = displayedDrugs.filter((d) => cohortKm[d.toLowerCase()]?.tier === 'unavailable')

    // Evidence rows for a drug that never entered `ranked_drugs` at all — i.e.
    // every row for that drug carried documented CIViC resistance/adverse
    // significance. Kept visible here (never plotted) so that evidence isn't
    // silently dropped from the page.
    const excludedEvidence = data
        ? data.evidence.filter((e) => !rankedDrugs.some((d) => d.toLowerCase() === e.drug.toLowerCase()))
        : []

    const checkMoreDrugs = async () => {
        const batch = notCheckedDrugs.slice(0, COHORT_KM_BATCH)
        if (batch.length === 0) return
        setCheckingMore(true)
        setPollTimedOut(false)
        try {
            const results = await getCohortKM({ modelId, drugs: batch })
            const stillBuilding = mergeCohortKm(results)
            if (stillBuilding.length > 0) {
                pollStartRef.current = Date.now()
                pollRef.current = setTimeout(() => pollCohortKm(stillBuilding), POLL_INTERVAL_MS)
            }
        } catch {
            // Best-effort — the button stays visible so the user can retry.
        } finally {
            setCheckingMore(false)
        }
    }

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
                    Surface documented CIViC/DGIdb drug–biomarker associations for this patient's
                    risk-driving genes, with real GEO cohort survival curves for the top matched drugs and
                    an AI-written summary framed as research hypotheses.
                </p>
            )}

            {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
            )}

            {data && (
                <div className="space-y-3">
                    <p className="text-sm text-gray-700 whitespace-pre-line">{data.rationale}</p>

                    {data.evidence.length > 0 && (
                        <div className="border border-gray-200 rounded-lg p-3 bg-white">
                            <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
                                <h4 className="text-sm font-semibold text-gray-700">Treatment outcome comparison</h4>
                                <div className="flex items-center gap-1.5 text-xs">
                                    <span className="text-gray-500">Show top</span>
                                    {PRESET_TOP_N.map((n) => (
                                        <button
                                            key={n}
                                            onClick={() => setTopN(n)}
                                            className={`px-2 py-0.5 rounded border ${
                                                topN === n
                                                    ? 'bg-purple-600 text-white border-purple-600'
                                                    : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                                            }`}
                                        >
                                            {n}
                                        </button>
                                    ))}
                                    <button
                                        onClick={() => setTopN('all')}
                                        className={`px-2 py-0.5 rounded border ${
                                            topN === 'all'
                                                ? 'bg-purple-600 text-white border-purple-600'
                                                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                                        }`}
                                    >
                                        All ({rankedDrugs.length})
                                    </button>
                                    <input
                                        type="number"
                                        min={1}
                                        max={rankedDrugs.length || 1}
                                        value={typeof topN === 'number' ? topN : rankedDrugs.length}
                                        onChange={(e) => {
                                            const v = Math.round(Number(e.target.value))
                                            if (Number.isFinite(v)) {
                                                setTopN(Math.max(1, Math.min(rankedDrugs.length || 1, v)))
                                            }
                                        }}
                                        className="w-12 border border-gray-300 rounded px-1 py-0.5 text-gray-700"
                                    />
                                </div>
                            </div>
                            <p className="text-[11px] text-gray-500 mb-2">
                                Real GEO cohort survival for the top {displayedDrugs.length} matched drug(s) —
                                solid line: same cohort as the patient's baseline (observational, not
                                randomized); dotted line: a different, treatment-matched GEO cohort — plotted
                                alongside your currently predicted survival (bold dashed). Advisory, not a
                                prescription or a prediction that you will respond.
                            </p>

                            {buildingDrugs.length > 0 && !pollTimedOut && (
                                <div className="text-[11px] text-indigo-700 bg-indigo-50 border border-indigo-200 rounded p-2 mb-2 flex items-center gap-2">
                                    <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                                    {cohortKm[buildingDrugs[0].toLowerCase()]?.build_stage
                                        ?? `Building cohort models for ${buildingDrugs.join(', ')}… (~2 min each, auto-refreshing)`}
                                </div>
                            )}

                            {buildingDrugs.length > 0 && pollTimedOut && (
                                <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 mb-2">
                                    Still building {buildingDrugs.join(', ')} after 10 minutes — this can happen
                                    with less-common drugs. Click Regenerate to retry, or check back shortly.
                                </div>
                            )}

                            {curves.length > 0 && <KaplanMeierChart curves={curves} height={260} />}

                            {curves.length === 0 && buildingDrugs.length === 0 && (
                                <p className="text-[11px] text-gray-400">
                                    No plottable GEO cohort outcome data yet for the selected drugs.
                                </p>
                            )}

                            {insufficientN.length > 0 && (
                                <p className="text-[11px] text-gray-400 mt-1">
                                    Not enough matched patients/events to plot reliably: {insufficientN
                                        .map((d) => `${d.drug} (n=${d.nSamples}, ${d.nEvents} events)`)
                                        .join(', ')}.
                                </p>
                            )}

                            {unavailableDrugs.length > 0 && (
                                <p className="text-[11px] text-gray-400 mt-1">
                                    No matching GEO cohort data for: {unavailableDrugs.join(', ')}.
                                </p>
                            )}

                            {notCheckedDrugs.length > 0 && (
                                <div className="mt-2 flex items-center gap-2 text-[11px]">
                                    <span className="text-gray-400">
                                        Not checked yet for GEO cohort data: {notCheckedDrugs.join(', ')}.
                                    </span>
                                    <button
                                        onClick={checkMoreDrugs}
                                        disabled={checkingMore}
                                        className="px-2 py-0.5 rounded border border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100 disabled:opacity-50 flex-shrink-0"
                                    >
                                        {checkingMore ? 'Checking…' : `Check ${Math.min(notCheckedDrugs.length, COHORT_KM_BATCH)} more`}
                                    </button>
                                </div>
                            )}

                            <div className="overflow-x-auto mt-3">
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
                                        {data.evidence
                                            .filter((e) => displayedDrugKeys.has(e.drug.toLowerCase()))
                                            .map((e, i) => (
                                                <tr key={i} className="border-b border-gray-100">
                                                    <td className="py-1 pr-2 font-medium text-gray-800">{e.gene}</td>
                                                    <td className="py-1 pr-2">
                                                        <div className="flex items-center gap-1.5">
                                                            {chartedDrugKeys.has(e.drug.toLowerCase()) && (
                                                                <span
                                                                    className="w-2 h-2 rounded-full flex-shrink-0"
                                                                    style={{ backgroundColor: drugColor[e.drug.toLowerCase()] }}
                                                                />
                                                            )}
                                                            {e.drug}
                                                        </div>
                                                    </td>
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
                                            ))}
                                    </tbody>
                                </table>
                            </div>

                            {excludedEvidence.length > 0 && (
                                <div className="mt-3 pt-2 border-t border-gray-100">
                                    <p className="text-[11px] font-medium text-gray-500 mb-1">
                                        Documented resistance / adverse-response evidence (excluded from the
                                        comparison chart above, shown here for disclosure)
                                    </p>
                                    <ul className="text-[11px] text-gray-500 space-y-0.5">
                                        {excludedEvidence.map((e, i) => (
                                            <li key={i}>
                                                {e.gene} → {e.drug} — {e.significance ?? e.evidence_type}
                                                {e.url && (
                                                    <>
                                                        {' '}(<a
                                                            href={e.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-indigo-600 hover:underline"
                                                        >
                                                            {e.source}
                                                        </a>)
                                                    </>
                                                )}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default TherapyDirections
