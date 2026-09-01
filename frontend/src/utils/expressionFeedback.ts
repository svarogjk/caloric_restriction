// Live diagnostics for pasted "GENE value" expression text, layered on top of
// parsePastedExpression() in signatureViz.ts (same regex, so what parses here
// is exactly what parses there).
//
// Thresholds mirror SignatureService in the backend:
//   QN_MIN_GENES      ~= SignatureService._QN_MIN_GENES      (signature_service.py)
//   LOW_COVERAGE_FRAC ~= SignatureService._LOW_COVERAGE_FRAC (signature_service.py)
// GET /api/gallery also returns these as `scoring_thresholds` — prefer that
// server value when available and fall back to these constants otherwise.

export const QN_MIN_GENES = 40
export const LOW_COVERAGE_FRAC = 0.6

export type SkipReason = 'no-numeric-value' | 'invalid-symbol' | 'duplicate' | 'header-row'

export interface SkippedLine {
    lineNumber: number
    text: string
    reason: SkipReason
}

export interface ExpressionFeedback {
    parsed: Record<string, number>
    geneCount: number
    skipped: SkippedLine[]
    duplicates: string[]
    /** geneCount >= qnMinGenes */
    qnReady: boolean
    signatureMatched: number
    signatureTotal: number
    /** 1 when no signature gene list is known yet (nothing to compare against). */
    coverageFrac: number
    /** coverageFrac < lowCoverageFrac, only meaningful when signatureTotal > 0. */
    lowCoverage: boolean
    valueRange: [number, number] | null
    scaleHint: 'log2-like' | 'possibly-raw-counts' | 'unknown'
    multiColumn: boolean
}

// Same regex as parsePastedExpression() in utils/signatureViz.ts — kept in sync deliberately.
const LINE_RE = /^([A-Za-z0-9_.-]+)[\s,:\t]+(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)/
const HEADER_WORDS = new Set(['gene', 'symbol', 'gene_symbol', 'value', 'expression', 'log2', 'sample'])

export function analyseExpression(
    text: string,
    signatureGenes: string[] = [],
    thresholds: { qnMinGenes?: number; lowCoverageFrac?: number } = {},
): ExpressionFeedback {
    const qnMinGenes = thresholds.qnMinGenes ?? QN_MIN_GENES
    const lowCoverageFrac = thresholds.lowCoverageFrac ?? LOW_COVERAGE_FRAC

    const parsed: Record<string, number> = {}
    const skipped: SkippedLine[] = []
    const duplicateSet = new Set<string>()
    const seen = new Set<string>()
    let multiFieldLines = 0
    let nonBlankLines = 0

    text.split('\n').forEach((rawLine, idx) => {
        const line = rawLine.trim()
        if (!line) return
        nonBlankLines++

        const fields = line.split(/[\s,:\t]+/).filter(Boolean)
        if (fields.length >= 4) multiFieldLines++

        const m = line.match(LINE_RE)
        if (!m) {
            const firstWord = fields[0]?.toLowerCase()
            const looksHeader = fields.length <= 2 && firstWord != null && HEADER_WORDS.has(firstWord) && !/\d/.test(line)
            skipped.push({
                lineNumber: idx + 1,
                text: line,
                reason: looksHeader ? 'header-row' : fields.length < 2 ? 'no-numeric-value' : 'invalid-symbol',
            })
            return
        }

        const symbol = m[1].toUpperCase()
        if (seen.has(symbol)) duplicateSet.add(symbol)
        seen.add(symbol)
        parsed[symbol] = parseFloat(m[2])
    })

    const geneCount = Object.keys(parsed).length
    const values = Object.values(parsed)
    const valueRange: [number, number] | null = values.length
        ? [Math.min(...values), Math.max(...values)]
        : null

    let scaleHint: ExpressionFeedback['scaleHint'] = 'unknown'
    if (valueRange) {
        if (valueRange[1] > 1000) scaleHint = 'possibly-raw-counts'
        else if (valueRange[0] >= -2 && valueRange[1] <= 20) scaleHint = 'log2-like'
    }

    const sigSet = new Set(signatureGenes.map((g) => g.toUpperCase()))
    const signatureTotal = sigSet.size
    const signatureMatched = signatureTotal > 0 ? [...sigSet].filter((g) => g in parsed).length : 0
    const coverageFrac = signatureTotal > 0 ? signatureMatched / signatureTotal : 1

    return {
        parsed,
        geneCount,
        skipped,
        duplicates: [...duplicateSet],
        qnReady: geneCount >= qnMinGenes,
        signatureMatched,
        signatureTotal,
        coverageFrac,
        lowCoverage: signatureTotal > 0 && coverageFrac < lowCoverageFrac,
        valueRange,
        scaleHint,
        multiColumn: nonBlankLines > 0 && multiFieldLines / nonBlankLines > 0.6,
    }
}
