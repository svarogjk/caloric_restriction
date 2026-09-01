import { ReferenceKMCurve, TreatmentKMEvidence, SignatureGene } from '../services/api'
import { KMChartCurve } from '../components/KaplanMeierChart'

/**
 * Risk-group colours shared by the signature panel and Oncologist Mode.
 * Recharts fills/strokes can't read Tailwind classes, so this stays the source
 * of truth for chart colors — MUST stay equal to --color-risk-* in index.css.
 */
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
    /** Drugs whose only evidence is a different-cohort risk-tertile curve, with
     *  no tumour profile to say which tertile is comparable. Disclosed rather
     *  than plotted against an arbitrary tertile. */
    needsPatientProfile: string[]
    /** The window (in years) every plotted cohort actually observed — all curves
     *  are truncated to it. Disclosed in the caption so a reader knows the
     *  comparison isn't extrapolated past somebody's follow-up. */
    horizonYears: number
    /** Set when the patient's baseline curve was deliberately NOT overlaid,
     *  explaining why. Overlaying a curve from a different cohort with
     *  different follow-up invites reading the gap as a treatment effect. */
    baselineOmittedReason?: string
}

/** Put KM times on a common scale (years), from whatever unit the source cohort
 *  reported. Curves here are merged from INDEPENDENTLY built models whose GEO
 *  metadata may report days, months or years (e.g. a baseline cohort in days
 *  alongside a treatment cohort in years). Merging them unconverted makes a
 *  difference in FOLLOW-UP LENGTH look like a difference in outcome — which is
 *  exactly how a treated cohort ends up drawn below an untreated baseline. */
export function timesToYears(times: number[], unit?: string | null): number[] {
    const u = (unit ?? 'days').toLowerCase()
    const per = u.startsWith('year') ? 1 : u.startsWith('month') ? 12 : 365.25
    return times.map((t) => t / per)
}

