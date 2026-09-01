/** Fenced blocks and inline code, captured so they can be skipped. */
const CODE_SEGMENTS = /(```[\s\S]*?```|`[^`\n]*`)/g
const GSE_ACCESSION = /\bGSE(\d+)\b/g
/** An accession that is already the text of a markdown link. Capturing, so
 *  String.split keeps the match instead of deleting it. */
const ALREADY_LINKED = /(\[[^\]]*GSE\d+[^\]]*\]\([^)]*\))/g

export const gseUrl = (accession: string) =>
    `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${accession}`

/**
 * Turn bare GSE accessions into links to the GEO record.
 *
 * The system prompt requires every dataset reference to carry its accession,
 * and _compute_domain_score rewards them, so they are the densest grounding
 * signal in an assistant turn — worth making clickable.
 *
 * Code spans are split out and left alone: rewriting a GSE inside a fenced
 * block would corrupt sample code into markdown link syntax.
 */
export function linkifyGse(markdown: string): string {
    return markdown
        .split(CODE_SEGMENTS)
        .map((segment, i) => {
            if (i % 2 === 1) return segment // odd indices are the captured code spans
            return segment
                .split(ALREADY_LINKED)
                .map((part, j) => (j % 2 === 1 ? part : part.replace(GSE_ACCESSION, (m) => `[${m}](${gseUrl(m)})`)))
                .join('')
        })
        .join('')
}

/** Every distinct accession cited in a turn, in order of first appearance. */
export function extractGseIds(text: string): string[] {
    const seen: string[] = []
    for (const m of text.matchAll(GSE_ACCESSION)) {
        if (!seen.includes(m[0])) seen.push(m[0])
    }
    return seen
}
