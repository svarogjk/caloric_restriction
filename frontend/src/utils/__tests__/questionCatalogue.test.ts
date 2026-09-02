import { describe, it, expect } from 'vitest'
import {
    QUESTION_CATALOGUE, matchQuestion, getQuestion, fillTemplate, isTemplateReady,
} from '../questionCatalogue'
import { WORKFLOW_STEP_IDS } from '../caseWorkflow'

describe('QUESTION_CATALOGUE', () => {
    it('has unique ids', () => {
        const ids = QUESTION_CATALOGUE.map((q) => q.id)
        expect(new Set(ids).size).toBe(ids.length)
    })

    // A question whose steps aren't real pipeline steps would render an empty
    // workflow map and silently promise something the app can't run.
    it('only references real workflow steps', () => {
        for (const q of QUESTION_CATALOGUE) {
            expect(q.steps.length).toBeGreaterThan(0)
            for (const step of q.steps) expect(WORKFLOW_STEP_IDS).toContain(step)
        }
    })

    it('always includes the evidence step — nothing is answered without cohorts', () => {
        for (const q of QUESTION_CATALOGUE) expect(q.steps).toContain('evidence')
    })

    it('marks patient-dependent questions as needing the profile step', () => {
        for (const q of QUESTION_CATALOGUE) {
            expect(q.steps.includes('profile')).toBe(q.needsPatient)
        }
    })

    it('declares every placeholder its template actually uses', () => {
        for (const q of QUESTION_CATALOGUE) {
            for (const name of ['gene', 'cancer'] as const) {
                const used = q.template.includes(`{${name}}`)
                expect(q.placeholders.includes(name)).toBe(used)
            }
        }
    })
})

describe('matchQuestion', () => {
    it('ignores empty or trivial input', () => {
        expect(matchQuestion('')).toBeNull()
        expect(matchQuestion('  ')).toBeNull()
        expect(matchQuestion('hi')).toBeNull()
    })

    it('maps a risk question', () => {
        expect(matchQuestion('is she high risk?')?.question.id).toBe('risk')
    })

    it('maps a treatment question — the phrasing a clinician actually uses', () => {
        expect(matchQuestion('will she benefit from chemo?')?.question.id).toBe('treatment')
        expect(matchQuestion('what therapy should we discuss')?.question.id).toBe('treatment')
    })

    it('maps a model-trust question', () => {
        expect(matchQuestion('how good is this model?')?.question.id).toBe('trust')
        expect(matchQuestion('which cohorts is it validated on')?.question.id).toBe('trust')
    })

    it('maps a single-gene hypothesis question', () => {
        expect(matchQuestion('is MKI67 prognostic in breast cancer?')?.question.id).toBe('gene')
    })

    it('maps an open discovery question', () => {
        expect(matchQuestion('which genes predict survival in gastric cancer?')?.question.id).toBe('discovery')
    })

    it('returns null for something the app cannot answer', () => {
        expect(matchQuestion('what should I tell the family about hospice')).toBeNull()
    })
})

describe('fillTemplate', () => {
    const gene = getQuestion('gene')!

    it('substitutes and upper-cases a gene symbol', () => {
        expect(fillTemplate(gene, { gene: 'mki67', cancer: 'breast cancer' })).toContain('MKI67')
        expect(fillTemplate(gene, { gene: 'mki67', cancer: 'breast cancer' })).toContain('breast cancer')
    })

    // Never invent a value the clinician did not supply — leave it visibly unfilled.
    it('leaves an unsupplied placeholder visible', () => {
        expect(fillTemplate(gene, { gene: 'TP53' })).toContain('{cancer}')
        expect(isTemplateReady(gene, { gene: 'TP53' })).toBe(false)
        expect(isTemplateReady(gene, { gene: 'TP53', cancer: 'lung' })).toBe(true)
    })

    it('treats a question with no placeholders as always ready', () => {
        expect(isTemplateReady(getQuestion('risk')!, {})).toBe(true)
    })
})
