import { useEffect, useState } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { AnalysisProgress } from '../store/chatSlice'

export interface UseAnalysisRunResult {
    /** True while a cross-cohort analysis is in flight. */
    isRunning: boolean
    runningRunId: string | null
    /** Progress keyed by run id, so a finished run keeps its last frame instead
     *  of being blanked by the next run starting. */
    progressByRun: Record<string, AnalysisProgress | null>
    begin: (runId: string) => void
    end: (runId: string) => void
}

/**
 * Per-run view over the single global `chat.analysisProgress` field.
 *
 * Redux stays the transport — the SSE thunk keeps writing one field — but the
 * thread can hold several analysis entries, and they must not all animate off
 * whichever run happens to be live. `runAnalysis.pending` also nulls that field,
 * so without this a second run would blank the first entry's bar.
 */
export function useAnalysisRun(): UseAnalysisRunResult {
    const progress = useSelector((s: RootState) => s.chat.analysisProgress)
    const [runningRunId, setRunningRunId] = useState<string | null>(null)
    const [progressByRun, setProgressByRun] = useState<Record<string, AnalysisProgress | null>>({})

    useEffect(() => {
        if (!runningRunId || !progress) return
        setProgressByRun((prev) => ({ ...prev, [runningRunId]: progress }))
    }, [progress, runningRunId])

    return {
        isRunning: runningRunId !== null,
        runningRunId,
        progressByRun,
        begin: (runId) => {
            setProgressByRun((prev) => ({ ...prev, [runId]: null }))
            setRunningRunId(runId)
        },
        // Guarded so a late-finishing run can't clear a newer one's slot.
        end: (runId) => setRunningRunId((cur) => (cur === runId ? null : cur)),
    }
}
