import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getStoredToken, removeStoredToken } from './authApi'

const API_BASE_URL = '/api'

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor: Add auth token to requests
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = getStoredToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor: Handle 401 errors
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            removeStoredToken()
            // Optionally redirect to login or dispatch logout action
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)

export interface KMCurveData {
    times: number[]
    survival_probabilities: number[]
    ci_lower: number[] | null
    ci_upper: number[] | null
    n_samples: number
    n_events: number
}

export interface GeneDatasetResult {
    dataset_id: string
    dataset_title: string
    hazard_ratio: number
    hazard_ratio_ci_lower: number
    hazard_ratio_ci_upper: number
    cox_p_value: number
    log_rank_p_value: number
    risk_direction: 'high_risk' | 'low_risk'
    n_samples: number
    median_survival_high: number | null
    median_survival_low: number | null
    km_curve_high: KMCurveData | null
    km_curve_low: KMCurveData | null
    // Multivariate (clinically-adjusted) Cox results (F16)
    adjusted_hazard_ratio?: number | null
    multivariate_cox_p?: number | null
    covariates_used?: string[] | null
}

export interface GeneSurvivalResponse {
    gene_id: string
    gene_symbol: string | null
    n_datasets: number
    avg_hazard_ratio: number
    avg_cox_p_value: number
    avg_log_rank_p_value: number
    predominant_risk: 'high_risk' | 'low_risk'
    risk_direction_consistency: number
    datasets: string[]
    per_dataset_results: GeneDatasetResult[] | null
}

export interface SurvivalAnalysisResponse {
    query: string
    n_datasets_analyzed: number
    n_datasets_with_survival: number
    common_genes: GeneSurvivalResponse[]
    processing_time: number
    timestamp: string
    result_id?: string | null
}

export interface AnalysisProgressEvent {
    stage: string
    message: string
    current?: number | null
    total?: number | null
}

export function streamAnalysis(
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    organism: string | null = null,
    cancerGenesOnly: boolean = false,
    geneFilter: string[] | null = null,
    minOccurrence: number = 2,
    onProgress: (event: AnalysisProgressEvent) => void,
    onComplete: (result: SurvivalAnalysisResponse) => void,
    onError: (message: string) => void,
): EventSource {
    const params = new URLSearchParams({
        query,
        model,
        max_datasets: String(maxDatasets),
        ranking_multiplier: String(rankingMultiplier),
        min_occurrence: String(minOccurrence),
        cancer_genes_only: String(cancerGenesOnly),
    })
    if (organism) {
        params.set('organism', organism)
    }
    if (geneFilter && geneFilter.length > 0) {
        for (const gene of geneFilter) {
            params.append('gene_filter', gene)
        }
    }
    const es = new EventSource(`/api/search/stream?${params.toString()}`)

    es.onmessage = (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data as string) as {
                stage: string
                message?: string
                current?: number | null
                total?: number | null
                result?: SurvivalAnalysisResponse
            }
            if (data.stage === 'result') {
                es.close()
                onComplete(data.result!)
            } else if (data.stage === 'error') {
                es.close()
                onError(data.message ?? 'Unknown error')
            } else {
                onProgress({
                    stage: data.stage,
                    message: data.message ?? '',
                    current: data.current ?? undefined,
                    total: data.total ?? undefined,
                })
            }
        } catch (parseErr) {
            console.error('SSE parse error:', parseErr)
        }
    }

    es.onerror = () => {
        es.close()
        onError('Connection lost during analysis')
    }

    return es
}

export async function getAnalysisResult(resultId: string): Promise<SurvivalAnalysisResponse> {
    const response = await axios.get<SurvivalAnalysisResponse>(`/api/results/${resultId}`)
    return response.data
}

