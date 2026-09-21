import React from 'react'
import {
    CANCER_GENE_FILTER_CAVEAT,
    EXPRESSION_LOAD_TEXT,
    ExpressionLoadScope,
} from '../../constants/expressionLoad'

interface ExpressionLoadNoticeProps {
    /** Which canonical string to use when `text` isn't supplied. */
    scope?: ExpressionLoadScope
    /** Visual weight. 'block' = boxed callout, 'inline' = small text,
     *  'footnote' = tiny muted line, 'badge' = pill for sitting beside a button. */
    variant?: 'block' | 'inline' | 'footnote' | 'badge'
    /** Override the canonical copy. Prefer adding a scope over passing this. */
    text?: string
    /** Append the COSMIC caveat. Set it wherever that checkbox is on screen. */
    showFilterCaveat?: boolean
    className?: string
}

/** Decorative — a database cylinder, the one glyph that marks every one of
 *  these notices so the cost reads the same everywhere it appears. */
const DataIcon: React.FC<{ className?: string }> = ({ className = '' }) => (
    <svg
        viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"
        className={`flex-shrink-0 ${className}`}
    >
        <ellipse cx="8" cy="3.6" rx="5.1" ry="2.2" />
        <path d="M2.9 3.6v8.8c0 1.21 2.28 2.2 5.1 2.2s5.1-.99 5.1-2.2V3.6" />
        <path d="M2.9 8c0 1.21 2.28 2.2 5.1 2.2S13.1 9.21 13.1 8" />
    </svg>
)

/**
 * Single source of truth for "this action loads gene expression data" warnings.
 *
 * Use it on any control whose click triggers a GEO expression-matrix load —
 * running an analysis, building a signature, scoring against a saved analysis,
 * or building a treatment model. Do NOT use it for actions that read only
 * clinical metadata (treatment-arm curves) or score against an already-built
 * model: those are effectively instant, and warning about them trains people to
 * ignore the notice where it matters.
 *
 * Deliberately in the accent hue, not the amber used by <RuoNotice>. The two
 * appear on the same screens and say unrelated things — one is a cost estimate,
 * the other a research-use disclaimer — so they must not read as one band.
 */
const ExpressionLoadNotice: React.FC<ExpressionLoadNoticeProps> = ({
    scope = 'analysis', variant = 'block', text, showFilterCaveat = false, className = '',
}) => {
    const content = text ?? EXPRESSION_LOAD_TEXT[scope]

    if (variant === 'badge') {
        return (
            <span
                title={showFilterCaveat ? `${content} ${CANCER_GENE_FILTER_CAVEAT}` : content}
                className={`inline-flex items-center gap-1 rounded-full border border-border-accent bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent-fg ${className}`}
            >
                <DataIcon className="w-3 h-3" />
                Loads expression data
            </span>
        )
    }

    if (variant === 'footnote') {
        return (
            <p className={`flex items-start gap-1.5 text-[11px] text-fg-faint ${className}`}>
                {/* Always the accent hue, even where the text is muted — the glyph
                    is what makes these notices recognisable as one family. */}
                <DataIcon className="w-3 h-3 mt-[1px] text-accent-fg" />
                <span>
                    {content}
                    {showFilterCaveat && <> {CANCER_GENE_FILTER_CAVEAT}</>}
                </span>
            </p>
        )
    }

    if (variant === 'inline') {
        return (
            <p className={`flex items-start gap-1.5 text-xs text-fg-muted ${className}`}>
                <DataIcon className="w-3.5 h-3.5 mt-[2px] text-accent-fg" />
                <span>
                    {content}
                    {showFilterCaveat && <> {CANCER_GENE_FILTER_CAVEAT}</>}
                </span>
            </p>
        )
    }

    return (
        <div
            className={`flex items-start gap-2 rounded-control border border-border-accent bg-accent-soft p-2 text-xs text-accent-fg ${className}`}
        >
            <DataIcon className="w-3.5 h-3.5 mt-[2px]" />
            <span>
                {content}
                {showFilterCaveat && (
                    <span className="block mt-1 opacity-80">{CANCER_GENE_FILTER_CAVEAT}</span>
                )}
            </span>
        </div>
    )
}

export default ExpressionLoadNotice
