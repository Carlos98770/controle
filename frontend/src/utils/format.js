export const formatNumber = (value) => {
  const number = Number(value)
  if (Math.abs(number) < 0.0005) return '0'
  return number.toFixed(3).replace(/\.000$/, '')
}

export const complexLatex = (value) => {
  const real = formatNumber(value.real)
  const imag = Number(value.imag)
  if (Math.abs(imag) <= 0.001) return real

  const imaginary = `${formatNumber(Math.abs(imag))}\\,\\mathrm{j}`
  if (Math.abs(Number(value.real)) < 0.0005) return imag < 0 ? `-${imaginary}` : imaginary
  return `${real} ${imag < 0 ? '-' : '+'} ${imaginary}`
}

export const polynomialLatex = (values = []) =>
  values
    .map((coefficient, index) => {
      const power = values.length - index - 1
      const number = Number(coefficient)

      if (Math.abs(number) < 1e-10) return ''

      const sign = number < 0 ? '-' : '+'
      const absolute = Math.abs(number)
      const factor = power > 0 && Math.abs(absolute - 1) < 1e-10
        ? ''
        : formatNumber(absolute)
      const term = power === 0
        ? factor
        : `${factor}s${power === 1 ? '' : `^{${power}}`}`

      return `${index === 0 && number > 0 ? '' : ` ${sign} `}${term}`
    })
    .filter(Boolean)
    .join('') || '0'

export const factorizedPolynomialLatex = (values = [], roots = []) => {
  if (!values.length) return '0'

  const leading = Number(values[0])
  const coefficient = Math.abs(leading - 1) < 1e-10
    ? ''
    : Math.abs(leading + 1) < 1e-10
      ? '-'
      : formatNumber(leading)

  const factors = roots.map(({ real, imag }) => {
    const realValue = Number(real)
    const imagValue = Number(imag)

    if (Math.abs(imagValue) <= 0.001) {
      if (Math.abs(realValue) < 0.0005) return 's'
      return realValue > 0
        ? `\\left(s-${formatNumber(realValue)}\\right)`
        : `\\left(s+${formatNumber(Math.abs(realValue))}\\right)`
    }

    return `\\left(s-\\left(${complexLatex({ real: realValue, imag: imagValue })}\\right)\\right)`
  })

  return `${coefficient}${factors.join('\\,') || '1'}`
}
