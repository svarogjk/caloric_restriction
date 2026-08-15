import React, { useMemo } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

export interface KMChartCurve {
    key: string
    label: string
    times: number[]
    survival_probabilities: number[]
    ci_lower?: number[] | null
    ci_upper?: number[] | null
    color: string
    strokeWidth?: number
    strokeOpacity?: number
    dashed?: boolean
    /** Explicit dash pattern (e.g. '2 4' for a fine dotted line, distinguishing a
     *  different-cohort curve from a solid same-cohort one). Overrides `dashed`. */
    strokeDasharray?: string
}

interface KaplanMeierChartProps {
    curves: KMChartCurve[]
    /** Unit the supplied `times` are already expressed in. Use 'years' when the
     *  caller has normalized heterogeneous cohorts onto one scale itself (see
     *  `timesToYears` in utils/signatureViz). */
    timeUnit?: 'days' | 'months' | 'years'
    height?: number
}

interface ChartRow { time: number; [key: string]: number }

function stepValue(times: number[], values: number[], time: number): number | undefined {
    if (times.length === 0) return undefined
    let val = 1.0
    for (let i = 0; i < times.length; i++) {
        if (times[i] <= time) val = values[i]
        else break
    }
    return val
}

function buildChartData(curves: KMChartCurve[]): ChartRow[] {
    const allTimes = new Set<number>([0])
    for (const c of curves) for (const t of c.times) allTimes.add(t)
    const sorted = Array.from(allTimes).sort((a, b) => a - b)

    return sorted.map((time) => {
        const row: ChartRow = { time }
        for (const c of curves) {
            const v = stepValue(c.times, c.survival_probabilities, time)
            if (v !== undefined) row[c.key] = v
            if (c.ci_lower && c.ci_lower.length) {
                const lo = stepValue(c.times, c.ci_lower, time)
                if (lo !== undefined) row[`${c.key}__ci_lower`] = lo
            }
            if (c.ci_upper && c.ci_upper.length) {
                const hi = stepValue(c.times, c.ci_upper, time)
                if (hi !== undefined) row[`${c.key}__ci_upper`] = hi
            }
        }
        return row
    })
}

/**
 * Shared Kaplan-Meier survival chart: step curves with optional CI bands on a
 * shared merged time axis. Consumers supply already-computed KM curves
 * (times + survival_probabilities, optionally ci_lower/ci_upper) — this
 * component only merges axes and renders, it fits nothing.
 */
const KaplanMeierChart: React.FC<KaplanMeierChartProps> = ({ curves, timeUnit = 'days', height = 240 }) => {
    const data = useMemo(() => buildChartData(curves), [curves])
    const perYear = timeUnit === 'years' ? 1 : timeUnit === 'months' ? 12 : 365

    if (data.length === 0) return null

    return (
        <div style={{ width: '100%', height }}>
            <ResponsiveContainer>
                <LineChart data={data} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                        dataKey="time"
                        // Numeric (not categorical) so Recharts picks a handful of
                        // evenly spaced ticks instead of one per event time, and
                        // so short follow-ups don't collapse to a row of "0"s.
                        type="number"
                        domain={[0, 'dataMax']}
                        tickFormatter={(t: number) => {
                            const yrs = t / perYear
                            return yrs < 3 ? yrs.toFixed(1) : yrs.toFixed(0)
                        }}
                        tick={{ fontSize: 10, fill: '#6b7280' }}
                        label={{ value: 'Years', position: 'insideBottom', offset: -10, fontSize: 10, fill: '#9ca3af' }}
                    />
                    <YAxis
                        domain={[0, 1]}
                        tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                        tick={{ fontSize: 10, fill: '#6b7280' }}
                        width={36}
                    />
                    <Tooltip
                        formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                        labelFormatter={(t: number) => `${(t / perYear).toFixed(1)} yr`}
                        contentStyle={{ fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {curves.flatMap((c) => [
                        <Line
                            key={c.key}
                            type="stepAfter"
                            dataKey={c.key}
                            name={c.label}
                            stroke={c.color}
                            strokeWidth={c.strokeWidth ?? 2}
                            strokeOpacity={c.strokeOpacity ?? 1}
                            strokeDasharray={c.strokeDasharray ?? (c.dashed ? '5 5' : undefined)}
                            dot={false}
                            connectNulls
                        />,
                        ...(c.ci_lower && c.ci_lower.length ? [
                            <Line
                                key={`${c.key}__ci_lower`}
                                type="stepAfter"
                                dataKey={`${c.key}__ci_lower`}
                                stroke={c.color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                            />,
                        ] : []),
                        ...(c.ci_upper && c.ci_upper.length ? [
                            <Line
                                key={`${c.key}__ci_upper`}
                                type="stepAfter"
                                dataKey={`${c.key}__ci_upper`}
                                stroke={c.color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                            />,
                        ] : []),
                    ])}
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}

export default KaplanMeierChart
