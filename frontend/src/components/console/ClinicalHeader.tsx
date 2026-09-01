import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import { setSelectedModel } from '../../store/chatSlice'
import { UserMenu } from '../auth'

interface ClinicalHeaderProps {
    isAuthenticated: boolean
    onOpenAuthModal: () => void
}

/**
 * Replaces the research-chat nav for the clinical console. Deliberately
 * minimal: the settings a doctor never needs (HR sliders, dataset count,
 * ranking multiplier) also live in the chart rail now; /research keeps the
 * full 7-tab results view and remains reachable from here.
 */
const ClinicalHeader: React.FC<ClinicalHeaderProps> = ({ isAuthenticated, onOpenAuthModal }) => {
    const dispatch = useDispatch<AppDispatch>()
    const selectedModel = useSelector((s: RootState) => s.chat.selectedModel)
    const [advancedOpen, setAdvancedOpen] = useState(false)

    return (
        <nav className="bg-surface shadow-sm border-b border-border h-12 flex-shrink-0">
            <div className="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                    <Link to="/" className="flex items-center gap-1.5 font-semibold text-fg-strong hover:text-accent-fg transition-colors">
                        🩺 Oncology Decision Support
                    </Link>
                    <span className="hidden sm:inline text-[10px] font-medium text-ruo bg-ruo-bg border border-ruo-border rounded-full px-2 py-0.5">
                        RESEARCH USE ONLY
                    </span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                    <Link to="/research" className="text-fg-muted hover:text-accent-fg transition-colors">Research mode</Link>
                    <Link to="/help" className="text-fg-muted hover:text-accent-fg transition-colors">Help</Link>
                    {isAuthenticated && (
                        <>
                            <Link to="/history" className="text-fg-muted hover:text-accent-fg transition-colors">History</Link>
                            <Link to="/compare" className="text-fg-muted hover:text-accent-fg transition-colors">Compare</Link>
                        </>
                    )}
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => setAdvancedOpen((o) => !o)}
                            className="text-fg-muted hover:text-accent-fg transition-colors"
                        >
                            ⚙ Advanced
                        </button>
                        {advancedOpen && (
                            <div className="absolute right-0 mt-2 w-56 bg-surface border border-border rounded-card shadow-[var(--shadow-card)] p-3 z-20">
                                <label className="block text-[11px] font-medium text-fg-muted mb-1">Assistant model</label>
                                <select
                                    value={selectedModel}
                                    onChange={(e) => dispatch(setSelectedModel(e.target.value as 'mistral' | 'mistral-large' | 'anthropic'))}
                                    className="w-full text-sm border border-border-strong rounded-control px-2 py-1 mb-2"
                                >
                                    <option value="mistral-large">mistral-large-latest</option>
                                    <option value="mistral">mistral-small-latest</option>
                                    <option value="anthropic">claude-haiku-4-5-20251001</option>
                                </select>
                                <Link to="/research" className="text-xs text-accent-fg hover:underline">
                                    Open Research mode →
                                </Link>
                            </div>
                        )}
                    </div>
                    {isAuthenticated ? (
                        <UserMenu />
                    ) : (
                        <button
                            onClick={onOpenAuthModal}
                            className="px-3 py-1.5 text-sm font-medium text-accent-fg border border-border-accent rounded-control hover:bg-accent-soft transition-colors"
                        >
                            Sign in
                        </button>
                    )}
                </div>
            </div>
        </nav>
    )
}

export default ClinicalHeader
