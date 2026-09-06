import Plotly from 'plotly.js-dist-min'
import createPlotlyComponent from 'react-plotly.js/factory'
import { formatNumber } from '../utils/format'

const Plot = createPlotlyComponent(Plotly)

function pointTrace(values, name, symbol, color) {
  return {
    x: values.map((point) => point.real),
    y: values.map((point) => point.imag),
    mode: 'markers',
    type: 'scatter',
    name,
    text: values.map((point, index) => (
      `${name} ${index + 1}: ${formatNumber(point.real)} ` +
      `${point.imag >= 0 ? '+' : '-'} ${formatNumber(Math.abs(point.imag))}j`
    )),
    hovertemplate: '%{text}<extra></extra>',
    marker: {
      symbol,
      size: 12,
      color,
      line: { color, width: 2 },
    },
  }
}

function branchTraces(data) {
  return Array.from({ length: data.poles.length }, (_, branchIndex) => ({
    x: data.lgr.map((sample) => sample.roots[branchIndex].real),
    y: data.lgr.map((sample) => sample.roots[branchIndex].imag),
    mode: 'lines',
    type: 'scatter',
    name: `Ramo ${branchIndex + 1}`,
    line: { color: '#007aff', width: 2 },
    hoverinfo: 'skip',
    showlegend: false,
  }))
}

function asymptoteTraces(data) {
  if (data.centroid == null) return []

  return data.asymptoteAngles.map((angle, index) => {
    const radians = angle * Math.PI / 180
    const length = 100

    return {
      x: [data.centroid, data.centroid + length * Math.cos(radians)],
      y: [0, length * Math.sin(radians)],
      mode: 'lines',
      type: 'scatter',
      name: 'Assíntota',
      line: { color: '#ff9500', dash: 'dash', width: 1 },
      hoverinfo: 'skip',
      showlegend: index === 0,
    }
  })
}

export default function RootLocusPlot({ data }) {
  const traces = [
    ...branchTraces(data),
    ...asymptoteTraces(data),
    pointTrace(data.poles, 'Polos', 'x', '#ff375f'),
    pointTrace(data.zeros, 'Zeros', 'circle-open', '#34c759'),
  ]

  const layout = {
    autosize: true,
    dragmode: 'pan',
    margin: { l: 60, r: 22, t: 18, b: 55 },
    paper_bgcolor: '#101827',
    plot_bgcolor: '#101827',
    font: { family: 'Manrope', color: '#dfe7f5', size: 11 },
    xaxis: {
      title: 'Parte real σ',
      zeroline: true,
      gridcolor: '#34445d',
      zerolinecolor: '#72809a',
    },
    yaxis: {
      title: 'Parte imaginária jω',
      zeroline: true,
      gridcolor: '#34445d',
      zerolinecolor: '#72809a',
      scaleanchor: 'x',
      scaleratio: 1,
    },
    legend: { orientation: 'h', y: -0.18 },
    hovermode: 'closest',
    uirevision: 'lgr',
  }

  const config = {
    responsive: true,
    displaylogo: false,
    displayModeBar: true,
    scrollZoom: true,
    doubleClick: 'reset',
    modeBarButtonsToRemove: ['select2d', 'lasso2d'],
  }

  return (
    <Plot
      className="plotly"
      data={traces}
      layout={layout}
      config={config}
      useResizeHandler
    />
  )
}
