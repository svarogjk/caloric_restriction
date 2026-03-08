import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { RootState, AppDispatch } from '../store/store'
import { fetchAnalysisHistory } from '../store/chatSlice'

const AnalysisHistoryPage: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>()
    const navigate = useNavigate()
    const { analysisHistory, historyLoading } = useSelector((state: RootState) => state.chat)
    const [searchQuery, setSearchQuery] = useState('')
    const [copiedId, setCopiedId] = useState<string | null>(null)

    useEffect(() => {
        dispatch(fetchAnalysisHistory())
    }, [dispatch])

    const filteredHistory = analysisHistory.filter((item) => {
        if (!searchQuery.trim()) return true
        return item.query.toLowerCase().includes(searchQuery.toLowerCase())
    })

    const formatDate = (isoString: string): string => {
        return new Date(isoString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        })
    }

    const handleCopyLink = async (resultId: string) => {
        const url = `${window.location.origin}/results/${resultId}`
        try {
            await navigator.clipboard.writeText(url)
            setCopiedId(resultId)
            setTimeout(() => setCopiedId(null), 2500)
        } catch (err) {
            console.error('Clipboard write failed:', err)
        }
    }

    const handleView = async (resultId: string) => {
        await handleCopyLink(resultId)
        navigate(`/results/${resultId}`)
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Nav */}
            <nav className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-4xl mx-auto px-4">
                    <div className="flex items-center justify-between h-14">
                        <Link to="/" className="text-xl font-semibold text-gray-800 hover:text-indigo-600 transition-colors">
                            GEO Survival Analysis
                        </Link>
                        <div className="flex items-center gap-4">
                            <Link
                                to="/history"
                                className="text-sm font-medium text-indigo-600 border-b-2 border-indigo-600 pb-0.5"
                            >
                                History
                            </Link>
                            <Link
                                to="/"
                                className="text-sm font-medium text-gray-500 hover:text-gray-700"
                            >
                                Chat
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Content */}
            <main className="max-w-4xl mx-auto px-4 py-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-800">Analysis History</h2>
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        New Analysis
                    </Link>
                </div>

                {/* Search */}
                <div className="mb-4">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Filter by query..."
                        className="w-full px-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                    />
                </div>

                {/* Loading */}
                {historyLoading && (
                    <div className="flex items-center justify-center py-16">
                        <svg className="animate-spin h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                    </div>
                )}

                {/* Empty state */}
                {!historyLoading && filteredHistory.length === 0 && (
                    <div className="text-center py-16">
                        {searchQuery.trim() ? (
                            <p className="text-gray-500">No analyses match your search.</p>
                        ) : (
                            <div>
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-100 flex items-center justify-center">
                                    <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                    </svg>
                                </div>
                                <p className="text-gray-600 font-medium mb-2">No analyses yet</p>
                                <p className="text-gray-400 text-sm mb-4">Run your first analysis in the chat.</p>
                                <Link
                                    to="/"
                                    className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
                                >
                                    Start Analyzing
                                </Link>
                            </div>
                        )}
                    </div>
                )}

                {/* List */}
                {!historyLoading && filteredHistory.length > 0 && (
                    <div className="space-y-3">
                        {filteredHistory.map((item) => (
                            <div
                                key={item.result_id}
                                className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 hover:shadow-md transition-shadow"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <p className="font-semibold text-gray-800 truncate" title={item.query}>
                                            {item.query}
                                        </p>
                                        <p className="text-xs text-gray-400 mt-0.5">{formatDate(item.created_at)}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                                                {item.n_datasets_analyzed} datasets
                                            </span>
                                            <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                                                {item.n_genes_found} genes
                                            </span>
                                            {item.processing_time_seconds !== null && (
                                                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                                                    {item.processing_time_seconds.toFixed(1)}s
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        <button
                                            onClick={() => handleCopyLink(item.result_id)}
                                            className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                                                copiedId === item.result_id
                                                    ? 'bg-green-100 text-green-700 border-green-300'
                                                    : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                                            }`}
                                        >
                                            {copiedId === item.result_id ? '✓ Copied' : 'Copy Link'}
                                        </button>
                                        <button
                                            onClick={() => handleView(item.result_id)}
                                            className="text-xs px-3 py-1.5 rounded border bg-indigo-600 text-white border-indigo-600 hover:bg-indigo-700 transition-colors"
                                        >
                                            View
                                        </button>
                                        <Link
                                            to="/"
                                            className="text-xs px-3 py-1.5 rounded border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
                                        >
                                            Re-run
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    )
}

export default AnalysisHistoryPage
