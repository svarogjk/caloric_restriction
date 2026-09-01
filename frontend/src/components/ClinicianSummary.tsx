import React, { useState } from 'react'
import { interpretResults } from '../services/api'
import { AnalysisResult } from '../store/chatSlice'
import { RuoNotice } from './ui'

interface ClinicianSummaryProps {
    results: AnalysisResult
    model?: string
}

/**
 * F21 — AI clinician summary grounded in the real AnalysisResponse. Sends the
 * top genes (with HRs + GSEs) to the pydantic-ai agent and renders a plain-
 * language, advisory predictive interpretation with its Domain Score.
 */
const ClinicianSummary: React.FC<ClinicianSummaryProps> = ({ results, model }) => {
    const [summary, setSummary] = useState<string | null>(null)
    const [domainScore, setDomainScore] = useState<number | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleGenerate = async () => {
        setLoading(true)
        setError(null)
        try {
            const topGenes = [...results.common_genes]
                .sort((a, b) => b.n_datasets - a.n_datasets || a.avg_cox_p_value - b.avg_cox_p_value)
                .slice(0, 8)
                .map((g) => ({
                    gene_symbol: g.gene_symbol,
                    avg_hazard_ratio: g.avg_hazard_ratio,
                    avg_cox_p_value: g.avg_cox_p_value,
                    n_datasets: g.n_datasets,
                    predominant_risk: g.predominant_risk,
                    datasets: g.datasets,
                }))
            const resp = await interpretResults({
                query: results.query,
                model,
                genes: topGenes,
                n_datasets_with_survival: results.n_datasets_with_survival,
            })
            setSummary(resp.summary)
            setDomainScore(resp.domain_score)
        } catch {
            setError('Could not generate a clinician summary right now.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="border border-accent-soft bg-accent-soft/40 rounded-lg p-3">
            <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-accent-fg">Clinician summary</h4>
                {domainScore !== null && (
                    <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            domainScore >= 70
                                ? 'bg-ok-soft text-ok'
                                : domainScore >= 40
                                  ? 'bg-warn-soft text-warn'
                                  : 'bg-surface-sunken text-fg-muted'
                        }`}
                        title="Domain Score — how grounded this answer is in real GEO data"
                    >
                        DS {domainScore}
                    </span>
                )}
            </div>

            {!summary && (
                <div className="mt-2">
                    <p className="text-xs text-fg-muted mb-2">
                        Generate a plain-language interpretation grounded in these genes, hazard ratios,
                        and cohorts.
                    </p>
                    <RuoNotice variant="inline" className="mb-2" />
                    <button
                        onClick={handleGenerate}
                        disabled={loading || results.common_genes.length === 0}
                        className="px-3 py-1.5 text-sm bg-accent text-on-accent rounded hover:bg-accent-hover disabled:opacity-50"
                    >
                        {loading ? 'Generating…' : 'Generate summary'}
                    </button>
                </div>
            )}

            {error && <p className="text-sm text-danger mt-2">{error}</p>}

            {summary && (
                <div className="mt-2">
                    <p className="text-sm text-fg whitespace-pre-line leading-relaxed">{summary}</p>
                    <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="mt-2 text-xs text-accent-fg hover:underline disabled:opacity-50"
                    >
                        {loading ? 'Regenerating…' : '↺ Regenerate'}
                    </button>
                </div>
            )}
        </div>
    )
}

export default ClinicianSummary
