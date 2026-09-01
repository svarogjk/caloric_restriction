// Canonical research-use-only / advisory disclaimer strings.
//
// These are CLIENT-AUTHORED FALLBACKS only. Wherever an API response already
// carries its own `disclaimer` field (PredictResponse.disclaimer,
// TherapyRationaleResponse.disclaimer, PrognosticModel.disclaimer,
// TreatmentComparison.disclaimer), pass that server string to <RuoNotice text=.../>
// instead — the server is the source of truth and the two must not drift.

export const RUO_TEXT = {
    prediction:
        'Research use only. This is an advisory, hypothesis-generating risk estimate — ' +
        'not a prescription, not a diagnosis, and not a guarantee of response. Discuss with the care team.',
    treatment:
        'Research use only. These are advisory treatments to discuss, not a prescription — ' +
        'grounded in GEO cohort outcomes and public biomarker→therapy evidence, not a clinical decision-making device.',
    intake:
        'Research use only. Patient data is scored in this browser session and never stored. ' +
        'Attaching it predicts a risk group and surfaces advisory treatments to discuss.',
    report:
        'RESEARCH USE ONLY — NOT FOR CLINICAL DECISION-MAKING. This report is advisory and hypothesis-generating.',
    general:
        'Predictive + advisory, research use only — not a prescription or a guarantee of response.',
} as const

export type RuoScope = keyof typeof RUO_TEXT
