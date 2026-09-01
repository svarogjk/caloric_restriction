import React from 'react'
import { RUO_TEXT, RuoScope } from '../../constants/ruo'

interface RuoNoticeProps {
    /** Visual weight. 'block' = boxed callout, 'inline' = plain small text, 'footnote' = tiny muted line. */
    variant?: 'block' | 'inline' | 'footnote'
    /** Which canonical string to fall back to when `text` isn't supplied. */
    scope?: RuoScope
    /** Prefer the server's own disclaimer text (e.g. PredictResponse.disclaimer) over the client fallback. */
    text?: string
    className?: string
}

/**
 * Single source of truth for research-use-only / advisory disclaimers, replacing
 * ~14 hand-copied strings across the app. Always prefer passing a server-authored
 * `text` (PredictResponse.disclaimer, TherapyRationaleResponse.disclaimer, etc.)
 * so the UI never drifts from what the backend actually promises.
 */
const RuoNotice: React.FC<RuoNoticeProps> = ({ variant = 'block', scope = 'general', text, className = '' }) => {
    const content = text ?? RUO_TEXT[scope]

    if (variant === 'footnote') {
        return <p className={`text-[11px] text-fg-faint ${className}`}>{content}</p>
    }

    if (variant === 'inline') {
        return <p className={`text-xs text-fg-muted ${className}`}>{content}</p>
    }

    return (
        <div className={`text-xs text-ruo bg-ruo-bg border border-ruo-border rounded-control p-2 ${className}`}>
            {content}
        </div>
    )
}

export default RuoNotice
