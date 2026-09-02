// The questions this app can actually answer, each bound to a concrete pipeline.
//
// The point is honesty about capability: a free-text question used to go straight
// to the LLM, so anything outside the app's reach came back as generic prose with
// no computation behind it (the failure mode .claude/rules/chat_agent.md calls
// "a response that could have come from ChatGPT"). Every entry here maps onto
// endpoints that exist, and onto the workflow steps that have to run first.
//
// Matching is deliberately deterministic regex, not an LLM classifier: the
// mapping is shown to the clinician for confirmation, and a classifier that is
// itself a language model would just move the guessing one layer down.
//
// Mirrored (ids only) by _QUESTION_IDS in
// backend/app/services/chat/console_actions.py — see the note there.

import { WorkflowStepId } from './caseWorkflow'

export type QuestionId = 'risk' | 'drivers' | 'trust' | 'treatment' | 'regimens' | 'gene' | 'discovery'

export interface AnswerableQuestion {
    id: QuestionId
    /** Shown to the clinician, in their words. */
    label: string
    /** What the app actually produces — no promises the endpoints can't keep. */
    delivers: string
    /** The turn sent to the agent. May contain {gene} / {cancer} placeholders. */
    template: string
    /** Pipeline steps this question needs; everything else is marked not-needed. */
    steps: WorkflowStepId[]
    /** False for questions answerable with no tumour profile at all. */
    needsPatient: boolean
    /** Placeholder names the caller must fill before sending. */
    placeholders: ('gene' | 'cancer')[]
    /**
     * Tie-break when two entries match equally well. Higher = more specific.
     * "is MKI67 prognostic in breast cancer?" fires both `risk` (\bprognos) and
     * `gene`; the concrete single-gene run is the better reading, and relying on
     * catalogue order to settle that would be invisible to whoever edits it next.
     */
    priority: number
    match: RegExp[]
}

