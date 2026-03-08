import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
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
import { RootState, AppDispatch } from '../store/store'
import { fetchAnalysisHistory } from '../store/chatSlice'
import { compareAnalyses, CompareResponse, GeneComparisonItem } from '../services/api'

type ActiveTab = 'shared' | 'only_a' | 'only_b'

interface ScatterPoint {
    gene_symbol: string
    hr_a: number
    hr_b: number
    log_hr_a: number
    log_hr_b: number
    direction_agrees: boolean
}

const ComparisonPage: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>()
    const { analysisHistory, historyLoading } = useSelector((state: RootState) => state.chat)

    const [selectedA, setSelectedA] = useState('')
    const [selectedB, setSelectedB] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [result, setResult] = useState<CompareResponse | null>(null)
    const [activeTab, setActiveTab] = useState<ActiveTab>('shared')

    useEffect(() => {
        dispatch(fetchAnalysisHistory())
    }, [dispatch])

    const formatDate = (isoString: string): string =>
        new Date(isoString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        })

    const canCompare = selectedA !== '' && selectedB !== '' && selectedA !== selectedB

    const handleCompare = async () => {
        if (!canCompare) return
        setLoading(true)
        setError(null)
        setResult(null)
        try {
            const data = await compareAnalyses(selectedA, selectedB)
            setResult(data)
            setActiveTab('shared')
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Comparison failed'
            setError(msg)
        } finally {
            setLoading(false)
        }
    }

    const scatterData: ScatterPoint[] = result
        ? result.shared_genes.map((g: GeneComparisonItem) => ({
              gene_symbol: g.gene_symbol,
              hr_a: g.hr_a,
              hr_b: g.hr_b,
              log_hr_a: Math.log(g.hr_a),
              log_hr_b: Math.log(g.hr_b),
              direction_agrees: g.direction_agrees,
          }))
        : []

    const pointColor = (pt: ScatterPoint): string => {
        if (!pt.direction_agrees) return '#9ca3af'
        return pt.log_hr_a > 0 ? '#ef4444' : '#3b82f6'
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Nav */}
            <nav className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-5xl mx-auto px-4">
                    <div className="flex items-center justify-between h-14">
                        <Link to="/" className="text-xl font-semibold text-gray-800 hover:text-indigo-600 transition-colors">
                            GEO Survival Analysis
                        </Link>
                        <div className="flex items-center gap-4">
                            <Link to="/history" className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors">
                                History
                            </Link>
                            <Link to="/compare" className="text-sm font-medium text-indigo-600 border-b-2 border-indigo-600 pb-0.5">
                                Compare
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-5xl mx-auto px-4 py-6">
                <h2 className="text-2xl font-bold text-gray-800 mb-1">Analysis Comparison</h2>
                <p className="text-sm text-gray-500 mb-6">
                    Find genes significant across two independent studies — e.g. breast cancer vs lung cancer.
                </p>

                {/* Selectors */}
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 mb-6">
                    {historyLoading ? (
                        <div className="flex items-center justify-center py-8">
                            <svg className="animate-spin h-6 w-6 text-indigo-600" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        </div>
                    ) : analysisHistory.length < 2 ? (
                        <p className="text-sm text-gray-500 text-center py-4">
                            You need at least two saved analyses to compare.{' '}
                            <Link to="/" className="text-indigo-600 hover:underline">Run an analysis</Link>.
                        </p>
                    ) : (
                        <div className="flex flex-col sm:flex-row gap-4 items-end">
                            <div className="flex-1">
                                <label className="block text-xs font-medium text-gray-600 mb-1">Analysis A</label>
                                <select
                                    value={selectedA}
                                    onChange={(e) => setSelectedA(e.target.value)}
                                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                                >
                                    <option value="">Select analysis...</option>
                                    {analysisHistory.map((item) => (
                                        <option key={item.result_id} value={item.result_id}>
                                            {item.query} — {formatDate(item.created_at)} ({item.n_genes_found} genes)
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="block text-xs font-medium text-gray-600 mb-1">Analysis B</label>
                                <select
                                    value={selectedB}
                                    onChange={(e) => setSelectedB(e.target.value)}
                                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                                >
                                    <option value="">Select analysis...</option>
                                    {analysisHistory.map((item) => (
                                        <option key={item.result_id} value={item.result_id}>
                                            {item.query} — {formatDate(item.created_at)} ({item.n_genes_found} genes)
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={handleCompare}
                                disabled={!canCompare || loading}
                                className="px-5 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                            >
                                {loading ? 'Comparing...' : 'Compare'}
                            </button>
                        </div>
                    )}
                    {selectedA === selectedB && selectedA !== '' && (
                        <p className="text-xs text-amber-600 mt-2">Select two different analyses to compare.</p>
                    )}
                </div>

                {/* Error */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-6 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {/* Loading spinner */}
                {loading && (
                    <div className="flex items-center justify-center py-16">
                        <svg className="animate-spin h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                    </div>
                )}

                {/* Results */}
                {result && !loading && (
                    <div className="space-y-6">
                        {/* Header */}
                        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                            <p className="text-xs text-gray-400 mb-0.5 uppercase tracking-wide font-medium">Comparing</p>
                            <div className="flex flex-col sm:flex-row gap-1 sm:gap-4 text-sm font-semibold text-gray-800">
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block"></span>
                                    A: {result.query_a}
                                </span>
                                <span className="text-gray-300 hidden sm:inline">vs</span>
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
                                    B: {result.query_b}
                                </span>
                            </div>
                        </div>

                        {/* Stats row */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-indigo-600">{result.n_shared}</p>
                                <p className="text-xs text-gray-500 mt-1">Shared genes</p>
                            </div>
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-indigo-600">
                                    {result.direction_agreement_pct !== null ? `${result.direction_agreement_pct}%` : '—'}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">Direction agreement</p>
                            </div>
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-indigo-600">
                                    {result.spearman_r !== null ? result.spearman_r.toFixed(2) : '—'}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">Spearman r (log HR)</p>
                            </div>
                        </div>

                        {/* HR Scatter plot */}
                        {scatterData.length > 0 && (
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                                <h3 className="text-sm font-semibold text-gray-700 mb-1">Hazard Ratio Correlation</h3>
                                <p className="text-xs text-gray-400 mb-3">
                                    Each point is a shared gene. X = log(HR) in A, Y = log(HR) in B.
                                    Red = both high-risk, Blue = both low-risk, Gray = direction disagrees.
                                </p>
                                <div className="h-72">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 40 }}>
                                            <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                                            <XAxis
                                                type="number"
                                                dataKey="log_hr_a"
                                                name="log HR (A)"
                                                label={{ value: 'log HR — A', position: 'insideBottom', offset: -15, fontSize: 11 }}
                                                tick={{ fontSize: 11 }}
                                            />
                                            <YAxis
                                                type="number"
                                                dataKey="log_hr_b"
                                                name="log HR (B)"
                                                label={{ value: 'log HR — B', angle: -90, position: 'insideLeft', offset: 10, fontSize: 11 }}
                                                tick={{ fontSize: 11 }}
                                            />
                                            <Tooltip
                                                content={({ active, payload }) => {
                                                    if (!active || !payload?.length) return null
                                                    const pt = payload[0].payload as ScatterPoint
                                                    return (
                                                        <div className="bg-white border border-gray-200 rounded shadow-md px-3 py-2 text-xs">
                                                            <p className="font-semibold text-gray-800 mb-1">{pt.gene_symbol}</p>
                                                            <p className="text-gray-600">HR-A: {pt.hr_a.toFixed(3)}</p>
                                                            <p className="text-gray-600">HR-B: {pt.hr_b.toFixed(3)}</p>
                                                            <p className={pt.direction_agrees ? 'text-green-600' : 'text-amber-600'}>
                                                                {pt.direction_agrees ? 'Direction agrees' : 'Direction differs'}
                                                            </p>
                                                        </div>
                                                    )
                                                }}
                                            />
                                            <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="4 4" />
                                            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
                                            <Scatter data={scatterData} isAnimationActive={false}>
                                                {scatterData.map((pt, idx) => (
                                                    <Cell key={idx} fill={pointColor(pt)} fillOpacity={0.8} r={5} />
                                                ))}
                                            </Scatter>
                                        </ScatterChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="flex gap-4 justify-center mt-2 text-xs text-gray-500">
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"></span> Both high-risk</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span> Both low-risk</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400 inline-block"></span> Direction differs</span>
                                </div>
                            </div>
                        )}

                        {/* Tabs */}
                        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                            <div className="flex border-b border-gray-200">
                                {(
                                    [
                                        { key: 'shared', label: `Shared Genes (${result.n_shared})` },
                                        { key: 'only_a', label: `Only in A (${result.n_unique_a})` },
                                        { key: 'only_b', label: `Only in B (${result.n_unique_b})` },
                                    ] as { key: ActiveTab; label: string }[]
                                ).map(({ key, label }) => (
                                    <button
                                        key={key}
                                        onClick={() => setActiveTab(key)}
                                        className={`px-5 py-3 text-sm font-medium transition-colors ${
                                            activeTab === key
                                                ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                                                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                                        }`}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>

                            <div className="p-4">
                                {/* Shared genes table */}
                                {activeTab === 'shared' && (
                                    result.shared_genes.length === 0 ? (
                                        <p className="text-sm text-gray-400 text-center py-8">No genes in common between the two analyses.</p>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="text-xs font-medium text-gray-500 uppercase border-b border-gray-100">
                                                        <th className="text-left py-2 pr-4">Gene</th>
                                                        <th className="text-right py-2 px-3">HR-A</th>
                                                        <th className="text-right py-2 px-3">HR-B</th>
                                                        <th className="text-right py-2 px-3">p-val A</th>
                                                        <th className="text-right py-2 px-3">p-val B</th>
                                                        <th className="text-right py-2 px-3">Datasets A</th>
                                                        <th className="text-right py-2 px-3">Datasets B</th>
                                                        <th className="text-center py-2 pl-3">Direction</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-50">
                                                    {result.shared_genes.map((g: GeneComparisonItem) => (
                                                        <tr key={g.gene_symbol} className="hover:bg-gray-50 transition-colors">
                                                            <td className="py-2 pr-4 font-semibold text-gray-800">{g.gene_symbol}</td>
                                                            <td className={`py-2 px-3 text-right tabular-nums ${g.hr_a > 1 ? 'text-red-600' : 'text-blue-600'}`}>
                                                                {g.hr_a.toFixed(3)}
                                                            </td>
                                                            <td className={`py-2 px-3 text-right tabular-nums ${g.hr_b > 1 ? 'text-red-600' : 'text-blue-600'}`}>
                                                                {g.hr_b.toFixed(3)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right tabular-nums text-gray-600">
                                                                {g.p_value_a < 0.001 ? g.p_value_a.toExponential(2) : g.p_value_a.toFixed(4)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right tabular-nums text-gray-600">
                                                                {g.p_value_b < 0.001 ? g.p_value_b.toExponential(2) : g.p_value_b.toFixed(4)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right text-gray-600">{g.n_datasets_a}</td>
                                                            <td className="py-2 px-3 text-right text-gray-600">{g.n_datasets_b}</td>
                                                            <td className="py-2 pl-3 text-center">
                                                                {g.direction_agrees ? (
                                                                    <span className="text-green-600 font-bold text-base" title="Direction agrees">✓</span>
                                                                ) : (
                                                                    <span className="text-amber-500 font-bold text-base" title="Direction differs">✗</span>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )
                                )}

                                {/* Unique to A */}
                                {activeTab === 'only_a' && (
                                    result.unique_to_a.length === 0 ? (
                                        <p className="text-sm text-gray-400 text-center py-8">No genes unique to Analysis A.</p>
                                    ) : (
                                        <div className="flex flex-wrap gap-2 py-2">
                                            {result.unique_to_a.map((sym) => (
                                                <span key={sym} className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-full border border-indigo-200">
                                                    {sym}
                                                </span>
                                            ))}
                                        </div>
                                    )
                                )}

                                {/* Unique to B */}
                                {activeTab === 'only_b' && (
                                    result.unique_to_b.length === 0 ? (
                                        <p className="text-sm text-gray-400 text-center py-8">No genes unique to Analysis B.</p>
                                    ) : (
                                        <div className="flex flex-wrap gap-2 py-2">
                                            {result.unique_to_b.map((sym) => (
                                                <span key={sym} className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-full border border-emerald-200">
                                                    {sym}
                                                </span>
                                            ))}
                                        </div>
                                    )
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}

export default ComparisonPage
