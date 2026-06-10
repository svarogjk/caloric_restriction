import { ReferenceKMCurve } from '../services/api'

/** Risk-group colours shared by the signature panel and Oncologist Mode. */
export const GROUP_COLORS: Record<string, string> = {
    low: '#22c55e',
    intermediate: '#f59e0b',
    high: '#ef4444',
}

/** Parse pasted "GENE value" lines (space/comma/colon/tab separated) into a map. */
export function parsePastedExpression(text: string): Record<string, number> {
    const out: Record<string, number> = {}
    for (const line of text.split('\n')) {
        const m = line.trim().match(/^([A-Za-z0-9_.-]+)[\s,:\t]+(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)/)
        if (m) {
            out[m[1].toUpperCase()] = parseFloat(m[2])
        }
    }
    return out
}

/** Merge step KM curves onto a shared sorted time axis for Recharts. */
export function buildKMChartData(curves: ReferenceKMCurve[]): Array<Record<string, number>> {
    const allTimes = new Set<number>()
    for (const c of curves) for (const t of c.times) allTimes.add(t)
    const sorted = Array.from(allTimes).sort((a, b) => a - b)
    if (sorted.length === 0) return []

    const stepValue = (curve: ReferenceKMCurve, time: number): number | undefined => {
        if (curve.times.length === 0) return undefined
        let val = 1.0
        for (let i = 0; i < curve.times.length; i++) {
            if (curve.times[i] <= time) val = curve.survival_probabilities[i]
            else break
        }
        return val
    }

    return sorted.map((time) => {
        const row: Record<string, number> = { time }
        for (const c of curves) {
            const v = stepValue(c, time)
            if (v !== undefined) row[c.group] = v
        }
        return row
    })
}
