// Parses a doctor's free-text case description ("64F ER+/PR+/HER2− invasive
// ductal, pT2N0, Ki-67 ~10%") into structured chart facts, ENTIRELY CLIENT-SIDE.
//
// This is a privacy control, not just a convenience: the raw sentence a doctor
// types at the bedside can contain patient identifiers, so it must never be
// sent to the LLM or persisted as a chat message. Only the extracted, de-identified
// facts (cancer type, a small set of clinical covariate names/values, matched
// spans) leave this function — the composer decides what to do with them.

export interface MatchedSpan {
    start: number
    end: number
    field: string
}

export interface ExtractedCaseFacts {
    /** One of the curated gallery keys (breast/lung/colorectal/ovarian/gastric/glioma),
     *  or null when a cancer type was mentioned but has no curated model (e.g. prostate),
     *  or no cancer type was recognised at all. */
    cancerKey: string | null
    /** The matched cancer-type phrase, for chip display, even when cancerKey is null. */
    cancerTerm: string | null
    /** Best-effort clinical covariates recognised in the text — callers should
     *  normalise these against the selected model's clinical_covariates and
     *  keep only the intersection before offering them to a form. */
    covariates: Record<string, string>
    matchedSpans: MatchedSpan[]
    /** Whatever text is left after stripping every matched span, trimmed. Non-empty
     *  usually means the message also asks a genuine question ("...is she high risk?"). */
    residualText: string
    /** true when ≥1 cancer term or ≥2 covariates were found — the composer's signal
     *  that this text should be read into the chart rather than sent as a chat message. */
    looksLikeCase: boolean
}

// Only these six have a curated, cross-cohort-validated model (see CURATED_CANCERS
// in backend/app/api/gallery_routes.py) — everything else recognised here still
// gets a cancerTerm chip, but routes through "build a cohort model" instead of
// scoring in seconds.
const CANCER_SYNONYMS: { pattern: RegExp; term: string; cancerKey: string | null }[] = [
    { pattern: /\bbreast\b/i, term: 'breast', cancerKey: 'breast' },
    // Breast-specific shorthand doctors use without ever saying "breast":
    // hormone-receptor status, ductal/lobular histology, luminal subtyping.
    { pattern: /\b(?:invasive ductal|ductal carcinoma|lobular carcinoma|luminal [ab]|triple[- ]negative|ER[+-]\s*\/?\s*PR[+-])\b/i, term: 'breast', cancerKey: 'breast' },
    { pattern: /\b(?:lung|nsclc)\b/i, term: 'lung', cancerKey: 'lung' },
    { pattern: /\b(?:colorectal|colon|rectal)\b/i, term: 'colorectal', cancerKey: 'colorectal' },
    { pattern: /\bovarian\b/i, term: 'ovarian', cancerKey: 'ovarian' },
    { pattern: /\b(?:gastric|stomach)\b/i, term: 'gastric', cancerKey: 'gastric' },
    { pattern: /\b(?:glioblastoma|glioma|gbm)\b/i, term: 'glioma', cancerKey: 'glioma' },
    { pattern: /\bprostate\b/i, term: 'prostate', cancerKey: null },
    { pattern: /\bpancreatic\b/i, term: 'pancreatic', cancerKey: null },
]

// Two forms, tried in order: "47 y/o male" (a real word boundary separates the
// digits from the word), then the run-on clinical shorthand "64F" / "58M" —
// note NO \b between the digit and the letter there, since digit->letter is
// not a boundary in regex (both are \w), so one can't be inserted before "F"/"M".
const AGE_YO_RE = /\b(\d{1,3})\s*(?:y\.?\/?o\.?|years?[- ]?old)\b/i
const AGE_SHORT_RE = /\b(\d{1,3})\s?(M|F)\b/i
const TNM_RE = /\bp?T([0-4])\s*N([0-3x])\b/i
const GRADE_RE = /\bgrade\s*([1-4])\b/i
const KI67_RE = /\bki-?67\s*(?:~|≈|of)?\s*(\d{1,3})\s*%/i

export function parseCaseDescription(text: string): ExtractedCaseFacts {
    const covariates: Record<string, string> = {}
    const matchedSpans: MatchedSpan[] = []
    const consumed: [number, number][] = []

    const record = (m: RegExpMatchArray, field: string) => {
        if (m.index == null) return
        matchedSpans.push({ start: m.index, end: m.index + m[0].length, field })
        consumed.push([m.index, m.index + m[0].length])
    }

    let cancerKey: string | null = null
    let cancerTerm: string | null = null
    for (const { pattern, term, cancerKey: key } of CANCER_SYNONYMS) {
        const m = text.match(pattern)
        if (m) {
            cancerTerm = term
            cancerKey = key
            record(m, 'cancer_type')
            break
        }
    }

    const ageMatch = text.match(AGE_YO_RE) ?? text.match(AGE_SHORT_RE)
    if (ageMatch) {
        covariates.age = ageMatch[1]
        record(ageMatch, 'age')
    }

    const tnmMatch = text.match(TNM_RE)
    if (tnmMatch) {
        covariates.stage = `T${tnmMatch[1]}N${tnmMatch[2].toUpperCase()}`
        record(tnmMatch, 'stage')
    }

    const gradeMatch = text.match(GRADE_RE)
    if (gradeMatch) {
        covariates.grade = gradeMatch[1]
        record(gradeMatch, 'grade')
    }

    const ki67Match = text.match(KI67_RE)
    if (ki67Match) {
        covariates.ki67 = ki67Match[1]
        record(ki67Match, 'ki67')
    }

    // Residual text: everything not covered by a matched span, collapsed and trimmed.
    consumed.sort((a, b) => a[0] - b[0])
    let residual = ''
    let cursor = 0
    for (const [start, end] of consumed) {
        if (start > cursor) residual += text.slice(cursor, start)
        cursor = Math.max(cursor, end)
    }
    residual += text.slice(cursor)
    const residualText = residual.replace(/[,\s]+/g, ' ').replace(/^[\s,.\-–—]+|[\s,.\-–—]+$/g, '').trim()

    return {
        cancerKey,
        cancerTerm,
        covariates,
        matchedSpans,
        residualText,
        looksLikeCase: cancerTerm !== null || Object.keys(covariates).length >= 2,
    }
}

// Belt-and-braces check on the text about to be SENT (a plain question, or a
// residual question left after extracting case facts) — heuristics above can
// miss things, so this is a second, independent gate before anything reaches
// the LLM or gets persisted as a chat message.
const IDENTIFIER_PATTERNS = [
    /\bMRN\b/i,
    /\b\d{6,}\b/, // a long digit run — MRN/phone/SSN-shaped, not a lab value
    /\b(?:[Mm]rs?|[Mm]s|[Dd]r)\.?\s+[A-Z][a-z]+\b/, // a title + capitalised name (title case-insensitive, name must stay capitalised)
    /\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/, // a date, e.g. a DOB
]

export function looksIdentifying(text: string): boolean {
    return IDENTIFIER_PATTERNS.some((p) => p.test(text))
}
