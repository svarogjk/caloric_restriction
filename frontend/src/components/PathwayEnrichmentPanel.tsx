import React, { useState } from 'react'
import axios from 'axios'

export interface EnrichmentTerm {
    term_id: string
    term_name: string
    source: string
    p_value: number
    intersection_size: number
    query_size: number
}

interface PathwayEnrichmentPanelProps {
    geneSymbols: string[]
    organism?: string
}

const SOURCE_FILTERS = ['ALL', 'GO:BP', 'GO:MF', 'KEGG', 'REAC'] as const
type SourceFilter = (typeof SOURCE_FILTERS)[number]

const MAX_TERMS = 50

const PathwayEnrichmentPanel: React.FC<PathwayEnrichmentPanelProps> = ({
    geneSymbols,
    organism = 'hsapiens',
}) => {
    const [terms, setTerms] = useState<EnrichmentTerm[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [activeSource, setActiveSource] = useState<SourceFilter>('ALL')
    const [hasRun, setHasRun] = useState(false)

    const handleRunEnrichment = async () => {
        if (geneSymbols.length === 0) return
        setLoading(true)
        setError(null)
        setHasRun(true)
        try {
            const response = await axios.post<EnrichmentTerm[]>('/api/enrich', {
                genes: geneSymbols,
                organism,
            })
            const sorted = [...response.data].sort((a, b) => a.p_value - b.p_value)
            setTerms(sorted)
        } catch (err) {
            setError('Enrichment analysis failed. The service may not be available yet.')
            console.error('Enrichment error:', err)
        } finally {
            setLoading(false)
        }
    }

    const filteredTerms = terms
        .filter((t) => activeSource === 'ALL' || t.source === activeSource)
        .slice(0, MAX_TERMS)

    const formatQValue = (p: number): string => p.toFixed(4)

    return (
        <div className="mt-6 border-t pt-4">
            <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-gray-700">Enrichment Analysis</h4>
                <button
                    onClick={handleRunEnrichment}
                    disabled={loading || geneSymbols.length === 0}
                    className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {loading ? 'Running...' : 'Run Pathway Analysis'}
                </button>
            </div>

            <p className="text-xs text-gray-500 mb-3">
                {geneSymbols.length} significant gene{geneSymbols.length !== 1 ? 's' : ''} available for enrichment analysis
            </p>

            {/* Error */}
            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700 mb-3">
                    {error}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex items-center gap-2 py-4 text-sm text-gray-500">
                    <svg className="animate-spin h-4 w-4 text-indigo-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Running pathway enrichment...
                </div>
            )}

            {/* Results */}
            {!loading && hasRun && terms.length === 0 && !error && (
                <p className="text-sm text-gray-400 text-center py-4">
                    No enriched pathways found. Try with more genes.
                </p>
            )}

            {!loading && terms.length > 0 && (
                <div>
                    {/* Source filter buttons */}
                    <div className="flex gap-1 mb-3 flex-wrap">
                        {SOURCE_FILTERS.map((src) => (
                            <button
                                key={src}
                                onClick={() => setActiveSource(src)}
                                className={`px-2 py-1 text-xs rounded border transition-colors ${
                                    activeSource === src
                                        ? 'bg-indigo-600 text-white border-indigo-600'
                                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                                }`}
                            >
                                {src}
                            </button>
                        ))}
                        <span className="text-xs text-gray-400 self-center ml-1">
                            {filteredTerms.length} term{filteredTerms.length !== 1 ? 's' : ''}
                            {filteredTerms.length === MAX_TERMS ? ` (top ${MAX_TERMS})` : ''}
                        </span>
                    </div>

                    {/* Table */}
                    <div className="overflow-y-auto max-h-64 border border-gray-200 rounded">
                        <table className="w-full text-xs">
                            <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                    <th className="px-3 py-2 text-left font-medium text-gray-600 border-b">Source</th>
                                    <th className="px-3 py-2 text-left font-medium text-gray-600 border-b">Term Name</th>
                                    <th className="px-3 py-2 text-center font-medium text-gray-600 border-b">Genes</th>
                                    <th className="px-3 py-2 text-right font-medium text-gray-600 border-b">q-value</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredTerms.map((term) => (
                                    <tr key={term.term_id} className="hover:bg-gray-50 border-b border-gray-100 last:border-0">
                                        <td className="px-3 py-2">
                                            <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 whitespace-nowrap">
                                                {term.source}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-gray-800 max-w-xs">
                                            <span title={term.term_name} className="block truncate">
                                                {term.term_name}
                                            </span>
                                            <span className="text-gray-400">{term.term_id}</span>
                                        </td>
                                        <td className="px-3 py-2 text-center text-gray-600">
                                            {term.intersection_size}/{term.query_size}
                                        </td>
                                        <td className="px-3 py-2 text-right font-mono text-gray-700">
                                            {formatQValue(term.p_value)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}

export default PathwayEnrichmentPanel
