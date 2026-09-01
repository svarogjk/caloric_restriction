import { PredictResponse, SignatureGene } from '../services/api'
import { estimateGeneDrivers } from './signatureViz'

export interface PatientPromptContext {
    cancerLabel: string
    prediction: PredictResponse | null
    signatureGeneDetails: SignatureGene[]
    lastExpression: Record<string, number>
}

const FALLBACK_QUESTIONS = [
    'I have a new patient — where do I start?',
    'Which cancer types have validated models?',
    'What does a C-index of 0.7 mean in practice?',
    'What is the difference between prognostic and predictive biomarkers?',
]

/**
 * Chart-aware suggested questions. Each one is written to force a specific
 * grounded tool call (get_signature_model_evidence, get_gene_info, the
 * show_* actions) — satisfying the "call a tool on every substantive
 * question" mandate by construction, not by hoping the model complies.
 */
export function buildPatientPrompts(ctx: PatientPromptContext | null): string[] {
    if (!ctx?.prediction) return FALLBACK_QUESTIONS

    const { cancerLabel, prediction, signatureGeneDetails, lastExpression } = ctx
    // See estimateGeneDrivers' docstring — PredictResponse.contributions has no
    // per-gene breakdown to draw "top genes" from, so this is an approximation
    // from the model's own coefficients, not the exact per-gene score.
    const drivers = estimateGeneDrivers(signatureGeneDetails, lastExpression)
    const top = drivers.slice(0, 2).map((d) => d.gene_symbol)
    const g1 = top[0] ?? null
    const g2 = top[1]

    const questions = [
        `Which GEO cohorts is this ${cancerLabel} risk model built and validated on?`,
        g1
            ? (g2 ? `Why might ${g1} and ${g2} be pushing this patient's risk score?` : `Why might ${g1} be pushing this patient's risk score?`)
            : 'What is this risk score based on?',
        `How much should I trust a ${prediction.risk_group}-risk call at the ${Math.round(prediction.risk_percentile)}th percentile with C-index ${prediction.pooled_c_index.toFixed(2)}?`,
        g1 ? `What treatments have documented evidence for ${g1} in ${cancerLabel}?` : `What treatments have evidence in ${cancerLabel}?`,
        'Have I analysed this cancer type before?',
    ]
    return questions
}
