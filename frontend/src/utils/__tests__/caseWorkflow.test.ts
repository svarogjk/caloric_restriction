import { describe, it, expect } from 'vitest'
import { deriveWorkflow, WorkflowInput, WorkflowStepId } from '../caseWorkflow'
import { analyseExpression, ExpressionFeedback } from '../expressionFeedback'
import { PredictResponse } from '../../services/api'

const EMPTY_FEEDBACK = analyseExpression('')

/** 45 genes: over QN_MIN_GENES, so no "too few genes" caveat fires. */
const RICH_FEEDBACK: ExpressionFeedback = analyseExpression(
    Array.from({ length: 45 }, (_, i) => `GENE${i} ${(i % 12) + 4}`).join('\n'),
)

const PREDICTION = {
    risk_group: 'high',
    risk_percentile: 82,
    pooled_c_index: 0.71,
    scored_on: 'combined',
    warnings: [],
} as unknown as PredictResponse

const base: WorkflowInput = {
    sourceKind: 'none',
    sourceLabel: '',
    hasModel: false,
    modelIsDemo: false,
    feedback: EMPTY_FEEDBACK,
    prediction: null,
    analysisRunning: false,
    evidenceDetail: null,
    focusGenesUsed: false,
    neededSteps: null,
    shownWhy: false,
    shownOptions: false,
    covariateCount: 0,
}

const statusOf = (input: WorkflowInput, id: WorkflowStepId) =>
    deriveWorkflow(input).steps.find((s) => s.id === id)!

describe('deriveWorkflow', () => {
    it('starts on the case step with nothing loaded', () => {
        const w = deriveWorkflow(base)
        expect(w.current).toBe('case')
        expect(w.doneIds).toEqual([])
        expect(statusOf(base, 'case').status).toBe('active')
    })

    it('blocks later steps by naming the first unmet prerequisite', () => {
        const score = statusOf(base, 'score')
        expect(score.status).toBe('blocked')
        expect(score.blockedReason).toMatch(/Step 1 \(Case\)/)
    })

    // Profile has no prerequisites: a clinician may paste the expression before
    // choosing a cancer type, and blocking that would be a lie about the API.
    it('lets the profile be provided before the cancer type', () => {
        const input = { ...base, feedback: RICH_FEEDBACK }
        expect(statusOf(input, 'profile').status).toBe('done')
        expect(deriveWorkflow(input).current).toBe('case')
    })

    it('advances to evidence once the case and profile are in but no model exists', () => {
        const input: WorkflowInput = {
            ...base, sourceKind: 'pending', sourceLabel: 'Prostate', feedback: RICH_FEEDBACK,
        }
        expect(deriveWorkflow(input).current).toBe('evidence')
        expect(statusOf(input, 'evidence').status).toBe('active')
    })

    // `current` is the earliest unfinished step, so an unmet profile still comes
    // first even though evidence is independently unblocked.
    it('points at the profile before evidence when no expression is pasted', () => {
        const input: WorkflowInput = { ...base, sourceKind: 'pending', sourceLabel: 'Prostate' }
        expect(deriveWorkflow(input).current).toBe('profile')
        expect(statusOf(input, 'evidence').status).toBe('active')
    })

    it('reports a cohort build in flight as running, not blocked', () => {
        const input: WorkflowInput = {
            ...base,
            sourceKind: 'pending', sourceLabel: 'Prostate', feedback: RICH_FEEDBACK, analysisRunning: true,
        }
        const evidence = statusOf(input, 'evidence')
        expect(evidence.status).toBe('running')
        expect(evidence.detail).toMatch(/2-5 minutes/)
        expect(deriveWorkflow(input).current).toBe('evidence')
    })

    it('reaches score once case, profile and evidence are all done', () => {
        const input: WorkflowInput = {
            ...base,
            sourceKind: 'curated', sourceLabel: 'Breast cancer', hasModel: true, feedback: RICH_FEEDBACK,
        }
        expect(deriveWorkflow(input).current).toBe('score')
        expect(statusOf(input, 'score').status).toBe('active')
    })
})

