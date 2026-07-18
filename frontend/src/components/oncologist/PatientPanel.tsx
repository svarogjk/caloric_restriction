import React, { useEffect, useRef, useState } from 'react'
import {
    personalizePatient, getDemoPatient, getSignatureModel,
    PredictResponse, ClinicalCovariateSpec, ReferenceKMCurve,
} from '../../services/api'
import { parsePastedExpression } from '../../utils/signatureViz'
import PatientReadout from './PatientReadout'

interface PatientPanelProps {
    /** A saved analysis to auto-build a signature from… */
    resultId?: string | null
    /** …or a pre-built/curated model to score against directly. One is required. */
    modelId?: string | null
    label: string                                  // cancer / query label for the report
    initialCovariates?: ClinicalCovariateSpec[]    // curated: known up front
    /** Render expanded immediately (Oncologist Mode) vs. behind a checkbox (results tab). */
    alwaysOpen?: boolean
    /** Patient expression carried from the landing page. */
    initialExpression?: string
    /** Auto-run the personalize call once the data + result are ready. */
    autoRun?: boolean
    /** Cancer type key (e.g. "breast") — enables treatment context toggle in the readout. */
    cancerType?: string | null
}

/**
 * Unified patient personalization. Attaching patient data to ANY analysis (or a
 * curated model) auto-builds/reuses the signature and scores the patient — there
 * is no separate "build signature" step. Predictive + advisory, research use only.
 */
