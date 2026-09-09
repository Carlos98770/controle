import { useEffect, useRef, useState } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import { complexLatex, factorizedPolynomialLatex, formatNumber, polynomialLatex } from '../utils/format'
import RootLocusPlot from './RootLocusPlot'

function Formula({ children, className = '' }) {
  return (
    <div className={`formula ${className}`.trim()}>
      <BlockMath math={children} />
    </div>
  )
}

function FormulaList({ formulas = [] }) {
  return formulas.map((formula, index) => <Formula key={index}>{formula}</Formula>)
}

function MathChip({ math, className = '' }) {
  return (
    <span className={`math-chip ${className}`.trim()}>
      <InlineMath math={math} />
    </span>
  )
}

function MathLabel({ children }) {
  return <span className="math-label"><InlineMath math={`\\text{${children}}`} /></span>
}

function Step({ number, title, children }) {
  return (
    <article className="step" data-step={number}>
      <div className="step-summary">
        <span className="step-number">{String(number).padStart(2, '0')}</span>
        <span className="step-title">{title}</span>
        <span className="step-kind">Etapa {number}</span>
      </div>
      <div className="step-content">{children}</div>
    </article>
  )
}

function RootChips({ values, prefix = '' }) {
  return values.map((value, index) => (
    <MathChip
      key={index}
      math={`${prefix}_{${index + 1}} = ${complexLatex(value)}`}
    />
  ))
}

