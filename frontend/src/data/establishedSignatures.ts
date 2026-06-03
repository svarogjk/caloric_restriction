// Established clinical prognostic signature gene lists (F19).
//
// These are PUBLIC gene *membership* lists used only for concordance/overlap
// benchmarking — we never reproduce the proprietary coefficients or recurrence
// scores of these assays. Direction (risk vs protective) is annotated where it
// is well established in the literature for the listed genes.
//
// Sources: published gene panels for Oncotype DX (21-gene), MammaPrint
// (70-gene, abbreviated to commonly-cited members), and PAM50.

export interface EstablishedSignature {
    name: string
    description: string
    // gene_symbol -> 'risk' | 'protective' | 'unknown'
    genes: Record<string, 'risk' | 'protective' | 'unknown'>
}

export const ESTABLISHED_SIGNATURES: EstablishedSignature[] = [
    {
        name: 'Oncotype DX (21-gene)',
        description: 'Breast cancer recurrence assay; 16 cancer-related + 5 reference genes.',
        genes: {
            MKI67: 'risk', AURKA: 'risk', BIRC5: 'risk', CCNB1: 'risk', MYBL2: 'risk',
            MMP11: 'risk', CTSL2: 'risk', GRB7: 'risk', ERBB2: 'risk',
            ESR1: 'protective', PGR: 'protective', BCL2: 'protective', SCUBE2: 'protective',
            GSTM1: 'unknown', CD68: 'risk', BAG1: 'protective',
            ACTB: 'unknown', GAPDH: 'unknown', RPLP0: 'unknown', GUSB: 'unknown', TFRC: 'unknown',
        },
    },
    {
        name: 'MammaPrint (70-gene, core)',
        description: 'Breast cancer distant-recurrence signature (commonly-cited members).',
        genes: {
            MMP9: 'risk', MELK: 'risk', EXT1: 'risk', GNAZ: 'risk', GMPS: 'risk',
            ORC6: 'risk', PRC1: 'risk', RFC4: 'risk', RUNDC1: 'risk', SCUBE2: 'protective',
            DCK: 'unknown', FLT1: 'risk', HRASLS: 'protective', STK32B: 'unknown',
            RASSF7: 'unknown', DTL: 'risk', CENPA: 'risk', ECT2: 'risk',
        },
    },
    {
        name: 'PAM50',
        description: 'Intrinsic breast cancer subtype classifier (50 genes).',
        genes: {
            MKI67: 'risk', AURKA: 'risk', BIRC5: 'risk', CCNB1: 'risk', MYBL2: 'risk',
            CEP55: 'risk', NDC80: 'risk', UBE2C: 'risk', PTTG1: 'risk', RRM2: 'risk',
            CDC20: 'risk', ORC6: 'risk', KIF2C: 'risk', CDC6: 'risk', EXO1: 'risk',
            ANLN: 'risk', CCNE1: 'risk', CDC25C: 'risk', MELK: 'risk', NUF2: 'risk',
            ESR1: 'protective', PGR: 'protective', BCL2: 'protective', FOXA1: 'protective',
            GATA3: 'protective', MLPH: 'protective', NAT1: 'protective', MAPT: 'protective',
            ERBB2: 'risk', GRB7: 'risk', FGFR4: 'risk', KRT5: 'unknown', KRT14: 'unknown',
            KRT17: 'unknown', MIA: 'unknown', SFRP1: 'unknown', BAG1: 'protective',
        },
    },
]
