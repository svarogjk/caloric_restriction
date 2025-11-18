import React from 'react'

interface SearchBarProps {
  query: string
  onChange: (value: string) => void
  onSearch: () => void
  loading: boolean
}

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
        placeholder="e.g., Does caloric restriction extend lifespan in mice?"
        disabled={loading}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed transition"
      />
    </div>
  )
}

export default SearchBar
