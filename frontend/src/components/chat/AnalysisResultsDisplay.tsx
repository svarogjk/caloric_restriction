import React, { useState } from 'react'
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    ReferenceLine,
} from 'recharts'
import { AnalysisResult, GeneSurvival } from '../../store/chatSlice'
import { GeneSurvival as SearchGeneSurvival } from '../../store/searchSlice'
import KaplanMeierPlot from '../KaplanMeierPlot'

interface AnalysisResultsDisplayProps {
    results: AnalysisResult
    onClose?: () => void
}

interface TransformedGene {
    gene_id: string
    gene_symbol: string | null
    hazard_ratio: number
    log_hazard_ratio: number
    negLog10PValue: number
    p_value: number
    color: string
    predominant_risk: string
    n_datasets: number
    original: GeneSurvival
}

const AnalysisResultsDisplay: React.FC<AnalysisResultsDisplayProps> = ({ results, onClose }) => {
    const [selectedGene, setSelectedGene] = useState<GeneSurvival | null>(null)
    const [expandedGeneId, setExpandedGeneId] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'summary' | 'volcano' | 'genes'>('summary')

    // Transform data for volcano plot
    const transformedData = React.useMemo<TransformedGene[]>(() => {
        return results.common_genes.map((gene) => ({
            gene_id: gene.gene_id,
            gene_symbol: gene.gene_symbol,
            hazard_ratio: gene.avg_hazard_ratio,
            log_hazard_ratio: Math.log2(gene.avg_hazard_ratio),
            negLog10PValue: -Math.log10(gene.avg_log_rank_p_value),
            p_value: gene.avg_log_rank_p_value,
            color: getGeneColor(gene.avg_hazard_ratio, gene.avg_log_rank_p_value),
            predominant_risk: gene.predominant_risk,
            n_datasets: gene.n_datasets,
            original: gene,
        }))
    }, [results.common_genes])

    function getGeneColor(hazardRatio: number, pValue: number): string {
        const negLog10P = -Math.log10(pValue)
        const significanceThreshold = -Math.log10(0.05)

        if (negLog10P > significanceThreshold && hazardRatio > 1.5) {
            return '#ef4444' // Red - high risk
        }
        if (negLog10P > significanceThreshold && hazardRatio < 0.67) {
            return '#3b82f6' // Blue - protective
        }
        if (negLog10P > significanceThreshold) {
            return '#f59e0b' // Amber - moderate
        }
        return '#9ca3af' // Gray - not significant
    }

    // Sort genes by number of datasets then p-value
    const sortedGenes = [...results.common_genes].sort((a, b) => {
        if (b.n_datasets !== a.n_datasets) {
            return b.n_datasets - a.n_datasets
        }
        return a.avg_cox_p_value - b.avg_cox_p_value
    })

    const CustomTooltip: React.FC<{ active?: boolean; payload?: any[] }> = ({ active, payload }) => {
        if (active && payload && payload[0]) {
            const data = payload[0].payload as TransformedGene
            return (
                <div className="bg-white p-3 border border-gray-300 rounded shadow-lg z-50">
                    <p className="font-semibold text-gray-800">
                        {data.gene_symbol || data.gene_id}
                    </p>
                    <div className="mt-2 space-y-1">
                        <p className="text-sm text-gray-600">
                            <span className="font-medium">HR:</span>{' '}
                            <span className={data.hazard_ratio > 1 ? 'text-red-600' : 'text-blue-600'}>
                                {data.hazard_ratio.toFixed(2)}
                            </span>
                        </p>
                        <p className="text-sm text-gray-600">
                            <span className="font-medium">P:</span>{' '}
                            {data.p_value < 0.001 ? data.p_value.toExponential(2) : data.p_value.toFixed(4)}
                        </p>
                        <p className="text-sm text-gray-600">
                            <span className="font-medium">Datasets:</span> {data.n_datasets}
                        </p>
                    </div>
                </div>
            )
        }
        return null
    }

    const xMin = Math.min(...transformedData.map((d) => d.log_hazard_ratio), -1)
    const xMax = Math.max(...transformedData.map((d) => d.log_hazard_ratio), 1)
    const yMax = Math.max(...transformedData.map((d) => d.negLog10PValue), 3)

    return (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-3 flex items-center justify-between">
                <div>
                    <h3 className="text-white font-semibold">Survival Analysis Results</h3>
                    <p className="text-indigo-100 text-sm">Query: {results.query}</p>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="text-white hover:bg-white/20 rounded p-1"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-3 gap-2 p-3 bg-gray-50 border-b">
                <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">{results.n_datasets_analyzed}</p>
                    <p className="text-xs text-gray-500">Datasets Analyzed</p>
                </div>
                <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">{results.n_datasets_with_survival}</p>
                    <p className="text-xs text-gray-500">With Survival Data</p>
                </div>
                <div className="text-center">
                    <p className="text-2xl font-bold text-purple-600">{results.common_genes.length}</p>
                    <p className="text-xs text-gray-500">Survival Genes</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b">
                <button
                    onClick={() => setActiveTab('summary')}
                    className={`flex-1 px-4 py-2 text-sm font-medium ${
                        activeTab === 'summary'
                            ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Summary
                </button>
                <button
                    onClick={() => setActiveTab('volcano')}
                    className={`flex-1 px-4 py-2 text-sm font-medium ${
                        activeTab === 'volcano'
                            ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Volcano Plot
                </button>
                <button
                    onClick={() => setActiveTab('genes')}
                    className={`flex-1 px-4 py-2 text-sm font-medium ${
                        activeTab === 'genes'
                            ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Genes ({results.common_genes.length})
                </button>
            </div>

            {/* Tab Content */}
            <div className="p-4">
                {activeTab === 'summary' && (
                    <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                            Analysis completed in {results.processing_time.toFixed(2)} seconds.
                        </p>

                        {results.ranking_recommendations && (
                            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                                <div className="flex items-start gap-2">
                                    <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p className="text-sm font-medium text-blue-800">
                                            Quality Score: {results.ranking_quality_score?.toFixed(1) || 'N/A'}/10
                                        </p>
                                        <p className="text-sm text-blue-700">{results.ranking_recommendations}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Top 5 genes summary */}
                        {sortedGenes.length > 0 && (
                            <div>
                                <h4 className="font-medium text-gray-800 mb-2">Top Survival-Associated Genes</h4>
                                <div className="space-y-2">
                                    {sortedGenes.slice(0, 5).map((gene) => (
                                        <div
                                            key={gene.gene_id}
                                            className="flex items-center justify-between p-2 bg-gray-50 rounded cursor-pointer hover:bg-gray-100"
                                            onClick={() => setSelectedGene(gene)}
                                        >
                                            <div>
                                                <span className="font-medium">{gene.gene_symbol || gene.gene_id}</span>
                                                <span className="text-xs text-gray-500 ml-2">({gene.n_datasets} datasets)</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`text-sm font-medium ${
                                                    gene.predominant_risk === 'high_risk' ? 'text-red-600' : 'text-blue-600'
                                                }`}>
                                                    HR: {gene.avg_hazard_ratio.toFixed(2)}
                                                </span>
                                                <span className={`text-xs px-2 py-0.5 rounded ${
                                                    gene.predominant_risk === 'high_risk'
                                                        ? 'bg-red-100 text-red-700'
                                                        : 'bg-blue-100 text-blue-700'
                                                }`}>
                                                    {gene.predominant_risk === 'high_risk' ? '↑ Risk' : '↓ Protective'}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'volcano' && results.common_genes.length > 0 && (
                    <div>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <ScatterChart margin={{ top: 10, right: 10, bottom: 30, left: 40 }}>
                                    <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
                                    <XAxis
                                        type="number"
                                        dataKey="log_hazard_ratio"
                                        domain={[xMin - 0.5, xMax + 0.5]}
                                        tickFormatter={(value) => value.toFixed(1)}
                                        label={{
                                            value: 'log₂(HR)',
                                            position: 'insideBottom',
                                            offset: -10,
                                        }}
                                        fontSize={12}
                                    />
                                    <YAxis
                                        type="number"
                                        dataKey="negLog10PValue"
                                        domain={[0, yMax + 1]}
                                        label={{
                                            value: '-log₁₀(p)',
                                            angle: -90,
                                            position: 'insideLeft',
                                        }}
                                        fontSize={12}
                                    />
                                    <ReferenceLine x={0} stroke="#6b7280" strokeDasharray="3 3" />
                                    <ReferenceLine y={-Math.log10(0.05)} stroke="#6b7280" strokeDasharray="3 3" />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Scatter
                                        data={transformedData}
                                        onClick={(data: any) => data && setSelectedGene(data.original)}
                                        cursor="pointer"
                                    >
                                        {transformedData.map((entry, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={entry.color}
                                                r={entry.n_datasets > 3 ? 5 : 4}
                                            />
                                        ))}
                                    </Scatter>
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="flex gap-4 justify-center mt-2 text-xs">
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                                <span>High Risk</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                <span>Protective</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                                <span>Moderate</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                                <span>NS</span>
                            </div>
                        </div>
                        <p className="text-xs text-gray-400 text-center mt-1">Click a gene to view Kaplan-Meier curves</p>
                    </div>
                )}

                {activeTab === 'genes' && (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {sortedGenes.map((gene) => (
                            <div
                                key={gene.gene_id}
                                className="border rounded-lg overflow-hidden"
                            >
                                <div
                                    className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
                                    onClick={() => setExpandedGeneId(expandedGeneId === gene.gene_id ? null : gene.gene_id)}
                                >
                                    <div className="flex items-center gap-3">
                                        <span className={`w-3 h-3 rounded-full ${
                                            gene.predominant_risk === 'high_risk' ? 'bg-red-500' : 'bg-blue-500'
                                        }`}></span>
                                        <div>
                                            <span className="font-medium">{gene.gene_symbol || gene.gene_id}</span>
                                            {gene.gene_symbol && (
                                                <span className="text-xs text-gray-500 ml-1">({gene.gene_id})</span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="text-right text-sm">
                                            <div className={gene.avg_hazard_ratio > 1 ? 'text-red-600' : 'text-blue-600'}>
                                                HR: {gene.avg_hazard_ratio.toFixed(2)}
                                            </div>
                                            <div className="text-gray-500 text-xs">
                                                p: {gene.avg_cox_p_value < 0.001
                                                    ? gene.avg_cox_p_value.toExponential(2)
                                                    : gene.avg_cox_p_value.toFixed(4)}
                                            </div>
                                        </div>
                                        <svg
                                            className={`w-5 h-5 text-gray-400 transition-transform ${
                                                expandedGeneId === gene.gene_id ? 'rotate-180' : ''
                                            }`}
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>

                                {expandedGeneId === gene.gene_id && (
                                    <div className="p-3 border-t bg-white">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <div>
                                                <span className="text-gray-500">Datasets:</span>
                                                <span className="ml-1 font-medium">{gene.n_datasets}</span>
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Consistency:</span>
                                                <span className="ml-1 font-medium">
                                                    {(gene.risk_direction_consistency * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setSelectedGene(gene)}
                                            className="mt-2 w-full py-1.5 text-sm bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
                                        >
                                            View Kaplan-Meier Curves
                                        </button>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Kaplan-Meier Modal */}
            {selectedGene && (
                <KaplanMeierPlot
                    gene={selectedGene as SearchGeneSurvival}
                    onClose={() => setSelectedGene(null)}
                />
            )}
        </div>
    )
}

export default AnalysisResultsDisplay