export const QUESTION_CATALOGUE: AnswerableQuestion[] = [
    {
        id: 'risk',
        label: 'How high is this patient’s risk?',
        delivers: 'Risk group and percentile against the cohort reference, with the model’s C-index.',
        template:
            'How high is this patient’s risk on the validated model for this cancer type? ' +
            'Give the risk group, the percentile, and how well the model discriminates.',
        steps: ['case', 'profile', 'evidence', 'score'],
        needsPatient: true,
        placeholders: [],
        priority: 1,
        match: [/\brisk\b/i, /\bprognos/i, /how (bad|serious|aggressive)/i, /\bsurvival chance/i, /\boutlook\b/i],
    },
    {
        id: 'drivers',
        label: 'Which genes drive this risk, and what biology?',
        delivers: 'Top risk-increasing and protective signature genes, plus pathway/GO enrichment for them.',
        template:
            'Which genes are driving this patient’s risk score, and what biological programme do they represent?',
        steps: ['case', 'profile', 'evidence', 'score', 'why'],
        needsPatient: true,
        placeholders: [],
        priority: 2,
        match: [/\bwhich genes?\b/i, /\bdriv/i, /\bwhy .*(score|risk)/i, /\bpathway/i, /\bbiology\b/i, /\bmechanis/i],
    },
    {
        id: 'trust',
        label: 'How trustworthy is this model?',
        delivers: 'Training and validation cohorts (GSE accessions), per-cohort C-index, nomogram, and concordance with established signatures.',
        template:
            'How trustworthy is this model? Which GEO cohorts is it trained and validated on, ' +
            'what is its C-index per cohort, and how does it compare with established signatures?',
        steps: ['case', 'evidence', 'why'],
        needsPatient: false,
        placeholders: [],
        priority: 3,
        match: [/\btrust/i, /\bhow good\b/i, /\bc-?index\b/i, /\bvalidat/i, /\breliab/i, /\baccura/i, /\bwhich cohorts?\b/i],
    },
    {
        id: 'treatment',
        label: 'What treatments have documented evidence for this profile?',
        delivers: 'CIViC/DGIdb biomarker→therapy records for the risk-driving genes, with treated-vs-untreated cohort curves. Advisory, research use only.',
        template:
            'What treatments have documented biomarker evidence for this patient’s profile? ' +
            'Show the evidence sources and the cohort outcomes behind them.',
        steps: ['case', 'profile', 'evidence', 'score', 'options'],
        needsPatient: true,
        placeholders: [],
        priority: 2,
        match: [/\btreatment/i, /\btherap/i, /\bdrug/i, /\bchemo/i, /\bregimen\b/i, /\bwhat .*(give|offer)/i],
    },
    {
        id: 'regimens',
        label: 'How do documented treatment cohorts compare here?',
        delivers: 'Per-treatment risk group and reference KM curves from GEO cohorts where each regimen was documented. Observational, not randomised.',
        template:
            'How do outcomes compare across the documented treatment cohorts for this cancer type, ' +
            'and which risk group does this patient fall into within each one?',
        steps: ['case', 'profile', 'evidence', 'options'],
        needsPatient: true,
        placeholders: [],
        priority: 4,
        match: [/\bcompare\b.*\btreatment/i, /\btreatment cohort/i, /\bacross (treatments|regimens)/i, /\bwhich regimen/i],
    },
    {
        id: 'gene',
        label: 'Is a specific gene prognostic or predictive here?',
        delivers: 'A cross-cohort run restricted to that gene: per-dataset HR, log-rank p, and the expression×treatment interaction test. P-values are nominal, not FDR-adjusted.',
        template:
            'Is {gene} prognostic or predictive in {cancer}? Report the per-cohort hazard ratios, ' +
            'the pooled effect, and the expression×treatment interaction where the cohorts support it.',
        steps: ['case', 'evidence'],
        needsPatient: false,
        placeholders: ['gene', 'cancer'],
        priority: 5,
        match: [/\bis\s+[A-Z0-9]{2,10}\s+(prognostic|predictive)/i, /\bdoes\s+(high|low)\s+[A-Z0-9]{2,10}/i, /\binteraction\b/i],
    },
    {
        id: 'discovery',
        label: 'Which genes predict survival in a cancer type?',
        delivers: 'An open cross-cohort discovery run: genes ranked by consistency across independent GEO cohorts, with forest plots and I².',
        template:
            'Which genes predict survival in {cancer}? Rank them by consistency across independent GEO cohorts.',
        steps: ['case', 'evidence'],
        needsPatient: false,
        placeholders: ['cancer'],
        priority: 5,
        match: [/\bwhich genes?\b.*\b(predict|associated)/i, /\bdiscover/i, /\bfind genes?\b/i, /\bbiomarkers? for\b/i],
    },
]

export function getQuestion(id: QuestionId): AnswerableQuestion | undefined {
    return QUESTION_CATALOGUE.find((q) => q.id === id)
}

export interface QuestionMatch {
    question: AnswerableQuestion
    /** Number of patterns that fired — a crude confidence, shown as nothing more. */
    hits: number
}

/**
 * Best catalogue entry for a free-text question, or null when nothing matches.
 *
 * Ranked by how many patterns fired, then by `priority` — so a broad entry like
 * `risk` never beats a specific one like `gene` just by appearing first in the
 * array. Never used to rewrite what the clinician typed: the caller shows the
 * mapping and asks.
 */
export function matchQuestion(text: string): QuestionMatch | null {
    const trimmed = text.trim()
    if (trimmed.length < 3) return null

    let best: QuestionMatch | null = null
    for (const question of QUESTION_CATALOGUE) {
        const hits = question.match.filter((re) => re.test(trimmed)).length
        if (hits === 0) continue
        if (best === null || hits > best.hits || (hits === best.hits && question.priority > best.question.priority)) {
            best = { question, hits }
        }
    }
    return best
}

/** Fill {gene} / {cancer} placeholders. Unfilled ones are left visible, never invented. */
export function fillTemplate(question: AnswerableQuestion, vars: { gene?: string; cancer?: string }): string {
    return question.template
        .replace(/\{gene\}/g, vars.gene?.trim().toUpperCase() || '{gene}')
        .replace(/\{cancer\}/g, vars.cancer?.trim() || '{cancer}')
}

/** True once every placeholder the template needs has a value. */
export function isTemplateReady(question: AnswerableQuestion, vars: { gene?: string; cancer?: string }): boolean {
    return question.placeholders.every((p) => !!vars[p]?.trim())
}
