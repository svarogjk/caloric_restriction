import React from 'react'
import { AnalysisProgress as AnalysisProgressType } from '../../store/chatSlice'

interface AnalysisProgressProps {
    progress: AnalysisProgressType | null
}

const STAGES = [
    { key: 'searching_geo', label: 'Searching GEO' },
    { key: 'ranking_datasets', label: 'Ranking datasets' },
    { key: 'loading_dataset', label: 'Loading datasets' },
    { key: 'analyzing_genes', label: 'Running survival analysis' },
    { key: 'complete', label: 'Complete' },
]

function getStageIndex(stage: string): number {
    const idx = STAGES.findIndex((s) => s.key === stage)
    return idx === -1 ? 0 : idx
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ progress }) => {
    if (!progress) return null

    const currentIndex = getStageIndex(progress.stage)
    const isComplete = progress.stage === 'complete'

    const showProgressBar =
        progress.stage === 'loading_dataset' &&
        progress.total != null &&
        progress.total > 0

    const pct =
        showProgressBar && progress.total
            ? Math.round(((progress.current ?? 0) / progress.total) * 100)
            : 0

    return (
        <div className="mx-4 mt-2 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
            <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-3">
                Analysis Progress
            </p>

            <ol className="space-y-2">
                {STAGES.map((s, idx) => {
                    const done = idx < currentIndex || isComplete
                    const active = idx === currentIndex && !isComplete
                    return (
                        <li key={s.key} className="flex items-center gap-3">
                            {/* Step indicator */}
                            <span
                                className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                    done
                                        ? 'bg-green-500 text-white'
                                        : active
                                        ? 'bg-indigo-600 text-white animate-pulse'
                                        : 'bg-gray-200 text-gray-400'
                                }`}
                            >
                                {done ? (
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                ) : (
                                    idx + 1
                                )}
                            </span>

                            {/* Label */}
                            <span
                                className={`text-sm ${
                                    done
                                        ? 'text-green-700 line-through'
                                        : active
                                        ? 'text-indigo-800 font-medium'
                                        : 'text-gray-400'
                                }`}
                            >
                                {s.label}
                            </span>
                        </li>
                    )
                })}
            </ol>

            {/* Current message */}
            <p className="mt-3 text-sm text-indigo-700">{progress.message}</p>

            {/* Progress bar for dataset loading */}
            {showProgressBar && (
                <div className="mt-2">
                    <div className="flex justify-between text-xs text-indigo-600 mb-1">
                        <span>{progress.current ?? 0} / {progress.total} datasets loaded</span>
                        <span>{pct}%</span>
                    </div>
                    <div className="w-full bg-indigo-100 rounded-full h-2">
                        <div
                            className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${pct}%` }}
                        />
                    </div>
                </div>
            )}
        </div>
    )
}

export default AnalysisProgress
