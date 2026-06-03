import React, { useState } from 'react'

interface InfoTooltipProps {
    text: string
    label?: string
}

/**
 * F21 — plain-language "what does this mean?" tooltip. A small ⓘ affordance that
 * reveals a lay explanation on hover/focus. Keyboard accessible.
 */
const InfoTooltip: React.FC<InfoTooltipProps> = ({ text, label = 'what does this mean?' }) => {
    const [open, setOpen] = useState(false)
    return (
        <span className="relative inline-flex items-center">
            <button
                type="button"
                aria-label={label}
                onMouseEnter={() => setOpen(true)}
                onMouseLeave={() => setOpen(false)}
                onFocus={() => setOpen(true)}
                onBlur={() => setOpen(false)}
                className="text-gray-400 hover:text-indigo-600 text-xs cursor-help"
            >
                ⓘ
            </button>
            {open && (
                <span
                    role="tooltip"
                    className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-1 w-56 bg-gray-800 text-white text-xs rounded px-2 py-1.5 shadow-lg"
                >
                    {text}
                </span>
            )}
        </span>
    )
}

export default InfoTooltip
