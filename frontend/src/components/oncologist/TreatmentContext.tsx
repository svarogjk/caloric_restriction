import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
    getTreatmentContext,
    TreatmentComparison,
    TreatmentComparisonResult,
} from '../../services/api'
import { GROUP_COLORS } from '../../utils/signatureViz'

interface TreatmentContextProps {
    cancerType: string
    expression: Record<string, number>
    clinical?: Record<string, string | number> | null
}

// Distinct line colours for each treatment (up to 6).
const TREATMENT_COLORS = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444']

function parseExpression(raw: string): Record<string, number> {
    const out: Record<string, number> = {}
    for (const line of raw.split('\n')) {
        const parts = line.trim().split(/\s+/)
        if (parts.length >= 2) {
            const val = parseFloat(parts[1])
            if (!isNaN(val)) out[parts[0].toUpperCase()] = val
        }
    }
    return out
}

function fiveYearSurvival(t: TreatmentComparison): string {
    if (!t.predicted_survival) return '—'
    const horizon = t.predicted_survival.find((h) => h.horizon_label === '5-year')
    if (!horizon) return '—'
    return `${(horizon.survival_probability * 100).toFixed(0)}%`
}

interface KMPoint { time: number; [key: string]: number }

function buildMultiKM(treatments: TreatmentComparison[], patientRiskGroup: string | null): KMPoint[] {
    const allTimes = new Set<number>([0])
    const curves: Array<{ key: string; times: number[]; probs: number[] }> = []

    for (const t of treatments) {
        if (!t.reference_km || t.is_building) continue
        const group = (t.risk_group ?? patientRiskGroup ?? 'low').toLowerCase()
        const curve = t.reference_km.find((c) => c.group === group) ?? t.reference_km[0]
        if (!curve) continue
        curves.push({ key: t.slug, times: curve.times, probs: curve.survival_probabilities })
        curve.times.forEach((ti) => allTimes.add(Math.round(ti)))
    }

    const sortedTimes = Array.from(allTimes).sort((a, b) => a - b)
    return sortedTimes.map((time) => {
        const row: KMPoint = { time }
        for (const { key, times, probs } of curves) {
            let prob = 1
            for (let i = times.length - 1; i >= 0; i--) {
                if (times[i] <= time) { prob = probs[i]; break }
            }
            row[key] = Math.round(prob * 1000) / 1000
        }
        return row
    })
}

