import type cytoscape from 'cytoscape'

export const graphStyles: cytoscape.StylesheetJson = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-family': 'Bricolage Grotesque Variable, Bricolage Grotesque, sans-serif',
      'font-size': 10,
      'font-weight': 600,
      color: '#14201e',
      'text-valign': 'bottom',
      'text-margin-y': 5,
      'text-wrap': 'wrap',
      'text-max-width': '120px',
      'border-width': 2,
      'border-color': '#f4f4ee',
    },
  },
  {
    selector: 'node.node-producer',
    style: {
      shape: 'ellipse',
      width: 28,
      height: 28,
      'background-color': '#8f3b28',
    },
  },
  {
    selector: 'node.producer-group',
    style: {
      shape: 'hexagon',
      width: 32,
      height: 32,
      'background-color': '#7a5a20',
    },
  },
  {
    selector: 'node.producer-other, node.producer-unknown',
    style: {
      'background-color': '#66736d',
    },
  },
  {
    selector: 'node.node-album',
    style: {
      shape: 'rectangle',
      width: 17,
      height: 17,
      'background-color': 'data(color)',
      label: 'data(label)',
      'font-size': 10,
      'text-max-width': '100px',
      'text-background-color': '#dde2dc',
      'text-background-opacity': 0.9,
      'text-background-padding': '2px',
    },
  },
  {
    selector: 'node.node-album:selected',
    style: {
      'border-color': '#14201e',
      'border-width': 3,
    },
  },
  {
    selector: 'node.node-album.missing-year',
    style: {
      'background-color': '#66736d',
    },
  },
  {
    selector: 'node.node-band',
    style: {
      shape: 'round-rectangle',
      width: 44,
      height: 24,
      'background-color': '#173d3d',
      color: '#f4f4ee',
    },
  },
  {
    selector: 'node.self-produced',
    style: {
      'border-color': '#7a5a20',
      'border-width': 4,
    },
  },
  {
    selector: 'edge',
    style: {
      width: 'mapData(weight, 0, 10, 1, 5)',
      'line-color': '#66736d',
      'line-opacity': 0.55,
      'curve-style': 'bezier',
      'target-arrow-shape': 'none',
    },
  },
  {
    selector: 'edge.role-co-producer',
    style: {
      'line-style': 'dashed',
    },
  },
  {
    selector: 'edge.support-partial',
    style: {
      'line-opacity': 0.38,
    },
  },
  {
    selector: 'edge.support-unknown',
    style: {
      'line-opacity': 0.25,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#14201e',
      'border-width': 3,
    },
  },
  {
    selector: 'edge:selected',
    style: {
      'line-color': '#8f3b28',
      'line-opacity': 1,
      label: 'data(label)',
      'font-family': 'Bricolage Grotesque Variable, Bricolage Grotesque, sans-serif',
      'font-size': 9,
      color: '#14201e',
      'text-background-color': '#f4f4ee',
      'text-background-opacity': 0.9,
      'text-background-padding': '2px',
      'text-rotation': 'autorotate',
    },
  },
  {
    selector: 'node.overview-node',
    style: {
      width: 'data(size)',
      height: 'data(size)',
      'font-size': 8,
      'text-max-width': '80px',
      'min-zoomed-font-size': 12,
    },
  },
  {
    selector: 'node.overview-node.node-band',
    style: {
      'font-size': 9,
      'min-zoomed-font-size': 0,
    },
  },
  {
    selector: 'node.overview-node:selected',
    style: {
      'min-zoomed-font-size': 0,
    },
  },
  {
    selector: 'node.overview-node.search-match',
    style: {
      'min-zoomed-font-size': 0,
      'border-color': '#7a5a20',
      'border-width': 4,
      opacity: 1,
    },
  },
  {
    selector: 'node.overview-node.isolated-producer',
    style: {
      opacity: 0.45,
    },
  },
  {
    selector: 'node.overview-node.searchable-producer',
    style: {
      opacity: 0.3,
    },
  },
]
