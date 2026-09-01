import { PredictResponse, ReferenceKMCurve, SurvivalAnalysisResponse } from '../../services/api'
import { ExtractedCaseFacts } from '../../utils/caseParser'
import { ConsoleAction } from '../../services/chatApi'

export type ActionStatus = 'proposed' | 'applied' | 'declined' | 'failed'

export type ConsoleEntry =
    /** `sentTurn` is the de-identified turn actually forwarded to the agent, or
     *  null when the whole message was read into the chart locally. */
    | { kind: 'doctor-note'; id: string; text: string; extracted: ExtractedCaseFacts; sentTurn: string | null; timestamp?: string }
    | { kind: 'doctor-question'; id: string; text: string; timestamp?: string }
    | { kind: 'assistant'; id: string; text: string; domainScore?: number; modelUsed?: string; timestamp?: string; streaming?: boolean }
    | { kind: 'action'; id: string; action: ConsoleAction; status: ActionStatus; detail?: string }
    | { kind: 'intake'; id: string }
    | {
          kind: 'readout'
          id: string
          prediction: PredictResponse
          modelId: string
          cancerLabel: string
          modelIsDemo: boolean
          referenceCurves?: ReferenceKMCurve[]
          timeUnit: string
          expression: Record<string, number>
          clinical: Record<string, string>
      }
    | { kind: 'summary'; id: string; resultId: string | null; query: string }
    | { kind: 'model-quality'; id: string; modelId: string }
    | { kind: 'treatment-evidence'; id: string; modelId: string; riskGroup: string | null; genes: string[]; baselineCurve: ReferenceKMCurve | null; expression: Record<string, number>; clinical: Record<string, string>; timeUnit: string }
    | { kind: 'treatment-context'; id: string; cancerType: string; expression: Record<string, number>; clinical: Record<string, string> }
    | { kind: 'pathway'; id: string; geneSymbols: string[] }
    | {
          kind: 'analysis-progress'
          id: string
          runId: string
          query: string
          /** Terminal states matter: without them a finished run leaves a bar
           *  animating forever, and a failed one leaves no trace at all. */
          status: 'running' | 'done' | 'failed'
          error?: string
      }
    | {
          kind: 'analysis-result'
          id: string
          runId: string
          query: string
          result: SurvivalAnalysisResponse
          resultId: string | null
          /** Signature model auto-built from the result — gates treatment curves. */
          modelId: string | null
          /** Genes the question named; non-empty ⇒ a focused hypothesis test,
           *  which also means the p-values are NOT multiple-testing corrected. */
          focusGenes: string[]
      }

/**
 * Where the chart's risk model comes from. A discriminated union rather than
 * four loose useState fields, because the combinations are NOT independent:
 * `startCohortBuild` used to clear cancerKey/modelId while keeping resultId,
 * which made the Score gate and buildPatientContext() read the chart as empty.
 * That state is now unrepresentable.
 */
export type ChartSource =
    | { kind: 'none' }
    /** A curated cancer type from GET /api/gallery. */
    | { kind: 'curated'; cancerKey: string; label: string; modelId: string | null; resultId: string | null }
    /** A case loaded with no curated model yet — a cohort build is the next step. */
    | { kind: 'pending'; label: string; query: string }
    /** A cohort model built on demand from a natural-language query. */
    | { kind: 'cohort'; label: string; query: string; resultId: string }

export const chartModelId = (s: ChartSource): string | null => (s.kind === 'curated' ? s.modelId : null)
export const chartResultId = (s: ChartSource): string | null =>
    s.kind === 'curated' || s.kind === 'cohort' ? s.resultId : null
export const chartCancerKey = (s: ChartSource): string | null => (s.kind === 'curated' ? s.cancerKey : null)
export const chartLabel = (s: ChartSource): string => (s.kind === 'none' ? '' : s.label)
/** True once the chart has something /api/predict can actually score against. */
export const hasModelSource = (s: ChartSource): boolean => !!chartModelId(s) || !!chartResultId(s)

/**
 * Why "Score patient" is disabled, or undefined when it is enabled. Pure so it
 * can be unit-tested — this gate was silently dead in two reachable states.
 */
export function scoreDisabledReason(source: ChartSource, geneCount: number): string | undefined {
    if (!hasModelSource(source)) {
        if (source.kind === 'curated') return 'This cancer type\u2019s model is still being prepared'
        if (source.kind === 'pending') return 'Build a cohort model for this case first \u2014 about 3 minutes'
        return 'Pick a cancer type, or build a cohort model, first'
    }
    if (geneCount === 0) return 'Paste the tumour expression profile above \u2014 one "GENE value" per line'
    return undefined
}
