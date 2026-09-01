import React, { useState } from 'react'
import { Card, Button, Chip } from '../../ui'
import { ForestPlot } from '../../ForestPlot'
import KaplanMeierChart from '../../KaplanMeierChart'
import PredictiveArmTable from '../../analysis/PredictiveArmTable'
import { SurvivalAnalysisResponse as AnalysisResult, GeneSurvivalResponse } from '../../../services/api'
import {
    summariseAnalysis, pValueLabel, directionConcordance, bestKmDataset, kmCurvePair,
    resolveTimeUnit, MIN_DATASETS_FOR_I2,
} from '../../../utils/analysisSummary'

interface AnalysisResultCardProps {
    result: AnalysisResult
    resultId: string | null
    /** Signature model auto-built from this result — gates treatment curves. */
    modelId: string | null
    /** Genes the question named. Non-empty ⇒ focused hypothesis test. */
    focusGenes: string[]
    onShowTreatmentEvidence: () => void
    onScorePatient: () => void
    onAsk: (question: string) => void
}

const formatP = (p: number | null): string => {
    if (p == null) return '—'
    return p < 0.001 ? p.toExponential(1) : p.toFixed(3)
}

const DirectionChip: React.FC<{ gene: GeneSurvivalResponse }> = ({ gene }) => (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
        gene.predominant_risk === 'high_risk' ? 'bg-danger-soft text-danger' : 'bg-accent-soft text-accent-fg'
    }`}>
        {gene.predominant_risk === 'high_risk' ? '↑ worse survival' : '↓ protective'}
    </span>
)

/**
 * A completed cross-cohort analysis, rendered in the conversation thread.
 *
 * Deliberately NOT `AnalysisResultsDisplay`: that component embeds PatientPanel,
 * which owns a second `usePatientScoring` instance. Mounting it beside the
 * console's own instance would give two independent /api/personalize calls and
 * let the rail and this card show different risk groups for the same patient.
 * It stays the full 7-tab view behind "Open full result", where the console is
 * not mounted. Do not "simplify" this by mounting it here.
 */
const AnalysisResultCard: React.FC<AnalysisResultCardProps> = ({
    result, resultId, modelId, focusGenes, onShowTreatmentEvidence, onScorePatient, onAsk,
}) => {
    const s = summariseAnalysis(result, focusGenes)
    const [expanded, setExpanded] = useState<string | null>(s.isFocused ? (s.genes[0]?.gene_id ?? null) : null)
    const [predictiveOnly, setPredictiveOnly] = useState(false)

    const listed = (predictiveOnly ? s.genes.filter((g) => g.is_predictive) : s.genes)
        .slice(0, s.isFocused ? undefined : 5)

    const renderGeneBody = (gene: GeneSurvivalResponse) => {
        const p = pValueLabel(gene, result)
        const kmDs = bestKmDataset(gene)
        const forestRows = gene.per_dataset_results ?? []
        const het = gene.n_datasets >= MIN_DATASETS_FOR_I2 ? gene.heterogeneity_stats : null
        const i2 = het?.i_squared

        return (
            <div className="mt-2 pt-2 border-t border-border">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[11px]">
                    <span className="text-fg-muted">
                        Pooled HR <span className="font-medium text-fg-strong">{gene.avg_hazard_ratio.toFixed(2)}</span>
                    </span>
                    <span className="text-fg-muted">
                        {p.label} <span className="font-medium text-fg-strong">{formatP(p.value)}</span>
                    </span>
                    <span className="text-fg-muted">
                        Significant in <span className="font-medium text-fg-strong">{gene.n_datasets}</span> cohorts,
                        direction concordant in {directionConcordance(gene)}
                    </span>
                </div>
                {p.caption && <p className="text-[10px] text-fg-faint mt-0.5">{p.caption}</p>}

                {kmDs ? (
                    <div className="mt-2">
                        <p className="text-[11px] text-fg-muted mb-1">
                            {kmDs.dataset_id} — largest cohort with curves (n={kmDs.n_samples})
                        </p>
                        <KaplanMeierChart
                            curves={kmCurvePair(kmDs, gene.gene_symbol ?? gene.gene_id)}
                            timeUnit={resolveTimeUnit(kmDs)}
                            height={200}
                        />
                    </div>
                ) : (
                    <p className="text-[11px] text-fg-faint mt-2">No Kaplan-Meier curves were stored for this gene.</p>
                )}

                {forestRows.length >= 2 && (
                    <div className="mt-3">
                        <ForestPlot
                            geneName={gene.gene_symbol ?? gene.gene_id}
                            datasets={forestRows}
                            pooledHR={gene.avg_hazard_ratio}
                            heterogeneityStats={het}
                        />
                        {/* I² is unstable below ~3 cohorts, so it is withheld rather
                            than shown as a number nobody should act on. */}
                        {gene.n_datasets < MIN_DATASETS_FOR_I2 && (
                            <p className="text-[10px] text-fg-faint mt-1">
                                Heterogeneity (I²) is not reported below {MIN_DATASETS_FOR_I2} cohorts — it is
                                too unstable to interpret.
                            </p>
                        )}
                        {i2 != null && i2 > 50 && (
                            <p className="text-[10px] text-warn mt-1">
                                I² = {i2.toFixed(0)}% — the effect is inconsistent across cohorts; read the pooled
                                hazard ratio cautiously.
                            </p>
                        )}
                    </div>
                )}

                <PredictiveArmTable gene={gene} />

                <button
                    type="button"
                    onClick={() => onAsk(`What is known about ${gene.gene_symbol ?? gene.gene_id} in this cancer type, and does this hazard ratio agree with the literature?`)}
                    className="mt-2 text-[11px] text-accent-fg hover:underline"
                >
                    Ask about {gene.gene_symbol ?? gene.gene_id}
                </button>
            </div>
        )
    }

    return (
        <Card>
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <h3 className="text-sm font-semibold text-fg-strong">{result.query}</h3>
                <span className="text-[11px] text-fg-faint">
                    {s.nDatasetsWithSurvival} of {s.nDatasets} cohorts with survival data · {Math.round(s.processingTime)}s
                </span>
            </div>

            {s.isFocused ? (
                <p className="text-[11px] text-fg-muted mt-0.5">
                    Focused on {focusGenes.join(', ')} — a pre-specified hypothesis test across independent cohorts.
                </p>
            ) : (
                <p className="text-[11px] text-fg-muted mt-0.5">
                    {s.nGenes} genes survived cross-cohort ranking.
                </p>
            )}

            {s.missingFocusGenes.length > 0 && (
                <p className="text-[11px] text-warn mt-1.5">
                    ⚠ {s.missingFocusGenes.join(', ')} did not reach significance in enough cohorts to be
                    reported — an absence of evidence here, not evidence of absence.
                </p>
            )}

            {!s.isFocused && s.nPredictive > 0 && (
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <Chip tone="warning">
                        {s.nPredictive} of {s.nGenes} treatment-effect-modifying
                    </Chip>
                    <button
                        type="button"
                        onClick={() => setPredictiveOnly((v) => !v)}
                        className="text-[11px] text-accent-fg hover:underline"
                    >
                        {predictiveOnly ? 'show all genes' : 'show only these'}
                    </button>
                </div>
            )}

            <div className="mt-3 divide-y divide-border">
                {listed.map((gene) => {
                    const open = expanded === gene.gene_id
                    const p = pValueLabel(gene, result)
                    return (
                        <div key={gene.gene_id} className="py-2">
                            <button
                                type="button"
                                onClick={() => setExpanded(open ? null : gene.gene_id)}
                                className="w-full flex items-center gap-2 text-left"
                            >
                                <span className="text-fg-faint text-[11px]" aria-hidden>{open ? '▾' : '▸'}</span>
                                <span className="font-medium text-sm text-fg-strong">{gene.gene_symbol ?? gene.gene_id}</span>
                                <DirectionChip gene={gene} />
                                {gene.is_predictive && <Chip tone="warning">predictive</Chip>}
                                <span className="flex-1" />
                                <span className="text-[11px] text-fg-muted">
                                    HR {gene.avg_hazard_ratio.toFixed(2)} · {p.label} {formatP(p.value)} · {gene.n_datasets} cohorts
                                </span>
                            </button>
                            {open && renderGeneBody(gene)}
                        </div>
                    )
                })}
                {listed.length === 0 && (
                    <p className="py-2 text-[11px] text-fg-faint">
                        No genes to show. Try a broader query, a lower minimum-cohort threshold, or widening the
                        hazard-ratio gates in the chart settings.
                    </p>
                )}
            </div>

            <div className="mt-3 pt-3 border-t border-border flex flex-wrap items-start gap-2">
                <Button
                    size="sm"
                    onClick={onShowTreatmentEvidence}
                    disabled={!modelId}
                    disabledReason={modelId ? undefined : 'Still building a model from this analysis'}
                >
                    Show treatment curves
                </Button>
                <Button size="sm" variant="secondary" onClick={onScorePatient}>
                    Score a patient against this
                </Button>
                {resultId && (
                    <a
                        href={`/results/${resultId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-accent-fg hover:underline self-center"
                    >
                        Open full result ↗
                    </a>
                )}
            </div>
            {resultId && (
                <p className="text-[10px] text-fg-faint mt-1">
                    Saved as <code className="font-mono">{resultId}</code> — this card is not kept when the page
                    reloads, but that link is permanent.
                </p>
            )}
        </Card>
    )
}

export default AnalysisResultCard
