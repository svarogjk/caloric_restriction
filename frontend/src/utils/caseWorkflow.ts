// The clinical console's workflow state, DERIVED from the chart rather than
// stored alongside it.
//
// Why derived: the console previously had no single notion of "where we are", so
// the UI and the agent's system prompt each guessed independently — and disagreed
// (backend/app/services/chat/pydantic_ai_service.py appended two competing
// "MISSING:" ladders to the same prompt). Everything here is a pure function of
// state that already exists, so the side rail, the in-thread next-step card and
// the agent's prompt cannot drift apart.
//
// This module deliberately takes primitives rather than ChartSource/the scoring
// hook: it stays a leaf with no runtime imports, which keeps it trivially
// testable and keeps utils/ from depending on components/.

import { PredictResponse } from '../services/api'
import { ExpressionFeedback } from './expressionFeedback'

export type WorkflowStepId = 'case' | 'profile' | 'evidence' | 'score' | 'why' | 'options'

export type StepStatus =
    /** Satisfied. */
    | 'done'
    /** Satisfied, but a scientific caveat applies to everything downstream. */
    | 'done-with-caveat'
    /** Every prerequisite is met — this is the step to do now. */
    | 'active'
    /** An earlier step has to happen first. */
    | 'blocked'
    /** A computation for this step is in flight. */
    | 'running'
    /** The chosen question does not need this step. */
    | 'not-needed'

export interface WorkflowStep {
    id: WorkflowStepId
    /** 1-based position in the full pipeline, stable regardless of the goal. */
    index: number
    label: string
    /** One line on what this step establishes — the "why am I doing this". */
    purpose: string
    status: StepStatus
    /** What is currently set, e.g. "breast · curated model" or "28 genes". */
    detail: string | null
    /** Why this step cannot run yet. Null unless status is 'blocked'. */
    blockedReason: string | null
    /** Scientific limitations that apply once this step is done. Rendered, not buried. */
    caveats: string[]
    /** The console_actions.py tool that advances this step, for the agent prompt. */
    actionTool: string | null
}

export interface WorkflowInput {
    /** ChartSource.kind — see components/console/types.ts. */
    sourceKind: 'none' | 'curated' | 'pending' | 'cohort'
    sourceLabel: string
    /** True once /api/personalize has a model_id or result_id to score against. */
    hasModel: boolean
    modelIsDemo: boolean
    feedback: ExpressionFeedback
    prediction: PredictResponse | null
    /** A cross-cohort run is in flight — the evidence step is 'running', not blocked. */
    analysisRunning: boolean
    /** Cohort provenance for the evidence step, e.g. "7 GEO cohorts". */
    evidenceDetail: string | null
    /** The run was restricted to named genes, so its p-values are nominal. */
    focusGenesUsed: boolean
    /** Steps the chosen question needs. Null = no goal picked yet, so all apply. */
    neededSteps: WorkflowStepId[] | null
    shownWhy: boolean
    shownOptions: boolean
    covariateCount: number
}

export interface WorkflowState {
    steps: WorkflowStep[]
    /** The step to do now — first 'active' or 'running'. Null when everything is settled. */
    current: WorkflowStepId | null
    /** Position for the collapsed "Step 3 of 6" summary. */
    currentIndex: number
    totalNeeded: number
    doneIds: WorkflowStepId[]
    /** Every caveat in force across the pipeline, de-duplicated, in step order. */
    caveats: string[]
}

interface StepSpec {
    id: WorkflowStepId
    label: string
    purpose: string
    /** Steps that must be done before this one can start. */
    requires: WorkflowStepId[]
    actionTool: string | null
    /** Sentence used when this step is what's blocking a later one. */
    missing: string
}

const SPECS: StepSpec[] = [
    {
        id: 'case',
        label: 'Case',
        purpose: 'Which cancer type, and therefore which validated model applies.',
        requires: [],
        actionTool: 'set_cancer_type',
        missing: 'the cancer type is not set yet',
    },
    {
        id: 'profile',
        label: 'Profile',
        purpose: 'The tumour expression values this patient is scored from.',
        requires: [],
        actionTool: 'request_tumour_profile',
        missing: 'no tumour expression profile has been provided',
    },
    {
        id: 'evidence',
        label: 'Evidence',
        purpose: 'The independent GEO cohorts the score is validated against.',
        requires: ['case'],
        actionTool: 'run_survival_analysis',
        missing: 'there is no validated model to score against',
    },
    {
        id: 'score',
        label: 'Score',
        purpose: 'Where this patient sits against that cohort reference.',
        requires: ['case', 'profile', 'evidence'],
        actionTool: 'score_patient',
        missing: 'the patient has not been scored',
    },
    {
        id: 'why',
        label: 'Why',
        purpose: 'What drives the score, and how far the model can be trusted.',
        requires: ['evidence'],
        actionTool: 'show_model_quality',
        missing: 'the model has not been examined',
    },
    {
        id: 'options',
        label: 'Options',
        purpose: 'Treatments with documented evidence, for discussion.',
        requires: ['evidence'],
        actionTool: 'show_treatment_evidence',
        missing: 'treatment evidence has not been looked up',
    },
]

export const WORKFLOW_STEP_IDS: WorkflowStepId[] = SPECS.map((s) => s.id)

/** A synthetic demo model is illustrative — it must never read as evidence. */
const DEMO_CAVEAT = 'Synthetic demo model — illustrative only, not evidence about a real cohort.'