function RouthTable({ data }) {
  const firstRow = data.routh.rows[0] || []

  return (
    <div className="routh-table" role="region" aria-label="Tabela de Routh-Hurwitz">
      <table>
        <thead>
          <tr>
            <th><InlineMath math="s" /></th>
            {firstRow.map((_, index) => (
              <th key={index}><InlineMath math={`C_{${index + 1}}`} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.routh.rows.map((row, index) => (
            <tr key={index}>
              <th><InlineMath math={`s^{${data.routh.powers[index]}}`} /></th>
              {row.map((cell, column) => (
                <td key={column}><InlineMath math={cell || '0'} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PointAngleDetails({ data, pointValues, pointResults, pointDetailsList }) {
  return pointDetailsList.map((pointDetailsForPoint, index) => {
    const pointValue = pointValues[index] || pointValues[0]
    const pointResult = pointResults[index] || pointResults[0]
    const pointLabel = pointValues.length > 1 ? `s_0^{(${index + 1})}` : 's_0'
    const poleAngleSum = pointResult.poleAngleSum ?? data.details.poleAngleSum ?? 0
    const zeroAngleSum = pointResult.zeroAngleSum ?? data.details.zeroAngleSum ?? 0
    const mainAngle = -pointResult.angle
    const normalizedAngle = ((mainAngle % 360) + 360) % 360

    return (
      <div className="calculation-block" key={`point-angle-${index}`}>
        <Formula>{`${pointLabel}=${complexLatex(pointValue)}`}</Formula>
        {pointDetailsForPoint.poles.map((term) => <div className="term-line" key={`p-${index}-${term.index}`}><InlineMath math={`${pointLabel}-p_${term.index}=${complexLatex(term.difference)}\\quad\\Rightarrow\\quad\\angle=${formatNumber(term.angle)}^\\circ`} /></div>)}
        {pointDetailsForPoint.zeros.map((term) => <div className="term-line" key={`z-${index}-${term.index}`}><InlineMath math={`${pointLabel}-z_${term.index}=${complexLatex(term.difference)}\\quad\\Rightarrow\\quad\\angle=${formatNumber(term.angle)}^\\circ`} /></div>)}
        <Formula>{`\\sum\\theta_i=\\sum\\angle(${pointLabel}-p_i)=${formatNumber(poleAngleSum)}^\\circ\\qquad\\sum\\phi_j=\\sum\\angle(${pointLabel}-z_j)=${formatNumber(zeroAngleSum)}^\\circ`}</Formula>
        <Formula>{`\\Delta\\theta=\\sum\\theta_i-\\sum\\phi_j=${formatNumber(poleAngleSum)}-${formatNumber(zeroAngleSum)}=${formatNumber(mainAngle)}^\\circ`}</Formula>
        <Formula>{`\\Delta\\theta_{\\mathrm{norm}}=${formatNumber(normalizedAngle)}^\\circ`}</Formula>
        <div className={pointResult.belongs ? 'answer good' : 'answer bad'}>
          <InlineMath math={pointResult.belongs ? '\\text{Ponto pertencente ao LGR}' : '\\text{Ponto fora do LGR}'} />
          <InlineMath math={`\\qquad\\Delta\\theta_{\\mathrm{norm}}=${formatNumber(normalizedAngle)}^\\circ`} />
        </div>
      </div>
    )
  })
}

function PointModuleDetails({ pointValues, pointResults, pointDetailsList }) {
  return pointDetailsList.map((pointDetailsForPoint, index) => {
    const pointValue = pointValues[index] || pointValues[0]
    const pointResult = pointResults[index] || pointResults[0]
    const pointLabel = pointValues.length > 1 ? `s_0^{(${index + 1})}` : 's_0'

    return (
      <div className="calculation-block" key={`point-module-${index}`}>
        <Formula>{`${pointLabel}=${complexLatex(pointValue)}`}</Formula>
        {pointDetailsForPoint.poles.map((term) => <div className="term-line" key={`p-${index}-${term.index}`}><InlineMath math={`${pointLabel}-p_${term.index}=${complexLatex(term.difference)}\\quad\\Rightarrow\\quad|${pointLabel}-p_${term.index}|=${formatNumber(term.distance)}`} /></div>)}
        {pointDetailsForPoint.zeros.map((term) => <div className="term-line" key={`z-${index}-${term.index}`}><InlineMath math={`${pointLabel}-z_${term.index}=${complexLatex(term.difference)}\\quad\\Rightarrow\\quad|${pointLabel}-z_${term.index}|=${formatNumber(term.distance)}`} /></div>)}
        <Formula>{`\\prod_i|${pointLabel}-p_i|=${formatNumber(pointDetailsForPoint.poleProduct)}`}</Formula>
        <Formula>{`\\prod_j|${pointLabel}-z_j|=${formatNumber(pointDetailsForPoint.zeroProduct)}`}</Formula>
        <Formula>{`K=\\frac{${formatNumber(pointDetailsForPoint.poleProduct)}}{${formatNumber(pointDetailsForPoint.zeroProduct)}}=${formatNumber(pointResult.gain)}`}</Formula>
      </div>
    )
  })
}

function StepsContent({ data }) {
  const details = data.details
  const calculations = data.stepCalculations || {}
  const realAxis = calculations.realAxis || []
  const breakaway = calculations.breakaway || { derivativeNumerator: details.dNumerator, derivativeDenominator: details.dDenominator, equation: [], candidates: [] }
  const jw = calculations.jw || { reDenominator: [], imDenominator: [], reNumerator: [], imNumerator: [], cross: [], candidates: [] }
  const angleDetails = calculations.angles || { departures: [], arrivals: [] }
  const pointDetails = calculations.point || { poles: [], zeros: [], poleProduct: 1, zeroProduct: 1, gain: data.point.gain }
  const pointValues = data.pointValues?.length ? data.pointValues : [data.pointValue]
  const pointResults = data.points?.length ? data.points : [data.point]
  const pointDetailsList = calculations.points?.length ? calculations.points : [pointDetails]
  const factorizedD = factorizedPolynomialLatex(data.denominator, data.poles)
  const factorizedN = factorizedPolynomialLatex(data.numerator, data.zeros)
  const roots = (values, prefix) => values.map((value, index) => <MathChip key={index} math={`${prefix ? `${prefix}_{${index + 1}}=` : ''}${complexLatex(value)}`} />)
  const sumReal = (values) => values.reduce((sum, value) => sum + Number(value.real), 0)
  const sumRealTerms = (values) => values.length ? values.map((value) => `(${formatNumber(value.real)})`).join('+') : '0'
  const status = (valid, good = 'válido', bad = 'descartado') => <span className={valid ? 'calculation-status good' : 'calculation-status bad'}>{valid ? good : bad}</span>

  return (
    <>
      <Step number={1} title="Montar a função de transferência e o polinômio característico">
        <p>Partimos dos blocos informados e calculamos todos os produtos antes de montar a equação característica.</p>
        <Formula>{`G(s)=K\\,\\frac{${polynomialLatex(details.nG)}}{${polynomialLatex(details.dG)}}`}</Formula>
        <Formula>{`H(s)=\\frac{${polynomialLatex(details.nH)}}{${polynomialLatex(details.dH)}}`}</Formula>
        <FormulaList formulas={[
          `G(s)H(s)=K\\,\\frac{N_G(s)N_H(s)}{D_G(s)D_H(s)}=K\\,\\frac{${polynomialLatex(data.numerator)}}{${polynomialLatex(data.denominator)}}=K\\,P(s)`,
          `N(s)=N_G(s)N_H(s)=(${polynomialLatex(details.nG)})(${polynomialLatex(details.nH)})=${polynomialLatex(data.numerator)}`,
          `D(s)=D_G(s)D_H(s)=(${polynomialLatex(details.dG)})(${polynomialLatex(details.dH)})=${polynomialLatex(data.denominator)}`,
        ]} />
        <p>Para realimentação negativa, os polos de malha fechada são encontrados fazendo o denominador igual a zero.</p>
        <Formula>{`1+K\\,L(s)=0`}</Formula>
        <Formula>{`P(s,K)=D(s)+K\\,N(s)`}</Formula>
        <Formula>{`P(s,K)=${polynomialLatex(data.denominator)}+K\\left(${polynomialLatex(data.numerator)}\\right)=0`}</Formula>
        <Formula>{`P(s,K)=D(s)+K\\,N(s)=0\\quad\\Longrightarrow\\quad P(s,K)=${factorizedD}+K\\left(${factorizedN}\\right)=0`}</Formula>
        <Formula>{`P(s,K)=a(K)\\prod_{i=1}^{n_p}\\left(s-s_i(K)\\right),\\qquad P(s_i(K),K)=0`}</Formula>
        <p>A forma fatorada do polinômio característico depende do valor de <InlineMath math="K" />. Para cada ganho, calculamos as raízes de <InlineMath math="P(s,K)" />; a forma fatorada parametrizada acima é a forma usada no LGR.</p>
      </Step>

      <Step number={2} title="Obter a forma fatorada de P(s)">
        <p>Agora fatoramos numerador e denominador de <InlineMath math="P(s)=N(s)/D(s)" /> pelas raízes calculadas.</p>
        <Formula>{`N(s)=${polynomialLatex(data.numerator)}= ${factorizedN}`}</Formula>
        <Formula>{`D(s)=${polynomialLatex(data.denominator)}= ${factorizedD}`}</Formula>
        <Formula>{`P(s)=\\frac{N(s)}{D(s)}=\\frac{${factorizedN}}{${factorizedD}}`}</Formula>
        <div className="root-line"><MathLabel>Zeros de N</MathLabel>{data.zeros.length ? roots(data.zeros, 'z') : <span className="muted">Nenhum zero finito.</span>}</div>
        <div className="root-line"><MathLabel>Polos de D</MathLabel>{roots(data.poles, 'p')}</div>
      </Step>

      <Step number={3} title="Polos e zeros no plano s">
        <p>Resolvemos os polinômios do numerador e do denominador e localizamos cada raiz no plano complexo.</p>
        <FormulaList formulas={[
          `${polynomialLatex(data.numerator)}=0\\Longrightarrow z_i`,
          `${polynomialLatex(data.denominator)}=0\\Longrightarrow p_i`,
        ]} />
        <div className="root-line"><MathLabel>Zeros</MathLabel>{data.zeros.length ? roots(data.zeros, 'z') : <span className="muted">Nenhum zero finito.</span>}</div>
        <div className="root-line"><MathLabel>Polos</MathLabel>{roots(data.poles, 'p')}</div>
        <div className="step-plot"><RootLocusPlot data={data} mode="poles" compact /></div>
      </Step>

      <Step number={4} title="Determinar os segmentos do eixo real">
        <p>Em cada intervalo, escolhemos um ponto de teste, contamos polos e zeros à direita e aplicamos a regra da quantidade ímpar.</p>
        <Formula>{`N_{\\mathrm{direita}}(s_t)=\\#\\{p_i,z_i:\\operatorname{Re}(p_i,z_i)>s_t\\}`}</Formula>
        <Formula>{`N_{\\mathrm{direita}}(s_t)\\equiv1\\pmod{2}\\Longrightarrow s_t\\in\\mathcal{L}`}</Formula>
        {realAxis.map((segment, index) => (
          <div className="calculation-row" key={index}>
            <InlineMath math={`I_${index + 1}=(${segment.from == null ? '-\\infty' : formatNumber(segment.from)},${formatNumber(segment.to)}]`} />
            <InlineMath math={`\\quad s_t=${formatNumber(segment.test)}`} />
            <InlineMath math={`\\quad N_{\\mathrm{direita}}=${segment.rightCount}`} />
            {status(segment.belongs, 'ímpar → pertence', 'par → não pertence')}
          </div>
        ))}
        <div className="answer">
          {data.realSegments.length
            ? data.realSegments.map((segment, index) => (
              <MathChip key={index} math={`\\text{ímpar}\\Longrightarrow\\left(${segment.from == null ? '-\\infty' : formatNumber(segment.from)},\\,${formatNumber(segment.to)}\\right]`} />
            ))
            : <span>Nenhum intervalo válido.</span>}
        </div>
        <div className="step-plot"><RootLocusPlot data={data} mode="real" compact /></div>
      </Step>

      <Step number={5} title="Calcular o número de ramos">
        <p>Cada ramo começa em um polo quando <InlineMath math="K=0" /> e termina em um zero quando <InlineMath math="K\to\infty" /> ou segue para o infinito.</p>
        <Formula>{`n_p=${data.poles.length},\\qquad n_z=${data.zeros.length}`}</Formula>
        <Formula>{`L=\\max(n_p,n_z)=\\max(${data.poles.length},${data.zeros.length})=${Math.max(data.poles.length, data.zeros.length)}\\;\\text{ramos}`}</Formula>
      </Step>

      <Step number={6} title="Verificar simetria">
        <p>Como os coeficientes de <InlineMath math="P(s,K)" /> são reais para <InlineMath math="K\in\mathbb{R}" />, toda raiz complexa tem sua conjugada.</p>
        <Formula>{`P(s,K)\\in\\mathbb{R}[s]\\Longrightarrow s_i=\\sigma+j\\omega\\;\\Rightarrow\\;s_i^*=\\sigma-j\\omega`}</Formula>
        <Formula>{`\\mathcal{L}\\text{ é simétrico em relação ao eixo real}`}</Formula>
      </Step>

      <Step number={7} title="Encontrar centroide e assíntotas">
        <p>As assíntotas descrevem os ramos que seguem para o infinito. Primeiro calculamos a quantidade de assíntotas e o centroide.</p>
        {data.centroid == null ? (
          <Formula>{`n_a=n_p-n_z=${data.poles.length}-${data.zeros.length}=0\\Longrightarrow\\text{não há assíntotas}`}</Formula>
        ) : (
          <>
            <Formula>{`n_a=n_p-n_z=${data.poles.length}-${data.zeros.length}=${data.poles.length - data.zeros.length}`}</Formula>
            <Formula>{`\\sum\\operatorname{Re}(p_i)=${sumRealTerms(data.poles)}=${formatNumber(sumReal(data.poles))},\\qquad\\sum\\operatorname{Re}(z_i)=${sumRealTerms(data.zeros)}=${formatNumber(sumReal(data.zeros))}`}</Formula>
            <Formula>{`\\sigma_a=\\frac{\\sum p_i-\\sum z_i}{n_a}=\\frac{${formatNumber(sumReal(data.poles))}-${formatNumber(sumReal(data.zeros))}}{${data.poles.length - data.zeros.length}}=${formatNumber(data.centroid)}`}</Formula>
            <Formula>{`\\phi_q=\\frac{(2q+1)180^\\circ}{n_a}\\qquad q=0,1,\\ldots,n_a-1`}</Formula>
            <FormulaList formulas={data.asymptoteAngles.map((angle, index) => `\\phi_${index}=\\frac{(2\\cdot${index}+1)180^\\circ}{${data.poles.length - data.zeros.length}}=${formatNumber(angle)}^\\circ`)} />
            <div className="answer">
              {data.asymptoteAngles.map((angle, index) => <MathChip key={index} math={`\\phi_{${index}}=${formatNumber(angle)}^\\circ`} />)}
            </div>
            <div className="step-plot"><RootLocusPlot data={data} mode="asymptotes" compact /></div>
          </>
        )}
      </Step>

      <Step number={8} title="Localizar pontos de breakaway / break-in">
        <p>Isolamos <InlineMath math="K(s)" />, derivamos e resolvemos a equação resultante. Em seguida, testamos cada candidato no eixo real e no ganho positivo.</p>
        <Formula>{`P(s,K)=0\\Longrightarrow K(s)=-\\frac{D(s)}{N(s)}`}</Formula>
        <Formula>{`\\frac{dK}{ds}=0\\Longrightarrow N(s)D'(s)-D(s)N'(s)=0`}</Formula>
        <Formula>{`N(s)=${polynomialLatex(data.numerator)}\\qquad D(s)=${polynomialLatex(data.denominator)}`}</Formula>
        <Formula>{`N'(s)=${polynomialLatex(breakaway.derivativeNumerator)}`}</Formula>
        <Formula>{`D'(s)=${polynomialLatex(breakaway.derivativeDenominator)}`}</Formula>
        <Formula>{`${polynomialLatex(breakaway.equation)}=0`}</Formula>
        {breakaway.candidates.map((item, index) => (
          <div className="calculation-row" key={index}>
            <InlineMath math={`s_${index + 1}=${complexLatex(item.root)}`} />
            {item.gain ? <InlineMath math={`\\quad K(s_${index + 1})=${complexLatex(item.gain)}`} /> : <InlineMath math="\\quad K\\;\\text{indefinido}" />}
            {item.realAxis && <InlineMath math={`\\quad N_{\\mathrm{direita}}=${item.rightCount}`} />}
            {status(item.valid)}
          </div>
        ))}
        <div className="answer">
          {data.breakaway.length
            ? data.breakaway.map((item, index) => <MathChip key={index} math={`s=${complexLatex(item.point)}\\qquad K=${formatNumber(item.gain)}`} />)
            : <span>Nenhum ponto válido encontrado.</span>}
        </div>
        <div className="step-plot"><RootLocusPlot data={data} mode="breakaway" compact /></div>
      </Step>

      <Step number={9} title="Aplicar Routh-Hurwitz e encontrar o cruzamento jω">
        <p>Construímos a tabela de Routh a partir de <InlineMath math="P(s,K)" />. Para estabilidade, os elementos da primeira coluna devem manter o mesmo sinal.</p>
        <Formula>{`P(s,K)=${polynomialLatex(data.denominator)}+K\\left(${polynomialLatex(data.numerator)}\\right)=0\\qquad K>0`}</Formula>
        <RouthTable data={data} />
        <p>Condições obtidas da primeira coluna:</p>
        <FormulaList formulas={(data.routh.conditions || data.routh.rows.map((row, index) => ({ power: data.routh.powers[index], expression: row[0] || '0', condition: null }))).map((item) => `s^{${item.power}}:\\quad ${item.expression}>0${item.condition ? `\\;\\Longrightarrow\\;${item.condition}` : ''}`)} />
        {(data.routh.criticalGains || []).map((gain, index) => <Formula key={index}>{`K_{\\mathrm{crit}}=${formatNumber(gain)}`}</Formula>)}
        <p>Para o cruzamento com o eixo imaginário, substituímos <InlineMath math="s=j\\omega" /> e separamos as partes real e imaginária.</p>
        <Formula>{`D(j\\omega)=D_R(\\omega)+jD_I(\\omega),\\qquad N(j\\omega)=N_R(\\omega)+jN_I(\\omega)`}</Formula>
        <FormulaList formulas={[
          `D_R(\\omega)=${polynomialLatex(jw.reDenominator, '\\omega')}`,
          `D_I(\\omega)=${polynomialLatex(jw.imDenominator, '\\omega')}`,
          `N_R(\\omega)=${polynomialLatex(jw.reNumerator, '\\omega')}`,
          `N_I(\\omega)=${polynomialLatex(jw.imNumerator, '\\omega')}`,
          `D_R(\\omega)N_I(\\omega)-D_I(\\omega)N_R(\\omega)=0\\Longrightarrow ${polynomialLatex(jw.cross, '\\omega')}=0`,
        ]} />
        {jw.candidates.map((item, index) => (
          <div className="calculation-row" key={index}>
            {item.omega != null
              ? <InlineMath math={`\\omega_${index + 1}=${formatNumber(item.omega)}`} />
              : <InlineMath math={`\\omega_${index + 1}=${complexLatex(item.root)}`} />}
            {item.omega != null && <InlineMath math={`\\quad D_R=${formatNumber(item.reD)},D_I=${formatNumber(item.imD)},N_R=${formatNumber(item.reN)},N_I=${formatNumber(item.imN)}`} />}
            {item.gain != null && <InlineMath math={`\\quad K=${formatNumber(item.gain)}`} />}
            {status(item.valid)}
          </div>
        ))}
        <div className="answer">
          {data.jwCrossings.length
            ? data.jwCrossings.map((item, index) => <MathChip key={index} math={`K=${formatNumber(item.gain)}\\qquad\\omega=${formatNumber(item.omega)}\\;\\mathrm{rad/s}`} />)
            : <span>Nenhum cruzamento positivo encontrado.</span>}
        </div>
        <div className="step-plot"><RootLocusPlot data={data} mode="jw" compact /></div>
      </Step>

      <Step number={10} title="Calcular ângulos de partida e chegada">
        <p>Aplicamos a condição de fase termo a termo nos polos e zeros complexos.</p>
        <Formula>{`\\theta_{d,k}=180^\\circ-\\sum_{j\\ne k}\\angle(p_k-p_j)+\\sum_j\\angle(p_k-z_j)`}</Formula>
        {angleDetails.departures.length ? angleDetails.departures.map((item, index) => (
          <div className="calculation-block" key={index}>
            <Formula>{`p_k=${complexLatex(item.point)}\\qquad\\sum\\angle(p_k-p_j)=${formatNumber(item.poleSum)}^\\circ\\qquad\\sum\\angle(p_k-z_j)=${formatNumber(item.zeroSum)}^\\circ`}</Formula>
            {item.poleTerms.map((term, termIndex) => <div className="term-line" key={`p-${termIndex}`}><InlineMath math={`\\angle(${complexLatex(term.difference)})=${formatNumber(term.angle)}^\\circ`} /></div>)}
            {item.zeroTerms.map((term, termIndex) => <div className="term-line" key={`z-${termIndex}`}><InlineMath math={`\\angle(${complexLatex(term.difference)})=${formatNumber(term.angle)}^\\circ`} /></div>)}
            <div className="answer"><MathChip math={`\\theta_d=${formatNumber((item.angle + 360) % 360)}^\\circ\\;\\left(\\equiv${formatNumber(item.angle)}^\\circ\\right)`} /></div>
          </div>
        )) : <span className="muted">Nenhum polo complexo.</span>}
        <Formula>{`\\theta_{a,k}=180^\\circ+\\sum_j\\angle(z_k-p_j)-\\sum_{j\\ne k}\\angle(z_k-z_j)`}</Formula>
        {angleDetails.arrivals.length ? angleDetails.arrivals.map((item, index) => (
          <div className="calculation-block" key={index}>
            <Formula>{`z_k=${complexLatex(item.point)}\\qquad\\sum\\angle(z_k-z_j)=${formatNumber(item.zeroSum)}^\\circ\\qquad\\sum\\angle(z_k-p_i)=${formatNumber(item.poleSum)}^\\circ`}</Formula>
            {item.zeroTerms.map((term, termIndex) => <div className="term-line" key={`z-${termIndex}`}><InlineMath math={`\\angle(${complexLatex(term.difference)})=${formatNumber(term.angle)}^\\circ`} /></div>)}
            {item.poleTerms.map((term, termIndex) => <div className="term-line" key={`p-${termIndex}`}><InlineMath math={`\\angle(${complexLatex(term.difference)})=${formatNumber(term.angle)}^\\circ`} /></div>)}
            <div className="answer"><MathChip math={`\\theta_a=${formatNumber((item.angle + 360) % 360)}^\\circ\\;\\left(\\equiv${formatNumber(item.angle)}^\\circ\\right)`} /></div>
          </div>
        )) : <span className="muted">Nenhum zero complexo.</span>}
        <div className="step-plot"><RootLocusPlot data={data} mode="angles" compact /></div>
      </Step>

      <Step number={11} title="Aplicar o critério de ângulo">
        <p>{pointValues.length > 1 ? 'Para cada ponto conjugado, somamos os ângulos formados com todos os polos e zeros.' : 'Para o ponto de teste, somamos os ângulos formados com todos os polos e zeros.'}</p>
        <Formula>{`\\sum_i\\angle(s_0-z_i)-\\sum_i\\angle(s_0-p_i)=\\pm180^\\circ(2q+1)`}</Formula>
        <PointAngleDetails data={data} pointValues={pointValues} pointResults={pointResults} pointDetailsList={pointDetailsList} />
        <div className="step-plot"><RootLocusPlot data={data} mode="point" compact /></div>
      </Step>

      <Step number={12} title="Aplicar o critério de módulo">
        <p>{pointValues.length > 1 ? 'Calculamos cada diferença, distância, produto e ganho para os dois pontos conjugados.' : 'Calculamos cada diferença, distância, produto e finalmente o ganho que faria o ponto satisfazer o critério de módulo.'}</p>
        <Formula>{`K=\\frac{\\prod_i|s_0-p_i|}{\\prod_j|s_0-z_j|}`}</Formula>
        <PointModuleDetails pointValues={pointValues} pointResults={pointResults} pointDetailsList={pointDetailsList} />
      </Step>
    </>
  )
}

export default function StepCarousel({ data }) {
  const [current, setCurrent] = useState(0)
  const startX = useRef(null)

  useEffect(() => setCurrent(0), [data])

  const totalSteps = 12
  const go = (next) => setCurrent(Math.max(0, Math.min(totalSteps - 1, next)))
  const onPointerDown = (event) => { startX.current = event.clientX }
  const onPointerUp = (event) => {
    if (startX.current == null) return
    const distance = event.clientX - startX.current
    if (Math.abs(distance) > 45) go(current + (distance < 0 ? 1 : -1))
    startX.current = null
  }

  return (
    <section className="steps" aria-labelledby="steps-title">
      <div className="steps-heading">
        <div>
          <p className="eyebrow">RESOLUÇÃO GUIADA</p>
          <h3 id="steps-title">Os 12 passos da análise</h3>
        </div>
        <span className="muted">Arraste para o lado ou use os controles</span>
      </div>
      <div
        className="carousel-window"
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onPointerCancel={() => { startX.current = null }}
      >
        <div className="steps-track" style={{ transform: `translateX(-${current * (100 / totalSteps)}%)` }}>
          <StepsContent data={data} />
        </div>
      </div>
      <div className="carousel-controls">
        <button className="carousel-arrow" onClick={() => go(current - 1)} disabled={current === 0} aria-label="Passo anterior">‹</button>
        <div className="carousel-dots" aria-label="Selecionar passo">
          {Array.from({ length: totalSteps }, (_, index) => <button key={index} className={index === current ? 'active' : ''} onClick={() => go(index)} aria-label={`Ir para o passo ${index + 1}`} aria-current={index === current ? 'step' : undefined} />)}
        </div>
        <span className="step-counter">{String(current + 1).padStart(2, '0')} / {totalSteps}</span>
        <button className="carousel-arrow" onClick={() => go(current + 1)} disabled={current === totalSteps - 1} aria-label="Próximo passo">›</button>
      </div>
    </section>
  )
}