const PatientPanel: React.FC<PatientPanelProps> = ({
    resultId, modelId, label, initialCovariates, alwaysOpen, initialExpression, autoRun, cancerType,
}) => {
    const [enabled, setEnabled] = useState(!!alwaysOpen || !!initialExpression)
    const [exprText, setExprText] = useState(initialExpression ?? '')
    const [covariates, setCovariates] = useState<ClinicalCovariateSpec[]>(initialCovariates ?? [])
    const [clinical, setClinical] = useState<Record<string, string>>({})
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [prediction, setPrediction] = useState<PredictResponse | null>(null)
    const [resolvedModelId, setResolvedModelId] = useState<string | null>(modelId ?? null)
    const [modelIsDemo, setModelIsDemo] = useState(false)
    const [referenceCurves, setReferenceCurves] = useState<ReferenceKMCurve[] | undefined>()
    const [timeUnit, setTimeUnit] = useState('days')
    const [resolvedCancerType, setResolvedCancerType] = useState<string | null>(null)

    // For a curated/pre-built model, load its covariates + demo capability up front.
    useEffect(() => {
        if (!modelId) return
        getSignatureModel(modelId)
            .then((m) => {
                if (!initialCovariates) setCovariates(m.clinical_covariates ?? [])
                setModelIsDemo(m.is_demo)
                setTimeUnit(m.time_unit)
            })
            .catch(() => undefined)
    }, [modelId, initialCovariates])

    const setField = (name: string, value: string) => setClinical((c) => ({ ...c, [name]: value }))

    const loadDemoPatient = async () => {
        const mid = resolvedModelId
        if (!mid) return
        setError(null)
        try {
            const expr = await getDemoPatient(mid)
            setExprText(Object.entries(expr).map(([g, v]) => `${g} ${Number(v).toFixed(3)}`).join('\n'))
            const demoClinical: Record<string, string> = {}
            for (const cov of covariates) {
                if (cov.kind === 'numeric') {
                    const mid2 = cov.min_value != null && cov.max_value != null
                        ? Math.round((cov.min_value + cov.max_value) / 2) : 60
                    demoClinical[cov.name] = String(mid2)
                } else if (cov.options?.length) {
                    demoClinical[cov.name] = cov.options[cov.options.length - 1]
                }
            }
            setClinical(demoClinical)
        } catch {
            setError('Could not load the demo patient.')
        }
    }

    const personalize = async () => {
        const expr = parsePastedExpression(exprText)
        if (Object.keys(expr).length === 0) {
            setError('Could not parse any "GENE value" pairs. Use one per line, e.g. "TP53 8.2".')
            return
        }
        const clin = Object.fromEntries(Object.entries(clinical).filter(([, v]) => v !== ''))
        setLoading(true)
        setError(null)
        try {
            const resp = await personalizePatient({
                resultId, modelId, expression: expr,
                clinical: Object.keys(clin).length ? clin : null,
            })
            setPrediction(resp.prediction)
            setResolvedModelId(resp.model_id)
            setModelIsDemo(resp.model_is_demo)
            setResolvedCancerType(resp.cancer_type)
            setCovariates(resp.clinical_covariates)        // reveal clinical fields for refinement
            // Fetch full model once for the multi-group reference KM.
            try {
                const full = await getSignatureModel(resp.model_id)
                const combined = resp.prediction.scored_on.startsWith('combined') && full.combined_reference_km
                setReferenceCurves(combined ? full.combined_reference_km! : full.reference_km)
                setTimeUnit(full.time_unit)
            } catch {
                setReferenceCurves(undefined)
            }
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Personalization failed.')
        } finally {
            setLoading(false)
        }
    }

    // Carry-through: when patient data arrives from the landing page and the
    // analysis is saved (result_id ready), score automatically — once.
    const autoRanRef = useRef(false)
    useEffect(() => {
        if (autoRun && !autoRanRef.current && (resultId || modelId) && exprText.trim()) {
            autoRanRef.current = true
            void personalize()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoRun, resultId, modelId, exprText])

    if (!resultId && !modelId) {
        return (
            <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded p-4">
                Save this analysis to personalize it for a patient.
            </div>
        )
    }

    return (
        <div className="space-y-4">
            {!alwaysOpen && (
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => setEnabled(e.target.checked)}
                        className="rounded border-gray-300"
                    />
                    Personalize for a patient (research use only)
                </label>
            )}

            {enabled && (
                <>
                    <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                        <strong>Research use only.</strong> Patient data is scored in your browser session and
                        never stored. Attaching it auto-builds this analysis's risk model, predicts a risk group,
                        and surfaces advisory treatments to discuss — not a prescription or a guarantee of response.
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Tumour expression profile</label>
                        <textarea
                            value={exprText}
                            onChange={(e) => setExprText(e.target.value)}
                            rows={6}
                            placeholder={'Paste "GENE value" per line:\nTP53 8.2\nMKI67 11.4\n…'}
                            className="w-full text-xs font-mono border border-gray-300 rounded p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                        <p className="text-[11px] text-gray-400 mt-1">
                            Paste the <strong>full tumour profile</strong> (all measured genes, ≥40), not just
                            the signature genes — this enables cross-platform quantile normalization. With only a
                            few genes it falls back to per-gene ranking, which assumes a comparable scale.
                        </p>
                    </div>

                    {covariates.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Clinical covariates <span className="font-normal text-gray-400">(optional — blank ⇒ expression only)</span>
                            </label>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                {covariates.map((cov) => (
                                    <div key={cov.name}>
                                        <label className="block text-xs text-gray-500 mb-0.5">{cov.display_label}</label>
                                        {cov.kind === 'categorical' && cov.options ? (
                                            <select
                                                value={clinical[cov.name] ?? ''}
                                                onChange={(e) => setField(cov.name, e.target.value)}
                                                className="w-full text-sm border border-gray-300 rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                            >
                                                <option value="">—</option>
                                                {cov.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                                            </select>
                                        ) : (
                                            <input
                                                type="number"
                                                value={clinical[cov.name] ?? ''}
                                                min={cov.min_value ?? undefined}
                                                max={cov.max_value ?? undefined}
                                                onChange={(e) => setField(cov.name, e.target.value)}
                                                className="w-full text-sm border border-gray-300 rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="flex gap-2">
                        <button
                            onClick={personalize}
                            disabled={loading || !exprText.trim()}
                            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                        >
                            {loading ? 'Building model & scoring…' : prediction ? 'Re-score patient' : 'Predict & suggest treatments'}
                        </button>
                        {resolvedModelId && (
                            <button
                                onClick={loadDemoPatient}
                                disabled={loading}
                                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 border border-gray-300 rounded hover:bg-gray-200 disabled:opacity-50"
                            >
                                Load demo patient
                            </button>
                        )}
                    </div>

                    {error && (
                        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
                    )}

                    {prediction && resolvedModelId && (
                        <PatientReadout
                            prediction={prediction}
                            modelId={resolvedModelId}
                            cancerLabel={label}
                            modelIsDemo={modelIsDemo}
                            referenceCurves={referenceCurves}
                            timeUnit={timeUnit}
                            cancerType={cancerType ?? resolvedCancerType}
                            expressionRaw={exprText}
                            clinicalValues={clinical}
                        />
                    )}
                </>
            )}
        </div>
    )
}

export default PatientPanel
