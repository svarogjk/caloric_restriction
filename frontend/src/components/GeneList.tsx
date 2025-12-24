import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { GeneSurvival, expandGene } from '../store/searchSlice'
import { RootState } from '../store/store'
import GeneCard from './GeneCard'

interface GeneListProps {
  genes: GeneSurvival[]
}

const GeneList: React.FC<GeneListProps> = ({ genes }) => {
  const dispatch = useDispatch()
  const expandedGeneId = useSelector(
    (state: RootState) => state.search.expandedGeneId
  )

  // Sort genes by number of datasets in descending order, then by p-value
  const sortedGenes = [...genes].sort((a, b) => {
    if (b.n_datasets !== a.n_datasets) {
      return b.n_datasets - a.n_datasets
    }
    return a.avg_cox_p_value - b.avg_cox_p_value
  })

  return (
    <div className="space-y-4">
      {sortedGenes.map((gene) => (
        <GeneCard
          key={gene.gene_id}
          gene={gene}
          isExpanded={expandedGeneId === gene.gene_id}
          onToggle={() => dispatch(expandGene(gene.gene_id))}
        />
      ))}
    </div>
  )
}

export default GeneList
