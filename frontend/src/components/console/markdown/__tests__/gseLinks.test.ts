import { describe, it, expect } from 'vitest'
import { linkifyGse, extractGseIds } from '../gseLinks'

describe('linkifyGse', () => {
    it('links a bare accession', () => {
        expect(linkifyGse('built on GSE2034')).toBe(
            'built on [GSE2034](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE2034)',
        )
    })

    it('leaves accessions inside inline code alone', () => {
        expect(linkifyGse('use `GSE2034` here')).toBe('use `GSE2034` here')
    })

    it('leaves accessions inside a fenced block alone', () => {
        const md = '```\ndownload GSE2034\n```'
        expect(linkifyGse(md)).toBe(md)
    })

    it('does not double-link an accession that is already a link', () => {
        const md = '[GSE2034](https://example.com/GSE2034)'
        expect(linkifyGse(md)).toBe(md)
    })

    it('links accessions in a table cell', () => {
        expect(linkifyGse('| GSE7390 | 198 |')).toContain('[GSE7390](https://www.ncbi.nlm.nih.gov')
    })
})

describe('extractGseIds', () => {
    it('dedupes and preserves first-appearance order', () => {
        expect(extractGseIds('GSE7390 then GSE2034 then GSE7390')).toEqual(['GSE7390', 'GSE2034'])
    })

    it('returns nothing when there are no accessions', () => {
        expect(extractGseIds('no datasets mentioned')).toEqual([])
    })
})
