import React, { useEffect, useRef, useState } from 'react'
import { ClinicalCovariateSpec } from '../../services/api'
import PatientReadout from './PatientReadout'
import ClinicalCovariateFields from './ClinicalCovariateFields'
import { RuoNotice } from '../ui'
import { usePatientScoring } from '../../hooks/usePatientScoring'

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
    /** Survival genes found by the `resultId` analysis. A signature needs ≥ 2,
     * so a resultId-backed panel with too few can't build one — surface that
     * up front instead of letting the user fill out the form and hit a 422. */
    geneCount?: number
}

/**
 * Unified patient personalization. Attaching patient data to ANY analysis (or a
 * curated model) auto-builds/reuses the signature and scores the patient — there
 * is no separate "build signature" step. Predictive + advisory, research use only.
 */
const PatientPanel: React.FC<PatientPanelProps> = ({
    resultId, modelId, label, initialCovariates, alwaysOpen, initialExpression, autoRun, geneCount,
}) => {
    const [enabled, setEnabled] = useState(!!alwaysOpen || !!initialExpression)
    const [exprText, setExprText] = useState(initialExpression ?? '')
    const [clinical, setClinical] = useState<Record<string, string>>({})

    const {
        prediction, resolvedModelId, modelIsDemo, covariates, referenceCurves, timeUnit,
        lastExpression, lastClinical, loading, error, score, loadDemoPatient,
    } = usePatientScoring({ resultId, modelId, initialCovariates })

    const setField = (name: string, value: string) => setClinical((c) => ({ ...c, [name]: value }))

    const handleLoadDemoPatient = async () => {
        const demo = await loadDemoPatient()
        if (!demo) return
        setExprText(demo.exprText)
        setClinical(demo.clinical)
    }

    const personalize = () => score(exprText, clinical)

    // Carry-through: when patient data arrives from the landing page and the
    // analysis is saved (result_id ready), score automatically — once.
    const autoRanRef = useRef(false)
    useEffect(() => {
        if (autoRun && !autoRanRef.current && (resultId || modelId) && exprText.trim()) {
            autoRanRef.current = true
            void score(exprText, clinical)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoRun, resultId, modelId, exprText])

    if (!resultId && !modelId) {
        return (
            <div className="text-sm text-fg-muted border border-dashed border-border-strong rounded p-4">
                Save this analysis to personalize it for a patient.
            </div>
        )
    }

    if (resultId && !modelId && geneCount !== undefined && geneCount < 2) {
        return (
            <div className="text-sm text-fg-muted border border-dashed border-border-strong rounded p-4">
                This analysis found too few survival-associated genes ({geneCount}) to build a
                signature — a patient can't be personalized against it. Try a broader query, a
                lower significance threshold, or more datasets.
            </div>
        )
    }

    return (
        <div className="space-y-4">
            {!alwaysOpen && (
                <label className="flex items-center gap-2 text-sm font-medium text-fg">
                    <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => setEnabled(e.target.checked)}
                        className="rounded border-border-strong"
                    />
                    Personalize for a patient (research use only)
                </label>
            )}

            {enabled && (
                <>
                    <RuoNotice scope="intake" />

                    <div>
                        <label className="block text-sm font-medium text-fg mb-1">Tumour expression profile</label>
                        <textarea
                            value={exprText}
                            onChange={(e) => setExprText(e.target.value)}
                            rows={6}
                            placeholder={'Paste "GENE value" per line:\nTP53 8.2\nMKI67 11.4\n…'}
                            className="w-full text-xs font-mono border border-border-strong rounded p-2 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                        />
                        <p className="text-[11px] text-fg-faint mt-1">
                            Paste the <strong>full tumour profile</strong> (all measured genes, ≥40), not just
                            the signature genes — this enables cross-platform quantile normalization. With only a
                            few genes it falls back to per-gene ranking, which assumes a comparable scale.
                        </p>
                    </div>

                    <ClinicalCovariateFields covariates={covariates} values={clinical} onChange={setField} />

                    <div className="flex gap-2">
                        <button
                            onClick={personalize}
                            disabled={loading || !exprText.trim()}
                            className="px-4 py-2 text-sm bg-accent text-on-accent rounded hover:bg-accent-hover disabled:opacity-50"
                        >
                            {loading ? 'Building model & scoring…' : prediction ? 'Re-score patient' : 'Predict & suggest treatments'}
                        </button>
                        {resolvedModelId && (
                            <button
                                onClick={handleLoadDemoPatient}
                                disabled={loading}
                                className="px-4 py-2 text-sm bg-surface-sunken text-fg border border-border-strong rounded hover:bg-surface-hover disabled:opacity-50"
                            >
                                Load demo patient
                            </button>
                        )}
                    </div>

                    {error && (
                        <div className="text-sm text-danger bg-danger-soft border border-danger-border rounded p-2">{error}</div>
                    )}

                    {prediction && resolvedModelId && (
                        <PatientReadout
                            prediction={prediction}
                            modelId={resolvedModelId}
                            cancerLabel={label}
                            modelIsDemo={modelIsDemo}
                            referenceCurves={referenceCurves}
                            timeUnit={timeUnit}
                            expression={lastExpression}
                            clinical={lastClinical}
                        />
                    )}
                </>
            )}
        </div>
    )
}

export default PatientPanel
