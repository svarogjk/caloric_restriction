import { describe, expect, it } from 'vitest'
import { parseCaseDescription } from '../caseParser'
import { SAMPLE_PATIENTS } from '../samplePatients'

// The parser must handle the app's own worked examples — if a doctor pastes
// exactly the vignette shown on a case card, it should be recognised.
describe('parseCaseDescription against the real case-library vignettes', () => {
    for (const p of SAMPLE_PATIENTS) {
        it(`recognises "${p.name}" (${p.vignette})`, () => {
            const facts = parseCaseDescription(p.vignette)
            expect(facts.looksLikeCase).toBe(true)
            expect(facts.cancerTerm).not.toBeNull()
            if (p.cancerKey) {
                expect(facts.cancerKey).toBe(p.cancerKey)
            }
        })
    }
})
