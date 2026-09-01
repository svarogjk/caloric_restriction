import { describe, it, expect } from 'vitest'
import {
    pValueLabel, summariseAnalysis, directionConcordance, bestKmDataset, resolveTimeUnit,
} from '../analysisSummary'
import {
    SurvivalAnalysisResponse as AnalysisResult, GeneSurvivalResponse, GeneDatasetResult, KMCurveData,
} from '../../services/api'

const km = (n: number): KMCurveData => ({
    times: [0, 10, 20], survival_probabilities: [1, 0.8, 0.6],
    ci_lower: null, ci_upper: null, n_samples: n, n_events: Math.floor(n / 3),
})

const ds = (id: string, n: number, opts: Partial<GeneDatasetResult> = {}): GeneDatasetResult => ({
    dataset_id: id, dataset_title: id, hazard_ratio: 1.8,
    hazard_ratio_ci_lower: 1.2, hazard_ratio_ci_upper: 2.6,
    cox_p_value: 0.004, log_rank_p_value: 0.005, risk_direction: 'high_risk',
    n_samples: n, median_survival_high: null, median_survival_low: null,
    km_curve_high: km(n), km_curve_low: km(n), ...opts,
})

const gene = (symbol: string, over: Partial<GeneSurvivalResponse> = {}): GeneSurvivalResponse => ({
    gene_id: symbol, gene_symbol: symbol, n_datasets: 3,
    avg_hazard_ratio: 1.8, avg_cox_p_value: 0.004, avg_log_rank_p_value: 0.005,
    predominant_risk: 'high_risk', risk_direction_consistency: 1,
    datasets: ['GSE1', 'GSE2', 'GSE3'],
    per_dataset_results: [ds('GSE1', 100), ds('GSE2', 250), ds('GSE3', 80)],
    min_fdr_adjusted_p_value: 0.02, ...over,
})

const analysis = (genes: GeneSurvivalResponse[], diagnostics?: AnalysisResult['diagnostics']): AnalysisResult => ({
    query: 'gastric cancer overall survival', n_datasets_analyzed: 8,
    n_datasets_with_survival: 5, common_genes: genes, processing_time: 142, timestamp: '',
    diagnostics,
})

describe('pValueLabel', () => {
    // The whole point: BH over one hypothesis is a no-op, so the stored
    // "FDR" number equals the nominal p and must not be called a q-value.
    it('reports a nominal p when a gene filter restricted the run', () => {
        const out = pValueLabel(gene('MKI67'), analysis([gene('MKI67')], {
            datasets_analyzed: 8, datasets_with_genes: 5, n_genes_tested: 1, gene_filter_applied: true,
        }))
        expect(out.label).toBe('nominal Cox p')
        expect(out.value).toBe(0.004)
        expect(out.caption).toMatch(/not multiple-testing corrected/)
    })

    it('reports an FDR q for a genome-wide run', () => {
        const out = pValueLabel(gene('MKI67'), analysis([gene('MKI67')], {
            datasets_analyzed: 8, datasets_with_genes: 5, n_genes_tested: 19000, gene_filter_applied: false,
        }))
        expect(out.label).toBe('FDR q')
        expect(out.value).toBe(0.02)
        expect(out.caption).toMatch(/19,000/)
    })

    it('treats a single tested gene as restricted even if the flag is missing', () => {
        const out = pValueLabel(gene('MKI67'), analysis([gene('MKI67')], {
            datasets_analyzed: 1, datasets_with_genes: 1, n_genes_tested: 1,
        }))
        expect(out.label).toBe('nominal Cox p')
    })

    it('never claims FDR on a result saved before diagnostics existed', () => {
        const g = gene('MKI67', { min_fdr_adjusted_p_value: undefined })
        const out = pValueLabel(g, analysis([g]))
        expect(out.label).toBe('avg Cox p')
        expect(out.caption).toBeNull()
    })
})

describe('summariseAnalysis', () => {
    it('focuses on the named gene and keeps the rest out', () => {
        const s = summariseAnalysis(analysis([gene('MKI67'), gene('TP53')]), ['MKI67'])
        expect(s.isFocused).toBe(true)
        expect(s.genes.map((g) => g.gene_symbol)).toEqual(['MKI67'])
        expect(s.nGenes).toBe(2)
        expect(s.missingFocusGenes).toEqual([])
    })

    it('matches focus genes case-insensitively', () => {
        const s = summariseAnalysis(analysis([gene('MKI67')]), ['mki67'])
        expect(s.genes).toHaveLength(1)
    })

    it('reports a focus gene the run did not return', () => {
        const s = summariseAnalysis(analysis([gene('TP53')]), ['MKI67'])
        expect(s.genes).toEqual([])
        expect(s.missingFocusGenes).toEqual(['MKI67'])
    })

    it('lists every gene for a discovery question', () => {
        const s = summariseAnalysis(analysis([gene('MKI67'), gene('TP53')]))
        expect(s.isFocused).toBe(false)
        expect(s.genes).toHaveLength(2)
    })

    it('counts predictive genes', () => {
        const s = summariseAnalysis(analysis([gene('A', { is_predictive: true }), gene('B')]))
        expect(s.nPredictive).toBe(1)
    })
})

describe('bestKmDataset / resolveTimeUnit / directionConcordance', () => {
    it('picks the largest cohort that has both curves', () => {
        expect(bestKmDataset(gene('MKI67'))?.dataset_id).toBe('GSE2')
    })

    it('ignores cohorts missing a curve', () => {
        const g = gene('MKI67', { per_dataset_results: [ds('GSE1', 100), ds('GSE2', 900, { km_curve_low: null })] })
        expect(bestKmDataset(g)?.dataset_id).toBe('GSE1')
    })

    it('returns null when no cohort has curves', () => {
        expect(bestKmDataset(gene('MKI67', { per_dataset_results: null }))).toBeNull()
    })

    it('falls back to days when the unit predates the field', () => {
        expect(resolveTimeUnit(ds('GSE1', 10))).toBe('days')
        expect(resolveTimeUnit(ds('GSE1', 10, { survival_time_unit: 'months' }))).toBe('months')
        expect(resolveTimeUnit(null)).toBe('days')
    })

    it('converts consistency into a cohort count', () => {
        expect(directionConcordance(gene('MKI67', { n_datasets: 4, risk_direction_consistency: 0.75 }))).toBe(3)
    })
})
