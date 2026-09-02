import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import { createConversation, sendMessage, runAnalysis, saveAnalysisResult, abortActiveAnalysis } from '../../store/chatSlice'
import { getGallery, buildSignature, GalleryCancer, PredictResponse } from '../../services/api'
import { PatientContextPayload, ResearchContextPayload, ConsoleAction } from '../../services/chatApi'
import { SamplePatient, SAMPLE_PATIENTS } from '../../utils/samplePatients'
import { parseCaseDescription, looksIdentifying } from '../../utils/caseParser'
import { estimateGeneDrivers } from '../../utils/signatureViz'
import { analyseExpression, QN_MIN_GENES, LOW_COVERAGE_FRAC } from '../../utils/expressionFeedback'
import { buildPatientPrompts } from '../../utils/patientPrompts'
import { summariseAnalysis } from '../../utils/analysisSummary'
import { deriveWorkflow, WorkflowStep, WorkflowStepId } from '../../utils/caseWorkflow'
import {
    AnswerableQuestion, QuestionId, QUESTION_CATALOGUE, getQuestion, fillTemplate,
} from '../../utils/questionCatalogue'
import { usePatientScoring } from '../../hooks/usePatientScoring'
import { useAnalysisRun } from '../../hooks/useAnalysisRun'
import { useConsoleActions, ConsoleActionHandlers } from '../../hooks/useConsoleActions'
import {
    ConsoleEntry, ActionStatus, ChartSource,
    chartModelId, chartResultId, chartCancerKey, chartLabel, hasModelSource, scoreDisabledReason,
} from './types'
import ChartStrip from './ChartStrip'
import ConsoleThread from './ConsoleThread'
import ConsoleComposer from './ConsoleComposer'
import PatientRail from './PatientRail'

let idCounter = 0
const newId = () => `e${Date.now()}-${idCounter++}`

