import { describe, expect, it } from 'vitest'
import { parseCaseDescription } from '../caseParser'

describe('parseCaseDescription', () => {
    it('extracts cancer type, age, stage, and grade from a tumour-board vignette', () => {
        const facts = parseCaseDescription('64F, ER+/PR+/HER2−, invasive ductal breast cancer, pT2N0, grade 2, Ki-67 ~10%')
        expect(facts.cancerKey).toBe('breast')
        expect(facts.cancerTerm).toBe('breast')
        expect(facts.covariates.age).toBe('64')
        expect(facts.covariates.stage).toBe('T2N0')
        expect(facts.covariates.grade).toBe('2')
        expect(facts.covariates.ki67).toBe('10')
        expect(facts.looksLikeCase).toBe(true)
    })

    it('recognises a cancer type with no curated model as cancerTerm with a null cancerKey', () => {
        const facts = parseCaseDescription('70M, prostate adenocarcinoma, Gleason 4+3=7, pT3a, PSA 14')
        expect(facts.cancerTerm).toBe('prostate')
        expect(facts.cancerKey).toBeNull()
        expect(facts.looksLikeCase).toBe(true)
    })

    it('does not treat a plain question as a case description', () => {
        const facts = parseCaseDescription('What does a C-index of 0.7 mean in practice?')
        expect(facts.cancerKey).toBeNull()
        expect(facts.cancerTerm).toBeNull()
        expect(Object.keys(facts.covariates)).toHaveLength(0)
        expect(facts.looksLikeCase).toBe(false)
    })

    it('requires at least two covariates when no cancer type is mentioned', () => {
        const oneCovariate = parseCaseDescription('64 year old female patient')
        expect(oneCovariate.looksLikeCase).toBe(false)

        const twoCovariates = parseCaseDescription('64F, grade 2 tumour')
        expect(twoCovariates.looksLikeCase).toBe(true)
    })

    it('separates a residual question from the recognised clinical facts', () => {
        const facts = parseCaseDescription('64F breast cancer pT2N0 — is she high risk?')
        expect(facts.cancerKey).toBe('breast')
        expect(facts.residualText.length).toBeGreaterThan(0)
        expect(facts.residualText.toLowerCase()).toContain('is she high risk')
        // The raw sentence must never appear as a single untouched blob once facts
        // are extracted from it — this is what lets the composer send ONLY the
        // residual question, never the original text with the age embedded in it.
        expect(facts.residualText).not.toContain('64F')
        expect(facts.residualText).not.toContain('pT2N0')
    })

    it('never leaves age or stage digits in the residual text for a pure case description', () => {
        const facts = parseCaseDescription('58M, IDH-wildtype glioblastoma, MGMT unmethylated, post gross-total resection')
        expect(facts.cancerKey).toBe('glioma')
        expect(facts.covariates.age).toBe('58')
        expect(facts.residualText).not.toContain('58M')
    })

    it('matchedSpans cover exactly the substrings that produced a fact', () => {
        const text = '64F breast cancer pT2N0'
        const facts = parseCaseDescription(text)
        for (const span of facts.matchedSpans) {
            expect(text.slice(span.start, span.end).length).toBeGreaterThan(0)
        }
        const fields = facts.matchedSpans.map((s) => s.field)
        expect(fields).toContain('cancer_type')
        expect(fields).toContain('age')
        expect(fields).toContain('stage')
    })
})

import { looksIdentifying } from '../caseParser'

describe('looksIdentifying (belt-and-braces send-time gate)', () => {
    it('flags an MRN', () => {
        expect(looksIdentifying('MRN 4429301, is she high risk?')).toBe(true)
    })

    it('flags a long bare digit run', () => {
        expect(looksIdentifying('patient id 887321, high risk?')).toBe(true)
    })

    it('flags a title plus capitalised name', () => {
        expect(looksIdentifying('Mrs Smith is worried about her results')).toBe(true)
    })

    it('flags a date shaped like a DOB', () => {
        expect(looksIdentifying('DOB 04/12/1965, is she high risk?')).toBe(true)
    })

    it('does not flag an ordinary clinical question', () => {
        expect(looksIdentifying('is she high risk given a C-index of 0.74?')).toBe(false)
    })

    it('does not flag a GSE accession', () => {
        expect(looksIdentifying('validated on GSE158309 with 327 samples')).toBe(false)
    })
})
