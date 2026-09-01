import { useCallback, useEffect, useState } from 'react'
import {
    personalizePatient, getDemoPatient, getSignatureModel,
    PredictResponse, ClinicalCovariateSpec, ReferenceKMCurve, SignatureGene,
} from '../services/api'
import { parsePastedExpression } from '../utils/signatureViz'

interface UsePatientScoringArgs {
    /** A saved analysis to auto-build a signature from… */
    resultId?: string | null
    /** …or a pre-built/curated model to score against directly. One is required. */
    modelId?: string | null
    /** Curated: covariates already known up front, skips the model metadata fetch for them. */
    initialCovariates?: ClinicalCovariateSpec[]
}

export interface UsePatientScoringResult {
    prediction: PredictResponse | null
    resolvedModelId: string | null
    modelIsDemo: boolean
    covariates: ClinicalCovariateSpec[]
    /** Gene symbols in the model's signature — drives expression coverage feedback. */
    signatureGenes: string[]
    /** Full signature genes (with coefficients) — for estimateGeneDrivers(), not just coverage checks. */
    signatureGeneDetails: SignatureGene[]
    referenceCurves: ReferenceKMCurve[] | undefined
    timeUnit: string
    /** Last-scored expression/clinical, kept alongside `prediction` so downstream
     *  panels (e.g. treatment evidence) can re-score against related cohort models. */
    lastExpression: Record<string, number>
    lastClinical: Record<string, string>
    loading: boolean
    error: string | null
    /** Parses `exprText` ("GENE value" per line) and scores it via /api/personalize.
     *  Optional overrides let a caller score against a model/result it just set
     *  in its own state without waiting for that to propagate back into this
     *  hook's `modelId`/`resultId` arguments on the next render (avoids a stale
     *  closure — see ClinicalConsole's loadCase). */
    score: (exprText: string, clinical: Record<string, string>, overrideModelId?: string | null, overrideResultId?: string | null) => Promise<void>
    /** Fetches a synthetic demo patient for this model, pre-formatted for a textarea. */
    loadDemoPatient: () => Promise<{ exprText: string; clinical: Record<string, string> } | null>
    reset: () => void
}

/**
 * The single place in the codebase that calls personalizePatient() — the function
 * that touches patient data. Shared by PatientPanel and the clinical console so
 * there is exactly one scoring code path to reason about for privacy and correctness.
 */
export function usePatientScoring({ resultId, modelId, initialCovariates }: UsePatientScoringArgs): UsePatientScoringResult {
    const [covariates, setCovariates] = useState<ClinicalCovariateSpec[]>(initialCovariates ?? [])
    const [signatureGenes, setSignatureGenes] = useState<string[]>([])
    const [signatureGeneDetails, setSignatureGeneDetails] = useState<SignatureGene[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [prediction, setPrediction] = useState<PredictResponse | null>(null)
    const [resolvedModelId, setResolvedModelId] = useState<string | null>(modelId ?? null)
    const [modelIsDemo, setModelIsDemo] = useState(false)
    const [referenceCurves, setReferenceCurves] = useState<ReferenceKMCurve[] | undefined>()
    const [timeUnit, setTimeUnit] = useState('days')
    const [lastExpression, setLastExpression] = useState<Record<string, number>>({})
    const [lastClinical, setLastClinical] = useState<Record<string, string>>({})

    // For a curated/pre-built model, load its covariates + signature genes up front.
    // Also resyncs resolvedModelId and clears any prior prediction whenever `modelId`
    // changes on an already-mounted hook instance — the clinical console swaps
    // cancer types on one instance (PatientPanel, by contrast, mounts fresh per model).
    useEffect(() => {
        setResolvedModelId(modelId ?? null)
        setPrediction(null)
        setReferenceCurves(undefined)
        setLastExpression({})
        setLastClinical({})
        setError(null)
        if (!modelId) return
        getSignatureModel(modelId)
            .then((m) => {
                if (!initialCovariates) setCovariates(m.clinical_covariates ?? [])
                setModelIsDemo(m.is_demo)
                setTimeUnit(m.time_unit)
                setSignatureGenes(m.genes.map((g) => g.gene_symbol))
                setSignatureGeneDetails(m.genes)
            })
            .catch(() => undefined)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [modelId])

    const score = useCallback(async (
        exprText: string, clinical: Record<string, string>,
        overrideModelId?: string | null, overrideResultId?: string | null,
    ) => {
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
                resultId: overrideResultId !== undefined ? overrideResultId : resultId,
                modelId: overrideModelId !== undefined ? overrideModelId : modelId,
                expression: expr,
                clinical: Object.keys(clin).length ? clin : null,
            })
            setPrediction(resp.prediction)
            setResolvedModelId(resp.model_id)
            setModelIsDemo(resp.model_is_demo)
            setCovariates(resp.clinical_covariates)        // reveal clinical fields for refinement
            setLastExpression(expr)
            setLastClinical(clin)
            // Fetch full model once for the multi-group reference KM + signature gene list.
            try {
                const full = await getSignatureModel(resp.model_id)
                const combined = resp.prediction.scored_on.startsWith('combined') && full.combined_reference_km
                setReferenceCurves(combined ? full.combined_reference_km! : full.reference_km)
                setTimeUnit(full.time_unit)
                setSignatureGenes(full.genes.map((g) => g.gene_symbol))
                setSignatureGeneDetails(full.genes)
            } catch {
                setReferenceCurves(undefined)
            }
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Personalization failed.')
        } finally {
            setLoading(false)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [resultId, modelId])

    const loadDemoPatient = useCallback(async () => {
        const mid = resolvedModelId
        if (!mid) return null
        setError(null)
        try {
            const expr = await getDemoPatient(mid)
            const exprText = Object.entries(expr).map(([g, v]) => `${g} ${Number(v).toFixed(3)}`).join('\n')
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
            return { exprText, clinical: demoClinical }
        } catch {
            setError('Could not load the demo patient.')
            return null
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [resolvedModelId, covariates])

    const reset = useCallback(() => {
        setPrediction(null)
        setResolvedModelId(modelId ?? null)
        setModelIsDemo(false)
        setReferenceCurves(undefined)
        setTimeUnit('days')
        setLastExpression({})
        setLastClinical({})
        setError(null)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [modelId])

    return {
        prediction, resolvedModelId, modelIsDemo, covariates, signatureGenes, signatureGeneDetails,
        referenceCurves, timeUnit, lastExpression, lastClinical, loading, error,
        score, loadDemoPatient, reset,
    }
}
