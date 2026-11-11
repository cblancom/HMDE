export function GraphLegend() {
  return (
    <section className="graph-legend-panel" aria-labelledby="graph-legend-heading">
      <h2 id="graph-legend-heading">How to read the network</h2>
      <ul className="graph-legend" aria-label="Graph legend">
        <li><span className="legend-swatch legend-swatch--person" aria-hidden="true" />Producer, person</li>
        <li><span className="legend-swatch legend-swatch--group" aria-hidden="true" />Producer, group or self-produced</li>
        <li><span className="legend-swatch legend-swatch--album" aria-hidden="true" />Album, color by year</li>
        <li className="legend-year"><span className="legend-year__scale" aria-hidden="true" />1960 to 2026</li>
        <li><span className="legend-swatch legend-swatch--band" aria-hidden="true" />Band or artist</li>
        <li><span className="legend-swatch legend-swatch--solid" aria-hidden="true" />Producer edge</li>
        <li><span className="legend-swatch legend-swatch--dashed" aria-hidden="true" />Co-producer edge</li>
      </ul>
      <p className="graph-note">Dashed edges are co-producer credits. Fainter edges have partial or unknown recording support.</p>
    </section>
  )
}
