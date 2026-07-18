import { ReferenceKMCurve, TreatmentComparison, SurvivalAtHorizon } from '../services/api'
import { KMChartCurve } from '../components/KaplanMeierChart'

/** Risk-group colours shared by the signature panel and Oncologist Mode. */
export const GROUP_COLORS: Record<string, string> = {
    low: '#22c55e',
    intermediate: '#f59e0b',
    high: '#ef4444',
}

/** Distinct line colours for each treatment cohort in a multi-treatment KM chart (up to 6). */
export const TREATMENT_COLORS = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444']

/** 5-year survival probability for one treatment cohort, formatted for display. */
export function fiveYearSurvival(t: TreatmentComparison): string {
    const horizon = t.predicted_survival?.find((h: SurvivalAtHorizon) => h.horizon_label === '5-year')
    if (!horizon) return '—'
    return `${(horizon.survival_probability * 100).toFixed(0)}%`
}

/** One KM curve per ready treatment cohort — the patient's assigned risk group within
 *  each treatment-specific model — for a shared multi-treatment KaplanMeierChart.
 *  When `baseline` is supplied (the patient's own predicted curve, unrelated to any
 *  treatment-specific model), it is prepended as a neutral dashed reference line so
 *  it's directly comparable against each treatment's cohort curve on the same plot. */
export function treatmentComparisonCurves(
    treatments: TreatmentComparison[], patientRiskGroup: string | null,
    baseline?: ReferenceKMCurve | null,
): KMChartCurve[] {
    // Index by position in the full list (not the filtered "ready" subset) so a
    // treatment's colour always matches between this chart and the comparison table.
    const curves: KMChartCurve[] = treatments.flatMap((t, i) => {
        if (!t.reference_km || t.is_building) return []
        const group = (t.risk_group ?? patientRiskGroup ?? 'low').toLowerCase()
        const curve = t.reference_km.find((c) => c.group === group) ?? t.reference_km[0]
        if (!curve) return []
        return [{
            key: t.slug,
            label: t.name,
            times: curve.times,
            survival_probabilities: curve.survival_probabilities,
            color: TREATMENT_COLORS[i % TREATMENT_COLORS.length],
        }]
    })

    if (baseline && baseline.times.length > 0) {
        curves.unshift({
            key: '__baseline',
            label: 'Your predicted survival (current)',
            times: baseline.times,
            survival_probabilities: baseline.survival_probabilities,
            color: '#374151',
            strokeWidth: 3,
            dashed: true,
        })
    }

    return curves
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
