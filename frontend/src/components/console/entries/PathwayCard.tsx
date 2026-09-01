import React from 'react'
import PathwayEnrichmentPanel from '../../PathwayEnrichmentPanel'

/** "What's the biology behind this score?" — thin wrapper, the panel self-fetches. */
const PathwayCard: React.FC<{ geneSymbols: string[] }> = ({ geneSymbols }) => (
    <PathwayEnrichmentPanel geneSymbols={geneSymbols} />
)

export default PathwayCard
