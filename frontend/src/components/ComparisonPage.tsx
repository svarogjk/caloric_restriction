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
        <div className="min-h-screen bg-surface-sunken">
            {/* Nav */}
            <nav className="bg-surface shadow-sm border-b border-border">
                <div className="max-w-5xl mx-auto px-4">
                    <div className="flex items-center justify-between h-14">
                        <Link to="/" className="text-xl font-semibold text-fg-strong hover:text-accent-fg transition-colors">
                            GEO Survival Analysis
                        </Link>
                        <div className="flex items-center gap-4">
                            <Link to="/history" className="text-sm font-medium text-fg-muted hover:text-accent-fg transition-colors">
                                History
                            </Link>
                            <Link to="/compare" className="text-sm font-medium text-accent-fg border-b-2 border-accent pb-0.5">
                                Compare
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-5xl mx-auto px-4 py-6">
                <h2 className="text-2xl font-bold text-fg-strong mb-1">Analysis Comparison</h2>
                <p className="text-sm text-fg-muted mb-6">
                    Find genes significant across two independent studies — e.g. breast cancer vs lung cancer.
                </p>

                {/* Selectors */}
                <div className="bg-surface rounded-lg border border-border shadow-sm p-5 mb-6">
                    {historyLoading ? (
                        <div className="flex items-center justify-center py-8">
                            <svg className="animate-spin h-6 w-6 text-accent-fg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        </div>
                    ) : analysisHistory.length < 2 ? (
                        <p className="text-sm text-fg-muted text-center py-4">
                            You need at least two saved analyses to compare.{' '}
                            <Link to="/" className="text-accent-fg hover:underline">Run an analysis</Link>.
                        </p>
                    ) : (
                        <div className="flex flex-col sm:flex-row gap-4 items-end">
                            <div className="flex-1">
                                <label className="block text-xs font-medium text-fg-muted mb-1">Analysis A</label>
                                <select
                                    value={selectedA}
                                    onChange={(e) => setSelectedA(e.target.value)}
                                    className="w-full text-sm border border-border-strong rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-ring bg-surface"
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
                                <label className="block text-xs font-medium text-fg-muted mb-1">Analysis B</label>
                                <select
                                    value={selectedB}
                                    onChange={(e) => setSelectedB(e.target.value)}
                                    className="w-full text-sm border border-border-strong rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-ring bg-surface"
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
                                className="px-5 py-2 text-sm font-medium rounded-lg bg-accent text-on-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                            >
                                {loading ? 'Comparing...' : 'Compare'}
                            </button>
                        </div>
                    )}
                    {selectedA === selectedB && selectedA !== '' && (
                        <p className="text-xs text-warn mt-2">Select two different analyses to compare.</p>
                    )}
                </div>

                {/* Error */}
                {error && (
                    <div className="bg-danger-soft border border-danger-border rounded-lg px-4 py-3 mb-6 text-sm text-danger">
                        {error}
                    </div>
                )}

                {/* Loading spinner */}
                {loading && (
                    <div className="flex items-center justify-center py-16">
                        <svg className="animate-spin h-8 w-8 text-accent-fg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                    </div>
                )}

                {/* Results */}
                {result && !loading && (
                    <div className="space-y-6">
                        {/* Header */}
                        <div className="bg-surface rounded-lg border border-border shadow-sm p-4">
                            <p className="text-xs text-fg-faint mb-0.5 uppercase tracking-wide font-medium">Comparing</p>
                            <div className="flex flex-col sm:flex-row gap-1 sm:gap-4 text-sm font-semibold text-fg-strong">
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-accent inline-block"></span>
                                    A: {result.query_a}
                                </span>
                                <span className="text-fg-faint hidden sm:inline">vs</span>
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-ok inline-block"></span>
                                    B: {result.query_b}
                                </span>
                            </div>
                        </div>

                        {/* Stats row */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-surface rounded-lg border border-border shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-accent-fg">{result.n_shared}</p>
                                <p className="text-xs text-fg-muted mt-1">Shared genes</p>
                            </div>
                            <div className="bg-surface rounded-lg border border-border shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-accent-fg">
                                    {result.direction_agreement_pct !== null ? `${result.direction_agreement_pct}%` : '—'}
                                </p>
                                <p className="text-xs text-fg-muted mt-1">Direction agreement</p>
                            </div>
                            <div className="bg-surface rounded-lg border border-border shadow-sm p-4 text-center">
                                <p className="text-3xl font-bold text-accent-fg">
                                    {result.spearman_r !== null ? result.spearman_r.toFixed(2) : '—'}
                                </p>
                                <p className="text-xs text-fg-muted mt-1">Spearman r (log HR)</p>
                            </div>
                        </div>

                        {/* HR Scatter plot */}
                        {scatterData.length > 0 && (
                            <div className="bg-surface rounded-lg border border-border shadow-sm p-4">
                                <h3 className="text-sm font-semibold text-fg mb-1">Hazard Ratio Correlation</h3>
                                <p className="text-xs text-fg-faint mb-3">
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
                                                        <div className="bg-surface border border-border rounded shadow-md px-3 py-2 text-xs">
                                                            <p className="font-semibold text-fg-strong mb-1">{pt.gene_symbol}</p>
                                                            <p className="text-fg-muted">HR-A: {pt.hr_a.toFixed(3)}</p>
                                                            <p className="text-fg-muted">HR-B: {pt.hr_b.toFixed(3)}</p>
                                                            <p className={pt.direction_agrees ? 'text-ok' : 'text-warn'}>
                                                                {pt.direction_agrees ? 'Direction agrees' : 'Direction differs'}
                                                            </p>
                                                        </div>
                                                    )
                                                }}
                                            />
                                            <ReferenceLine x={0} stroke="var(--color-chart-label)" strokeDasharray="4 4" />
                                            <ReferenceLine y={0} stroke="var(--color-chart-label)" strokeDasharray="4 4" />
                                            <Scatter data={scatterData} isAnimationActive={false}>
                                                {scatterData.map((pt, idx) => (
                                                    <Cell key={idx} fill={pointColor(pt)} fillOpacity={0.8} r={5} />
                                                ))}
                                            </Scatter>
                                        </ScatterChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="flex gap-4 justify-center mt-2 text-xs text-fg-muted">
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger inline-block"></span> Both high-risk</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent inline-block"></span> Both low-risk</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-fg-faint inline-block"></span> Direction differs</span>
                                </div>
                            </div>
                        )}

                        {/* Tabs */}
                        <div className="bg-surface rounded-lg border border-border shadow-sm overflow-hidden">
                            <div className="flex border-b border-border">
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
                                                ? 'text-accent-fg border-b-2 border-accent bg-accent-soft'
                                                : 'text-fg-muted hover:text-fg hover:bg-surface-sunken'
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
                                        <p className="text-sm text-fg-faint text-center py-8">No genes in common between the two analyses.</p>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="text-xs font-medium text-fg-muted uppercase border-b border-border">
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
                                                <tbody className="divide-y divide-border">
                                                    {result.shared_genes.map((g: GeneComparisonItem) => (
                                                        <tr key={g.gene_symbol} className="hover:bg-surface-sunken transition-colors">
                                                            <td className="py-2 pr-4 font-semibold text-fg-strong">{g.gene_symbol}</td>
                                                            <td className={`py-2 px-3 text-right tabular-nums ${g.hr_a > 1 ? 'text-danger' : 'text-accent-fg'}`}>
                                                                {g.hr_a.toFixed(3)}
                                                            </td>
                                                            <td className={`py-2 px-3 text-right tabular-nums ${g.hr_b > 1 ? 'text-danger' : 'text-accent-fg'}`}>
                                                                {g.hr_b.toFixed(3)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right tabular-nums text-fg-muted">
                                                                {g.p_value_a < 0.001 ? g.p_value_a.toExponential(2) : g.p_value_a.toFixed(4)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right tabular-nums text-fg-muted">
                                                                {g.p_value_b < 0.001 ? g.p_value_b.toExponential(2) : g.p_value_b.toFixed(4)}
                                                            </td>
                                                            <td className="py-2 px-3 text-right text-fg-muted">{g.n_datasets_a}</td>
                                                            <td className="py-2 px-3 text-right text-fg-muted">{g.n_datasets_b}</td>
                                                            <td className="py-2 pl-3 text-center">
                                                                {g.direction_agrees ? (
                                                                    <span className="text-ok font-bold text-base" title="Direction agrees">✓</span>
                                                                ) : (
                                                                    <span className="text-warn font-bold text-base" title="Direction differs">✗</span>
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
                                        <p className="text-sm text-fg-faint text-center py-8">No genes unique to Analysis A.</p>
                                    ) : (
                                        <div className="flex flex-wrap gap-2 py-2">
                                            {result.unique_to_a.map((sym) => (
                                                <span key={sym} className="px-2.5 py-1 bg-accent-soft text-accent-fg text-xs font-medium rounded-full border border-border-accent">
                                                    {sym}
                                                </span>
                                            ))}
                                        </div>
                                    )
                                )}

                                {/* Unique to B */}
                                {activeTab === 'only_b' && (
                                    result.unique_to_b.length === 0 ? (
                                        <p className="text-sm text-fg-faint text-center py-8">No genes unique to Analysis B.</p>
                                    ) : (
                                        <div className="flex flex-wrap gap-2 py-2">
                                            {result.unique_to_b.map((sym) => (
                                                <span key={sym} className="px-2.5 py-1 bg-ok-soft text-ok text-xs font-medium rounded-full border border-ok-border">
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