describe('deriveWorkflow — goal scoping', () => {
    // The defect this fixes: with no patient loaded the agent used to be told both
    // "call run_survival_analysis" AND "tumour profile missing" by two independent
    // MISSING ladders in the system prompt.
    it('marks patient steps not-needed for a cohort-only question', () => {
        const input: WorkflowInput = { ...base, neededSteps: ['case', 'evidence'] }
        expect(statusOf(input, 'profile').status).toBe('not-needed')
        expect(statusOf(input, 'score').status).toBe('not-needed')
        expect(statusOf(input, 'options').status).toBe('not-needed')
        expect(deriveWorkflow(input).totalNeeded).toBe(2)
    })

    it('never downgrades a step that is already done to not-needed', () => {
        const input: WorkflowInput = { ...base, feedback: RICH_FEEDBACK, neededSteps: ['case', 'evidence'] }
        expect(statusOf(input, 'profile').status).toBe('done')
    })

    it('counts position only among the steps the goal needs', () => {
        const input: WorkflowInput = {
            ...base, sourceKind: 'curated', sourceLabel: 'Breast', neededSteps: ['case', 'evidence', 'why'],
        }
        const w = deriveWorkflow(input)
        expect(w.current).toBe('evidence')
        expect(w.currentIndex).toBe(2)
        expect(w.totalNeeded).toBe(3)
    })
})

describe('deriveWorkflow — scientific caveats', () => {
    it('flags a thin profile as done-with-caveat, not plain done', () => {
        const input: WorkflowInput = { ...base, feedback: analyseExpression('TP53 8.2\nMKI67 5.1') }
        const profile = statusOf(input, 'profile')
        expect(profile.status).toBe('done-with-caveat')
        expect(profile.caveats.join(' ')).toMatch(/below 40/)
    })

    it('flags raw-count scale', () => {
        const input: WorkflowInput = { ...base, feedback: analyseExpression('TP53 41000\nMKI67 9200') }
        expect(statusOf(input, 'profile').caveats.join(' ')).toMatch(/raw counts/)
    })

    it('marks a demo model as illustrative, not evidence', () => {
        const input: WorkflowInput = {
            ...base, sourceKind: 'curated', sourceLabel: 'Breast', hasModel: true, modelIsDemo: true,
        }
        const evidence = statusOf(input, 'evidence')
        expect(evidence.status).toBe('done-with-caveat')
        expect(evidence.caveats.join(' ')).toMatch(/not evidence/)
        expect(deriveWorkflow(input).caveats.join(' ')).toMatch(/Synthetic demo model/)
    })

    it('labels a gene-restricted run as nominal rather than FDR-adjusted', () => {
        const input: WorkflowInput = {
            ...base, sourceKind: 'cohort', sourceLabel: 'q', hasModel: true, focusGenesUsed: true,
        }
        expect(statusOf(input, 'evidence').caveats.join(' ')).toMatch(/nominal/)
    })

    // A KM curve is a population estimator; the app must never imply it drew one
    // for a single patient (clinical-positioning skill §6).
    it('states the curve is the reference group’s, not the patient’s', () => {
        const input: WorkflowInput = {
            ...base,
            sourceKind: 'curated', sourceLabel: 'Breast', hasModel: true,
            feedback: RICH_FEEDBACK, prediction: PREDICTION,
        }
        const score = statusOf(input, 'score')
        expect(score.status).toBe('done-with-caveat')
        expect(score.caveats.join(' ')).toMatch(/reference group/)
        expect(score.detail).toMatch(/high risk · 82th pct · C-index 0\.71/)
    })

    it('carries the advisory notice once treatment options are shown', () => {
        const input: WorkflowInput = {
            ...base, sourceKind: 'curated', sourceLabel: 'Breast', hasModel: true, shownOptions: true,
        }
        expect(statusOf(input, 'options').caveats.join(' ')).toMatch(/research-use-only/)
        expect(statusOf(input, 'options').caveats.join(' ')).toMatch(/not randomised/)
    })

    // Done beats not-needed: a thin profile is still a thin profile even when the
    // chosen question does not depend on it, so its caveat must not be suppressed.
    it('keeps caveats from a done step the goal does not list', () => {
        const input: WorkflowInput = {
            ...base,
            feedback: analyseExpression('TP53 8.2'),
            neededSteps: ['case', 'evidence'],
        }
        expect(statusOf(input, 'profile').status).toBe('done-with-caveat')
        expect(deriveWorkflow(input).caveats.join(' ')).toMatch(/below 40/)
    })
})