const formatTurnTime = (iso?: string): string | undefined => {
    const d = iso ? new Date(iso) : new Date()
    return Number.isNaN(d.getTime()) ? undefined : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const ClinicalConsole: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>()
    const selectedModel = useSelector((s: RootState) => s.chat.selectedModel)
    const activeConversationId = useSelector((s: RootState) => s.chat.activeConversationId)
    const isStreaming = useSelector((s: RootState) => s.chat.isStreaming)
    const streamingContent = useSelector((s: RootState) => s.chat.streamingContent)

    const composerRef = useRef<HTMLTextAreaElement>(null)
    const conversationIdRef = useRef<string | null>(activeConversationId)
    const pendingActionsRef = useRef<Record<string, ConsoleAction>>({})

    const [cancers, setCancers] = useState<GalleryCancer[]>([])
    const [cancersLoading, setCancersLoading] = useState(true)
    const [thresholds, setThresholds] = useState({ qnMinGenes: QN_MIN_GENES, lowCoverageFrac: LOW_COVERAGE_FRAC })

    // The chart's model provenance as ONE value — see ChartSource in types.ts for
    // why this isn't four independent useState fields.
    const [source, setSource] = useState<ChartSource>({ kind: 'none' })
    const [exprText, setExprText] = useState('')
    const [clinical, setClinical] = useState<Record<string, string>>({})
    const [fileError, setFileError] = useState<string | null>(null)

    const cancerKey = chartCancerKey(source)
    const modelId = chartModelId(source)
    const resultId = chartResultId(source)
    const label = chartLabel(source)

    // The opening card is an entry rather than an "empty thread" placeholder, so
    // the catalogue of answerable questions stays in the log and can be scrolled
    // back to once the conversation has moved on.
    const [entries, setEntries] = useState<ConsoleEntry[]>([{ kind: 'start', id: 'start' }])
    const [railOpen, setRailOpen] = useState(false)
    /** Which catalogue question this session is pursuing — scopes the workflow so
     *  a cohort-only question is never told a tumour profile is missing. */
    const [goal, setGoal] = useState<QuestionId | null>(null)
    /** Model built from the most recent analysis — lets treatment evidence work
     *  with no patient chart at all. */
    const [lastAnalysisModelId, setLastAnalysisModelId] = useState<string | null>(null)

    const scoring = usePatientScoring({ resultId, modelId })
    const analysisRun = useAnalysisRun()

    // An analysis outlives the component that started it — close the stream on
    // unmount so leaving the console doesn't leave an SSE connection open.
    useEffect(() => abortActiveAnalysis, [])

    useEffect(() => {
        getGallery()
            .then((res) => {
                setCancers(res.cancers)
                setThresholds({ qnMinGenes: res.scoring_thresholds.qn_min_genes, lowCoverageFrac: res.scoring_thresholds.low_coverage_frac })
            })
            .catch(() => undefined)
            .finally(() => setCancersLoading(false))
    }, [])

    const pushEntry = (e: ConsoleEntry) => setEntries((prev) => [...prev, e])
    const updateActionEntry = (id: string, status: ActionStatus, detail?: string) =>
        setEntries((prev) => prev.map((e) => (e.kind === 'action' && e.id === id ? { ...e, status, detail } : e)))

    /** Offer a step as confirm/decline rather than running it — used for anything
     *  that costs minutes or overwrites the chart. */
    const proposeAction = (action: ConsoleAction) => {
        const id = newId()
        pendingActionsRef.current[id] = action
        pushEntry({ kind: 'action', id, action, status: 'proposed' })
    }

    const cancerIcon = cancers.find((c) => c.key === cancerKey)?.icon ?? null
    const expressionFeedback = useMemo(
        () => analyseExpression(exprText, scoring.signatureGenes, thresholds),
        [exprText, scoring.signatureGenes, thresholds],
    )
    const hasChart = source.kind !== 'none' || exprText.trim().length > 0

    // ---------- workflow (derived — see utils/caseWorkflow.ts) ----------
    const goalQuestion = goal ? getQuestion(goal) ?? null : null
    const lastAnalysis = useMemo(
        () => [...entries].reverse().find((e) => e.kind === 'analysis-result') ?? null,
        [entries],
    ) as Extract<ConsoleEntry, { kind: 'analysis-result' }> | null
    const analysisSummary = useMemo(
        () => (lastAnalysis ? summariseAnalysis(lastAnalysis.result, lastAnalysis.focusGenes) : null),
        [lastAnalysis],
    )
    const covariateCount = Object.values(clinical).filter((v) => v !== '').length

    /** Where the evidence step's cohorts came from — curated model, or this session's run. */
    const evidenceDetail = useMemo(() => {
        const curated = cancers.find((c) => c.key === cancerKey)
        if (source.kind === 'curated' && curated?.model_id) {
            const c = curated.pooled_c_index
            return [curated.n_genes ? `${curated.n_genes} genes` : null, c ? `C-index ${c.toFixed(2)}` : null]
                .filter(Boolean).join(' · ') || 'curated model'
        }
        if (analysisSummary) return `${analysisSummary.nDatasetsWithSurvival} GEO cohorts`
        return null
    }, [source.kind, cancerKey, cancers, analysisSummary])

    const workflow = useMemo(() => deriveWorkflow({
        sourceKind: source.kind,
        sourceLabel: label,
        hasModel: hasModelSource(source),
        modelIsDemo: scoring.modelIsDemo,
        feedback: expressionFeedback,
        prediction: scoring.prediction,
        analysisRunning: analysisRun.isRunning,
        evidenceDetail,
        focusGenesUsed: (lastAnalysis?.focusGenes.length ?? 0) > 0,
        neededSteps: goalQuestion?.steps ?? null,
        shownWhy: entries.some((e) => e.kind === 'model-quality' || e.kind === 'pathway'),
        shownOptions: entries.some((e) => e.kind === 'treatment-evidence' || e.kind === 'treatment-context'),
        covariateCount,
    }), [
        source, label, scoring.modelIsDemo, expressionFeedback, scoring.prediction,
        analysisRun.isRunning, evidenceDetail, lastAnalysis, goalQuestion, entries, covariateCount,
    ])

    // ---------- de-identified chart snapshot sent to the agent ----------
    const buildPatientContext = (): PatientContextPayload | null => {
        if (source.kind === 'none') return null
        const p = scoring.prediction
        // PredictResponse.contributions aggregates the WHOLE expression signature into
        // one "Expression signature" entry (see SignatureService._score_expression) —
        // there's no per-gene breakdown in the API. estimateGeneDrivers() approximates
        // one client-side from the model's own coefficients; see its docstring.
        const drivers = p ? estimateGeneDrivers(scoring.signatureGeneDetails, scoring.lastExpression) : []
        const topRisk = drivers.filter((d) => d.direction === 'risk').slice(0, 3).map((d) => d.gene_symbol)
        const topProtective = drivers.filter((d) => d.direction === 'protective').slice(0, 3).map((d) => d.gene_symbol)
        const covariateNames = p ? p.contributions.filter((c) => c.kind === 'clinical').map((c) => c.label) : []
        return {
            cancer_type: cancerKey,
            model_id: scoring.resolvedModelId,
            model_is_demo: scoring.modelIsDemo,
            genes_provided: expressionFeedback.geneCount || null,
            risk_group: (p?.risk_group as PatientContextPayload['risk_group']) ?? null,
            risk_percentile: p?.risk_percentile ?? null,
            genes_used: p?.genes_used ?? null,
            genes_total: p?.genes_total ?? null,
            pooled_c_index: p?.pooled_c_index ?? null,
            c_index_combined: p?.c_index_combined ?? null,
            delta_c_index: p?.delta_c_index ?? null,
            scored_on: p?.scored_on ?? null,
            top_risk_genes: topRisk,
            top_protective_genes: topProtective,
            clinical_covariate_names: covariateNames,
            warnings: p?.warnings ?? [],
        }
    }

    /**
     * Session state with no patient in it. Unlike buildPatientContext() this is
     * ALWAYS sent — "nothing loaded yet" is precisely what the agent needs in
     * order to drive the first step, and returning null there is what used to
     * leave it with no situational context at all in research mode.
     */
    const buildResearchContext = (): ResearchContextPayload => {
        const last = lastAnalysis
        const summary = analysisSummary
        const currentStep = workflow.steps.find((s) => s.id === workflow.current) ?? null
        return {
            has_patient_chart: source.kind !== 'none',
            expression_genes_pasted: expressionFeedback.geneCount || null,
            analysis_running: analysisRun.isRunning,
            analysis_result_id: last?.resultId ?? null,
            analysis_query: last?.query ?? null,
            analysis_model_id: last?.modelId ?? lastAnalysisModelId,
            analysis_n_genes: summary?.nGenes ?? null,
            analysis_n_datasets: summary?.nDatasetsWithSurvival ?? null,
            analysis_n_predictive_genes: summary?.nPredictive ?? null,
            analysis_gene_filter_applied: (last?.focusGenes.length ?? 0) > 0,
            analysis_top_genes: (summary?.genes ?? []).slice(0, 8).map((g) => g.gene_symbol ?? g.gene_id),
            treatment_evidence_shown: entries.some((e) => e.kind === 'treatment-evidence'),
            // The single workflow ladder. The agent used to receive two competing
            // "MISSING:" lines assembled independently on the backend; this is now
            // the one source, derived from the same state the clinician can see.
            workflow_goal: goal,
            workflow_step: workflow.current,
            workflow_done: workflow.doneIds,
            workflow_blocked_reason: currentStep?.blockedReason ?? null,
            workflow_next_action: currentStep?.actionTool ?? null,
            workflow_caveats: workflow.caveats.slice(0, 8),
        }
    }

    // ---------- sending to the agent ----------
    const ensureConversation = async (): Promise<string | null> => {
        if (conversationIdRef.current) return conversationIdRef.current
        const result = await dispatch(createConversation(undefined))
        if (createConversation.fulfilled.match(result)) {
            conversationIdRef.current = result.payload.conversationId
            return result.payload.conversationId
        }
        return null
    }

    const processActions = (actions: ConsoleAction[] | undefined) => {
        for (const action of actions ?? []) {
            if (consoleActions.needsConfirmation(action)) {
                proposeAction(action)
            } else {
                const result = consoleActions.execute(action)
                pushEntry({ kind: 'action', id: newId(), action, status: result.status, detail: result.detail })
            }
        }
    }

    const sendToAgent = async (text: string) => {
        const convId = await ensureConversation()
        if (!convId) return
        const patientContext = buildPatientContext()
        const researchContext = buildResearchContext()
        const resultAction = await dispatch(sendMessage({
            conversationId: convId, content: text, model: selectedModel, patientContext, researchContext,
        }))
        if (sendMessage.fulfilled.match(resultAction)) {
            pushEntry({
                kind: 'assistant', id: newId(), text: resultAction.payload.content,
                domainScore: resultAction.payload.domainScore,
                modelUsed: resultAction.payload.modelUsed,
                timestamp: formatTurnTime(resultAction.payload.createdAt),
            })
            processActions(resultAction.payload.actions)
        }
    }

    const handleSubmitQuestion = (text: string, newGoal?: QuestionId) => {
        if (newGoal) setGoal(newGoal)
        pushEntry({ kind: 'doctor-question', id: newId(), text, timestamp: formatTurnTime() })
        void sendToAgent(text)
    }

    /** A catalogue question picked from the start card: sets the goal, then asks it. */
    const chooseQuestion = (question: AnswerableQuestion, vars: { gene?: string; cancer?: string }) => {
        handleSubmitQuestion(fillTemplate(question, vars), question.id)
    }

    const handleSubmitCase = (rawText: string, facts: ReturnType<typeof parseCaseDescription>) => {
        // Work out what (if anything) will be sent BEFORE rendering the note, so the
        // "what was sent" disclosure states the truth rather than a hardcoded null.
        const parts: string[] = []
        if (facts.cancerTerm) parts.push(`a ${facts.cancerTerm} case`)
        const covNames = Object.keys(facts.covariates)
        if (covNames.length > 0) parts.push(`supplied ${covNames.join(', ')}`)
        const synthesizedNote = parts.length > 0
            ? `The clinician described ${parts.join(' and ')}. Nothing identifying was transmitted.`
            : null

        const residual = facts.residualText
        const hasResidualQuestion = residual.length > 3 && !looksIdentifying(residual)
        const turn = [synthesizedNote, hasResidualQuestion ? residual : null].filter(Boolean).join(' ')

        pushEntry({ kind: 'doctor-note', id: newId(), text: rawText, extracted: facts, sentTurn: turn || null, timestamp: formatTurnTime() })

        // Apply the extracted facts to the chart locally — nothing here is sent anywhere.
        if (facts.cancerTerm) {
            const cancer = facts.cancerKey ? cancers.find((c) => c.key === facts.cancerKey) : null
            if (cancer) {
                setSource({ kind: 'curated', cancerKey: cancer.key, label: cancer.label, modelId: cancer.model_id, resultId: cancer.result_id })
            } else {
                setSource({ kind: 'pending', label: facts.cancerTerm, query: `${facts.cancerTerm} overall survival` })
            }
        }
        if (Object.keys(facts.covariates).length > 0) {
            setClinical((prev) => ({ ...prev, ...facts.covariates }))
        }
        // Open the step the description did NOT settle. A note naming a cancer type
        // has completed step 1, so asking for it again would read as if the app had
        // ignored what was just typed.
        pushEntry(facts.cancerTerm ? { kind: 'intake', id: newId() } : { kind: 'case-setup', id: newId() })

        if (turn) void sendToAgent(turn)
    }

    /** Called by the StartCard, which owns its own input; the composer path
     *  parses first and calls handleSubmitCase directly. */
    const handleStartCase = (rawText: string) => handleSubmitCase(rawText, parseCaseDescription(rawText))

    // ---------- action handlers (what the client actually executes) ----------
    const selectCancer = (cancer: GalleryCancer) => {
        setSource({ kind: 'curated', cancerKey: cancer.key, label: cancer.label, modelId: cancer.model_id, resultId: cancer.result_id })
        setExprText('')
        setClinical({})
        setFileError(null)
        pushEntry({ kind: 'intake', id: newId() })
    }

    const loadCase = (patient: SamplePatient) => {
        const cancer = patient.cancerKey ? cancers.find((c) => c.key === patient.cancerKey) : null
        setExprText(patient.expression)
        setClinical(patient.clinical ?? {})
        setFileError(null)
        if (cancer) {
            setSource({ kind: 'curated', cancerKey: cancer.key, label: cancer.label, modelId: cancer.model_id, resultId: cancer.result_id })
            pushEntry({ kind: 'intake', id: newId() })
            if (cancer.model_id) {
                void scoring.score(patient.expression, patient.clinical ?? {}, cancer.model_id, cancer.result_id ?? null)
            }
            return
        }
        // No curated model for this cancer type — the case still loads, but scoring
        // needs a cohort model. Offer that build instead of leaving a dead Score button.
        setSource({ kind: 'pending', label: patient.name, query: patient.query })
        pushEntry({ kind: 'intake', id: newId() })
        proposeAction({ action: 'run_analysis', query: patient.query })
    }

    const doScore = () => {
        void scoring.score(exprText, clinical)
    }

    /** Scroll to the live form of a kind, opening one if the thread has none. */
    const focusEntry = (kind: 'case-setup' | 'intake') => {
        setRailOpen(false)
        const existing = [...entries].reverse().find((e) => e.kind === kind)
        const id = existing?.id ?? newId()
        if (!existing) pushEntry({ kind, id } as ConsoleEntry)
        requestAnimationFrame(() => {
            document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        })
    }

    /** Update one entry in place — analysis entries change status as the run
     *  proceeds, rather than being appended again. */
    const patchEntry = (id: string, patch: Partial<ConsoleEntry>) =>
        setEntries((prev) => prev.map((e) => (e.id === id ? ({ ...e, ...patch } as ConsoleEntry) : e)))

    /**
     * Run a real cross-cohort analysis and put the RESULT in the thread.
     *
     * This used to keep only `result_id` and throw the payload away, so a 2-5
     * minute run produced nothing the user could look at. The result now becomes
     * an entry; the chart source is still set so a patient can be scored against
     * it, and a signature model is built eagerly because treatment curves need
     * one and it is cheap once the cohorts are cached.
     */
    const startCohortBuild = async (query: string, candidateGenes: string[] = []) => {
        const runId = newId()
        const entryId = newId()
        pushEntry({ kind: 'analysis-progress', id: entryId, runId, query, status: 'running' })
        analysisRun.begin(runId)

        const resultAction = await dispatch(runAnalysis({ query, geneFilter: candidateGenes.length ? candidateGenes : undefined }))
        if (!runAnalysis.fulfilled.match(resultAction)) {
            analysisRun.end(runId)
            patchEntry(entryId, { status: 'failed', error: String(resultAction.payload ?? 'the run did not complete') })
            return
        }
        analysisRun.end(runId)
        patchEntry(entryId, { status: 'done' })

        const analysisResult = resultAction.payload
        const saveAction = await dispatch(saveAnalysisResult(analysisResult))
        const newResultId = saveAnalysisResult.fulfilled.match(saveAction) ? saveAction.payload : null

        if (newResultId) {
            setSource({ kind: 'cohort', label: query, query, resultId: newResultId })
        }

        const resultEntryId = newId()
        pushEntry({
            kind: 'analysis-result', id: resultEntryId, runId, query,
            result: { ...analysisResult, result_id: newResultId ?? analysisResult.result_id },
            resultId: newResultId, modelId: null, focusGenes: candidateGenes,
        })

        if (exprText.trim() && newResultId) {
            void scoring.score(exprText, clinical, null, newResultId)
        }

        // Treatment curves need a model_id, not a result_id. Building it is cheap
        // here (the cohorts are already cached) so the button is live by the time
        // anyone looks at the card; the expensive therapy lookup stays on request.
        if (newResultId) {
            try {
                const model = await buildSignature({ result_id: newResultId })
                patchEntry(resultEntryId, { modelId: model.model_id })
                setLastAnalysisModelId(model.model_id)
            } catch {
                // A signature needs at least a couple of usable genes. Without one
                // the card simply keeps its treatment button disabled.
            }
        }
    }

    /** Treatment evidence for a model, with or without a scored patient. Tier-1
     *  treated-vs-untreated arms are gene-independent and need only the model's
     *  training cohort, so this must not require a prediction — requiring one is
     *  what used to make the action a silent no-op in research mode. */
    const showTreatmentEvidenceFor = (mid: string) => {
        pushEntry({
            kind: 'treatment-evidence', id: newId(), modelId: mid,
            riskGroup: scoring.prediction?.risk_group ?? null,
            genes: scoring.signatureGenes,
            baselineCurve: scoring.prediction?.reference_km ?? null,
            expression: scoring.lastExpression,
            clinical: scoring.lastClinical,
            timeUnit: scoring.timeUnit,
        })
    }

    const handlers: ConsoleActionHandlers = {
        set_cancer_type: (key) => {
            const cancer = cancers.find((c) => c.key === key)
            if (cancer) selectCancer(cancer)
        },
        request_tumour_profile: () => pushEntry({ kind: 'intake', id: newId() }),
        load_example_case: (caseId) => {
            const patient = SAMPLE_PATIENTS.find((p) => p.id === caseId)
            if (patient) loadCase(patient)
        },
        score_patient: doScore,
        explain_for_clinician: () => pushEntry({ kind: 'summary', id: newId(), resultId, query: label }),
        show_model_quality: () => {
            if (scoring.resolvedModelId) pushEntry({ kind: 'model-quality', id: newId(), modelId: scoring.resolvedModelId })
        },
        show_treatment_evidence: () => {
            const mid = scoring.resolvedModelId ?? lastAnalysisModelId
            if (mid) showTreatmentEvidenceFor(mid)
        },
        show_treatment_context: () => {
            if (!cancerKey) return
            pushEntry({ kind: 'treatment-context', id: newId(), cancerType: cancerKey, expression: scoring.lastExpression, clinical: scoring.lastClinical })
        },
        show_driver_biology: () => {
            // The model's real signature gene panel — PredictResponse.contributions
            // has no per-gene breakdown to draw from (see estimateGeneDrivers docstring).
            if (scoring.signatureGenes.length > 0) pushEntry({ kind: 'pathway', id: newId(), geneSymbols: scoring.signatureGenes })
        },
        reuse_previous_analysis: (rid) => {
            setSource({ kind: 'cohort', label: label || 'Saved analysis', query: label, resultId: rid })
            if (exprText.trim()) void scoring.score(exprText, clinical, null, rid)
        },
        run_survival_analysis: (query, genes) => { void startCohortBuild(query, genes ?? []) },
    }

    /**
     * Run the current workflow step from the in-thread next-step card.
     *
     * Every branch is a real computation or an intake control — nothing here is
     * satisfied by the assistant producing prose, which is the whole point of
     * routing the workflow through app steps rather than through the model.
     */
    const advanceStep = (step: WorkflowStepId) => {
        switch (step) {
            case 'case':
                focusEntry('case-setup')
                return
            case 'profile':
                focusEntry('intake')
                return
            case 'evidence':
                // Only a 'pending' source has something to build: 'cohort' already
                // carries a resultId (so the step is done), and a curated type with
                // no model yet has nothing to build — advanceDisabledReason says so.
                if (source.kind === 'pending') void startCohortBuild(source.query)
                return
            case 'score':
                doScore()
                return
            case 'why':
                handlers.show_model_quality()
                if (scoring.prediction) handlers.show_driver_biology()
                return
            case 'options':
                handlers.show_treatment_evidence()
                return
        }
    }

    const consoleActions = useConsoleActions({
        handlers,
        hasChart,
        isKnownCaseId: (id) => SAMPLE_PATIENTS.some((p) => p.id === id),
        isKnownCancerKey: (key) => cancers.some((c) => c.key === key),
        analysisRunning: analysisRun.isRunning,
    })

    const dismissNoteFact = (entryId: string, key: string) => {
        setEntries((prev) => prev.map((e) => {
            if (e.kind !== 'doctor-note' || e.id !== entryId) return e
            if (key === 'cancerTerm') return { ...e, extracted: { ...e.extracted, cancerTerm: null, cancerKey: null } }
            const { [key]: _dropped, ...rest } = e.extracted.covariates
            return { ...e, extracted: { ...e.extracted, covariates: rest } }
        }))
        if (key === 'cancerTerm') {
            setSource({ kind: 'none' })
            scoring.reset()
        } else {
            setClinical((c) => {
                const { [key]: _dropped, ...rest } = c
                return rest
            })
        }
    }

    const handleConfirmAction = (entryId: string) => {
        const action = pendingActionsRef.current[entryId]
        if (!action) return
        const result = consoleActions.execute(action)
        updateActionEntry(entryId, result.status, result.detail)
        delete pendingActionsRef.current[entryId]
    }
    const handleDeclineAction = (entryId: string) => {
        updateActionEntry(entryId, 'declined')
        delete pendingActionsRef.current[entryId]
    }

    // ---------- sync scored predictions into the thread as readout cards ----------
    const lastRenderedPrediction = useRef<PredictResponse | null>(null)
    useEffect(() => {
        if (scoring.prediction && scoring.prediction !== lastRenderedPrediction.current && scoring.resolvedModelId) {
            lastRenderedPrediction.current = scoring.prediction
            pushEntry({
                kind: 'readout', id: newId(), prediction: scoring.prediction, modelId: scoring.resolvedModelId,
                cancerLabel: label, modelIsDemo: scoring.modelIsDemo, referenceCurves: scoring.referenceCurves,
                timeUnit: scoring.timeUnit, expression: scoring.lastExpression, clinical: scoring.lastClinical,
            })
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [scoring.prediction])

    const handleClear = () => {
        setSource({ kind: 'none' })
        setExprText('')
        setClinical({})
        setFileError(null)
        scoring.reset()
        pendingActionsRef.current = {}
        setEntries([{ kind: 'start', id: 'start' }])
        setRailOpen(false)
        setGoal(null)
        setLastAnalysisModelId(null)
    }

    // Once a patient is scored the suggested follow-ups are about THIS chart; before
    // that they are the catalogue, so the chips and the start card offer the same
    // set of answerable questions rather than two different vocabularies.
    const chips = scoring.prediction
        ? buildPatientPrompts({
            cancerLabel: label, prediction: scoring.prediction,
            signatureGeneDetails: scoring.signatureGeneDetails, lastExpression: scoring.lastExpression,
        })
        : QUESTION_CATALOGUE.filter((q) => q.placeholders.length === 0).map((q) => q.label)

    // Only the start card so far — the thread bottom-aligns and the composer lifts,
    // so the two meet in the middle instead of leaving a void above a bottom bar.
    const conversationEmpty = entries.length <= 1 && !isStreaming

    const disabledReason = scoreDisabledReason(source, expressionFeedback.geneCount)

    /** Why the current step's button can't run, beyond the workflow's own gating.
     *  The evidence case matters: a curated cancer type whose model is still being
     *  prepared leaves the step unblocked (its prerequisite IS met) with nothing
     *  to build, which used to render an enabled button that did nothing. */
    const advanceDisabledReason =
        workflow.current === 'score' ? disabledReason
        : workflow.current === 'evidence' && source.kind === 'curated'
            ? 'This cancer type\u2019s model is still being prepared \u2014 pick another type, or build a cohort model from your own query.'
            : undefined

    const loadDemoProfile = async () => {
        const demo = await scoring.loadDemoPatient()
        if (!demo) return
        setExprText(demo.exprText)
        setClinical((prev) => ({ ...demo.clinical, ...prev }))
        setFileError(null)
    }

    const contextSummary = source.kind === 'none'
        ? null
        : [
            source.label,
            expressionFeedback.geneCount > 0 ? `${expressionFeedback.geneCount} genes` : null,
            scoring.prediction ? `${scoring.prediction.risk_group} risk` : null,
        ].filter(Boolean).join(' · ')

    /** Superseded step rows and "score this patient" buttons jump to the one live
     *  intake form, which is now in the thread rather than in the rail. */
    const focusChart = () => focusEntry('intake')

    /**
     * A node clicked in the side workflow map: navigate to it, never run it.
     * Running is always an explicit click on the next-step card's button —
     * the evidence step costs 2-5 minutes of GEO downloads, and a map is a
     * place to look, not a place to spend someone's afternoon by accident.
     */
    const goToStep = (step: WorkflowStep) => {
        setRailOpen(false)
        if (step.status === 'active' || step.status === 'running') {
            requestAnimationFrame(() => {
                document.getElementById('next-step')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            })
            return
        }
        const kindsFor: Partial<Record<WorkflowStepId, ConsoleEntry['kind'][]>> = {
            case: ['case-setup'],
            profile: ['intake'],
            evidence: ['analysis-result'],
            score: ['readout'],
            why: ['model-quality', 'pathway'],
            options: ['treatment-evidence', 'treatment-context'],
        }
        const kinds = kindsFor[step.id] ?? []
        const target = [...entries].reverse().find((e) => kinds.includes(e.kind))
        const id = target?.id ?? 'next-step'
        requestAnimationFrame(() => {
            document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        })
    }

    /** Jump to the detailed PatientReadout that the rail summary condenses. */
    const openFullReadout = () => {
        const last = [...entries].reverse().find((e) => e.kind === 'readout')
        if (last) {
            setRailOpen(false)
            document.getElementById(last.id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
    }

    const askFromChart = (question: string) => {
        setRailOpen(false)
        handleSubmitQuestion(question)
    }

    const onClinicalChange = (name: string, value: string) =>
        setClinical((c) => ({ ...c, [name]: value }))

    const rail = (
        <PatientRail
            source={source}
            cancerIcon={cancerIcon}
            geneCount={expressionFeedback.geneCount}
            covariateCount={covariateCount}
            onClear={handleClear}
            onEditInThread={focusChart}
            workflow={workflow}
            goalLabel={goalQuestion?.label ?? null}
            onGoToStep={goToStep}
            onClearGoal={() => setGoal(null)}
            prediction={scoring.prediction}
            modelIsDemo={scoring.modelIsDemo}
            timeUnit={scoring.timeUnit}
            onOpenFullReadout={openFullReadout}
            onAsk={askFromChart}
            onClose={() => setRailOpen(false)}
        />
    )

    return (
        <div className="relative flex h-full bg-canvas">
            {/* Conversation column */}
            <div className="flex flex-col flex-1 min-w-0">
                {/* Below lg the rail is collapsed to this one-line strip. */}
                <div className="lg:hidden">
                    <ChartStrip
                        cancerLabel={label || null}
                        cancerIcon={cancerIcon}
                        genesProvided={expressionFeedback.geneCount}
                        prediction={scoring.prediction}
                        modelIsDemo={scoring.modelIsDemo}
                        workflow={workflow}
                        onClear={handleClear}
                        expanded={railOpen}
                        onToggle={() => setRailOpen((o) => !o)}
                    />
                </div>
                <ConsoleThread
                    entries={entries}
                    onConfirmAction={handleConfirmAction}
                    onDeclineAction={handleDeclineAction}
                    onDismissNoteFact={dismissNoteFact}
                    onFocusChart={focusChart}
                    onShowTreatmentEvidence={showTreatmentEvidenceFor}
                    onAsk={handleSubmitQuestion}
                    progressByRun={analysisRun.progressByRun}
                    isStreaming={isStreaming}
                    streamingContent={streamingContent}
                    empty={conversationEmpty}
                    startProps={{
                        onSubmitCase: handleStartCase,
                        onLoadCase: loadCase,
                        onChooseQuestion: chooseQuestion,
                        selectedGoal: goal,
                    }}
                    caseSetupProps={{
                        cancers,
                        cancersLoading,
                        onSelectCancer: selectCancer,
                        onBuildOther: (query) => void startCohortBuild(query),
                        selectedLabel: source.kind === 'none' ? null : label,
                        covariates: scoring.covariates,
                        clinical,
                        onClinicalChange,
                    }}
                    intakeProps={{
                        exprText,
                        onExprChange: (t) => { setExprText(t); setFileError(null) },
                        feedback: expressionFeedback,
                        covariates: scoring.covariates,
                        clinical,
                        onClinicalChange,
                        onScore: doScore,
                        loading: scoring.loading,
                        disabledReason,
                        fileError,
                        onFileError: setFileError,
                        onLoadDemoProfile: loadDemoProfile,
                        canLoadDemoProfile: !!scoring.resolvedModelId,
                    }}
                    nextStepProps={{
                        workflow,
                        goalLabel: goalQuestion?.label ?? null,
                        onAdvance: advanceStep,
                        advanceDisabledReason,
                        busy: scoring.loading,
                    }}
                />
                <ConsoleComposer
                    ref={composerRef}
                    onSubmitCase={handleSubmitCase}
                    onSubmitQuestion={handleSubmitQuestion}
                    chips={chips}
                    disabled={isStreaming}
                    contextSummary={contextSummary}
                    lifted={conversationEmpty}
                    requireGoal={goal === null}
                />
            </div>

            {/* Chart rail — persistent state, never scrolls away with the log.
                One instance: a column on lg+, a full-height sheet below it. */}
            <div
                className={`${railOpen ? 'block' : 'hidden'} lg:block absolute inset-0 z-20 bg-canvas lg:static lg:z-auto lg:w-rail lg:flex-shrink-0`}
            >
                {rail}
            </div>
        </div>
    )
}

export default ClinicalConsole
