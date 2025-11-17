import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setQuery,
  setSelectedModel,
  setLoading,
  setResults,
  setError,
} from '../store/searchSlice'
import { RootState } from '../store/store'
import { searchDatasets, getAvailableModels } from '../services/api'
import SearchBar from './SearchBar'
import ModelSelector from './ModelSelector'
import DatasetList from './DatasetList'

const SearchPage: React.FC = () => {
  const dispatch = useDispatch()
  const { query, selectedModel, results, loading, error } = useSelector(
    (state: RootState) => state.search
  )
  const [models, setModels] = React.useState<string[]>([])

  React.useEffect(() => {
    const fetchModels = async () => {
      try {
        const availableModels = await getAvailableModels()
        setModels(availableModels)
      } catch (err) {
        console.error('Failed to fetch models:', err)
      }
    }

    fetchModels()
  }, [])

  const handleSearch = React.useCallback(async () => {
    if (!query.trim()) {
      dispatch(setError('Please enter a search query'))
      return
    }

    dispatch(setLoading(true))
    dispatch(setError(null))

    try {
      const data = await searchDatasets(query, selectedModel)
      dispatch(setResults(data))
    } catch (err) {
      dispatch(
        setError(
          err instanceof Error ? err.message : 'Failed to search datasets'
        )
      )
    } finally {
      dispatch(setLoading(false))
    }
  }, [query, selectedModel, dispatch])

  const handleKeyPress = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">
          Genomic Data Search
        </h1>
        <p className="text-gray-600 mb-8">
          Explore differential expression datasets and analyze gene expression
          data
        </p>

        <div
          className="bg-white rounded-lg shadow-lg p-8 mb-8"
          onKeyPress={handleKeyPress}
        >
          <SearchBar
            query={query}
            onChange={(value) => dispatch(setQuery(value))}
            onSearch={handleSearch}
            loading={loading}
          />

          <ModelSelector
            selectedModel={selectedModel}
            models={models}
            onChange={(value) => dispatch(setSelectedModel(value))}
          />

          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Searching...
              </>
            ) : (
              'Search'
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-8">
            {error}
          </div>
        )}

        {results.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Results ({results.length})
            </h2>
            <DatasetList datasets={results} />
          </div>
        )}

        {!loading && results.length === 0 && !error && (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <p className="text-gray-500 text-lg mt-4">
              Enter a search query to begin
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default SearchPage
