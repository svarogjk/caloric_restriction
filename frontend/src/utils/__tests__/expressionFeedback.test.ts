import { describe, expect, it } from 'vitest'
import { analyseExpression, LOW_COVERAGE_FRAC, QN_MIN_GENES } from '../expressionFeedback'
import { parsePastedExpression } from '../signatureViz'
import { SAMPLE_PATIENTS } from '../samplePatients'

describe('analyseExpression', () => {
    it('fallback thresholds match the backend SignatureService defaults', () => {
        expect(QN_MIN_GENES).toBe(40)
        expect(LOW_COVERAGE_FRAC).toBe(0.6)
    })

    it('parses the same genes parsePastedExpression would, for a well-formed profile', () => {
        const text = 'ESR1 12.1\nPGR 11.4\nMKI67 5.8'
        const feedback = analyseExpression(text)
        expect(feedback.parsed).toEqual(parsePastedExpression(text))
        expect(feedback.geneCount).toBe(3)
        expect(feedback.skipped).toHaveLength(0)
    })

    it('flags fewer than QN_MIN_GENES as not ready for quantile normalization', () => {
        const feedback = analyseExpression('TP53 8.2\nMKI67 11.4')
        expect(feedback.geneCount).toBe(2)
        expect(feedback.qnReady).toBe(false)
    })

    it('marks a 50-gene real case profile as quantile-normalization ready', () => {
        const breastCase = SAMPLE_PATIENTS.find((p) => p.id === 'er_positive_breast')!
        const feedback = analyseExpression(breastCase.expression)
        expect(feedback.geneCount).toBe(50)
        expect(feedback.geneCount).toBeGreaterThanOrEqual(QN_MIN_GENES)
        expect(feedback.qnReady).toBe(true)
    })

    it('reports signature coverage against a supplied gene list', () => {
        const feedback = analyseExpression('ESR1 12.1\nPGR 11.4\nTP53 7.4', ['ESR1', 'PGR', 'MKI67', 'ERBB2'])
        expect(feedback.signatureTotal).toBe(4)
        expect(feedback.signatureMatched).toBe(2) // ESR1, PGR matched; MKI67, ERBB2 not provided
        expect(feedback.coverageFrac).toBeCloseTo(0.5)
        expect(feedback.lowCoverage).toBe(true) // 0.5 < LOW_COVERAGE_FRAC
    })

    it('does not flag low coverage when no signature gene list is known yet', () => {
        const feedback = analyseExpression('ESR1 12.1')
        expect(feedback.signatureTotal).toBe(0)
        expect(feedback.lowCoverage).toBe(false)
    })

    it('records why each unparseable line was skipped', () => {
        const feedback = analyseExpression('ESR1 12.1\nNOTAGENE\nMKI67 5.8\n$$$ 3.0')
        const reasons = feedback.skipped.map((s) => s.reason)
        expect(feedback.geneCount).toBe(2)
        expect(feedback.skipped.some((s) => s.text === 'NOTAGENE')).toBe(true)
        expect(reasons).toContain('no-numeric-value')
    })

    it('flags a header row distinctly from a malformed data line', () => {
        const feedback = analyseExpression('gene value\nESR1 12.1')
        const header = feedback.skipped.find((s) => s.text.toLowerCase().startsWith('gene'))
        expect(header?.reason).toBe('header-row')
    })

    it('detects likely raw counts vs. log2-scale values', () => {
        const log2 = analyseExpression('ESR1 12.1\nPGR 8.4')
        expect(log2.scaleHint).toBe('log2-like')

        const rawCounts = analyseExpression('ESR1 45210\nPGR 12890')
        expect(rawCounts.scaleHint).toBe('possibly-raw-counts')
    })

    it('flags duplicate gene symbols (case-insensitive)', () => {
        const feedback = analyseExpression('ESR1 12.1\nesr1 9.0')
        expect(feedback.duplicates).toEqual(['ESR1'])
        // Last occurrence wins, matching parsePastedExpression's plain-object semantics.
        expect(feedback.parsed.ESR1).toBe(9.0)
    })

    it('detects a pasted multi-sample matrix by column count', () => {
        const matrix = analyseExpression(
            'GENE\tSample1\tSample2\tSample3\nESR1\t12.1\t11.8\t12.4\nPGR\t11.4\t10.9\t11.1',
        )
        expect(matrix.multiColumn).toBe(true)
    })

    it('respects server-provided thresholds over the local fallback constants', () => {
        const feedback = analyseExpression('TP53 8.2\nMKI67 11.4', [], { qnMinGenes: 2 })
        expect(feedback.qnReady).toBe(true)
    })
})
