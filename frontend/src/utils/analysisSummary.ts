// Pure derivations over an AnalysisResult, kept out of the card so they can be
// unit-tested (the frontend test setup is node-only — no jsdom, no renderer).
import {
    SurvivalAnalysisResponse as AnalysisResult,
    GeneSurvivalResponse,
    GeneDatasetResult,
    KMCurveData,
} from '../services/api'

/** I² is unstable and effectively uninterpretable with only a couple of cohorts. */
export const MIN_DATASETS_FOR_I2 = 3

export interface PValueLabel {
    /** The number to show. */
    value: number | null
    /** What it may honestly be called. */
    label: string
    /** Longer caption; null when the plain label needs no qualification. */
    caption: string | null
}

/**
 * Decide what a gene's p-value may be CALLED.
 *
 * `gene_filter` restricts the tested set before Cox testing, so a one-gene run
 * hands Benjamini-Hochberg a single hypothesis — and BH over n=1 returns the
 * input unchanged. The stored `fdr_adjusted_p_value` is then numerically equal
 * to the nominal Cox p, and calling it an FDR q-value would be a false claim
 * about multiplicity correction.
 *
 * Reporting a nominal p for one pre-specified gene is legitimate; mislabelling
 * it is not. The decision is driven by `diagnostics`, never inferred from how
 * many genes came back.
 */
export function pValueLabel(gene: GeneSurvivalResponse, result: AnalysisResult): PValueLabel {
    const restricted = result.diagnostics?.gene_filter_applied === true
        || (result.diagnostics?.n_genes_tested ?? 0) === 1

    if (restricted) {
        return {
            value: gene.avg_cox_p_value ?? null,
            label: 'nominal Cox p',
            caption: 'single pre-specified gene — not multiple-testing corrected',
        }
    }
    const q = gene.min_fdr_adjusted_p_value
    if (q == null) {
        return { value: gene.avg_cox_p_value ?? null, label: 'avg Cox p', caption: null }
    }
    return {
        value: q,
        label: 'FDR q',
        caption: result.diagnostics?.n_genes_tested
            ? `Benjamini-Hochberg across ${result.diagnostics.n_genes_tested.toLocaleString()} genes tested`
            : 'Benjamini-Hochberg across all genes tested',
    }
}

/** How many of this gene's cohorts agree with its predominant direction. */
export function directionConcordance(gene: GeneSurvivalResponse): number {
    return Math.round((gene.risk_direction_consistency ?? 0) * gene.n_datasets)
}

/** The cohort with the most samples that actually carries both KM curves. */
export function bestKmDataset(gene: GeneSurvivalResponse): GeneDatasetResult | null {
    const usable = (gene.per_dataset_results ?? []).filter(
        (d) => d.km_curve_high?.times?.length && d.km_curve_low?.times?.length,
    )
    if (usable.length === 0) return null
    return usable.reduce((best, d) => (d.n_samples > best.n_samples ? d : best))
}

/** Recharts-ready pair for one cohort's high/low expression split. */
export function kmCurvePair(ds: GeneDatasetResult, geneLabel: string) {
    const mk = (curve: KMCurveData, label: string, color: string, dashed: boolean) => ({
        key: `${ds.dataset_id}-${label}`,
        label: `${geneLabel} ${label} (n=${curve.n_samples})`,
        times: curve.times,
        survival_probabilities: curve.survival_probabilities,
        ci_lower: curve.ci_lower,
        ci_upper: curve.ci_upper,
        color,
        dashed,
    })
    return [
        mk(ds.km_curve_high!, 'high', '#ef4444', false),
        mk(ds.km_curve_low!, 'low', '#3b82f6', true),
    ]
}

/** `survival_time_unit` is absent on results saved before it was plumbed
 *  through; 'days' is what timesToYears() assumes in that case. */
export function resolveTimeUnit(ds: GeneDatasetResult | null): 'days' | 'months' | 'years' {
    const u = ds?.survival_time_unit
    return u === 'months' || u === 'years' ? u : 'days'
}

export interface AnalysisSummary {
    /** The genes to show, focus genes first when the question named any. */
    genes: GeneSurvivalResponse[]
    /** Focus genes the run did NOT return — an answer in itself. */
    missingFocusGenes: string[]
    /** True when the question was about specific named genes. */
    isFocused: boolean
    nGenes: number
    nPredictive: number
    nDatasets: number
    nDatasetsWithSurvival: number
    processingTime: number
}

/**
 * Split an analysis into the shape the card renders.
 *
 * A question naming specific genes ("does high MKI67 predict worse survival?")
 * is a hypothesis test and gets a focused readout; an open question is
 * discovery and gets the ranked list.
 */
export function summariseAnalysis(result: AnalysisResult, focusGenes: string[] = []): AnalysisSummary {
    const all = result.common_genes ?? []
    const wanted = focusGenes.map((g) => g.trim().toUpperCase()).filter(Boolean)

    const matches = wanted.length
        ? all.filter((g) => wanted.includes((g.gene_symbol ?? g.gene_id).toUpperCase()))
        : []
    const found = new Set(matches.map((g) => (g.gene_symbol ?? g.gene_id).toUpperCase()))

    return {
        genes: wanted.length ? matches : all,
        missingFocusGenes: wanted.filter((w) => !found.has(w)),
        isFocused: wanted.length > 0,
        nGenes: all.length,
        nPredictive: all.filter((g) => g.is_predictive).length,
        nDatasets: result.n_datasets_analyzed,
        nDatasetsWithSurvival: result.n_datasets_with_survival,
        processingTime: result.processing_time,
    }
}
