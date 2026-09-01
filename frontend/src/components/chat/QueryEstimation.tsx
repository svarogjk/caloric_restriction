import React, { useState } from 'react'
import { QueryEstimation as QueryEstimationType } from '../../store/chatSlice'

interface QueryEstimationProps {
    estimation: QueryEstimationType
    originalQuery: string
    onRunAnalysis: (query: string) => void
    onDismiss: () => void
}

const QueryEstimation: React.FC<QueryEstimationProps> = ({
    estimation,
    originalQuery,
    onRunAnalysis,
    onDismiss,
}) => {
    const [showDatasets, setShowDatasets] = useState(false)
    const geoPreview = estimation.geoPreview

    const getConfidenceColor = (score: number) => {
        if (score >= 0.7) return 'green'
        if (score >= 0.4) return 'yellow'
        return 'red'
    }

    const getDiversityBadge = (diversity: string) => {
        switch (diversity) {
            case 'low':
                return { text: 'Low diversity', class: 'bg-ok-soft text-ok' }
            case 'medium':
                return { text: 'Medium diversity', class: 'bg-warn-soft text-warn' }
            case 'high':
                return { text: 'High diversity', class: 'bg-danger-soft text-danger' }
            default:
                return { text: diversity, class: 'bg-surface-sunken text-fg' }
        }
    }

    const color = getConfidenceColor(estimation.confidenceScore)

    const colorClasses = {
        green: {
            bg: 'bg-ok-soft',
            border: 'border-ok',
            text: 'text-ok',
            badge: 'bg-ok-soft text-ok',
        },
        yellow: {
            bg: 'bg-warn-soft',
            border: 'border-warn',
            text: 'text-warn',
            badge: 'bg-warn-soft text-warn',
        },
        red: {
            bg: 'bg-danger-soft',
            border: 'border-danger',
            text: 'text-danger',
            badge: 'bg-danger-soft text-danger',
        },
    }

    const classes = colorClasses[color]

    // Get top 3 platforms by count
    const topPlatforms = geoPreview?.platformCounts
        ? Object.entries(geoPreview.platformCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
        : []

    return (
        <div className={`${classes.bg} border-l-4 ${classes.border} p-4 mx-4 my-2 rounded-r-lg`}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    {/* Header with confidence score */}
                    <div className="flex items-center gap-3 mb-2">
                        <h4 className={`font-semibold ${classes.text}`}>
                            Query Analysis
                        </h4>
                        <span className={`px-2 py-0.5 text-sm rounded-full ${classes.badge}`}>
                            {(estimation.confidenceScore * 100).toFixed(0)}% Confidence
                        </span>
                    </div>

                    {/* GEO Preview Stats */}
                    {geoPreview ? (
                        <div className="mb-3">
                            {/* Main stats row */}
                            <div className="flex flex-wrap gap-3 text-sm text-fg-muted mb-2">
                                <span className="font-medium">
                                    {geoPreview.totalDatasets.toLocaleString()} datasets found
                                </span>
                                <span className="text-fg-faint">|</span>
                                <span>
                                    {geoPreview.datasetsWithSurvivalKeywords} with survival data
                                </span>
                                <span className="text-fg-faint">|</span>
                                <span>
                                    ~{Math.ceil(estimation.estimatedTimeSeconds / 60)} min
                                </span>
                            </div>

                            {/* Platform breakdown */}
                            {topPlatforms.length > 0 && (
                                <div className="flex items-center gap-2 text-sm mb-2">
                                    <span className="text-fg-muted">Platforms:</span>
                                    <div className="flex flex-wrap gap-1">
                                        {topPlatforms.map(([platform, count]) => (
                                            <span
                                                key={platform}
                                                className="px-2 py-0.5 bg-surface-sunken text-fg rounded text-xs"
                                            >
                                                {platform}: {count}
                                            </span>
                                        ))}
                                    </div>
                                    {geoPreview.platformDiversity && (
                                        <span className={`px-2 py-0.5 rounded text-xs ${getDiversityBadge(geoPreview.platformDiversity).class}`}>
                                            {getDiversityBadge(geoPreview.platformDiversity).text}
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Warnings */}
                            {geoPreview.warnings.length > 0 && (
                                <div className="mb-2">
                                    {geoPreview.warnings.slice(0, 2).map((warning, i) => (
                                        <div key={i} className="flex items-start gap-2 text-sm text-warn bg-warn-soft p-2 rounded mb-1">
                                            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                            </svg>
                                            <span>{warning}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Top Datasets Preview (collapsible) */}
                            {geoPreview.topDatasets.length > 0 && (
                                <div className="mt-2">
                                    <button
                                        onClick={() => setShowDatasets(!showDatasets)}
                                        className="flex items-center gap-1 text-sm text-accent-fg hover:text-accent-fg"
                                    >
                                        <svg
                                            className={`w-4 h-4 transition-transform ${showDatasets ? 'rotate-90' : ''}`}
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                        Show top {Math.min(geoPreview.topDatasets.length, 5)} datasets
                                    </button>

                                    {showDatasets && (
                                        <div className="mt-2 space-y-2">
                                            {geoPreview.topDatasets.slice(0, 5).map((ds) => (
                                                <div
                                                    key={ds.accession}
                                                    className="bg-surface p-2 rounded border border-border text-sm"
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-mono text-accent-fg">{ds.accession}</span>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-fg-muted text-xs">
                                                                n={ds.sampleCount}
                                                            </span>
                                                            {ds.hasSurvivalKeywords && (
                                                                <span className="px-1.5 py-0.5 bg-ok-soft text-ok rounded text-xs">
                                                                    survival
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <p className="text-fg text-xs line-clamp-2">
                                                        {ds.title}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Fallback: Original stats display when no GEO preview */
                        <div className="flex gap-4 text-sm text-fg-muted mb-3">
                            <span>
                                Est. {estimation.estimatedDatasets} datasets
                            </span>
                            <span>|</span>
                            <span>
                                ~{Math.ceil(estimation.estimatedTimeSeconds / 60)} min
                            </span>
                        </div>
                    )}

                    {/* Suggestions */}
                    {estimation.suggestions.length > 0 && (
                        <div className="mb-3">
                            <p className="text-sm font-medium text-fg mb-1">
                                Suggestions to improve results:
                            </p>
                            <ul className="text-sm text-fg-muted list-disc list-inside space-y-1">
                                {estimation.suggestions.slice(0, 3).map((suggestion, i) => (
                                    <li key={i}>{suggestion}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Improved Query */}
                    {estimation.improvedQuery && (
                        <div className="bg-surface p-3 rounded border border-border">
                            <p className="text-sm font-medium text-fg mb-1">
                                Suggested query:
                            </p>
                            <p className="text-sm text-accent-fg italic">
                                "{estimation.improvedQuery}"
                            </p>
                            <button
                                onClick={() => onRunAnalysis(estimation.improvedQuery!)}
                                className="mt-2 text-sm text-accent-fg hover:text-accent-fg font-medium"
                            >
                                Use this query
                            </button>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 ml-4">
                    <button
                        onClick={onDismiss}
                        className="text-fg-faint hover:text-fg-muted"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>

                    {estimation.canProceed && (
                        <button
                            onClick={() => onRunAnalysis(estimation.improvedQuery || originalQuery)}
                            className="px-4 py-2 bg-accent text-on-accent text-sm rounded-lg hover:bg-accent-hover transition-colors"
                        >
                            Run Analysis
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default QueryEstimation
