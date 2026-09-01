import React from 'react'
import AnalysisProgress from '../../chat/AnalysisProgress'
import { AnalysisProgress as AnalysisProgressType } from '../../../store/chatSlice'

interface AnalysisProgressEntryProps {
    query: string
    progress: AnalysisProgressType | null
    status: 'running' | 'done' | 'failed'
    error?: string
}

/** A cross-cohort analysis run, in the conversation log. Terminal states are
 *  part of the entry: a finished run must stop animating, and a failed one has
 *  to leave a visible trace rather than a bar that never completes. */
const AnalysisProgressEntry: React.FC<AnalysisProgressEntryProps> = ({ query, progress, status, error }) => {
    if (status === 'done') {
        return (
            <div className="flex items-center gap-2 text-[11px] pl-1 text-fg-faint">
                <span className="text-ok" aria-hidden>✓</span>
                <span>analysis complete — "{query}"</span>
            </div>
        )
    }

    if (status === 'failed') {
        return (
            <div className="bg-surface border border-danger-border rounded-card p-3">
                <p className="text-xs text-danger">
                    Analysis failed for "{query}"{error ? ` — ${error}` : ''}.
                </p>
                <p className="text-[11px] text-fg-faint mt-1">
                    Try a broader query, fewer restrictions, or a lower minimum-cohort threshold in the chart settings.
                </p>
            </div>
        )
    }

    return (
        <div className="bg-surface border border-border rounded-card p-3">
            <p className="text-xs text-fg-muted mb-2">
                Analysing "{query}" — searching GEO, running Cox regression across independent cohorts.
                Usually 2–5 minutes. You can keep asking questions while this runs.
            </p>
            <AnalysisProgress progress={progress} />
        </div>
    )
}

export default AnalysisProgressEntry
