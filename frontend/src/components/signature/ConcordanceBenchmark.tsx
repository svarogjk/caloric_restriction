import React from 'react'
import { PrognosticModel } from '../../services/api'
import { ESTABLISHED_SIGNATURES } from '../../data/establishedSignatures'

interface Props {
    model: PrognosticModel
}

/**
 * F19 — Concordance benchmark of our derived signature against established
 * clinical panels (Oncotype DX, MammaPrint, PAM50). We compare gene MEMBERSHIP
 * overlap and DIRECTION agreement only — never coefficient/recurrence-score
 * reproduction (those are proprietary and assay-specific).
 */
const ConcordanceBenchmark: React.FC<Props> = ({ model }) => {
    const ourGenes = React.useMemo(() => {
        const map = new Map<string, 'risk' | 'protective'>()
        for (const g of model.genes) {
            map.set(g.gene_symbol.toUpperCase(), g.coefficient >= 0 ? 'risk' : 'protective')
        }
        return map
    }, [model])

    const rows = React.useMemo(() => {
        return ESTABLISHED_SIGNATURES.map((sig) => {
            const sigGenes = Object.keys(sig.genes).map((s) => s.toUpperCase())
            const overlap: string[] = []
            let directionAgree = 0
            let directionComparable = 0
            for (const gene of sigGenes) {
                if (ourGenes.has(gene)) {
                    overlap.push(gene)
                    const theirDir = sig.genes[gene] ?? sig.genes[Object.keys(sig.genes).find((k) => k.toUpperCase() === gene)!]
                    const ourDir = ourGenes.get(gene)
                    if (theirDir && theirDir !== 'unknown' && ourDir) {
                        directionComparable += 1
                        if (theirDir === ourDir) directionAgree += 1
                    }
                }
            }
            return {
                name: sig.name,
                description: sig.description,
                nTheirs: sigGenes.length,
                overlap,
                directionAgree,
                directionComparable,
            }
        })
    }, [ourGenes])

    return (
        <div className="space-y-3">
            <p className="text-sm text-fg-muted">
                Gene-membership overlap and direction agreement between this GEO-derived signature
                ({model.genes.length} genes) and established clinical panels. Overlap with validated
                assays is corroborating evidence; novel genes may reflect GEO's broader cohort coverage.
            </p>
            <div className="overflow-x-auto">
                <table className="w-full text-sm border border-border rounded">
                    <thead className="bg-surface-sunken text-fg-muted text-left">
                        <tr>
                            <th className="px-3 py-2 font-medium">Established signature</th>
                            <th className="px-3 py-2 font-medium">Genes</th>
                            <th className="px-3 py-2 font-medium">Overlap</th>
                            <th className="px-3 py-2 font-medium">Direction agreement</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => (
                            <tr key={r.name} className="border-t border-border align-top">
                                <td className="px-3 py-2">
                                    <div className="font-medium text-fg-strong">{r.name}</div>
                                    <div className="text-xs text-fg-faint">{r.description}</div>
                                </td>
                                <td className="px-3 py-2 text-fg-muted">{r.nTheirs}</td>
                                <td className="px-3 py-2">
                                    {r.overlap.length === 0 ? (
                                        <span className="text-fg-faint">none</span>
                                    ) : (
                                        <div className="flex flex-wrap gap-1">
                                            {r.overlap.map((g) => (
                                                <span
                                                    key={g}
                                                    className="px-1.5 py-0.5 text-xs rounded bg-accent-soft text-accent-fg border border-accent-soft"
                                                >
                                                    {g}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </td>
                                <td className="px-3 py-2 text-fg-muted">
                                    {r.directionComparable === 0 ? (
                                        <span className="text-fg-faint">—</span>
                                    ) : (
                                        <span
                                            className={
                                                r.directionAgree / r.directionComparable >= 0.5
                                                    ? 'text-ok font-medium'
                                                    : 'text-warn font-medium'
                                            }
                                        >
                                            {r.directionAgree}/{r.directionComparable}
                                        </span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <p className="text-[11px] text-fg-faint">
                Membership/direction concordance only — proprietary coefficients and recurrence-score
                formulas of these assays are never reproduced.
            </p>
        </div>
    )
}

export default ConcordanceBenchmark
