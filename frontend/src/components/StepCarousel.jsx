import { useEffect, useRef, useState } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import { complexLatex, factorizedPolynomialLatex, formatNumber, polynomialLatex } from '../utils/format'

function Formula({ children, className = '' }) {
  return (
    <div className={`formula ${className}`.trim()}>
      <BlockMath math={children} />
    </div>
  )
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

function StepsContent({ data }) {
  const details = data.details
  const factorizedDenominator = factorizedPolynomialLatex(data.denominator, data.poles)
  const factorizedNumerator = factorizedPolynomialLatex(data.numerator, data.zeros)
  const gainFactor = factorizedNumerator === '1' ? 'K' : `K\\,\\left(${factorizedNumerator}\\right)`
  const roots = (values) => values.map((value, index) => (
    <MathChip key={index} math={complexLatex(value)} />
  ))

  return (
    <>
      <Step number={1} title="Montar a função de transferência e o polinômio característico">
        <p>Partimos dos dados informados e multiplicamos numeradores e denominadores.</p>
        <Formula>{`G(s)=\\frac{${polynomialLatex(details.nG)}}{${polynomialLatex(details.dG)}}`}</Formula>
        <Formula>{`H(s)=\\frac{${polynomialLatex(details.nH)}}{${polynomialLatex(details.dH)}}`}</Formula>
        <Formula>{`\\begin{aligned}N(s)&=N_G(s)N_H(s)\\\\&=${polynomialLatex(details.nG)}\\cdot${polynomialLatex(details.nH)}\\\\&=${polynomialLatex(data.numerator)}\\end{aligned}`}</Formula>
        <Formula>{`\\begin{aligned}D(s)&=D_G(s)D_H(s)\\\\&=${polynomialLatex(details.dG)}\\cdot${polynomialLatex(details.dH)}\\\\&=${polynomialLatex(data.denominator)}\\end{aligned}`}</Formula>
        <p>Para a realimentação negativa, isolamos a equação que define os polos do sistema em malha fechada.</p>
        <Formula>{`1+K\\,L(s)=0`}</Formula>
        <Formula>{`\\begin{aligned}P(s,K)&=D(s)+K\\,N(s)\\\\&=${polynomialLatex(data.denominator)}+K\\left(${polynomialLatex(data.numerator)}\\right)=0\\end{aligned}`}</Formula>
        <Formula>{`\\begin{aligned}P(s,K)&=D(s)+K\\,N(s)\\\\&=${factorizedDenominator}+${gainFactor}=0\\end{aligned}`}</Formula>
      </Step>

      <Step number={2} title="Identificar polos e zeros">
        <p>Resolvemos separadamente o numerador e o denominador da função de malha aberta.</p>
        <Formula>{`${polynomialLatex(data.numerator)}=0\\Longrightarrow\\text{zeros}`}</Formula>
        <div className="root-line"><MathLabel>Zeros</MathLabel>{data.zeros.length ? roots(data.zeros) : <span className="muted">Nenhum zero finito.</span>}</div>
        <Formula>{`${polynomialLatex(data.denominator)}=0\\Longrightarrow\\text{polos}`}</Formula>
        <div className="root-line"><MathLabel>Polos</MathLabel>{roots(data.poles)}</div>
      </Step>

      <Step number={3} title="Determinar os segmentos do eixo real">
        <p>Em cada intervalo, contamos os polos e zeros à direita. O segmento pertence ao LGR quando essa quantidade é ímpar.</p>
        <Formula>{`N_{\\mathrm{direita}}(s)\\equiv1\\pmod{2}\\Longrightarrow s\\in\\mathcal{L}`}</Formula>
        <div className="answer">
          {data.realSegments.length
            ? data.realSegments.map((segment, index) => (
              <MathChip key={index} math={`\\text{ímpar}\\Longrightarrow\\left(${segment.from == null ? '-\\infty' : formatNumber(segment.from)},\\,${formatNumber(segment.to)}\\right]`} />
            ))
            : <span>Nenhum intervalo válido.</span>}
        </div>
      </Step>

      <Step number={4} title="Verificar simetria">
        <p>Como os coeficientes do polinômio característico são reais, as raízes complexas aparecem em pares conjugados.</p>
        <Formula>{`s\\in\\mathcal{L}\\Longrightarrow s^*\\in\\mathcal{L}\\qquad\\mathcal{L}\\text{ é simétrico em relação ao eixo real}`}</Formula>
      </Step>

      <Step number={5} title="Calcular o número de ramos">
        <p>Cada ramo começa em um polo e termina em um zero ou no infinito.</p>
        <Formula>{`L=\\max\\left(n_p,n_z\\right)=\\max\\left(${data.poles.length},${data.zeros.length}\\right)=${Math.max(data.poles.length, data.zeros.length)}\\;\\text{ramos}`}</Formula>
      </Step>

      <Step number={6} title="Encontrar centroide e assíntotas">
        <p>As assíntotas descrevem o comportamento dos ramos que seguem para o infinito.</p>
        {data.centroid == null ? (
          <Formula>{`n_a=n_p-n_z=${data.poles.length}-${data.zeros.length}=0\\Longrightarrow\\text{não há assíntotas}`}</Formula>
        ) : (
          <>
            <Formula>{`n_a=n_p-n_z=${data.poles.length}-${data.zeros.length}\\qquad\\sigma_a=\\frac{\\sum p_i-\\sum z_i}{n_a}=${formatNumber(data.centroid)}`}</Formula>
            <Formula>{`\\phi_q=\\frac{(2q+1)180^\\circ}{n_a}\\qquad q=0,1,\\ldots,n_a-1`}</Formula>
            <div className="answer">
              {data.asymptoteAngles.map((angle, index) => <MathChip key={index} math={`\\phi_{${index}}=${formatNumber(angle)}^\\circ`} />)}
            </div>
          </>
        )}
      </Step>

      <Step number={7} title="Localizar pontos de breakaway / break-in">
        <p>Isolamos o ganho e procuramos os pontos em que sua derivada é nula.</p>
        <Formula>{`K(s)=-\\frac{D(s)}{N(s)}\\qquad\\frac{dK}{ds}=0`}</Formula>
        <Formula>{`D'(s)N(s)-D(s)N'(s)=0`}</Formula>
        <Formula>{`N'(s)=${polynomialLatex(details.dNumerator)}`}</Formula>
        <Formula>{`D'(s)=${polynomialLatex(details.dDenominator)}`}</Formula>
        <div className="answer">
          {data.breakaway.length
            ? data.breakaway.map((item, index) => <MathChip key={index} math={`s=${complexLatex(item.point)}\\qquad K=${formatNumber(item.gain)}`} />)
            : <span>Nenhum ponto válido encontrado.</span>}
        </div>
      </Step>

      <Step number={8} title="Aplicar o critério de estabilidade de Routh-Hurwitz">
        <p>Construímos a tabela a partir da equação característica. Para estabilidade, os elementos da primeira coluna devem ser positivos.</p>
        <Formula>{`D(s)+K\\,N(s)=0\\qquad K>0`}</Formula>
        <RouthTable data={data} />
        <div className="answer">
          {data.jwCrossings.length
            ? data.jwCrossings.map((item, index) => <MathChip key={index} math={`K=${formatNumber(item.gain)}\\qquad\\omega=${formatNumber(item.omega)}\\;\\mathrm{rad/s}`} />)
            : <span>Nenhum cruzamento positivo encontrado.</span>}
        </div>
      </Step>

      <Step number={9} title="Calcular ângulos de partida e chegada">
        <p>Aplicamos a condição de fase nos polos e zeros complexos.</p>
        <Formula>{`\\theta_{d,k}=180^\\circ-\\sum_{j\\ne k}\\angle(p_k-p_j)+\\sum_j\\angle(p_k-z_j)`}</Formula>
        <div className="root-line"><MathLabel>Partida</MathLabel>{data.departureAngles.length ? data.departureAngles.map((item, index) => <MathChip key={index} math={`${complexLatex(item.point)}\\longrightarrow${formatNumber(item.angle)}^\\circ`} />) : <span className="muted">Nenhum polo complexo.</span>}</div>
        <Formula>{`\\theta_{a,k}=180^\\circ+\\sum_j\\angle(z_k-p_j)-\\sum_{j\\ne k}\\angle(z_k-z_j)`}</Formula>
        <div className="root-line"><MathLabel>Chegada</MathLabel>{data.arrivalAngles.length ? data.arrivalAngles.map((item, index) => <MathChip key={index} math={`${complexLatex(item.point)}\\longrightarrow${formatNumber(item.angle)}^\\circ`} />) : <span className="muted">Nenhum zero complexo.</span>}</div>
      </Step>

      <Step number={10} title="Traçar o lugar geométrico das raízes">
        <p>Para cada valor de ganho, resolvemos a equação característica e conectamos as raízes correspondentes.</p>
        <Formula>{`D(s)+K\\,N(s)=0\\qquad K\\geq0`}</Formula>
        <Formula>{`\\mathcal{L}=\\left\\{s\\in\\mathbb{C}:D(s)+K\\,N(s)=0,\\;K\\geq0\\right\\}`}</Formula>
        <div className="mini-stat"><b>{data.lgr.length}</b> valores de <InlineMath math="K" /> calculados.</div>
      </Step>

      <Step number={11} title="Testar o critério de ângulo">
        <p>Para o ponto de teste, somamos os ângulos formados com todos os polos e zeros.</p>
        <Formula>{`s_0=${complexLatex(data.pointValue)}`}</Formula>
        <div className="root-line"><MathLabel>Polos</MathLabel><RootChips values={data.point.pole_angles.map((angle) => ({ real: angle, imag: 0 }))} prefix="\\theta" /></div>
        <div className="root-line"><MathLabel>Zeros</MathLabel>{data.point.zero_angles.length ? <RootChips values={data.point.zero_angles.map((angle) => ({ real: angle, imag: 0 }))} prefix="\\varphi" /> : <span className="muted">Soma dos ângulos: 0°.</span>}</div>
        <Formula>{`\\Delta\\theta=\\sum\\angle(s_0-z_i)-\\sum\\angle(s_0-p_i)=${formatNumber(data.point.angle)}^\\circ`}</Formula>
        <div className={data.point.belongs ? 'answer good' : 'answer bad'}>
          <InlineMath math={data.point.belongs ? '\\text{Ponto pertencente ao LGR}' : '\\text{Ponto fora do LGR}'} />
          <InlineMath math={`\\qquad\\Delta\\theta_{\\mathrm{norm}}=${formatNumber(data.point.normalized_angle)}^\\circ`} />
        </div>
      </Step>

      <Step number={12} title="Aplicar o critério de módulo">
        <p>Calculamos cada distância entre o ponto de teste, os polos e os zeros.</p>
        <div className="root-line"><MathLabel>Polos</MathLabel>{details.poleDistances.map((distance, index) => <MathChip key={index} math={`\\left|s_0-p_{${index + 1}}\\right|=${formatNumber(distance)}`} />)}</div>
        <div className="root-line"><MathLabel>Zeros</MathLabel>{details.zeroDistances.length ? details.zeroDistances.map((distance, index) => <MathChip key={index} math={`\\left|s_0-z_{${index + 1}}\\right|=${formatNumber(distance)}`} />) : <span className="muted">Produto dos zeros: 1.</span>}</div>
        <Formula>{`K=\\frac{${details.poleDistances.map(formatNumber).join('\\cdot')}}{${details.zeroDistances.length ? details.zeroDistances.map(formatNumber).join('\\cdot') : '1'}}=${formatNumber(data.point.gain)}`}</Formula>
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
