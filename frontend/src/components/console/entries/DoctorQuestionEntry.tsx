import React from 'react'

interface DoctorQuestionEntryProps {
    text: string
    timestamp?: string
}

/** A plain question from the clinician — safe to send, so it is shown as an
 *  ordinary outgoing bubble with no privacy disclosure attached. */
const DoctorQuestionEntry: React.FC<DoctorQuestionEntryProps> = ({ text, timestamp }) => (
    <div className="flex flex-col items-end gap-0.5">
        <div className="max-w-[85%] bg-accent text-on-accent rounded-card rounded-br-sm px-3 py-2 text-sm whitespace-pre-wrap">
            {text}
        </div>
        {timestamp && <span className="text-[10px] text-fg-faint pr-1">{timestamp}</span>}
    </div>
)

export default DoctorQuestionEntry
