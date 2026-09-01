import React, { useState } from 'react'
import { ExtractedCaseFacts } from '../../../utils/caseParser'
import { Chip } from '../../ui'

interface DoctorNoteEntryProps {
    text: string
    extracted: ExtractedCaseFacts
    /** The de-identified, synthesized turn actually sent to the agent (or null
     *  when nothing was sent because the whole message was read into the chart). */
    sentTurn: string | null
    timestamp?: string
    /** Drop a fact the parser got wrong, without retyping the case. */
    onDismissFact?: (key: string) => void
}

/**
 * A free-text case description the doctor typed, read into the chart LOCALLY.
 * The raw sentence is never sent to the LLM or persisted — only the extracted
 * facts (as chips) and, separately, any residual question. The disclosure below
 * shows the exact text that left the browser, so the claim is checkable rather
 * than merely asserted.
 */
const DoctorNoteEntry: React.FC<DoctorNoteEntryProps> = ({ text, extracted, sentTurn, timestamp, onDismissFact }) => {
    const [showSent, setShowSent] = useState(false)
    const chips: { key: string; label: string }[] = []
    if (extracted.cancerTerm) chips.push({ key: 'cancerTerm', label: extracted.cancerTerm })
    for (const [name, value] of Object.entries(extracted.covariates)) {
        chips.push({ key: name, label: `${name} ${value}` })
    }

    return (
        <div className="flex flex-col items-end gap-1">
            <div className="max-w-[85%] space-y-1.5">
                <div className="bg-accent text-on-accent rounded-card rounded-br-sm px-3 py-2 text-sm whitespace-pre-wrap">
                    {text}
                </div>
                <div className="bg-surface-sunken border border-border rounded-control px-2 py-1.5">
                    <div className="flex items-center gap-1.5">
                        <span aria-hidden>🔒</span>
                        <span className="text-[10px] font-medium text-fg-muted uppercase tracking-wide">
                            read into chart · not saved
                        </span>
                    </div>
                    {chips.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                            {chips.map((c) => (
                                <Chip
                                    key={c.key}
                                    tone="confirmed"
                                    onDismiss={onDismissFact ? () => onDismissFact(c.key) : undefined}
                                >
                                    {c.label} ✓
                                </Chip>
                            ))}
                        </div>
                    )}
                    <button
                        type="button"
                        onClick={() => setShowSent((s) => !s)}
                        className="text-[10px] text-fg-faint hover:text-accent-fg hover:underline mt-1"
                    >
                        {showSent ? '▾' : '▸'} what was sent
                    </button>
                    {showSent && (
                        <p className="text-[11px] text-fg-muted mt-1 italic">
                            {sentTurn ?? 'Nothing — the whole message was read into the chart locally.'}
                        </p>
                    )}
                </div>
            </div>
            {timestamp && <span className="text-[10px] text-fg-faint pr-1">{timestamp}</span>}
        </div>
    )
}

export default DoctorNoteEntry
