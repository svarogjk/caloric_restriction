import { ReferenceKMCurve, TreatmentKMEvidence } from '../services/api'
import { KMChartCurve } from '../components/KaplanMeierChart'

/** Risk-group colours shared by the signature panel and Oncologist Mode. */
export const GROUP_COLORS: Record<string, string> = {
    low: '#22c55e',
    intermediate: '#f59e0b',
    high: '#ef4444',
}

/** Distinct line colours for each treatment cohort in a multi-treatment KM chart (up to 10). */
export const TREATMENT_COLORS = [
    '#3b82f6', // blue
    '#ec4899', // pink
    '#22c55e', // green
    '#8b5cf6', // violet
    '#f59e0b', // amber
    '#ef4444', // red
    '#14b8a6', // teal
    '#f97316', // orange
    '#06b6d4', // cyan
    '#a855f7', // purple
]

// Minimum evidentiary bar before a cohort KM curve is plotted at all — below
// this, a curve is too unstable/misleading to show even when the backend
// technically returns one (e.g. a risk tertile that ends up with 1 event
// after a whole-cohort floor was checked pre-split). Matches this codebase's
// MIN_EVENTS convention (`SignatureService.MIN_EVENTS`); the sample floor is
// a companion stability check for the same reason.
const MIN_CURVE_EVENTS = 5
const MIN_CURVE_SAMPLES = 15

export interface InsufficientCurve {
    drug: string
    nSamples: number
    nEvents: number
}

export interface TopTreatmentCurves {
    curves: KMChartCurve[]
    /** Drugs whose cohort data resolved but didn't clear the minimum n/events
     *  bar to plot responsibly — surfaced as a footnote, never silently dropped. */
    insufficientN: InsufficientCurve[]
}

export type DrugCurveOutcome = 'plottable' | 'insufficient' | 'unavailable' | 'not_checked' | 'building'

/** Classifies whether a drug's cohort KM data (if any) will actually produce a
 *  plotted curve — shared by the color assignment below and by top-N backfill
 *  decisions, so both agree on what counts as "has a real curve" without
 *  duplicating the tier/threshold logic. */
export function classifyDrugCurve(
    drug: string,
    cohortKm: Record<string, TreatmentKMEvidence>,
    patientRiskGroup: string | null,
): DrugCurveOutcome {
    const km = cohortKm[drug.toLowerCase()]
    if (!km) return 'not_checked'
    if (km.is_building) return 'building'
    if (km.tier === 'not_checked') return 'not_checked'
    if (km.tier === 'unavailable') return 'unavailable'
    if (km.tier === 'arm_comparison' && km.arms && km.arms.length > 0) {
        const arm = km.arms[km.arms.length - 1]
        return arm.n_events < MIN_CURVE_EVENTS || arm.n_samples < MIN_CURVE_SAMPLES ? 'insufficient' : 'plottable'
    }
    if (km.tier === 'cohort_reference' && km.reference_km && km.reference_km.length > 0) {
        const group = (patientRiskGroup ?? 'low').toLowerCase()
        const curve = km.reference_km.find((c) => c.group === group) ?? km.reference_km[0]
        return curve.n_events < MIN_CURVE_EVENTS || curve.n_samples < MIN_CURVE_SAMPLES ? 'insufficient' : 'plottable'
    }
    return 'unavailable'
}

/** One representative KM curve per drug, built from its real-GEO-cohort evidence
 *  (F24b `cohort_km`), for the combined top-N treatment comparison chart.
 *
 *  Tier 1 ("arm_comparison" — treated vs untreated within the patient's own
 *  training cohort) is drawn solid: observational, but at least same-population.
 *  Tier 2 ("cohort_reference" — a treatment-matched but otherwise DIFFERENT GEO
 *  cohort) is drawn finely dotted and visually subordinate, since it is not
 *  directly comparable to the patient's baseline population. When `baseline` is
 *  supplied (the patient's own predicted curve), it is prepended as a thick
 *  dashed reference line. Every plotted curve's label carries its n/event count
 *  so a reader never has to cross-reference the table to judge stability. */
export function topTreatmentCurves(
    drugs: string[],
    cohortKm: Record<string, TreatmentKMEvidence>,
    patientRiskGroup: string | null,
    baseline?: ReferenceKMCurve | null,
): TopTreatmentCurves {
    const insufficientN: InsufficientCurve[] = []
    const curves: KMChartCurve[] = []
    // Color index only advances when a curve is actually pushed below — drugs
    // with no data, still building, not yet checked, or below the min n/events
    // bar must never consume a palette slot, or real curves get pushed further
    // apart in the palette (or wrap and repeat) than necessary.
    let colorIdx = 0
    for (const drug of drugs) {
        const km = cohortKm[drug.toLowerCase()]
        if (!km || km.is_building) continue
        if (km.tier === 'arm_comparison' && km.arms && km.arms.length > 0) {
            const arm = km.arms[km.arms.length - 1]
            if (arm.n_events < MIN_CURVE_EVENTS || arm.n_samples < MIN_CURVE_SAMPLES) {
                insufficientN.push({ drug, nSamples: arm.n_samples, nEvents: arm.n_events })
                continue
            }
            curves.push({
                key: drug,
                label: `${drug} (n=${arm.n_samples}, ${arm.n_events} events, same-cohort)`,
                times: arm.km_curve.times,
                survival_probabilities: arm.km_curve.survival_probabilities,
                ci_lower: arm.km_curve.ci_lower,
                ci_upper: arm.km_curve.ci_upper,
                color: TREATMENT_COLORS[colorIdx++ % TREATMENT_COLORS.length],
            })
            continue
        }
        if (km.tier === 'cohort_reference' && km.reference_km && km.reference_km.length > 0) {
            const group = (patientRiskGroup ?? 'low').toLowerCase()
            const curve = km.reference_km.find((c) => c.group === group) ?? km.reference_km[0]
            if (curve.n_events < MIN_CURVE_EVENTS || curve.n_samples < MIN_CURVE_SAMPLES) {
                insufficientN.push({ drug, nSamples: curve.n_samples, nEvents: curve.n_events })
                continue
            }
            curves.push({
                key: drug,
                label: `${drug} (n=${curve.n_samples}, ${curve.n_events} events, different cohort)`,
                times: curve.times,
                survival_probabilities: curve.survival_probabilities,
                color: TREATMENT_COLORS[colorIdx++ % TREATMENT_COLORS.length],
                strokeDasharray: '2 3',
            })
        }
    }

    if (baseline && baseline.times.length > 0) {
        curves.unshift({
            key: '__baseline',
            label: 'Your predicted survival (current)',
            times: baseline.times,
            survival_probabilities: baseline.survival_probabilities,
            color: '#374151',
            strokeWidth: 3,
            strokeDasharray: '8 4',
        })
    }

    return { curves, insufficientN }
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
