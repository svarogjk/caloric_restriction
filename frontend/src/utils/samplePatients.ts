// Example data for the chat welcome screen.
//
// Two complementary entry points, co-located here so they can't drift apart:
//   - SAMPLE_PATIENTS  → the Clinical column. Each entry is a complete patient case:
//                        a tumour-board vignette + the matching analysis query +
//                        a realistic tumour expression profile the user can edit/replace.
//   - RESEARCH_EXAMPLES → the Research column. Pure cross-cohort discovery/validation
//                        queries — no patient involved.

export interface SamplePatient {
    id: string
    name: string
    vignette: string      // one-line tumour-board case summary
    cancerHint: string    // short tag, e.g. "Run: breast cancer overall survival"
    query: string         // natural-language clinical question pre-filled into the input
    explanation: string
    direction: string
    color: string
    expression: string
}

export interface ResearchExample {
    text: string          // shown on the card and pre-filled into the input
    query: string         // the discovery/validation query
}

const genes = (pairs: [string, number][]): string =>
    pairs.map(([g, v]) => `${g} ${v}`).join('\n')

export const SAMPLE_PATIENTS: SamplePatient[] = [
    {
        id: 'er_positive_breast',
        name: 'ER+ Luminal Breast',
        vignette: '64F, ER+/PR+/HER2−, invasive ductal, pT2N0, Ki-67 ~10% — luminal A',
        cancerHint: 'Run: breast cancer overall survival',
        query: 'breast cancer overall survival',
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
        vignette: '47F, triple-negative (ER−/PR−/HER2−), grade 3 ductal, pT2N1, Ki-67 ~70%',
        cancerHint: 'Run: breast cancer overall survival',
        query: 'breast cancer overall survival',
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
        vignette: '59M never-smoker, EGFR-driven lung adenocarcinoma, stage IIIA',
        cancerHint: 'Run: lung adenocarcinoma overall survival',
        query: 'lung adenocarcinoma overall survival',
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
        vignette: '68M, left-sided colon adenocarcinoma, APC-mutant / Wnt-activated, pT3N1, MSS',
        cancerHint: 'Run: colorectal cancer overall survival',
        query: 'colorectal cancer overall survival',
        explanation: 'Wnt/β-catenin activated colorectal profile. High CTNNB1 and MYC with reduced APC expression indicate pathway hyperactivation. CDX2 confirms colonic epithelial origin. KRAS activation amplifies proliferative signalling.',
        direction: 'Expect Wnt pathway genes (CTNNB1, MYC, CDX2, AXIN2) and mismatch repair markers to dominate the prognostic signature for colorectal OS.',
        color: '#10b981',
        expression: genes([
            ['CTNNB1', 10.8], ['MYC', 11.3], ['APC', 5.4], ['CDX2', 10.5], ['KRAS', 9.8],
            ['AXIN2', 10.2], ['TCF4', 9.8], ['LEF1', 9.5], ['LGR5', 10.6], ['ASCL2', 9.9],
            ['TP53', 9.4], ['SMAD4', 7.2], ['TGFB1', 8.8], ['PIK3CA', 8.6], ['PTEN', 7.0],
            ['BRAF', 8.2], ['RAF1', 8.4], ['MAP2K1', 8.9], ['MAPK1', 9.0], ['NRAS', 8.1],
            ['MKI67', 10.4], ['TOP2A', 10.6], ['CDK1', 10.2], ['CCNB1', 10.0], ['AURKA', 9.8],
            ['CDH1', 9.2], ['VIM', 9.0], ['FN1', 10.0], ['COL1A1', 10.2], ['MMP9', 9.6],
            ['CEACAM5', 11.0], ['MUC2', 10.4], ['EPCAM', 10.8], ['KRT20', 10.6], ['KRT19', 10.4],
            ['VEGFA', 9.6], ['HIF1A', 9.4], ['ANGPT2', 8.6], ['PDGFRA', 8.4], ['FGF2', 8.2],
            ['MLH1', 7.8], ['MSH2', 7.6], ['MSH6', 7.4], ['PMS2', 7.2], ['BCL2', 8.0],
            ['BAX', 8.6], ['CASP3', 8.2], ['STAT3', 9.2], ['JUN', 8.8], ['FOS', 8.5],
        ]),
    },
    {
        id: 'ovarian_hgsc',
        name: 'High-Grade Serous Ovarian',
        vignette: '61F, high-grade serous ovarian carcinoma, FIGO IIIC, post-debulking + platinum',
        cancerHint: 'Run: ovarian cancer overall survival',
        query: 'ovarian cancer overall survival',
        explanation: 'High-grade serous ovarian carcinoma. Near-universal TP53 dysregulation with elevated WT1 and PAX8 (Müllerian lineage). CCNE1 amplification and high proliferation mark an aggressive, platinum-treated phenotype; CA125 (MUC16) and HE4 (WFDC2) are clinically tracked.',
        direction: 'Expect proliferation (MKI67, TOP2A, CCNB1, AURKA) and the TP53/CCNE1 axis to dominate. Homologous-recombination genes (BRCA1/2) contextualise platinum response in treated cohorts.',
        color: '#a855f7',
        expression: genes([
            ['TP53', 11.4], ['WT1', 11.0], ['PAX8', 11.2], ['MUC16', 11.6], ['WFDC2', 11.3],
            ['FOLR1', 10.8], ['CCNE1', 10.9], ['MYC', 10.6], ['MECOM', 9.8], ['SOX17', 10.2],
            ['MKI67', 11.5], ['TOP2A', 11.3], ['CCNB1', 11.1], ['AURKA', 10.8], ['CDK1', 11.0],
            ['BIRC5', 10.7], ['FOXM1', 11.2], ['PCNA', 10.9], ['CDC20', 10.6], ['BUB1', 10.4],
            ['BRCA1', 7.2], ['BRCA2', 7.0], ['RAD51', 8.4], ['PALB2', 6.8], ['PTEN', 6.4],
            ['RB1', 6.6], ['CDKN2A', 8.8], ['PIK3CA', 8.6], ['AKT1', 8.2], ['KRAS', 7.8],
            ['CDH1', 8.4], ['VIM', 9.6], ['SNAI2', 9.2], ['ZEB1', 8.8], ['FN1', 10.2],
            ['EPCAM', 10.4], ['KRT8', 10.0], ['KRT18', 9.8], ['KRT19', 9.6], ['MSLN', 10.5],
            ['VEGFA', 10.0], ['HIF1A', 9.4], ['ANGPT2', 8.6], ['MMP9', 9.2], ['SPP1', 10.1],
            ['CD8A', 7.4], ['PDCD1', 6.6], ['CD274', 7.0], ['GZMB', 7.2], ['IFNG', 6.4],
        ]),
    },
    {
        id: 'gastric_diffuse',
        name: 'Diffuse Gastric',
        vignette: '57M, gastric adenocarcinoma (diffuse type), pT3N2, CDH1-low / EMT',
        cancerHint: 'Run: gastric cancer overall survival',
        query: 'gastric cancer overall survival',
        explanation: 'Diffuse-type gastric adenocarcinoma with CDH1 (E-cadherin) loss driving an epithelial-mesenchymal phenotype (high VIM, SNAI1, ZEB1). Receptor tyrosine kinases (ERBB2, MET, FGFR2) and an angiogenic/stromal programme reflect an aggressive, poorly cohesive tumour.',
        direction: 'Expect CDH1 loss and EMT/stromal genes (VIM, FN1, MMP9) to rank as high-risk. RTK markers (ERBB2, MET, FGFR2) flag the natural targeted-therapy treatment context.',
        color: '#f59e0b',
        expression: genes([
            ['CDH1', 5.4], ['VIM', 11.4], ['SNAI1', 10.8], ['ZEB1', 10.6], ['ZEB2', 10.2],
            ['FN1', 11.2], ['TWIST1', 10.0], ['CDH2', 9.8], ['SPARC', 10.4], ['THBS1', 9.6],
            ['ERBB2', 9.4], ['MET', 9.8], ['FGFR2', 9.6], ['EGFR', 8.8], ['KRAS', 8.6],
            ['TP53', 9.6], ['PIK3CA', 8.4], ['PTEN', 6.8], ['SMAD4', 6.6], ['ARID1A', 7.0],
            ['MKI67', 10.2], ['TOP2A', 10.0], ['CCNB1', 9.8], ['AURKA', 9.4], ['CDK1', 9.9],
            ['CEACAM5', 10.6], ['MUC5AC', 10.8], ['MUC2', 9.8], ['MUC6', 9.4], ['TFF1', 9.6],
            ['EPCAM', 10.0], ['KRT8', 9.6], ['KRT18', 9.4], ['KRT19', 9.2], ['CLDN18', 10.4],
            ['VEGFA', 10.2], ['HIF1A', 9.8], ['ANGPT2', 9.0], ['MMP9', 10.4], ['MMP7', 9.8],
            ['MLH1', 7.4], ['MSH2', 7.2], ['MYC', 9.6], ['CCND1', 9.2], ['BCL2', 8.0],
            ['STAT3', 9.8], ['IL6', 9.2], ['CXCL8', 9.4], ['CD44', 9.8], ['ALDH1A1', 9.0],
        ]),
    },
    {
        id: 'prostate_ar',
        name: 'Prostate Adenocarcinoma (AR-driven)',
        vignette: '70M, prostate adenocarcinoma, Gleason 4+3=7, pT3a, PSA 14 — AR-driven',
        cancerHint: 'Run: prostate cancer overall survival',
        query: 'prostate cancer overall survival',
        explanation: 'Androgen-receptor-driven prostate adenocarcinoma. High AR, KLK3 (PSA) and FOLH1 (PSMA) with elevated ERG (TMPRSS2-ERG fusion proxy). PTEN loss marks a higher-risk luminal tumour; proliferation is modest, typical of localised disease.',
        direction: 'Expect the AR axis (AR, KLK3, FOLH1, NKX3-1) and PTEN loss to drive the prognostic signature. Contrast with neuroendocrine markers (RB1/TP53 loss) for aggressive variants.',
        color: '#0ea5e9',
        expression: genes([
            ['AR', 11.6], ['KLK3', 12.0], ['FOLH1', 11.2], ['ERG', 10.8], ['NKX3-1', 11.0],
            ['HOXB13', 10.6], ['AMACR', 11.4], ['KLK2', 10.9], ['TMPRSS2', 11.1], ['SPINK1', 7.4],
            ['PTEN', 5.6], ['TP53', 7.8], ['RB1', 8.2], ['MYC', 9.2], ['SPOP', 8.0],
            ['FOXA1', 10.8], ['CHGA', 5.8], ['SYP', 5.6], ['ENO2', 6.0], ['NCAM1', 5.9],
            ['MKI67', 6.4], ['TOP2A', 6.6], ['CCNB1', 6.2], ['AURKA', 6.0], ['CDK1', 6.3],
            ['EZH2', 8.8], ['CCND1', 8.0], ['CDKN1B', 7.0], ['CDKN2A', 6.4], ['BCL2', 7.2],
            ['CDH1', 10.2], ['VIM', 6.2], ['SNAI1', 5.8], ['ZEB1', 5.6], ['FN1', 6.8],
            ['EPCAM', 10.4], ['KRT8', 10.6], ['KRT18', 10.4], ['KRT19', 9.8], ['KLK4', 10.2],
            ['VEGFA', 7.4], ['HIF1A', 7.6], ['PIK3CA', 8.2], ['AKT1', 8.4], ['MTOR', 8.0],
            ['SCHLAP1', 9.0], ['PCA3', 10.0], ['GOLM1', 9.4], ['STAT3', 7.8], ['IGF1R', 8.2],
        ]),
    },
]

export const RESEARCH_EXAMPLES: ResearchExample[] = [
    {
        text: 'What genes predict overall survival in lung adenocarcinoma across independent GEO cohorts?',
        query: 'lung adenocarcinoma overall survival',
    },
    {
        text: 'Find colorectal cancer biomarkers consistently prognostic across multiple independent studies',
        query: 'colorectal cancer overall survival prognosis',
    },
    {
        text: 'Compare EGFR and KRAS as survival predictors in lung adenocarcinoma across GEO datasets',
        query: 'EGFR KRAS lung adenocarcinoma survival',
    },
    {
        text: 'Validate CDKN2A as a prognostic marker in pancreatic cancer across GEO cohorts',
        query: 'CDKN2A pancreatic cancer overall survival',
    },
    {
        text: 'Is high MKI67 expression associated with worse survival in gastric cancer?',
        query: 'MKI67 gastric cancer overall survival',
    },
]
