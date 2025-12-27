import React from 'react'

interface SearchBarProps {
  query: string
  onChange: (value: string) => void
  onSearch: () => void
  loading: boolean
}

const EXAMPLE_QUESTIONS = [
  // Cancer survival examples
  "What genes predict survival in breast cancer patients?",
  "Which biomarkers are associated with lung cancer prognosis?",
  "What genes affect overall survival in colorectal cancer?",
  "Which genes predict hepatocellular carcinoma patient outcome?",
  "What genes are prognostic in gastric cancer survival?",
  // Caloric restriction / aging examples  
  "Does caloric restriction extend lifespan in mice?",
  "What genes are affected by caloric restriction in aging?",
  "How does caloric restriction impact mitochondrial function?",
]

const SearchBar: React.FC<SearchBarProps> = ({
  query,
  onChange,
  onSearch,
  loading,
}) => {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Ask a Question
      </label>
      <input
        type="text"
        value={query}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && onSearch()}
        placeholder="e.g., What genes predict survival in breast cancer? or Does caloric restriction extend lifespan in mice?"
        disabled={loading}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed transition"
      />
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLE_QUESTIONS.map((question) => (
          <button
            key={question}
            onClick={() => {
              onChange(question)
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-indigo-100 text-indigo-700 rounded-full hover:bg-indigo-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}

export default SearchBar
