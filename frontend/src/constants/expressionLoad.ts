// Canonical copy for "this step has to load gene expression data" notices.
//
// Same contract as constants/ruo.ts: one string per scope so the wording can't
// drift between surfaces. Rendered exclusively through <ExpressionLoadNotice>.
//
// WHY THIS EXISTS
// Some things the app does read only a cohort's CLINICAL ANNOTATIONS — a few
// hundred KB of metadata, effectively instant. Others must download, decompress
// and probe→gene map the cohort's full EXPRESSION MATRIX — tens to hundreds of
// MB per cohort, minutes on a cache miss. Those two feel identical in the UI
// right up until one of them takes ten minutes, so the expensive ones say so
// up front.

export const EXPRESSION_LOAD_TEXT = {
    analysis:
        'Loads full expression matrices from GEO — one download, parse and probe→gene mapping ' +
        'per candidate cohort. Cohorts already cached locally are fast; new ones take minutes each.',
    signature:
        "Loads each cohort's full expression matrix to fit and cross-validate the Cox model. " +
        'Cohorts cached locally are fast; uncached ones are downloaded from GEO first.',
    patient:
        'Scoring against a saved analysis builds its signature first, which loads each cohort’s ' +
        'full expression matrix. Scoring against an already-built model is instant.',
    treatment:
        'Builds one prognostic model per treatment, each loading full expression matrices from GEO. ' +
        'Expect several minutes the first time a cancer type is opened.',
    cohortCurve:
        'Falls back to building a risk model, which loads full expression matrices from GEO. ' +
        'Curves drawn from a cohort’s recorded treatment arms need no expression data and appear within seconds.',
} as const

export type ExpressionLoadScope = keyof typeof EXPRESSION_LOAD_TEXT

// Worth stating wherever the COSMIC checkbox is visible alongside one of these.
// It is the intuitive assumption and it is wrong: the filter is applied to the
// matrix AFTER it has been downloaded, decompressed and mapped, so it changes
// how many genes are tested — never how much data is fetched.
export const CANCER_GENE_FILTER_CAVEAT =
    'Restricting to COSMIC cancer genes does not shorten this — it narrows which genes are ' +
    'tested after each matrix is loaded, not what gets downloaded.'