export type DrugCurveOutcome =
    | 'plottable'
    | 'insufficient'
    | 'unavailable'
    | 'not_checked'
    | 'building'
    /** A different-cohort (Tier-2) curve with no patient to pick the comparable
     *  risk group. See the guard in classifyDrugCurve for why this is not
     *  silently defaulted. */
    | 'needs_patient_profile'

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
        // BOTH arms must be stable — a treated-vs-untreated contrast built on a
        // solid treated arm and a 3-patient control arm is not interpretable.
        return km.arms.some((a) => a.n_events < MIN_CURVE_EVENTS || a.n_samples < MIN_CURVE_SAMPLES)
            ? 'insufficient'
            : 'plottable'
    }
    if (km.tier === 'cohort_reference' && km.reference_km && km.reference_km.length > 0) {
        // With no patient AND no per-cohort scoring there is no basis for
        // choosing a tertile. Defaulting to 'low' — as this used to — plots the
        // best-surviving third of a cohort and labels it as the drug's outcome,
        // which is systematically optimistic. Withhold it instead; the Tier-1
        // treated-vs-untreated contrast is the honest one without a patient.
        if (!km.matched_risk_group && !patientRiskGroup) return 'needs_patient_profile'
        const group = (km.matched_risk_group ?? patientRiskGroup)!.toLowerCase()
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
    baselineTimeUnit?: string | null,
): TopTreatmentCurves {
    const insufficientN: InsufficientCurve[] = []
    const needsPatientProfile: string[] = []
    const pending: KMChartCurve[] = []
    // Each pending curve's source time unit, tracked in parallel: these come
    // from independently built models and are NOT guaranteed to agree.
    const units: string[] = []
    // Color index only advances when a curve is actually pushed below — drugs
    // with no data, still building, not yet checked, or below the min n/events
    // bar must never consume a palette slot, or real curves get pushed further
    // apart in the palette (or wrap and repeat) than necessary.
    let colorIdx = 0
    // Several drugs routinely resolve to the SAME GEO series (the drug-name
    // query returns a generic cancer dataset regardless of the drug named).
    // Their curves are then identical by construction, so drawing one per drug
    // paints N lines on top of each other and implies replication that isn't
    // there. Emit one entry per cohort and name the drugs that share it.
    const drugsByAccession: Record<string, string[]> = {}
    for (const d of drugs) {
        const k = cohortKm[d.toLowerCase()]
        if (k && !k.is_building && k.accession && !k.same_cohort) {
            ;(drugsByAccession[k.accession] ??= []).push(d)
        }
    }
    const emittedAccessions = new Set<string>()
    let hasSameCohortCurve = false

    for (const drug of drugs) {
        const km = cohortKm[drug.toLowerCase()]
        if (!km || km.is_building) continue

        const shared = km.accession && !km.same_cohort ? drugsByAccession[km.accession] ?? [drug] : [drug]
        if (km.accession && !km.same_cohort) {
            if (emittedAccessions.has(km.accession)) continue
            emittedAccessions.add(km.accession)
        }
        // When a cohort is shared, the curve describes the cohort, not any one
        // drug — label it that way instead of picking a drug name arbitrarily.
        const subject = shared.length > 1
            ? `${km.arm_variable ?? 'Treatment'} cohort (${shared.slice(0, 3).join(', ')}${shared.length > 3 ? `, +${shared.length - 3}` : ''})`
            : drug

        if (km.tier === 'arm_comparison' && km.arms && km.arms.length > 0) {
            const bad = km.arms.find(
                (a) => a.n_events < MIN_CURVE_EVENTS || a.n_samples < MIN_CURVE_SAMPLES,
            )
            if (bad) {
                insufficientN.push({ drug, nSamples: bad.n_samples, nEvents: bad.n_events })
                continue
            }
            const color = TREATMENT_COLORS[colorIdx++ % TREATMENT_COLORS.length]
            const where = km.same_cohort ? 'same-cohort' : km.accession ?? 'different cohort'
            if (km.same_cohort) hasSameCohortCurve = true
            // Plot EVERY arm. Previously only the last (treated) arm was drawn,
            // which silently discarded the untreated comparator — the one thing
            // that makes this a treatment contrast rather than a lone curve.
            km.arms.forEach((arm, i) => {
                const isTreated = i === km.arms!.length - 1
                pending.push({
                    key: `${km.accession ?? drug}__arm${i}`,
                    label: `${subject} — ${arm.name} (n=${arm.n_samples}, ${arm.n_events} events, ${where})`,
                    times: arm.km_curve.times,
                    survival_probabilities: arm.km_curve.survival_probabilities,
                    ci_lower: arm.km_curve.ci_lower,
                    ci_upper: arm.km_curve.ci_upper,
                    color,
                    // Treated solid, its own control dashed + faded: one visual
                    // pair, so the gap between them reads as the contrast.
                    strokeWidth: isTreated ? 2.5 : 1.5,
                    strokeOpacity: isTreated ? 1 : 0.55,
                    strokeDasharray: isTreated ? undefined : '4 3',
                })
                units.push(km.time_unit ?? baselineTimeUnit ?? 'days')
            })
            continue
        }
        if (km.tier === 'cohort_reference' && km.reference_km && km.reference_km.length > 0) {
            // Prefer the group this patient actually scores into under THIS
            // treatment cohort's own model (see TreatmentKMEvidence doc) —
            // only fall back to the baseline's risk-group label (a different
            // model's tertile boundaries) if per-cohort scoring didn't run.
            // With neither, there is no comparable tertile: see classifyDrugCurve.
            if (!km.matched_risk_group && !patientRiskGroup) {
                needsPatientProfile.push(drug)
                continue
            }
            const group = (km.matched_risk_group ?? patientRiskGroup)!.toLowerCase()
            const curve = km.reference_km.find((c) => c.group === group) ?? km.reference_km[0]
            if (curve.n_events < MIN_CURVE_EVENTS || curve.n_samples < MIN_CURVE_SAMPLES) {
                insufficientN.push({ drug, nSamples: curve.n_samples, nEvents: curve.n_events })
                continue
            }
            pending.push({
                key: km.accession ?? drug,
                label: `${subject} (n=${curve.n_samples}, ${curve.n_events} events, different cohort — treated only, no control arm)`,
                times: curve.times,
                survival_probabilities: curve.survival_probabilities,
                color: TREATMENT_COLORS[colorIdx++ % TREATMENT_COLORS.length],
                strokeDasharray: '2 3',
            })
            units.push(km.time_unit ?? 'days')
        }
    }

    // The patient's baseline curve is only overlaid when it comes from the same
    // cohort as the treatment arms. Across cohorts it is NOT a counterfactual:
    // the two populations differ in stage mix, era, assay and — decisively —
    // follow-up length, so the gap between them measures study design, not
    // treatment. Overlaying it anyway is what makes "no treatment" look best.
    let baselineOmittedReason: string | undefined
    if (baseline && baseline.times.length > 0) {
        const comparable = pending.length === 0 || hasSameCohortCurve
        if (comparable) {
            pending.unshift({
                key: '__baseline',
                label: 'Your predicted survival (current)',
                times: baseline.times,
                survival_probabilities: baseline.survival_probabilities,
                color: '#374151',
                strokeWidth: 3,
                strokeDasharray: '8 4',
            })
            units.unshift(baselineTimeUnit ?? 'days')
        } else {
            baselineOmittedReason =
                'Your own predicted curve is not drawn here: these cohorts are different ' +
                'patient populations with different follow-up, so the distance between your ' +
                'curve and theirs would reflect study design rather than any treatment effect. ' +
                'Your curve is shown in "Reference survival by risk group" above. The comparison ' +
                'below is treated vs untreated within the same cohort, which is the contrast ' +
                'that speaks to whether treatment is associated with better survival.'
        }
    }

    if (pending.length === 0) {
        return { curves: [], insufficientN, needsPatientProfile, horizonYears: 0, baselineOmittedReason }
    }

    // 1. Put every curve on one scale. 2. Restrict to the window that EVERY
    //    plotted cohort actually observed. Without (2), a cohort followed for
    //    17 years is compared against one followed for 11 months and looks far
    //    worse purely because it had time to accrue deaths — an artefact of
    //    follow-up length, not of treatment.
    const inYears = pending.map((c, i) => ({ ...c, times: timesToYears(c.times, units[i]) }))
    const horizonYears = Math.min(...inYears.map((c) => Math.max(...c.times)))

    const curves = inYears
        .map((c) => {
            const keep = c.times.filter((t) => t <= horizonYears).length
            return {
                ...c,
                times: c.times.slice(0, keep),
                survival_probabilities: c.survival_probabilities.slice(0, keep),
                ci_lower: c.ci_lower ? c.ci_lower.slice(0, keep) : c.ci_lower,
                ci_upper: c.ci_upper ? c.ci_upper.slice(0, keep) : c.ci_upper,
            }
        })
        .filter((c) => c.times.length > 0)

    return { curves, insufficientN, needsPatientProfile, horizonYears, baselineOmittedReason }
}