export async function listAnalysisResults(limit = 20, offset = 0): Promise<AnalysisHistoryItem[]> {
    const token = getStoredToken()
    const response = await axios.get<AnalysisHistoryItem[]>('/api/results', {
        params: { limit, offset },
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    return response.data
}

export interface AnalysisHistoryItem {
    result_id: string
    query: string
    n_datasets_analyzed: number
    n_datasets_with_survival: number
    n_genes_found: number
    processing_time_seconds: number | null
    created_at: string
}

export interface GeneComparisonItem {
    gene_symbol: string
    hr_a: number
    hr_b: number
    p_value_a: number
    p_value_b: number
    n_datasets_a: number
    n_datasets_b: number
    direction_agrees: boolean
}

export interface CompareResponse {
    query_a: string
    query_b: string
    shared_genes: GeneComparisonItem[]
    unique_to_a: string[]
    unique_to_b: string[]
    n_shared: number
    n_unique_a: number
    n_unique_b: number
    direction_agreement_pct: number | null
    spearman_r: number | null
}

export async function compareAnalyses(resultIdA: string, resultIdB: string): Promise<CompareResponse> {
    const response = await apiClient.post<CompareResponse>('/compare', {
        result_id_a: resultIdA,
        result_id_b: resultIdB,
    })
    return response.data
}

// ==================== Clinician interpretation (F21) ====================

export interface InterpretResponse {
    summary: string
    domain_score: number
}

export async function interpretResults(params: {
    query: string
    model?: string
    genes: Array<{
        gene_symbol: string | null
        avg_hazard_ratio: number
        avg_cox_p_value: number
        n_datasets: number
        predominant_risk: string
        datasets: string[]
    }>
    n_datasets_with_survival: number
}): Promise<InterpretResponse> {
    const response = await apiClient.post<InterpretResponse>('/chat/interpret', {
        query: params.query,
        model: params.model ?? 'mistral',
        genes: params.genes,
        n_datasets_with_survival: params.n_datasets_with_survival,
    })
    return response.data
}

// ==================== Oncologist Mode gallery (F20) ====================

export interface ClinicalCovariateSpec {
    name: string
    display_label: string
    kind: 'numeric' | 'categorical'
    options: string[] | null
    min_value: number | null
    max_value: number | null
    required: boolean
}

export interface GalleryCancer {
    key: string
    label: string
    query: string
    blurb: string
    icon: string
    // Patient-scoring model (headline of Oncologist Mode):
    model_id: string | null
    n_genes: number | null
    pooled_c_index: number | null
    c_index_expression_only: number | null
    c_index_combined: number | null
    delta_c_index: number | null
    clinical_covariates: ClinicalCovariateSpec[]
    model_is_demo: boolean | null
    // Underlying cohort analysis (provenance):
    result_id: string | null
    n_genes_found: number | null
    n_datasets_with_survival: number | null
    cached_at: string | null
}

export async function getGallery(): Promise<GalleryCancer[]> {
    const response = await axios.get<{ cancers: GalleryCancer[] }>('/api/gallery')
    return response.data.cancers
}

// ==================== Prognostic Signature (F17/F18/F19/F23) ====================

export interface SignatureGene {
    gene_symbol: string
    coefficient: number
    hazard_ratio: number
    ref_mean: number
    ref_std: number
    ref_quantiles: number[]
}

export interface ReferenceKMCurve {
    group: string
    times: number[]
    survival_probabilities: number[]
    n_samples: number
    n_events: number
}

export interface CohortValidation {
    accession: string
    role: 'training' | 'validation'
    n_samples: number
    n_events: number
    c_index: number
}

export interface PrognosticModel {
    model_id: string
    query: string
    cancer_type?: string | null
    version: string
    created_at: string
    time_unit: string
    genes: SignatureGene[]
    risk_score_tertiles: number[]
    risk_score_quantiles: number[]
    reference_km: ReferenceKMCurve[]
    training_accession: string
    n_training_samples: number
    cohort_validations: CohortValidation[]
    pooled_c_index: number
    clinical_covariates?: ClinicalCovariateSpec[]
    expression_score_coefficient?: number
    combined_risk_tertiles?: number[] | null
    combined_risk_quantiles?: number[] | null
    combined_reference_km?: ReferenceKMCurve[] | null
    c_index_expression_only?: number | null
    c_index_clinical_only?: number | null
    c_index_combined?: number | null
    delta_c_index?: number | null
    is_demo: boolean
    disclaimer: string
}

export interface SurvivalAtHorizon {
    horizon_label: string
    time: number
    survival_probability: number
}

export interface RiskContribution {
    label: string
    contribution: number
    kind: 'expression' | 'clinical'
}

export interface PredictResponse {
    model_id: string
    risk_score: number
    risk_group: string
    risk_percentile: number
    genes_used: number
    genes_total: number
    reference_km: ReferenceKMCurve
    predicted_survival: SurvivalAtHorizon[]
    pooled_c_index: number
    scored_on: string
    normalization: string
    warnings: string[]
    contributions: RiskContribution[]
    c_index_expression_only: number | null
    c_index_clinical_only: number | null
    c_index_combined: number | null
    delta_c_index: number | null
    disclaimer: string
}

export async function buildSignature(params: {
    result_id?: string | null
    query?: string | null
    max_genes?: number
    demo?: boolean
}): Promise<PrognosticModel> {
    const response = await apiClient.post<PrognosticModel>('/signature', {
        result_id: params.result_id ?? null,
        query: params.query ?? null,
        max_genes: params.max_genes ?? 15,
        demo: params.demo ?? false,
    })
    return response.data
}

export async function getSignatureModel(modelId: string): Promise<PrognosticModel> {
    const response = await apiClient.get<PrognosticModel>(`/signature/${modelId}`)
    return response.data
}

export async function getDemoPatient(modelId: string): Promise<Record<string, number>> {
    const response = await apiClient.get<{ model_id: string; expression: Record<string, number> }>(
        `/signature/${modelId}/demo-patient`,
    )
    return response.data.expression
}

export async function predictSingleSample(
    modelId: string,
    expression: Record<string, number>,
    clinical?: Record<string, string | number> | null,
): Promise<PredictResponse> {
    const response = await apiClient.post<PredictResponse>('/predict', {
        model_id: modelId,
        expression,
        clinical: clinical ?? null,
    })
    return response.data
}

// ============ Unified personalization (auto-build + score) ============

export interface PersonalizeResponse {
    model_id: string
    cancer_type: string | null
    model_is_demo: boolean
    clinical_covariates: ClinicalCovariateSpec[]
    prediction: PredictResponse
}

export async function personalizePatient(params: {
    resultId?: string | null
    modelId?: string | null
    expression: Record<string, number>
    clinical?: Record<string, string | number> | null
    maxGenes?: number
}): Promise<PersonalizeResponse> {
    const response = await apiClient.post<PersonalizeResponse>('/personalize', {
        result_id: params.resultId ?? null,
        model_id: params.modelId ?? null,
        expression: params.expression,
        clinical: params.clinical ?? null,
        max_genes: params.maxGenes ?? 15,
    })
    return response.data
}

// ============ Grounded therapy rationale (Oncologist Mode) ============

export interface TherapyEvidenceRecord {
    gene: string
    source: 'CIViC' | 'DGIdb'
    drug: string
    evidence_type?: string | null
    significance?: string | null
    direction?: string | null
    evidence_level?: string | null
    disease?: string | null
    url?: string | null
    interaction_type?: string | null
    approved?: boolean | null
    source_db?: string | null
}

export interface TherapyRationaleResponse {
    rationale: string
    evidence: TherapyEvidenceRecord[]
    domain_score: number
    disclaimer: string
}

export async function getTherapyRationale(params: {
    modelId: string
    genes?: string[]
    riskGroup?: string | null
    model?: string
}): Promise<TherapyRationaleResponse> {
    const response = await apiClient.post<TherapyRationaleResponse>('/chat/therapy-rationale', {
        model_id: params.modelId,
        genes: params.genes ?? [],
        risk_group: params.riskGroup ?? null,
        model: params.model ?? 'mistral',
    })
    return response.data
}

export const searchDatasets = async (
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    organism: string | null = null,
    cancerGenesOnly: boolean = false,
    geneFilter: string[] | null = null,
): Promise<SurvivalAnalysisResponse> => {
    try {
        const response = await apiClient.post('/search', {
            query: query,
            model: model,
            max_datasets: maxDatasets,
            ranking_multiplier: rankingMultiplier,
            organism: organism,
            min_occurrence: 2,
            cancer_genes_only: cancerGenesOnly,
            gene_filter: geneFilter,
        })
        return response.data
    } catch (error) {
        console.error('Error searching datasets:', error)
        throw error
    }
}

