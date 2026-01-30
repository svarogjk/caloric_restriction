import React, { useState } from 'react'
import { QueryEstimation as QueryEstimationType } from '../../store/chatSlice'

interface QueryEstimationProps {
    estimation: QueryEstimationType
    onRunAnalysis: (query: string) => void
    onDismiss: () => void
}

const QueryEstimation: React.FC<QueryEstimationProps> = ({
    estimation,
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
                return { text: 'Low diversity', class: 'bg-green-100 text-green-700' }
            case 'medium':
                return { text: 'Medium diversity', class: 'bg-yellow-100 text-yellow-700' }
            case 'high':
                return { text: 'High diversity', class: 'bg-red-100 text-red-700' }
            default:
                return { text: diversity, class: 'bg-gray-100 text-gray-700' }
        }
    }

    const color = getConfidenceColor(estimation.confidenceScore)

    const colorClasses = {
        green: {
            bg: 'bg-green-50',
            border: 'border-green-500',
            text: 'text-green-700',
            badge: 'bg-green-100 text-green-800',
        },
        yellow: {
            bg: 'bg-yellow-50',
            border: 'border-yellow-500',
            text: 'text-yellow-700',
            badge: 'bg-yellow-100 text-yellow-800',
        },
        red: {
            bg: 'bg-red-50',
            border: 'border-red-500',
            text: 'text-red-700',
            badge: 'bg-red-100 text-red-800',
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
                            <div className="flex flex-wrap gap-3 text-sm text-gray-600 mb-2">
                                <span className="font-medium">
                                    {geoPreview.totalDatasets.toLocaleString()} datasets found
                                </span>
                                <span className="text-gray-400">|</span>
                                <span>
                                    {geoPreview.datasetsWithSurvivalKeywords} with survival data
                                </span>
                                <span className="text-gray-400">|</span>
                                <span>
                                    ~{Math.ceil(estimation.estimatedTimeSeconds / 60)} min
                                </span>
                            </div>

                            {/* Platform breakdown */}
                            {topPlatforms.length > 0 && (
                                <div className="flex items-center gap-2 text-sm mb-2">
                                    <span className="text-gray-500">Platforms:</span>
                                    <div className="flex flex-wrap gap-1">
                                        {topPlatforms.map(([platform, count]) => (
                                            <span
                                                key={platform}
                                                className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs"
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
                                        <div key={i} className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 p-2 rounded mb-1">
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
                                        className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
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
                                                    className="bg-white p-2 rounded border border-gray-200 text-sm"
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-mono text-blue-600">{ds.accession}</span>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-gray-500 text-xs">
                                                                n={ds.sampleCount}
                                                            </span>
                                                            {ds.hasSurvivalKeywords && (
                                                                <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                                                                    survival
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <p className="text-gray-700 text-xs line-clamp-2">
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
                        <div className="flex gap-4 text-sm text-gray-600 mb-3">
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
                            <p className="text-sm font-medium text-gray-700 mb-1">
                                Suggestions to improve results:
                            </p>
                            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                                {estimation.suggestions.slice(0, 3).map((suggestion, i) => (
                                    <li key={i}>{suggestion}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Improved Query */}
                    {estimation.improvedQuery && (
                        <div className="bg-white p-3 rounded border border-gray-200">
                            <p className="text-sm font-medium text-gray-700 mb-1">
                                Suggested query:
                            </p>
                            <p className="text-sm text-blue-600 italic">
                                "{estimation.improvedQuery}"
                            </p>
                            <button
                                onClick={() => onRunAnalysis(estimation.improvedQuery!)}
                                className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
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
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>

                    {estimation.canProceed && (
                        <button
                            onClick={() => onRunAnalysis(estimation.improvedQuery || '')}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
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
