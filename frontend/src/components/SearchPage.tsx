import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setQuery,
  setSelectedModel,
  setDatasetCount,
  setRankingMultiplier,
  setOrganism,
  setLoading,
  setResults,
  setError,
  GeneSurvival,
} from '../store/searchSlice'
import { RootState } from '../store/store'
import { searchDatasets, getAvailableModels } from '../services/api'
import SearchBar from './SearchBar'
import ModelSelector from './ModelSelector'
import DatasetCountSelector from './DatasetCountSelector'
import RankingMultiplierSelector from './RankingMultiplierSelector'
import GeneList from './GeneList'
import VolcanoPlot from './VolcanoPlot'
import KaplanMeierPlot from './KaplanMeierPlot'

const SearchPage: React.FC = () => {
  const dispatch = useDispatch()
  const { 
    query, 
    selectedModel, 
    datasetCount, 
    rankingMultiplier, 
    organism,
    results, 
    loading, 
    error,
  } = useSelector(
    (state: RootState) => state.search
  )
  const [models, setModels] = React.useState<string[]>([])
  const [selectedGene, setSelectedGene] = React.useState<GeneSurvival | null>(null)

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
      const data = await searchDatasets(
        query, 
        selectedModel, 
        datasetCount, 
        rankingMultiplier,
        organism
      )
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
  }, [query, selectedModel, datasetCount, rankingMultiplier, organism, dispatch])

  const handleKeyPress = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">
          Survival Analysis Search
        </h1>
        <p className="text-gray-600 mb-8">
          Discover survival-associated genes from GEO datasets for cancer prognosis, aging, and caloric restriction studies
        </p>

        <div
          className="bg-white rounded-lg shadow-lg p-8 mb-8"
          onKeyPress={handleKeyPress}
        >
          <div className="flex gap-6 mb-6">
            <ModelSelector
              selectedModel={selectedModel}
              models={models}
              onChange={(value) => dispatch(setSelectedModel(value))}
            />
            <DatasetCountSelector
              value={datasetCount}
              onChange={(value) => dispatch(setDatasetCount(value))}
            />
            <RankingMultiplierSelector
              value={rankingMultiplier}
              onChange={(value) => dispatch(setRankingMultiplier(value))}
            />
          </div>

          {/* Organism Selection */}
          <div className="bg-blue-50 rounded-lg p-4 mb-6 border border-blue-200">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">
                Organism:
              </label>
              <select
                value={organism || ''}
                onChange={(e) => dispatch(setOrganism(e.target.value || null))}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
              >
                <option value="">Any organism</option>
                <option value="Homo sapiens">Human (Homo sapiens)</option>
                <option value="Mus musculus">Mouse (Mus musculus)</option>
              </select>
              <span className="text-xs text-gray-500 italic">
                Select organism to filter datasets
              </span>
            </div>
          </div>

          <SearchBar
            query={query}
            onChange={(value) => dispatch(setQuery(value))}
            onSearch={handleSearch}
            loading={loading}
          />

          <button
            onClick={handleSearch}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-6 rounded-lg transition duration-200 flex items-center justify-center text-sm cursor-pointer active:bg-indigo-800"
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
                Analyzing survival data...
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

        {results && (
          <div>
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Survival Analysis Results
              </h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm font-medium">
                    Datasets Analyzed
                  </p>
                  <p className="text-3xl font-bold text-blue-600">
                    {results.n_datasets_analyzed}
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm font-medium">
                    With Survival Data
                  </p>
                  <p className="text-3xl font-bold text-green-600">
                    {results.n_datasets_with_survival}
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm font-medium">
                    Survival Genes
                  </p>
                  <p className="text-3xl font-bold text-purple-600">
                    {results.common_genes.length}
                  </p>
                </div>
              </div>
              <p className="text-gray-500 text-sm">
                Processing time: {results.processing_time.toFixed(2)} seconds
              </p>
            </div>

            {results.common_genes.length > 0 && (
              <div>
                {/* Volcano Plot Section */}
                <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                  <VolcanoPlot
                    data={results.common_genes}
                    onGeneClick={(gene) => setSelectedGene(gene)}
                    selectedGeneId={selectedGene?.gene_id}
                  />
                </div>

                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Survival-Associated Genes ({results.common_genes.length})
                </h2>
                <p className="text-gray-600 mb-4">
                  Genes significantly associated with survival outcomes across multiple datasets.
                  Higher hazard ratios indicate increased risk with higher expression.
                </p>
                <GeneList genes={results.common_genes} />
              </div>
            )}
          </div>
        )}

        {/* Kaplan-Meier Plot Modal */}
        {selectedGene && (
          <KaplanMeierPlot
            gene={selectedGene}
            onClose={() => setSelectedGene(null)}
          />
        )}

        {!loading && !results && !error && (
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
              Enter a search query to find survival-associated genes
            </p>
            <div className="text-gray-400 text-sm mt-4">
              <p className="font-medium text-gray-500">Click one of the example questions above or type your own query</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SearchPage
