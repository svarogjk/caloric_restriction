import React, { useState, useEffect, useRef } from 'react'
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
import { toPng } from 'html-to-image'
import { AnalysisResult, GeneSurvival } from '../../store/chatSlice'
import KaplanMeierPlot from '../KaplanMeierPlot'
import { ForestPlot } from '../ForestPlot'
import PathwayEnrichmentPanel from '../PathwayEnrichmentPanel'
import { getStoredToken } from '../../services/authApi'

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

const PAGE_SIZE = 20

const AnalysisResultsDisplay: React.FC<AnalysisResultsDisplayProps> = ({ results, onClose }) => {
    const [selectedGene, setSelectedGene] = useState<GeneSurvival | null>(null)
    const [expandedGeneId, setExpandedGeneId] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'summary' | 'volcano' | 'genes' | 'forest' | 'methods'>('summary')

    // F08: Forest plot gene selector
    const [selectedForestGeneId, setSelectedForestGeneId] = useState<string | null>(null)
    const selectedForestGene = results.common_genes.find(g => g.gene_id === selectedForestGeneId)
        ?? results.common_genes[0]

    // F02: Gene search + pagination state
    const [geneSearch, setGeneSearch] = useState('')
    const [genePage, setGenePage] = useState(0)

    // F18: Analysis parameters toggle
    const [paramsOpen, setParamsOpen] = useState(false)

    // F17: Methods copy feedback
    const [copied, setCopied] = useState(false)

    // F09: Share link feedback
    const [shareCopied, setShareCopied] = useState(false)

    // F15: Publication ZIP download state
    const [exporting, setExporting] = useState(false)

    const handleExportZip = async () => {
        if (!results.result_id || exporting) return
        setExporting(true)
        try {
            const token = getStoredToken()
            const response = await fetch(`/api/results/${results.result_id}/export`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            })
            if (!response.ok) {
                console.error('Export failed:', response.status, await response.text())
                return
            }
            const blob = await response.blob()
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `geo_survival_analysis.zip`
            a.click()
            URL.revokeObjectURL(url)
        } catch (err) {
            console.error('Export ZIP failed:', err)
        } finally {
            setExporting(false)
        }
    }

    const handleShare = async () => {
        if (!results.result_id) return
        const url = `${window.location.origin}/results/${results.result_id}`
        try {
            await navigator.clipboard.writeText(url)
            setShareCopied(true)
            setTimeout(() => setShareCopied(false), 2500)
        } catch (err) {
            console.error('Clipboard write failed:', err)
        }
    }

    // F04: Volcano plot ref for PNG export
    const volcanoRef = useRef<HTMLDivElement>(null)

    // Reset page when search changes
    useEffect(() => {
        setGenePage(0)
    }, [geneSearch])

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

    // F02: Filter + paginate
    const filteredGenes = sortedGenes.filter((gene) => {
        if (!geneSearch.trim()) return true
        const q = geneSearch.toLowerCase()
        return (
            (gene.gene_symbol?.toLowerCase().includes(q) ?? false) ||
            gene.gene_id.toLowerCase().includes(q)
        )
    })
    const totalFilteredGenes = filteredGenes.length
    const pagedGenes = filteredGenes.slice(genePage * PAGE_SIZE, (genePage + 1) * PAGE_SIZE)
    const totalPages = Math.ceil(totalFilteredGenes / PAGE_SIZE)
    const pageStart = genePage * PAGE_SIZE + 1
    const pageEnd = Math.min((genePage + 1) * PAGE_SIZE, totalFilteredGenes)

    // F04: CSV export
    const handleExportCSV = () => {
        const headers = 'Gene Symbol,Gene ID,N Datasets,Avg HR,Avg p-value,Consistency %,Risk Direction,Dataset IDs'
        const rows = sortedGenes.map((gene) => {
            const symbol = gene.gene_symbol ?? ''
            const consistency = (gene.risk_direction_consistency * 100).toFixed(1)
            const datasetIds = gene.datasets.join(';')
            const avgP = gene.avg_cox_p_value < 0.001
                ? gene.avg_cox_p_value.toExponential(2)
                : gene.avg_cox_p_value.toFixed(4)
            return `"${symbol}","${gene.gene_id}",${gene.n_datasets},${gene.avg_hazard_ratio.toFixed(4)},${avgP},${consistency},${gene.predominant_risk},"${datasetIds}"`
        })
        const csvString = [headers, ...rows].join('\n')
        const blob = new Blob([csvString], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'geo_survival_analysis.csv'
        a.click()
        URL.revokeObjectURL(url)
    }

    // F04: PNG export for volcano plot
    const handleExportPNG = async () => {
        if (!volcanoRef.current) return
        try {
            const dataUrl = await toPng(volcanoRef.current, { pixelRatio: 2 })
            const a = document.createElement('a')
            a.href = dataUrl
            a.download = 'volcano_plot.png'
            a.click()
        } catch (err) {
            console.error('PNG export failed:', err)
        }
    }

    // F17: Methods text
    const methodsText = `We searched NCBI GEO for datasets matching "${results.query}" and identified ${results.n_datasets_analyzed} datasets. Of these, ${results.n_datasets_with_survival} contained survival outcome data suitable for analysis. Gene expression was stratified into high and low groups using median expression as the cutoff threshold. Survival analysis was performed using Cox proportional hazards regression as implemented in the lifelines library (version 0.29+) for Python. Genes were considered significant at p < 0.05 with a hazard ratio reported for each dataset. Results represent cross-dataset meta-analysis across ${results.n_datasets_with_survival} independent cohorts. Analysis was performed using GEO Survival Analysis [URL] [Zenodo DOI: PLACEHOLDER].`

    const handleCopyMethods = async () => {
        try {
            await navigator.clipboard.writeText(methodsText)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch (err) {
            console.error('Clipboard write failed:', err)
        }
    }

    // F18: Analysis timestamp
    const analysisTimestamp = results.timestamp
        ? new Date(results.timestamp).toLocaleString()
        : new Date().toLocaleString()

    const CustomTooltip: React.FC<{ active?: boolean; payload?: Array<{ payload: TransformedGene }> }> = ({ active, payload }) => {
        if (active && payload && payload[0]) {
            const data = payload[0].payload
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
                <div className="flex items-center gap-2">
                    {results.result_id && (
                        <button
                            onClick={handleExportZip}
                            disabled={exporting}
                            className="text-xs px-2 py-1 rounded border transition-colors bg-white/20 text-white border-white/30 hover:bg-white/30 disabled:opacity-60 disabled:cursor-not-allowed"
                            title="Download publication-ready ZIP (genes.csv, methods.txt, params)"
                        >
                            {exporting ? 'Preparing...' : 'Download Package'}
                        </button>
                    )}
                    {results.result_id && (
                        <button
                            onClick={handleShare}
                            className={`text-xs px-2 py-1 rounded border transition-colors ${
                                shareCopied
                                    ? 'bg-green-500 text-white border-green-400'
                                    : 'bg-white/20 text-white border-white/30 hover:bg-white/30'
                            }`}
                            title="Copy shareable link"
                        >
                            {shareCopied ? '✓ Link copied!' : 'Share'}
                        </button>
                    )}
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
                <button
                    onClick={() => setActiveTab('forest')}
                    className={`flex-1 px-4 py-2 text-sm font-medium ${
                        activeTab === 'forest'
                            ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Forest Plot
                </button>
                <button
                    onClick={() => setActiveTab('methods')}
                    className={`flex-1 px-4 py-2 text-sm font-medium ${
                        activeTab === 'methods'
                            ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Methods
                </button>
            </div>

            {/* Tab Content */}
            <div className="p-4">
                {/* ===== SUMMARY TAB ===== */}
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

                        {/* F18: Analysis Parameters collapsible */}
                        <div className="mt-4">
                            <button
                                onClick={() => setParamsOpen((prev) => !prev)}
                                className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
                            >
                                <span>{paramsOpen ? '▼' : '▶'}</span>
                                <span>Analysis Parameters</span>
                            </button>
                            {paramsOpen && (
                                <div className="mt-2 bg-gray-50 border border-gray-200 rounded p-3 text-xs text-gray-600">
                                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
                                        <dt className="font-medium">Expression cutoff method</dt>
                                        <dd>Median split</dd>
                                        <dt className="font-medium">Significance threshold</dt>
                                        <dd>p &lt; 0.05 (Cox regression)</dd>
                                        <dt className="font-medium">Minimum datasets</dt>
                                        <dd>User-configured</dd>
                                        <dt className="font-medium">Organism</dt>
                                        <dd>User-configured</dd>
                                        <dt className="font-medium">Analysis timestamp</dt>
                                        <dd>{analysisTimestamp}</dd>
                                        <dt className="font-medium">Tool version</dt>
                                        <dd>v1.0.0</dd>
                                    </dl>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* ===== VOLCANO TAB ===== */}
                {activeTab === 'volcano' && results.common_genes.length > 0 && (
                    <div>
                        {/* F04: PNG export button */}
                        <div className="flex justify-end mb-2">
                            <button
                                onClick={handleExportPNG}
                                className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border border-gray-300"
                            >
                                Export PNG
                            </button>
                        </div>
                        <div className="h-64" ref={volcanoRef}>
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
                                        onClick={(data: unknown) => {
                                            const d = data as { original?: GeneSurvival }
                                            if (d?.original) setSelectedGene(d.original)
                                        }}
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

                {/* ===== GENES TAB ===== */}
                {activeTab === 'genes' && (
                    <div>
                        {/* F04: CSV export + F02: search + count header */}
                        <div className="flex items-center justify-between mb-3 gap-2">
                            <span className="text-sm text-gray-600 font-medium whitespace-nowrap">
                                {totalFilteredGenes} gene{totalFilteredGenes !== 1 ? 's' : ''}
                                {geneSearch.trim() && ` matching "${geneSearch}"`}
                            </span>
                            <div className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={geneSearch}
                                    onChange={(e) => setGeneSearch(e.target.value)}
                                    placeholder="Search genes..."
                                    className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 w-36"
                                />
                                <button
                                    onClick={handleExportCSV}
                                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border border-gray-300 whitespace-nowrap"
                                >
                                    Export CSV
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2 max-h-96 overflow-y-auto">
                            {pagedGenes.map((gene) => (
                                <div
                                    key={gene.gene_id}
                                    className="border rounded-lg overflow-hidden"
                                >
                                    <div
                                        className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
                                        onClick={() => setExpandedGeneId(expandedGeneId === gene.gene_id ? null : gene.gene_id)}
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className={`w-3 h-3 rounded-full flex-shrink-0 ${
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

                            {totalFilteredGenes === 0 && (
                                <p className="text-sm text-gray-400 text-center py-4">No genes match your search.</p>
                            )}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between mt-3 pt-3 border-t">
                                <span className="text-xs text-gray-500">
                                    Showing {pageStart}–{pageEnd} of {totalFilteredGenes} genes
                                </span>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setGenePage((p) => Math.max(0, p - 1))}
                                        disabled={genePage === 0}
                                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-300"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        onClick={() => setGenePage((p) => Math.min(totalPages - 1, p + 1))}
                                        disabled={genePage >= totalPages - 1}
                                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-300"
                                    >
                                        Next
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* F11: Pathway Enrichment */}
                        {(() => {
                            const significantGenes = results.common_genes
                                .filter((g) => g.avg_cox_p_value < 0.05)
                                .map((g) => g.gene_symbol)
                                .filter((s): s is string => Boolean(s))
                            return (
                                <PathwayEnrichmentPanel geneSymbols={significantGenes} />
                            )
                        })()}
                    </div>
                )}

                {/* ===== FOREST PLOT TAB ===== */}
                {activeTab === 'forest' && (
                    <div>
                        <div className="flex items-center gap-2 mb-3">
                            <label className="text-xs text-gray-600">Gene:</label>
                            <select
                                value={selectedForestGeneId ?? selectedForestGene?.gene_id ?? ''}
                                onChange={(e) => setSelectedForestGeneId(e.target.value)}
                                className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                            >
                                {results.common_genes.slice(0, 20).map((g) => (
                                    <option key={g.gene_id} value={g.gene_id}>
                                        {g.gene_symbol || g.gene_id}
                                    </option>
                                ))}
                            </select>
                        </div>
                        {selectedForestGene?.per_dataset_results && selectedForestGene.per_dataset_results.length >= 2 ? (
                            <ForestPlot
                                geneName={selectedForestGene.gene_symbol || selectedForestGene.gene_id}
                                datasets={selectedForestGene.per_dataset_results.map((ds) => ({
                                    dataset_id: ds.dataset_id,
                                    dataset_title: ds.dataset_title,
                                    hazard_ratio: ds.hazard_ratio,
                                    hazard_ratio_ci_lower: ds.hazard_ratio_ci_lower,
                                    hazard_ratio_ci_upper: ds.hazard_ratio_ci_upper,
                                    n_samples: ds.n_samples,
                                    cox_p_value: ds.cox_p_value,
                                }))}
                                pooledHR={selectedForestGene.avg_hazard_ratio}
                                heterogeneityStats={selectedForestGene.heterogeneity_stats}
                            />
                        ) : (
                            <p className="text-sm text-gray-400 text-center py-8">
                                Not enough per-dataset data for this gene (need ≥ 2 datasets with CI).
                            </p>
                        )}
                    </div>
                )}

                {/* ===== METHODS TAB ===== */}
                {activeTab === 'methods' && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium text-gray-700">Auto-Generated Methods Text</h4>
                            <button
                                onClick={handleCopyMethods}
                                className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                                    copied
                                        ? 'bg-green-100 text-green-700 border-green-300'
                                        : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                                }`}
                            >
                                {copied ? 'Copied!' : 'Copy to Clipboard'}
                            </button>
                        </div>
                        <textarea
                            readOnly
                            value={methodsText}
                            rows={8}
                            className="w-full text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded p-3 resize-none focus:outline-none"
                        />
                        <p className="text-xs text-gray-400">
                            Replace [URL] and [Zenodo DOI: PLACEHOLDER] with your published tool URL and DOI before submission.
                        </p>
                    </div>
                )}
            </div>

            {/* Kaplan-Meier Modal */}
            {selectedGene && (
                <KaplanMeierPlot
                    gene={selectedGene as GeneSurvival}
                    onClose={() => setSelectedGene(null)}
                />
            )}
        </div>
    )
}

export default AnalysisResultsDisplay
