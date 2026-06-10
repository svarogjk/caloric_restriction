/**
 * A sample tumour expression profile so an oncologist can see how patient
 * personalization works without their own data. It is a broad panel of common
 * cancer-associated genes on a typical microarray log2 scale (~4–13). Values are
 * illustrative; the app rank/quantile-normalizes them onto each model's
 * reference, so the absolute scale does not matter.
 */
export const SAMPLE_PATIENT_EXPRESSION: string = [
    ['TP53', 9.1], ['MKI67', 11.6], ['ESR1', 10.8], ['ERBB2', 8.4], ['EGFR', 7.2],
    ['KRAS', 8.9], ['MYC', 10.2], ['BRCA1', 6.7], ['BRCA2', 6.1], ['PTEN', 7.8],
    ['CDH1', 9.4], ['VIM', 10.6], ['CCND1', 9.9], ['CDKN2A', 5.8], ['RB1', 7.4],
    ['AKT1', 8.2], ['PIK3CA', 8.7], ['BCL2', 9.0], ['BAX', 8.1], ['CASP3', 7.6],
    ['VEGFA', 9.3], ['HIF1A', 8.5], ['CD44', 10.1], ['ALDH1A1', 7.0], ['EPCAM', 10.9],
    ['KRT19', 11.2], ['KRT8', 11.5], ['KRT18', 11.4], ['MUC1', 9.7], ['CEACAM5', 8.8],
    ['TOP2A', 10.3], ['AURKA', 9.2], ['BIRC5', 9.8], ['FOXM1', 9.1], ['PCNA', 10.7],
    ['STAT3', 8.6], ['JUN', 9.5], ['FOS', 8.9], ['CDK1', 9.6], ['CCNB1', 9.4],
    ['MMP9', 8.3], ['TIMP1', 9.9], ['SPP1', 10.0], ['COL1A1', 10.4], ['FN1', 10.5],
    ['CD8A', 6.9], ['PDCD1', 5.6], ['CD274', 6.3], ['GZMB', 6.8], ['IFNG', 5.9],
]
    .map(([g, v]) => `${g} ${v}`)
    .join('\n')
