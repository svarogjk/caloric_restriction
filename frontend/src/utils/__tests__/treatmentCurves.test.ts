import { describe, it, expect } from 'vitest'
import { classifyDrugCurve, topTreatmentCurves } from '../signatureViz'
import { TreatmentKMEvidence, ReferenceKMCurve } from '../../services/api'

const refCurve = (group: string, n = 100, events = 40): ReferenceKMCurve => ({
    group, times: [0, 365, 730], survival_probabilities: [1, 0.8, 0.6],
    n_samples: n, n_events: events,
} as ReferenceKMCurve)

const tier2 = (over: Partial<TreatmentKMEvidence> = {}): TreatmentKMEvidence => ({
    drug: 'tamoxifen', tier: 'cohort_reference', accession: 'GSE1',
    reference_km: [refCurve('low'), refCurve('intermediate'), refCurve('high')],
    time_unit: 'days', caveat: '', is_building: false, same_cohort: false,
    ...over,
} as TreatmentKMEvidence)

const tier1 = (over: Partial<TreatmentKMEvidence> = {}): TreatmentKMEvidence => ({
    drug: 'tamoxifen', tier: 'arm_comparison', accession: 'GSE1', same_cohort: true,
    arms: [
        { name: 'Treated', n_samples: 80, n_events: 30, km_curve: { times: [0, 365], survival_probabilities: [1, 0.9], ci_lower: null, ci_upper: null, n_samples: 80, n_events: 30 } },
        { name: 'Untreated/control', n_samples: 60, n_events: 28, km_curve: { times: [0, 365], survival_probabilities: [1, 0.7], ci_lower: null, ci_upper: null, n_samples: 60, n_events: 28 } },
    ],
    time_unit: 'days', caveat: '', is_building: false,
    ...over,
} as TreatmentKMEvidence)

describe('Tier-2 curves with no patient profile', () => {
    // The bug this guards: both matched_risk_group and patientRiskGroup are null
    // in research mode, and the old `?? 'low'` fallback plotted the
    // best-surviving third of a cohort as if it were the drug's outcome.
    it('withholds the curve instead of defaulting to the low-risk tertile', () => {
        const km = { tamoxifen: tier2() }
        expect(classifyDrugCurve('tamoxifen', km, null)).toBe('needs_patient_profile')

        const out = topTreatmentCurves(['tamoxifen'], km, null)
        expect(out.curves).toHaveLength(0)
        expect(out.needsPatientProfile).toEqual(['tamoxifen'])
    })

    it('plots the cohort-matched group when per-cohort scoring resolved one', () => {
        const km = { tamoxifen: tier2({ matched_risk_group: 'high' }) }
        expect(classifyDrugCurve('tamoxifen', km, null)).toBe('plottable')

        const out = topTreatmentCurves(['tamoxifen'], km, null)
        expect(out.curves.length).toBeGreaterThan(0)
        expect(out.needsPatientProfile).toEqual([])
    })

    it('falls back to the patient risk group when the cohort did not score one', () => {
        const km = { tamoxifen: tier2() }
        expect(classifyDrugCurve('tamoxifen', km, 'high')).toBe('plottable')
        expect(topTreatmentCurves(['tamoxifen'], km, 'high').needsPatientProfile).toEqual([])
    })
})

describe('Tier-1 arm comparison', () => {
    it('is the honest contrast with no patient at all — it is gene-independent', () => {
        const km = { tamoxifen: tier1() }
        expect(classifyDrugCurve('tamoxifen', km, null)).toBe('plottable')

        const out = topTreatmentCurves(['tamoxifen'], km, null)
        expect(out.curves.length).toBe(2) // treated + control
        expect(out.needsPatientProfile).toEqual([])
    })

    it('refuses a contrast built on an unstable control arm', () => {
        const km = {
            tamoxifen: tier1({
                arms: [
                    { name: 'Treated', n_samples: 80, n_events: 30, km_curve: { times: [0], survival_probabilities: [1], ci_lower: null, ci_upper: null, n_samples: 80, n_events: 30 } },
                    { name: 'Untreated/control', n_samples: 4, n_events: 1, km_curve: { times: [0], survival_probabilities: [1], ci_lower: null, ci_upper: null, n_samples: 4, n_events: 1 } },
                ],
            } as Partial<TreatmentKMEvidence>),
        }
        expect(classifyDrugCurve('tamoxifen', km, null)).toBe('insufficient')
    })
})
