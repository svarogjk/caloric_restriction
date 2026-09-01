import React, { useRef, useState } from 'react'

const MAX_FILE_BYTES = 5 * 1024 * 1024
const MAX_LINES = 100_000

interface ExpressionInputProps {
    value: string
    onChange: (value: string) => void
    onFileError?: (message: string) => void
    disabled?: boolean
    rows?: number
    /** Drives the border so the box itself shows whether it parsed, instead of
     *  the answer living only in a caption under the button. */
    state?: 'empty' | 'ok' | 'error'
}

/**
 * The tumour expression textarea, plus a drag/drop and file-picker path onto
 * the SAME text state — parsePastedExpression already handles space/tab/comma/
 * colon separators, so a 2-column CSV/TSV needs no new parsing, just a way to
 * get its text into the same box.
 */
const STATE_BORDER: Record<'empty' | 'ok' | 'error', string> = {
    empty: 'border-warn-border',
    ok: 'border-ok-border',
    error: 'border-danger-border',
}

const ExpressionInput: React.FC<ExpressionInputProps> = ({ value, onChange, onFileError, disabled, rows = 8, state = 'empty' }) => {
    const [dragOver, setDragOver] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const loadFile = (file: File) => {
        if (file.size > MAX_FILE_BYTES) {
            onFileError?.('That file is too large (over 5 MB) — this looks like a full expression matrix. Export a single sample\'s column first.')
            return
        }
        const reader = new FileReader()
        reader.onload = () => {
            const text = String(reader.result ?? '')
            if (text.split('\n').length > MAX_LINES) {
                onFileError?.('That file has too many lines — this looks like a full expression matrix. Export a single sample\'s column first.')
                return
            }
            onChange(text)
        }
        reader.onerror = () => onFileError?.('Could not read that file.')
        reader.readAsText(file)
    }

    return (
        <div
            className={`rounded-card border-2 border-dashed transition-colors ${dragOver ? 'border-border-accent bg-surface-accent' : 'border-transparent'}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                const file = e.dataTransfer.files?.[0]
                if (file) loadFile(file)
            }}
        >
            <textarea
                value={value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                rows={rows}
                placeholder={'Paste "GENE value" per line, or drop a CSV/TSV:\nESR1 12.1\nPGR 11.4\nMKI67 5.8\n…'}
                className={`w-full text-xs font-mono bg-surface-sunken text-fg border ${STATE_BORDER[state]} rounded-control p-2 focus:outline-none focus:ring-1 focus:ring-accent-ring resize-y`}
            />
            <div className="flex items-center justify-between mt-1">
                <p className="text-[11px] text-fg-faint">Drop a file here, or</p>
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[11px] text-accent-fg hover:underline"
                >
                    choose a file
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.tsv,.txt,.tab"
                    className="hidden"
                    onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) loadFile(file)
                        e.target.value = ''
                    }}
                />
            </div>
        </div>
    )
}

export default ExpressionInput
