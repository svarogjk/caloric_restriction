import { describe, expect, it, vi } from 'vitest'
import { useConsoleActions, ConsoleActionHandlers } from '../useConsoleActions'

type Args = Parameters<typeof useConsoleActions>[0]

function setup(over: Partial<Args> = {}) {
    const handlers = makeHandlers()
    const actions = useConsoleActions({
        handlers, hasChart: false, isKnownCaseId: () => true, isKnownCancerKey: () => true,
        analysisRunning: false, ...over,
    })
    return { handlers, ...actions }
}

function makeHandlers(): ConsoleActionHandlers {
    return {
        set_cancer_type: vi.fn(),
        request_tumour_profile: vi.fn(),
        load_example_case: vi.fn(),
        score_patient: vi.fn(),
        explain_for_clinician: vi.fn(),
        show_model_quality: vi.fn(),
        show_treatment_evidence: vi.fn(),
        show_treatment_context: vi.fn(),
        show_driver_biology: vi.fn(),
        reuse_previous_analysis: vi.fn(),
        run_survival_analysis: vi.fn(),
    }
}

describe('useConsoleActions', () => {
    it('executes set_cancer_type for a known key', () => {
        const { handlers, execute } = setup({ hasChart: false, isKnownCaseId: () => true, isKnownCancerKey: () => true })
        const result = execute({ action: 'set_cancer_type', cancer_key: 'breast' })
        expect(result.status).toBe('applied')
        expect(handlers.set_cancer_type).toHaveBeenCalledWith('breast')
    })

    it('fails set_cancer_type for an unknown key without calling the handler', () => {
        const { handlers, execute } = setup({ hasChart: false, isKnownCaseId: () => true, isKnownCancerKey: () => false })
        const result = execute({ action: 'set_cancer_type', cancer_key: 'banana' })
        expect(result.status).toBe('failed')
        expect(handlers.set_cancer_type).not.toHaveBeenCalled()
    })

    it('fails load_case for an unknown case id', () => {
        const { handlers, execute } = setup({ hasChart: false, isKnownCaseId: () => false, isKnownCancerKey: () => true })
        const result = execute({ action: 'load_case', case_id: 'not_real' })
        expect(result.status).toBe('failed')
        expect(handlers.load_example_case).not.toHaveBeenCalled()
    })

    it('always requires confirmation for run_analysis — it costs minutes of GEO downloads', () => {
        const { needsConfirmation } = setup()
        expect(needsConfirmation({ action: 'run_analysis', query: 'gastric cancer overall survival' })).toBe(true)
    })

    it('requires confirmation for load_case only when a chart is already open', () => {
        const withChart = setup({ hasChart: true })
        const withoutChart = setup({ hasChart: false })
        const action = { action: 'load_case', case_id: 'tnbc_aggressive' }
        expect(withChart.needsConfirmation(action)).toBe(true)
        expect(withoutChart.needsConfirmation(action)).toBe(false)
    })

    it('never requires confirmation for score_patient', () => {
        const { needsConfirmation } = setup({ hasChart: true })
        expect(needsConfirmation({ action: 'score_patient' })).toBe(false)
    })

    it('declines an unrecognised action name without throwing', () => {
        const { execute } = setup()
        const result = execute({ action: 'delete_everything' })
        expect(result.status).toBe('declined')
    })

    it('fails run_analysis with an empty query', () => {
        const { handlers, execute } = setup()
        const result = execute({ action: 'run_analysis', query: '   ' })
        expect(result.status).toBe('failed')
        expect(handlers.run_survival_analysis).not.toHaveBeenCalled()
    })

    it('forwards candidate genes so a single-gene question restricts the run', () => {
        const { handlers, execute } = setup()
        execute({ action: 'run_analysis', query: 'gastric cancer survival', candidate_genes: ['MKI67'] })
        expect(handlers.run_survival_analysis).toHaveBeenCalledWith('gastric cancer survival', ['MKI67'])
    })

    // Regression: the uncurated-case path (prostate) proposes this action, and a
    // stale name would silently fall through to `declined` — the dead end again.
    it('executes the run_analysis name that loadCase proposes', () => {
        const { handlers, execute } = setup()
        const result = execute({ action: 'run_analysis', query: 'prostate cancer overall survival' })
        expect(result.status).toBe('applied')
        expect(handlers.run_survival_analysis).toHaveBeenCalledWith('prostate cancer overall survival', undefined)
    })

    it('refuses a second analysis while one is already running', () => {
        const { handlers, execute } = setup({ analysisRunning: true })
        const result = execute({ action: 'run_analysis', query: 'lung cancer survival' })
        expect(result.status).toBe('failed')
        expect(result.detail).toMatch(/already running/)
        expect(handlers.run_survival_analysis).not.toHaveBeenCalled()
    })
})