const TreatmentContext: React.FC<TreatmentContextProps> = ({ cancerType, expression, clinical }) => {
    const [data, setData] = useState<TreatmentComparisonResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    const fetchData = useCallback(async () => {
        try {
            const result = await getTreatmentContext({ cancer_type: cancerType, expression, clinical })
            setData(result)
            setError(null)
            // Poll again if any are still building.
            if (result.treatments.some((t) => t.is_building)) {
                pollRef.current = setTimeout(fetchData, 15_000)
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load treatment context')
        }
    }, [cancerType, expression, clinical])

    useEffect(() => {
        fetchData()
        return () => { if (pollRef.current) clearTimeout(pollRef.current) }
    }, [fetchData])

    const patientRiskGroup = data?.treatments.find((t) => t.risk_group)?.risk_group ?? null
    const ready = data?.treatments.filter((t) => !t.is_building && !t.build_error) ?? []
    const building = data?.treatments.filter((t) => t.is_building) ?? []
    const failed = data?.treatments.filter((t) => t.build_error) ?? []
    const kmData = data ? buildMultiKM(data.treatments, patientRiskGroup) : []

    return (
        <div className="mt-6 space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-base font-semibold text-gray-800">Treatment context</h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                        Historical outcomes from GEO cohorts receiving each treatment — patients in the same
                        risk group as yours — to help weigh options. Advisory, not a prescription or a
                        prediction that you will respond.
                    </p>
                </div>
                <span className="flex-shrink-0 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Research use only
                </span>
            </div>

            {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">{error}</div>
            )}

            {!data && !error && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                    Loading treatment cohort data…
                </div>
            )}

            {/* Building notice */}
            {building.length > 0 && (
                <div className="text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 rounded p-3 flex items-center gap-2">
                    <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                    Building cohort models for {building.map((t) => t.name).join(', ')}… (~2 min each, auto-refreshing)
                </div>
            )}

            {/* Multi-treatment KM chart */}
            {ready.length > 0 && kmData.length > 1 && (
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <p className="text-xs font-medium text-gray-600 mb-3">
                        Kaplan-Meier curves — {patientRiskGroup?.toUpperCase() ?? 'assigned'} risk group, per treatment cohort
                    </p>
                    <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={kmData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis
                                dataKey="time"
                                tick={{ fontSize: 10, fill: '#6b7280' }}
                                label={{ value: 'Days', position: 'insideBottomRight', offset: -4, fontSize: 10, fill: '#9ca3af' }}
                            />
                            <YAxis
                                domain={[0, 1]}
                                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                                tick={{ fontSize: 10, fill: '#6b7280' }}
                                width={36}
                            />
                            <Tooltip
                                formatter={(val: number, name: string) => {
                                    const t = ready.find((r) => r.slug === name)
                                    return [`${(val * 100).toFixed(1)}%`, t?.name ?? name]
                                }}
                                labelFormatter={(label: number) => `Day ${label}`}
                                contentStyle={{ fontSize: 11 }}
                            />
                            <Legend
                                formatter={(value: string) => {
                                    const t = ready.find((r) => r.slug === value)
                                    return <span style={{ fontSize: 10 }}>{t?.name ?? value}</span>
                                }}
                            />
                            {ready.map((t, i) => (
                                <Line
                                    key={t.slug}
                                    type="stepAfter"
                                    dataKey={t.slug}
                                    stroke={TREATMENT_COLORS[i % TREATMENT_COLORS.length]}
                                    dot={false}
                                    strokeWidth={2}
                                    connectNulls
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Comparison table */}
            {data && (
                <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                        <thead>
                            <tr className="bg-gray-50 text-gray-500 text-left">
                                <th className="px-3 py-2 font-medium border-b border-gray-200">Treatment</th>
                                <th className="px-3 py-2 font-medium border-b border-gray-200">Your risk group</th>
                                <th className="px-3 py-2 font-medium border-b border-gray-200">5-yr survival</th>
                                <th className="px-3 py-2 font-medium border-b border-gray-200">C-index</th>
                                <th className="px-3 py-2 font-medium border-b border-gray-200">Cohorts</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.treatments.map((t, i) => (
                                <tr key={t.slug} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                                    <td className="px-3 py-2.5 font-medium text-gray-700 border-b border-gray-100">
                                        <div className="flex items-center gap-2">
                                            {!t.is_building && !t.build_error && (
                                                <span
                                                    className="w-2 h-2 rounded-full flex-shrink-0"
                                                    style={{ backgroundColor: TREATMENT_COLORS[i % TREATMENT_COLORS.length] }}
                                                />
                                            )}
                                            {t.name}
                                        </div>
                                    </td>
                                    <td className="px-3 py-2.5 border-b border-gray-100">
                                        {t.is_building ? (
                                            <span className="text-indigo-500 italic">Building…</span>
                                        ) : t.build_error ? (
                                            <span className="text-red-400">Error</span>
                                        ) : (
                                            <span
                                                className="px-2 py-0.5 rounded-full text-white text-[11px] font-semibold"
                                                style={{ backgroundColor: GROUP_COLORS[t.risk_group ?? 'low'] ?? '#6b7280' }}
                                            >
                                                {t.risk_group?.toUpperCase() ?? '—'}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-3 py-2.5 border-b border-gray-100 tabular-nums">
                                        {t.is_building ? '—' : fiveYearSurvival(t)}
                                    </td>
                                    <td className="px-3 py-2.5 border-b border-gray-100 tabular-nums text-gray-500">
                                        {t.pooled_c_index != null ? t.pooled_c_index.toFixed(2) : '—'}
                                    </td>
                                    <td className="px-3 py-2.5 border-b border-gray-100 text-gray-500">
                                        {t.n_cohorts != null ? `${t.n_cohorts} (n=${t.n_patients ?? '?'})` : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {failed.length > 0 && (
                <p className="text-[11px] text-gray-400">
                    Could not build models for: {failed.map((t) => t.name).join(', ')}.
                    These treatments may not have enough matching GEO datasets.
                </p>
            )}

            {data && (
                <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-2">
                    {data.treatments[0]?.disclaimer}
                </p>
            )}
        </div>
    )
}

interface TreatmentContextToggleProps {
    cancerType: string | null
    expressionRaw: string
    clinical?: Record<string, string | number> | null
}

export const TreatmentContextToggle: React.FC<TreatmentContextToggleProps> = ({
    cancerType, expressionRaw, clinical,
}) => {
    const [open, setOpen] = useState(false)

    if (!cancerType) return null
    const expression = parseExpression(expressionRaw)
    if (Object.keys(expression).length < 10) return null

    return (
        <div className="mt-4">
            <button
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-2 text-sm text-indigo-600 font-medium hover:text-indigo-800 transition-colors"
            >
                <svg
                    className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Compare treatment outcomes
                <span className="text-xs text-gray-400 font-normal">
                    — how do treated cohorts compare?
                </span>
            </button>
            {open && (
                <TreatmentContext
                    cancerType={cancerType}
                    expression={expression}
                    clinical={clinical}
                />
            )}
        </div>
    )
}

export default TreatmentContext
