import React, { useState } from 'react'
import Markdown from '../markdown/Markdown'
import { extractGseIds, gseUrl } from '../markdown/gseLinks'

interface AssistantEntryProps {
    text: string
    domainScore?: number
    modelUsed?: string
    timestamp?: string
    streaming?: boolean
}

/** The rubric is computed server-side in PydanticAIService._compute_domain_score;
 *  spelling it out here is what makes the number auditable rather than decorative. */
const DS_RUBRIC = [
    'How grounded this answer is in real GEO data:',
    '• each tool called +20 (max 40)',
    '• each GSE accession cited +15 (max 30)',
    '• hazard ratio / p-value / sample count +15',
    '• your organism or candidate gene +15',
].join('\n')

const dsTone = (score: number) =>
    score >= 70 ? 'bg-ok-soft text-ok' : score >= 40 ? 'bg-warn-soft text-warn' : 'bg-surface-sunken text-fg-faint'

const CopyButton: React.FC<{ text: string }> = ({ text }) => {
    const [copied, setCopied] = useState(false)
    const copy = async () => {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
        } catch {
            // Clipboard access can be denied (permissions, insecure origin) — a
            // failed copy should never take down the turn.
            setCopied(false)
        }
    }
    return (
        <button
            type="button"
            onClick={copy}
            aria-label="Copy this answer"
            className="text-[11px] text-fg-faint hover:text-accent-fg transition-colors"
        >
            {copied ? '✓ copied' : '⧉ copy'}
        </button>
    )
}

/**
 * One assistant turn. Deliberately NOT a bubble: grounded answers carry tables
 * and multi-paragraph reasoning that read badly in an 85%-width speech bubble,
 * so the doctor's messages are bubbles and the assistant gets the full column.
 *
 * The footer is the grounding strip — domain score plus the accessions actually
 * cited — so "is this answer backed by data?" is answerable at a glance.
 */
const AssistantEntry: React.FC<AssistantEntryProps> = ({ text, domainScore, modelUsed, timestamp, streaming }) => {
    const gseIds = streaming ? [] : extractGseIds(text)
    const hasFooter = !streaming && (domainScore != null || gseIds.length > 0)

    return (
        <div className="rounded-card border border-border bg-surface px-3.5 py-3" aria-live={streaming ? 'polite' : undefined}>
            <div className="flex items-center gap-2 mb-1.5">
                <span
                    className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-soft text-accent-fg text-[11px] flex items-center justify-center"
                    aria-hidden
                >
                    ✦
                </span>
                <span className="text-[11px] font-medium text-fg-muted">Assistant</span>
                {modelUsed && <span className="text-[11px] text-fg-faint">· {modelUsed}</span>}
                {timestamp && <span className="text-[11px] text-fg-faint">· {timestamp}</span>}
                <span className="flex-1" />
                {!streaming && text && <CopyButton text={text} />}
            </div>

            {/* While streaming, render plain text: a half-written markdown table
                re-parses into broken rows on every token. Swap to the real
                renderer once the turn is complete. */}
            {streaming ? (
                <div className="text-sm text-fg whitespace-pre-wrap">
                    {text || <span className="text-fg-faint">Thinking…</span>}
                    <span
                        className="inline-block w-[2px] h-[1em] ml-0.5 align-text-bottom bg-accent-fg animate-pulse"
                        aria-hidden
                    />
                </div>
            ) : (
                <Markdown>{text}</Markdown>
            )}

            {hasFooter && (
                <div className="flex items-center flex-wrap gap-1.5 mt-2.5 pt-2 border-t border-border">
                    {domainScore != null && (
                        <span
                            title={DS_RUBRIC}
                            className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${dsTone(domainScore)}`}
                        >
                            DS {domainScore}
                        </span>
                    )}
                    {gseIds.map((id) => (
                        <a
                            key={id}
                            href={gseUrl(id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-surface-sunken text-fg-muted border border-border hover:text-accent-fg hover:border-border-accent transition-colors"
                        >
                            {id}
                        </a>
                    ))}
                </div>
            )}
        </div>
    )
}

export default AssistantEntry
