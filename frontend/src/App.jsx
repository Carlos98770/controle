import { useState } from 'react'
import { Activity, Calculator, CircleHelp, Play, Settings2 } from 'lucide-react'
import { BlockMath, InlineMath } from 'react-katex'
import { formatNumber, polynomialLatex } from './utils/format'
import FormField from './components/FormField'
import RootLocusPlot from './components/RootLocusPlot'
import StepCarousel from './components/StepCarousel'

const initialForm = { nG: '1 2', dG: '1 4 0', nH: '1', dH: '1 1', pointReal: 0, pointImag: 0 }
const apiBaseUrl = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

function InfoCard({ title, children }) {
  return <div className="card info"><span className="muted">{title}</span><div className="info-value">{children}</div></div>
}

function ParameterPanel({ form, loading, error, onChange, onCalculate }) {
  return <aside className="panel controls">
    <div className="panel-title"><Calculator size={19} /><h3>Parâmetros</h3></div>
    <p className="hint">Coeficientes em ordem decrescente de s.</p>
    <div className="group"><h4>Função G(s)</h4><FormField label="Numerador" name="nG" value={form.nG} onChange={onChange} /><FormField label="Denominador" name="dG" value={form.dG} onChange={onChange} /></div>
    <div className="group"><h4>Função H(s)</h4><FormField label="Numerador" name="nH" value={form.nH} onChange={onChange} /><FormField label="Denominador" name="dH" value={form.dH} onChange={onChange} /></div>
    <div className="group"><h4>Ponto de teste</h4><div className="fields-inline"><FormField label="Real" name="pointReal" value={form.pointReal} onChange={onChange} /><FormField label="Imaginário" name="pointImag" value={form.pointImag} onChange={onChange} /></div></div>
    <button className="primary" onClick={onCalculate} disabled={loading}><Play size={17} fill="currentColor" />{loading ? 'Calculando...' : 'Calcular LGR'}</button>
    {error && <div className="error">{error}</div>}
  </aside>
}

function AnalysisSummary({ data }) {
  return <>
    <div className="result-head"><div><p className="eyebrow">RESULTADO DA ANÁLISE</p><h3>Visão geral do sistema</h3></div><span className="badge">{data.poles.length} polos · {data.zeros.length} zeros</span></div>
    <div className="cards"><div className="card chart-card"><div className="card-head"><h4>Gráfico do lugar das raízes</h4><div className="legend"><span className="blue" />LGR <span className="red" />Polos <span className="green" />Zeros</div></div><RootLocusPlot data={data} /></div><div className="card transfer-card"><h4>Função de malha aberta</h4><div className="summary-formula"><BlockMath math={`P(s)=\\frac{${polynomialLatex(data.numerator)}}{${polynomialLatex(data.denominator)}}`} /></div><p className="muted">Equação característica: <InlineMath math="D(s)+K\\,N(s)=0" /></p></div></div>
    <div className="cards three"><InfoCard title="Eixo real">{data.realSegments.length ? data.realSegments.map((segment, index) => <InlineMath key={index} math={`\\left(${segment.from == null ? '-\\infty' : formatNumber(segment.from)},\\,${formatNumber(segment.to)}\\right]`} />) : <span className="muted">Nenhum segmento.</span>}</InfoCard><InfoCard title="Centroide">{data.centroid == null ? <InlineMath math="\\text{Sem assíntotas}" /> : <InlineMath math={`\\sigma_a=${formatNumber(data.centroid)}`} />}</InfoCard><InfoCard title={<>Cruzamentos <InlineMath math="j\\omega" /></>}>{data.jwCrossings.length ? data.jwCrossings.map((item, index) => <InlineMath key={index} math={`\\omega=${formatNumber(item.omega)}\\quad K=${formatNumber(item.gain)}`} />) : <span className="muted">Nenhum encontrado.</span>}</InfoCard></div>
    <div className="card point"><h4>Resumo do ponto de teste <InlineMath math="s_0" /></h4><div className={data.point.belongs ? 'success' : 'warning'}><InlineMath math={data.point.belongs ? '\\text{Pertence ao LGR}' : '\\text{Não pertence ao LGR}'} /><strong><InlineMath math={`K=${formatNumber(data.point.gain)}`} /></strong><span className="point-angle"><InlineMath math={`\\Delta\\theta_{\\mathrm{norm}}=${formatNumber(data.point.normalized_angle)}^\\circ`} /></span></div></div>
    <StepCarousel data={data} />
  </>
}

export default function App() {
  const [form, setForm] = useState(initialForm)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const update = (name, value) => setForm((current) => ({ ...current, [name]: value }))
  const calculate = async () => {
    setLoading(true); setError('')
    try {
      const response = await fetch(`${apiBaseUrl}/api/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail)
      setData(result)
    } catch (requestError) { setError(requestError.message || 'Não foi possível calcular.') } finally { setLoading(false) }
  }
  return <div className="app">
    <header><div className="brand"><div className="logo"><Activity size={22} /></div><div><h1>LGR Studio</h1><small>Análise de sistemas de controle</small></div></div><div className="header-actions"><button className="icon"><CircleHelp size={18} /></button><button className="icon"><Settings2 size={18} /></button></div></header>
    <main><section className="intro"><div><p className="eyebrow">DCA-3701 · UFRN</p><h2>Lugar Geométrico das Raízes</h2><p>Explore a resolução completa de forma visual e interativa.</p></div><div className="status"><span className="dot" /> API conectada</div></section><div className="layout"><ParameterPanel form={form} loading={loading} error={error} onChange={update} onCalculate={calculate} /><section className="results">{data ? <AnalysisSummary data={data} /> : <div className="empty"><Activity size={42} /><h3>Pronto para analisar</h3><p>Informe os parâmetros e clique em calcular para visualizar a resolução.</p></div>}</section></div></main>
    <footer><span>LGR Studio · Projeto de Sistemas de Controle</span><span>FastAPI + React</span></footer>
  </div>
}
