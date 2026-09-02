import React from 'react'

interface PromptChipsProps {
    prompts: string[]
    onSelect: (prompt: string) => void
}

/** Chart-aware follow-up questions (see utils/patientPrompts.ts). They shift
 *  from generic orientation prompts to questions naming this patient's own
 *  drivers and risk group once a score exists. */
const PromptChips: React.FC<PromptChipsProps> = ({ prompts, onSelect }) => {
    if (prompts.length === 0) return null
    return (
        <div className="flex items-center gap-1.5 min-w-0 overflow-x-auto">
            <span className="flex-shrink-0 text-[10px] uppercase tracking-wide text-fg-faint">Suggested</span>
            {prompts.map((p) => (
                <button
                    key={p}
                    type="button"
                    onClick={() => onSelect(p)}
                    className="flex-shrink-0 px-2.5 py-1 bg-surface-sunken text-fg-muted border border-border text-[11px] rounded-full hover:bg-accent-soft hover:text-accent-fg hover:border-border-accent transition-colors"
                >
                    {p}
                </button>
            ))}
        </div>
    )
}

export default PromptChips
