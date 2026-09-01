import { describe, it, expect } from 'vitest'
import { ChartSource, scoreDisabledReason, hasModelSource, chartResultId, chartModelId } from '../types'

const NONE: ChartSource = { kind: 'none' }
const CURATED: ChartSource = { kind: 'curated', cancerKey: 'breast', label: 'Breast cancer', modelId: 'm1', resultId: 'r1' }
const CURATED_UNBUILT: ChartSource = { kind: 'curated', cancerKey: 'gastric', label: 'Gastric', modelId: null, resultId: null }
const PENDING: ChartSource = { kind: 'pending', label: 'Prostate AR', query: 'prostate cancer overall survival' }
const COHORT: ChartSource = { kind: 'cohort', label: 'gastric cancer overall survival', query: 'gastric cancer overall survival', resultId: 'r9' }

describe('scoreDisabledReason', () => {
    it('asks for a cancer type on an empty chart', () => {
        expect(scoreDisabledReason(NONE, 0)).toMatch(/Pick a cancer type/)
        expect(scoreDisabledReason(NONE, 50)).toMatch(/Pick a cancer type/)
    })

    it('asks for expression once a curated model is available', () => {
        expect(scoreDisabledReason(CURATED, 0)).toMatch(/tumour expression profile/)
    })

    it('enables scoring once a model and at least one gene are present', () => {
        expect(scoreDisabledReason(CURATED, 1)).toBeUndefined()
        expect(scoreDisabledReason(CURATED, 84)).toBeUndefined()
    })

    // The regression this union exists for: a finished cohort build used to clear
    // cancerKey AND modelId, so the gate fell back to "Choose a cancer type first"
    // forever even though resultId was set and /api/predict would have accepted it.
    it('enables scoring after a cohort model is built', () => {
        expect(hasModelSource(COHORT)).toBe(true)
        expect(chartResultId(COHORT)).toBe('r9')
        expect(chartModelId(COHORT)).toBeNull()
        expect(scoreDisabledReason(COHORT, 84)).toBeUndefined()
    })

    it('routes an uncurated case to a cohort build rather than a dead end', () => {
        expect(hasModelSource(PENDING)).toBe(false)
        expect(scoreDisabledReason(PENDING, 84)).toMatch(/Build a cohort model/)
    })

    it('says the model is unbuilt when a curated cancer type has no model yet', () => {
        expect(scoreDisabledReason(CURATED_UNBUILT, 84)).toMatch(/still being prepared/)
    })
})
