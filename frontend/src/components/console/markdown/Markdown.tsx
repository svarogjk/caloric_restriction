import React from 'react'
import ReactMarkdown, { Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { linkifyGse } from './gseLinks'

/**
 * Assistant turns arrive as markdown — the system prompt asks for cohort/HR/
 * C-index tables and bolded accessions. Element styling lives in `.md-body`
 * (index.css) against the semantic tokens, so it themes with everything else;
 * only structural wrappers are set here.
 *
 * No rehype-raw: raw HTML in model output is NOT rendered, which keeps this
 * structurally safe against anything the model emits.
 */
const COMPONENTS: Components = {
    // Wide tables must scroll inside the bubble, never widen the thread.
    table: ({ children, ...props }) => (
        <div className="overflow-x-auto">
            <table {...props}>{children}</table>
        </div>
    ),
    a: ({ children, ...props }) => (
        <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>
    ),
}

interface MarkdownProps {
    children: string
    className?: string
}

const Markdown: React.FC<MarkdownProps> = ({ children, className = '' }) => (
    <div className={`md-body ${className}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
            {linkifyGse(children)}
        </ReactMarkdown>
    </div>
)

export default Markdown
