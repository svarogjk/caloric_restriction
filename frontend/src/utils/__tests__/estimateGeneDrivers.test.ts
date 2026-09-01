import { describe, expect, it } from 'vitest'
import { estimateGeneDrivers } from '../signatureViz'
import { SignatureGene } from '../../services/api'

function gene(overrides: Partial<SignatureGene>): SignatureGene {
    return {
        gene_symbol: 'X', coefficient: 1, hazard_ratio: 1,
        ref_mean: 0, ref_std: 1, ref_quantiles: [],
        ...overrides,
    }
}

describe('estimateGeneDrivers', () => {
    it('ranks a gene with high expression and a positive coefficient as risk-increasing', () => {
        const genes = [gene({ gene_symbol: 'MKI67', coefficient: 0.5, ref_mean: 8, ref_std: 2 })]
        const [driver] = estimateGeneDrivers(genes, { MKI67: 12 })
        expect(driver.gene_symbol).toBe('MKI67')
        expect(driver.direction).toBe('risk')
    })

    it('ranks a gene with high expression and a negative coefficient as protective', () => {
        const genes = [gene({ gene_symbol: 'ESR1', coefficient: -0.5, ref_mean: 8, ref_std: 2 })]
        const [driver] = estimateGeneDrivers(genes, { ESR1: 12 })
        expect(driver.gene_symbol).toBe('ESR1')
        expect(driver.direction).toBe('protective')
    })

    it('skips genes the patient profile does not include', () => {
        const genes = [gene({ gene_symbol: 'MKI67' }), gene({ gene_symbol: 'ESR1' })]
        const drivers = estimateGeneDrivers(genes, { MKI67: 10 })
        expect(drivers.map((d) => d.gene_symbol)).toEqual(['MKI67'])
    })

    it('sorts by magnitude, largest deviation from reference first', () => {
        const genes = [
            gene({ gene_symbol: 'SMALL_DEV', coefficient: 1, ref_mean: 8, ref_std: 2 }),
            gene({ gene_symbol: 'BIG_DEV', coefficient: 1, ref_mean: 8, ref_std: 2 }),
        ]
        const drivers = estimateGeneDrivers(genes, { SMALL_DEV: 8.5, BIG_DEV: 14 })
        expect(drivers[0].gene_symbol).toBe('BIG_DEV')
    })

    it('never fabricates a driver for a gene at exactly the reference mean', () => {
        const genes = [gene({ gene_symbol: 'FLAT', coefficient: 1, ref_mean: 8, ref_std: 2 })]
        const drivers = estimateGeneDrivers(genes, { FLAT: 8 })
        expect(drivers).toHaveLength(0)
    })

    it('produces sane output against the real ER+ breast case response (regression guard)', () => {
        // Genes/coefficients approximating the curated breast model shape used in
        // manual API verification — ESR1 strongly protective, MKI67 strongly risk.
        const genes = [
            gene({ gene_symbol: 'ESR1', coefficient: -0.42, ref_mean: 8.0, ref_std: 2.1 }),
            gene({ gene_symbol: 'MKI67', coefficient: 0.38, ref_mean: 9.0, ref_std: 1.8 }),
        ]
        const expression = { ESR1: 12.1, MKI67: 5.8 } // the real ER+ Luminal Breast sample values
        const drivers = estimateGeneDrivers(genes, expression)
        expect(drivers.find((d) => d.gene_symbol === 'ESR1')?.direction).toBe('protective')
        expect(drivers.find((d) => d.gene_symbol === 'MKI67')?.direction).toBe('protective')
        // Both push protective here: ESR1 high+negative coefficient, MKI67 low+positive
        // coefficient (low proliferation is protective) — consistent with the vignette's
        // own stated expectation ("Expect ESR1/PGR to rank as protective").
    })
})
