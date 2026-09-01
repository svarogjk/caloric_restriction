import { ConsoleAction } from '../services/chatApi'

/**
 * Client-side execution of console workflow intents (see backend
 * console_actions.py). The agent PROPOSES a step; this hook re-validates its
 * precondition against the console's own state and, if it passes, calls the
 * matching handler — patient data never leaves the browser to reach here.
 */
export interface ConsoleActionHandlers {
    set_cancer_type: (cancerKey: string) => void
    request_tumour_profile: () => void
    load_example_case: (caseId: string) => void
    score_patient: () => void
    explain_for_clinician: () => void
    show_model_quality: () => void
    show_treatment_evidence: () => void
    show_treatment_context: () => void
    show_driver_biology: () => void
    reuse_previous_analysis: (resultId: string) => void
    /** Run a cross-cohort analysis. `candidateGenes` restricts the tested set —
     *  the agent supplies it for a question about specific named genes, which
     *  also makes the resulting p-values nominal rather than FDR-adjusted. */
    run_survival_analysis: (query: string, candidateGenes?: string[]) => void
}

export interface UseConsoleActionsArgs {
    handlers: ConsoleActionHandlers
    /** True when the chart already has cancer type/expression set — used to
     *  require confirmation before load_example_case overwrites it. */
    hasChart: boolean
    isKnownCaseId: (caseId: string) => boolean
    isKnownCancerKey: (cancerKey: string) => boolean
    /** Refuse a second analysis while one is in flight — /api/search/stream has
     *  no per-user rate limit and two concurrent GEO workflows thrash memory. */
    analysisRunning: boolean
}

export interface ExecuteResult {
    status: 'applied' | 'declined' | 'failed'
    detail?: string
}

export interface UseConsoleActionsResult {
    /** Actions that must never auto-apply: they overwrite chart data or cost minutes. */
    needsConfirmation: (action: ConsoleAction) => boolean
    execute: (action: ConsoleAction) => ExecuteResult
}

export function useConsoleActions({ handlers, hasChart, isKnownCaseId, isKnownCancerKey, analysisRunning }: UseConsoleActionsArgs): UseConsoleActionsResult {
    const needsConfirmation = (action: ConsoleAction): boolean => {
        if (action.action === 'run_analysis') return true
        if (action.action === 'load_case' && hasChart) return true
        return false
    }

    const execute = (action: ConsoleAction): ExecuteResult => {
        try {
            switch (action.action) {
                case 'set_cancer_type': {
                    const key = String(action.cancer_key ?? '')
                    if (!isKnownCancerKey(key)) return { status: 'failed', detail: 'unknown cancer type' }
                    handlers.set_cancer_type(key)
                    return { status: 'applied' }
                }
                case 'request_expression':
                    handlers.request_tumour_profile()
                    return { status: 'applied' }
                case 'load_case': {
                    const id = String(action.case_id ?? '')
                    if (!isKnownCaseId(id)) return { status: 'failed', detail: 'unknown case' }
                    handlers.load_example_case(id)
                    return { status: 'applied' }
                }
                case 'score_patient':
                    handlers.score_patient()
                    return { status: 'applied' }
                case 'explain_for_clinician':
                    handlers.explain_for_clinician()
                    return { status: 'applied' }
                case 'show_model_quality':
                    handlers.show_model_quality()
                    return { status: 'applied' }
                case 'show_treatment_evidence':
                    handlers.show_treatment_evidence()
                    return { status: 'applied' }
                case 'show_treatment_context':
                    handlers.show_treatment_context()
                    return { status: 'applied' }
                case 'show_driver_biology':
                    handlers.show_driver_biology()
                    return { status: 'applied' }
                case 'reuse_previous_analysis': {
                    const id = String(action.result_id ?? '')
                    if (!id) return { status: 'failed', detail: 'missing result id' }
                    handlers.reuse_previous_analysis(id)
                    return { status: 'applied' }
                }
                case 'run_analysis': {
                    const q = String(action.query ?? '').trim()
                    if (!q) return { status: 'failed', detail: 'missing query' }
                    if (analysisRunning) {
                        return { status: 'failed', detail: 'an analysis is already running' }
                    }
                    const genes = Array.isArray(action.candidate_genes)
                        ? (action.candidate_genes as unknown[]).map(String)
                        : undefined
                    handlers.run_survival_analysis(q, genes)
                    return { status: 'applied' }
                }
                default:
                    return { status: 'declined', detail: 'unknown action' }
            }
        } catch (err) {
            return { status: 'failed', detail: err instanceof Error ? err.message : 'execution error' }
        }
    }

    return { execute, needsConfirmation }
}
