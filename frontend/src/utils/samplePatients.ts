export interface SamplePatient {
    id: string
    name: string
    cancerHint: string
    explanation: string
    direction: string
    color: string
    expression: string
}

const genes = (pairs: [string, number][]): string =>
    pairs.map(([g, v]) => `${g} ${v}`).join('\n')

export const SAMPLE_PATIENTS: SamplePatient[] = [
    {
        id: 'er_positive_breast',
        name: 'ER+ Luminal Breast',
        cancerHint: 'Run: breast cancer overall survival',
        explanation: 'ER-positive luminal-A type tumour. ESR1 and PGR are elevated (hormone-receptor driven). Low MKI67 indicates a low proliferative index — this is typically the lower-risk breast cancer subtype.',
        direction: 'Expect ESR1/PGR to rank as protective (low-risk) markers. Good baseline for comparing against hormone-receptor-negative profiles.',
        color: '#ec4899',
        expression: genes([
            ['ESR1', 12.1], ['PGR', 11.4], ['MKI67', 5.8], ['ERBB2', 7.2], ['TP53', 7.4],
            ['GATA3', 11.8], ['FOXA1', 11.6], ['TFF1', 12.0], ['AGR2', 11.9], ['BCAS1', 10.4],
            ['CDH1', 10.8], ['KRT19', 10.9], ['KRT8', 10.7], ['KRT18', 10.5], ['EPCAM', 10.6],
            ['TOP2A', 6.2], ['AURKA', 6.5], ['BIRC5', 6.0], ['CCNB1', 6.1], ['CDK1', 6.3],
            ['MYC', 7.8], ['KRAS', 7.2], ['PIK3CA', 8.3], ['AKT1', 8.0], ['PTEN', 8.4],
            ['BRCA1', 7.0], ['BRCA2', 7.1], ['PALB2', 7.3], ['RAD51', 7.6], ['RB1', 8.0],
            ['CDKN2A', 6.0], ['TP63', 5.9], ['VIM', 5.8], ['SNAI1', 5.7], ['ZEB1', 5.6],
            ['BCL2', 10.2], ['BAX', 7.4], ['CASP3', 7.2], ['VEGFA', 7.8], ['HIF1A', 7.9],
            ['CD44', 7.6], ['ALDH1A1', 6.8], ['MUC1', 9.2], ['CEACAM5', 8.1], ['PCNA', 8.5],
            ['STAT3', 7.9], ['JUN', 7.6], ['FOS', 7.3], ['MMP9', 7.0], ['TIMP1', 9.0],
        ]),
    },
    {
        id: 'tnbc_aggressive',
        name: 'Triple-Negative Breast (TNBC)',
        cancerHint: 'Run: breast cancer overall survival',
        explanation: 'ER-/PR-/HER2-negative breast cancer. High MKI67 and TOP2A indicate aggressive proliferation. CDH1 loss suggests epithelial-mesenchymal transition. Typically higher-risk and less responsive to hormone therapy.',
        direction: 'Expect proliferation markers (TOP2A, MKI67, CCNB1, AURKA) to rank as high-risk. Compare with ER+ profile to see the hormone-receptor axis.',
        color: '#ef4444',
        expression: genes([
            ['ESR1', 5.2], ['PGR', 4.8], ['ERBB2', 6.1], ['GATA3', 5.0], ['FOXA1', 4.9],
            ['MKI67', 12.4], ['TOP2A', 11.8], ['AURKA', 11.5], ['BIRC5', 11.2], ['CDK1', 11.7],
            ['CCNB1', 11.6], ['FOXM1', 11.4], ['PCNA', 11.0], ['CCND1', 10.8], ['CDC20', 11.1],
            ['TP53', 10.2], ['BRCA1', 9.0], ['RB1', 5.8], ['CDKN2A', 9.6], ['PTEN', 6.2],
            ['CDH1', 5.5], ['VIM', 11.2], ['SNAI1', 10.8], ['ZEB1', 10.4], ['FN1', 11.0],
            ['MYC', 11.3], ['KRAS', 8.8], ['PIK3CA', 8.5], ['AKT1', 8.1], ['EGFR', 9.2],
            ['CD44', 11.0], ['ALDH1A1', 10.6], ['EPCAM', 8.4], ['KRT19', 8.0], ['KRT8', 7.8],
            ['BCL2', 6.0], ['BAX', 9.2], ['CASP3', 8.8], ['VEGFA', 10.1], ['HIF1A', 10.4],
            ['STAT3', 10.0], ['JUN', 9.8], ['FOS', 9.2], ['MMP9', 10.2], ['SPP1', 10.5],
            ['CD8A', 6.8], ['PDCD1', 6.1], ['CD274', 7.2], ['GZMB', 6.9], ['IFNG', 6.3],
        ]),
    },
    {
        id: 'lung_egfr_high',
        name: 'Lung Adenocarcinoma (EGFR-high)',
        cancerHint: 'Run: lung adenocarcinoma overall survival',
        explanation: 'EGFR-amplified lung profile with high proliferative index (MKI67) and reduced CDH1 — consistent with an EMT-prone, EGFR-driven adenocarcinoma. RB1 loss further suggests aggressive cell-cycle dysregulation.',
        direction: 'Expect EGFR and downstream RAS/MAPK/PI3K pathway genes to appear as top prognostic markers. EGFR-TKI cohorts are the natural treatment context.',
        color: '#3b82f6',
        expression: genes([
            ['EGFR', 11.2], ['MKI67', 11.0], ['CDH1', 5.8], ['RB1', 5.9], ['KRAS', 7.1],
            ['ERBB2', 7.8], ['MET', 9.4], ['ALK', 6.2], ['ROS1', 6.0], ['BRAF', 7.5],
            ['PIK3CA', 8.9], ['AKT1', 8.7], ['PTEN', 6.8], ['TP53', 9.2], ['STK11', 6.4],
            ['CDKN2A', 6.1], ['CCND1', 9.6], ['CDK4', 9.1], ['CDK6', 8.8], ['CCNB1', 10.2],
            ['TOP2A', 10.8], ['AURKA', 10.4], ['BIRC5', 10.0], ['CDK1', 10.6], ['FOXM1', 10.3],
            ['VIM', 10.2], ['ZEB1', 9.8], ['SNAI1', 9.6], ['FN1', 10.5], ['COL1A1', 9.9],
            ['MYC', 10.5], ['MYCL', 9.2], ['NKX2-1', 9.8], ['SFTPB', 7.2], ['SFTPC', 6.8],
            ['CD44', 9.4], ['ALDH1A1', 8.2], ['EPCAM', 9.6], ['KRT19', 9.8], ['KRT7', 10.0],
            ['VEGFA', 9.8], ['HIF1A', 9.6], ['ANGPT2', 8.8], ['MMP9', 9.2], ['TIMP1', 9.4],
            ['CD274', 7.8], ['PDCD1', 5.9], ['CD8A', 6.4], ['GZMB', 6.1], ['IFNG', 5.8],
        ]),
    },
    {
        id: 'colorectal_wnt',
        name: 'Colorectal (Wnt-activated)',
        cancerHint: 'Run: colorectal cancer overall survival',
        explanation: 'Wnt/β-catenin activated colorectal profile. High CTNNB1 and MYC with reduced APC expression indicate pathway hyperactivation. CDX2 confirms colonic epithelial origin. KRAS activation amplifies proliferative signalling.',
        direction: 'Expect Wnt pathway genes (CTNNB1, MYC, CDX2, AXIN2) and mismatch repair markers to dominate the prognostic signature for colorectal OS.',
        color: '#10b981',
        expression: genes([
            ['CTNNB1', 10.8], ['MYC', 11.3], ['APC', 5.4], ['CDX2', 10.5], ['KRAS', 9.8],
            ['AXIN2', 10.2], ['TCF4', 9.8], ['LEF1', 9.5], ['LGR5', 10.6], ['ASCL2', 9.9],
            ['TP53', 9.4], ['SMAD4', 7.2], ['TGFB1', 8.8], ['PIK3CA', 8.6], ['PTEN', 7.0],
            ['BRAF', 8.2], ['RAS', 9.1], ['RAF1', 8.4], ['MAP2K1', 8.9], ['MAPK1', 9.0],
            ['MKI67', 10.4], ['TOP2A', 10.6], ['CDK1', 10.2], ['CCNB1', 10.0], ['AURKA', 9.8],
            ['CDH1', 9.2], ['VIM', 9.0], ['FN1', 10.0], ['COL1A1', 10.2], ['MMP9', 9.6],
            ['CEACAM5', 11.0], ['MUC2', 10.4], ['EPCAM', 10.8], ['KRT20', 10.6], ['KRT19', 10.4],
            ['VEGFA', 9.6], ['HIF1A', 9.4], ['ANGPT2', 8.6], ['PDGFRA', 8.4], ['FGF2', 8.2],
            ['MLH1', 7.8], ['MSH2', 7.6], ['MSH6', 7.4], ['PMS2', 7.2], ['EPCAM', 10.8],
            ['BCL2', 8.0], ['BAX', 8.6], ['CASP3', 8.2], ['STAT3', 9.2], ['JUN', 8.8],
        ]),
    },
]