export interface GeneDriverEstimate {
    gene_symbol: string
    direction: 'risk' | 'protective'
    magnitude: number
}

/**
 * Approximate, client-side estimate of which signature genes push this
 * patient's risk up or down — for chip/prompt text only, NOT a reproduction
 * of the backend's real per-gene scoring.
 *
 * PredictResponse.contributions deliberately aggregates the whole expression
 * signature into ONE "Expression signature" entry (see
 * SignatureService._score_expression in the backend) — there is no per-gene
 * breakdown in the API response. The real per-gene term there is
 * `coefficient * norm.ppf(percentile_of(value, gene.ref_quantiles))`, which
 * needs the inverse normal CDF and the model's full reference-quantile
 * normalization pipeline to reproduce exactly.
 *
 * This uses a plain z-score proxy instead — `coefficient * (value - ref_mean)
 * / ref_std` — which has the same SIGN and roughly the same ORDERING as the
 * real per-gene term, but not the same magnitude (no percentile clipping, no
 * cross-platform quantile normalization). Good enough to name "genes worth
 * asking about"; not a substitute for the model's actual scoring.
 */
export function estimateGeneDrivers(genes: SignatureGene[], expression: Record<string, number>): GeneDriverEstimate[] {
    const out: GeneDriverEstimate[] = []
    for (const g of genes) {
        const raw = expression[g.gene_symbol]
        if (raw === undefined) continue
        const z = (raw - g.ref_mean) / (g.ref_std || 1)
        const score = g.coefficient * z
        if (score === 0) continue
        out.push({ gene_symbol: g.gene_symbol, direction: score > 0 ? 'risk' : 'protective', magnitude: Math.abs(score) })
    }
    return out.sort((a, b) => b.magnitude - a.magnitude)
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
