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

  const realRoots = [...data.poles, ...data.zeros].flatMap((point) => [point.real, point.imag])
  const span = Math.max(4, ...realRoots.map((value) => Math.abs(value) * 1.5))
  const length = span * 2.4

  return data.asymptoteAngles.map((angle, index) => {
    const radians = angle * Math.PI / 180

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

function segmentTraces(data) {
  return data.realSegments.map((segment, index) => {
    const left = segment.from == null ? Math.min(...data.poles.map((point) => point.real), ...data.zeros.map((point) => point.real)) - 8 : segment.from
    const right = segment.to
    return {
      x: [left, right],
      y: [0, 0],
      mode: 'lines',
      type: 'scatter',
      name: index === 0 ? 'Eixo real válido' : 'Segmento válido',
      line: { color: '#7b61ff', width: 5 },
      hoverinfo: 'skip',
      showlegend: index === 0,
    }
  })
}

function markerTrace(values, name, color, symbol) {
  if (!values.length) return []
  return [{
    x: values.map((point) => point.real),
    y: values.map((point) => point.imag),
    mode: 'markers',
    type: 'scatter',
    name,
    marker: { color, symbol, size: 10, line: { color, width: 2 } },
    hovertemplate: `${name}: %{x:.3f} + %{y:.3f}j<extra></extra>`,
  }]
}

function pointCriterionTraces(data) {
  const point = data.pointValue
  const traces = [{
    x: [point.real], y: [point.imag], mode: 'markers', type: 'scatter', name: 'Ponto de teste',
    marker: { color: data.point.belongs ? '#34c759' : '#ff9500', size: 13, symbol: 'diamond' },
    hovertemplate: 's₀: %{x:.3f} + %{y:.3f}j<extra></extra>',
  }]
  data.poles.forEach((root) => traces.push({
    x: [point.real, root.real], y: [point.imag, root.imag], mode: 'lines', type: 'scatter',
    name: 'Distância ao polo', line: { color: '#ff375f', width: 1, dash: 'dot' }, hoverinfo: 'skip', showlegend: false,
  }))
  data.zeros.forEach((root) => traces.push({
    x: [point.real, root.real], y: [point.imag, root.imag], mode: 'lines', type: 'scatter',
    name: 'Distância ao zero', line: { color: '#34c759', width: 1, dash: 'dot' }, hoverinfo: 'skip', showlegend: false,
  }))
  return traces
}

function angleTraces(data) {
  const angles = data.stepCalculations?.angles
  if (!angles) return []
  const roots = [...data.poles, ...data.zeros]
  const span = Math.max(1, ...roots.flatMap((point) => [Math.abs(point.real), Math.abs(point.imag)]))
  const length = Math.max(0.45, span * 0.28)
  const traces = []
  const add = (items, color, label) => items.forEach((item, index) => {
    const radians = item.angle * Math.PI / 180
    const endX = item.point.real + length * Math.cos(radians)
    const endY = item.point.imag + length * Math.sin(radians)
    traces.push({
      x: [item.point.real, endX], y: [item.point.imag, endY], mode: 'lines+markers', type: 'scatter',
      name: label, line: { color, width: 2 }, marker: { color, size: 7, symbol: 'triangle-up' },
      hovertemplate: `${label}: %{x:.3f} + %{y:.3f}j<extra></extra>`, showlegend: index === 0,
    })
  })
  add(angles.departures || [], '#b4233d', 'Ângulo de partida')
  add(angles.arrivals || [], '#16803c', 'Ângulo de chegada')
  return traces
}

export default function RootLocusPlot({ data, mode = 'full', compact = false }) {
  const showBranches = ['full', 'asymptotes', 'breakaway', 'jw', 'angles', 'point'].includes(mode)
  const showAsymptotes = ['full', 'asymptotes', 'breakaway', 'angles'].includes(mode)
  const showSegments = ['full', 'real', 'asymptotes', 'breakaway', 'angles'].includes(mode)
  const traces = [
    ...(showBranches ? branchTraces(data) : []),
    ...(showAsymptotes ? asymptoteTraces(data) : []),
    ...(showSegments ? segmentTraces(data) : []),
    pointTrace(data.poles, 'Polos', 'x', '#ff375f'),
    pointTrace(data.zeros, 'Zeros', 'circle-open', '#34c759'),
    ...(mode === 'breakaway' ? markerTrace(data.breakaway.map((item) => item.point), 'Breakaway / break-in', '#af52de', 'diamond') : []),
    ...(mode === 'jw' ? markerTrace(data.jwCrossings.map((item) => ({ real: 0, imag: item.omega })), 'Cruzamento jω', '#ff9500', 'star') : []),
    ...(mode === 'angles' ? angleTraces(data) : []),
    ...(mode === 'point' ? pointCriterionTraces(data) : []),
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
    uirevision: `lgr-${mode}`,
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
      className={`plotly ${compact ? 'plotly-compact' : ''}`}
      data={traces}
      layout={layout}
      config={config}
      useResizeHandler
    />
  )
}
