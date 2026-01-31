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
  setEstimation,
  setEstimationLoading,
  clearEstimation,
  GeneSurvival,
} from '../store/searchSlice'
import { RootState } from '../store/store'
import { searchDatasets, getAvailableModels, estimateQuery } from '../services/api'
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
    estimation,
    estimationLoading,
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

  // Step 1: Get estimation before running analysis
  const handleEstimate = React.useCallback(async () => {
    if (!query.trim()) {
      dispatch(setError('Please enter a search query'))
      return
    }

    dispatch(setEstimationLoading(true))
    dispatch(setError(null))
    dispatch(clearEstimation())

    try {
      const data = await estimateQuery(query)
      dispatch(setEstimation({
        confidenceScore: data.confidence_score,
        estimatedDatasets: data.estimated_datasets,
        estimatedTimeSeconds: data.estimated_time_seconds,
        canProceed: data.can_proceed,
        suggestions: data.suggestions,
        improvedQuery: data.improved_query,
      }))
    } catch (err) {
      // If estimation fails, allow proceeding anyway
      console.error('Estimation failed:', err)
      dispatch(setEstimation({
        confidenceScore: 0.5,
        estimatedDatasets: 0,
        estimatedTimeSeconds: 0,
        canProceed: true,
        suggestions: ['Estimation service unavailable. You can proceed with the analysis.'],
      }))
    } finally {
      dispatch(setEstimationLoading(false))
    }
  }, [query, dispatch])

  // Step 2: Run actual analysis after user confirms
  const handleRunAnalysis = React.useCallback(async (queryToRun?: string) => {
    const finalQuery = queryToRun || query
    if (!finalQuery.trim()) {
      dispatch(setError('Please enter a search query'))
      return
    }

    dispatch(clearEstimation())
    dispatch(setLoading(true))
    dispatch(setError(null))

    try {
      const data = await searchDatasets(
        finalQuery,
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
      handleEstimate()
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.7) return 'green'
    if (score >= 0.4) return 'yellow'
    return 'red'
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
            onSearch={handleEstimate}
            loading={loading || estimationLoading}
          />

          <button
            onClick={handleEstimate}
            disabled={loading || estimationLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-6 rounded-lg transition duration-200 flex items-center justify-center text-sm cursor-pointer active:bg-indigo-800"
          >
            {estimationLoading ? (
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
                Analyzing query...
              </>
            ) : loading ? (
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

        {/* Estimation Panel */}
        {estimation && !loading && (
          <div className={`rounded-lg shadow-lg p-6 mb-8 border-l-4 ${
            getConfidenceColor(estimation.confidenceScore) === 'green'
              ? 'bg-green-50 border-green-500'
              : getConfidenceColor(estimation.confidenceScore) === 'yellow'
              ? 'bg-yellow-50 border-yellow-500'
              : 'bg-red-50 border-red-500'
          }`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Query Analysis
                  </h3>
                  <span className={`px-3 py-1 text-sm rounded-full font-medium ${
                    getConfidenceColor(estimation.confidenceScore) === 'green'
                      ? 'bg-green-100 text-green-800'
                      : getConfidenceColor(estimation.confidenceScore) === 'yellow'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {(estimation.confidenceScore * 100).toFixed(0)}% Confidence
                  </span>
                </div>

                <div className="flex gap-6 text-sm text-gray-600 mb-4">
                  <span>
                    Est. {estimation.estimatedDatasets} datasets
                  </span>
                  <span>|</span>
                  <span>
                    ~{Math.ceil(estimation.estimatedTimeSeconds / 60)} min
                  </span>
                </div>

                {estimation.suggestions.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Suggestions to improve results:
                    </p>
                    <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                      {estimation.suggestions.slice(0, 4).map((suggestion, i) => (
                        <li key={i}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {estimation.improvedQuery && (
                  <div className="bg-white p-4 rounded-lg border border-gray-200 mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Suggested improved query:
                    </p>
                    <p className="text-sm text-blue-600 italic mb-3">
                      "{estimation.improvedQuery}"
                    </p>
                    <button
                      onClick={() => {
                        dispatch(setQuery(estimation.improvedQuery!))
                        handleRunAnalysis(estimation.improvedQuery!)
                      }}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium underline"
                    >
                      Use this query instead
                    </button>
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2 ml-6">
                <button
                  onClick={() => dispatch(clearEstimation())}
                  className="text-gray-400 hover:text-gray-600"
                  title="Dismiss"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="flex gap-3 mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={() => handleRunAnalysis()}
                className="px-6 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Run Analysis
              </button>
              <button
                onClick={() => dispatch(clearEstimation())}
                className="px-6 py-2 bg-gray-200 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

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

              {/* Ranking Recommendations */}
              {results.ranking_recommendations && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-start gap-2">
                    <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="text-sm font-medium text-blue-800 mb-1">
                        Analysis Quality: {results.ranking_quality_score?.toFixed(1) || 'N/A'}/10
                      </p>
                      <p className="text-sm text-blue-700">
                        {results.ranking_recommendations}
                      </p>
                    </div>
                  </div>
                </div>
              )}
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
