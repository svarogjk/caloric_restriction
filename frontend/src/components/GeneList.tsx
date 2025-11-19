import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { GeneOccurrence, expandGene } from '../store/searchSlice'
import { RootState } from '../store/store'
import GeneCard from './GeneCard'

interface GeneListProps {
  genes: GeneOccurrence[]
}

const GeneList: React.FC<GeneListProps> = ({ genes }) => {
  const dispatch = useDispatch()
  const expandedGeneId = useSelector(
    (state: RootState) => state.search.expandedGeneId
  )

  // Sort genes by number of datasets in descending order
  const sortedGenes = [...genes].sort((a, b) => b.n_datasets - a.n_datasets)

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