function caseDetail(input: WorkflowInput): string | null {
    if (input.sourceKind === 'none') return null
    const parts = [input.sourceLabel]
    if (input.sourceKind === 'curated') parts.push('curated model')
    if (input.sourceKind === 'cohort') parts.push('model built from your query')
    if (input.sourceKind === 'pending') parts.push('no model yet')
    if (input.covariateCount > 0) parts.push(`${input.covariateCount} covariate${input.covariateCount === 1 ? '' : 's'}`)
    return parts.join(' · ')
}

function profileCaveats(f: ExpressionFeedback): string[] {
    const out: string[] = []
    if (f.geneCount === 0) return out
    if (!f.qnReady) {
        out.push(
            `Only ${f.geneCount} genes — rank/quantile normalisation against the reference ` +
            'distribution is unreliable below 40.',
        )
    }
    if (f.lowCoverage) {
        out.push(
            `Only ${f.signatureMatched} of ${f.signatureTotal} signature genes are present ` +
            '(<60%) — the risk score is extrapolated from a partial profile.',
        )
    }
    if (f.scaleHint === 'possibly-raw-counts') {
        out.push('Values look like raw counts — scoring expects log2-scale expression.')
    }
    return out
}

function profileDetail(f: ExpressionFeedback): string | null {
    if (f.geneCount === 0) return null
    const parts = [`${f.geneCount} genes`]
    if (f.signatureTotal > 0) parts.push(`${f.signatureMatched}/${f.signatureTotal} signature`)
    return parts.join(' · ')
}

function scoreDetail(p: PredictResponse | null): string | null {
    if (!p) return null
    return `${p.risk_group} risk · ${Math.round(p.risk_percentile)}th pct · C-index ${p.pooled_c_index.toFixed(2)}`
}

/**
 * Derive the whole pipeline from current console state.
 *
 * A step is `done` when its own evidence exists, `active` when every prerequisite
 * is done, and `blocked` otherwise — naming the first unmet prerequisite, so the
 * UI and the agent give the clinician the same sentence.
 */
export function deriveWorkflow(input: WorkflowInput): WorkflowState {
    const needed = input.neededSteps
    const isNeeded = (id: WorkflowStepId) => needed === null || needed.includes(id)

    const done: Record<WorkflowStepId, boolean> = {
        case: input.sourceKind !== 'none',
        profile: input.feedback.geneCount > 0,
        evidence: input.hasModel,
        score: input.prediction !== null,
        why: input.shownWhy,
        options: input.shownOptions,
    }

    const caveatsById: Record<WorkflowStepId, string[]> = {
        case: [],
        profile: profileCaveats(input.feedback),
        evidence: [],
        score: [],
        why: [],
        options: [],
    }

    if (input.hasModel && input.modelIsDemo) caveatsById.evidence.push(DEMO_CAVEAT)
    if (input.hasModel && input.focusGenesUsed) {
        caveatsById.evidence.push(
            'This model came from a run restricted to named genes, so its p-values are ' +
            'nominal — not multiple-testing corrected.',
        )
    }
    if (input.prediction) {
        caveatsById.score.push(
            `Scored on ${input.prediction.scored_on}; the curve shown is the reference group's, ` +
            'not a curve estimated from this one patient.',
        )
        for (const w of input.prediction.warnings ?? []) caveatsById.score.push(w)
    }
    if (done.options) {
        caveatsById.options.push(
            'Advisory and research-use-only — treatments to discuss, not a prescription. ' +
            'Treated-vs-untreated cohort curves are observational, not randomised.',
        )
    }

    const detailById: Record<WorkflowStepId, string | null> = {
        case: caseDetail(input),
        profile: profileDetail(input.feedback),
        evidence: input.hasModel ? (input.evidenceDetail ?? 'validated model ready') : null,
        score: scoreDetail(input.prediction),
        why: done.why ? 'model quality reviewed' : null,
        options: done.options ? 'documented evidence shown' : null,
    }

    const steps: WorkflowStep[] = SPECS.map((spec, i) => {
        const base = {
            id: spec.id,
            index: i + 1,
            label: spec.label,
            purpose: spec.purpose,
            detail: detailById[spec.id],
            caveats: caveatsById[spec.id],
            actionTool: spec.actionTool,
        }

        if (done[spec.id]) {
            return {
                ...base,
                status: caveatsById[spec.id].length > 0 ? ('done-with-caveat' as StepStatus) : ('done' as StepStatus),
                blockedReason: null,
            }
        }

        if (!isNeeded(spec.id)) {
            return { ...base, status: 'not-needed' as StepStatus, blockedReason: null }
        }

        if (spec.id === 'evidence' && input.analysisRunning) {
            return { ...base, status: 'running' as StepStatus, blockedReason: null, detail: 'building — 2-5 minutes' }
        }

        const unmet = spec.requires.find((r) => !done[r])
        if (unmet) {
            const blockerIndex = SPECS.findIndex((s) => s.id === unmet)
            return {
                ...base,
                status: 'blocked' as StepStatus,
                blockedReason: `Step ${blockerIndex + 1} (${SPECS[blockerIndex].label}) first — ${SPECS[blockerIndex].missing}.`,
            }
        }

        return { ...base, status: 'active' as StepStatus, blockedReason: null }
    })

    const currentStep = steps.find((s) => s.status === 'active' || s.status === 'running') ?? null
    const doneIds = steps.filter((s) => s.status === 'done' || s.status === 'done-with-caveat').map((s) => s.id)
    const neededSteps = steps.filter((s) => s.status !== 'not-needed')

    return {
        steps,
        current: currentStep?.id ?? null,
        currentIndex: currentStep ? neededSteps.findIndex((s) => s.id === currentStep.id) + 1 : neededSteps.length,
        totalNeeded: neededSteps.length,
        doneIds,
        caveats: [...new Set(steps.flatMap((s) => (s.status === 'not-needed' ? [] : s.caveats)))],
    }
}
