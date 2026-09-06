import numpy as np
import sympy as sp


def parse_coefs(value):
    if isinstance(value, list):
        try:
            result = np.array([float(x) for x in value], dtype=float)
        except (TypeError, ValueError):
            return None
    else:
        try:
            result = np.array([float(x) for x in str(value).split()], dtype=float)
        except (TypeError, ValueError):
            return None
    return result if len(result) and np.any(result) else None


def fazer_passo1(n_g, d_g, n_h, d_h):
    return np.convolve(n_g, n_h), np.convolve(d_g, d_h)


def derivada_coeficientes(values):
    """Retorna os coeficientes da derivada, inclusive para polinômios constantes."""
    derivative = np.polyder(values)
    return derivative if len(derivative) else np.array([0.0])


def complex_json(value):
    return {"real": round(float(np.real(value)), 8), "imag": round(float(np.imag(value)), 8)}


def roots_json(values):
    return [complex_json(value) for value in values]


def achar_segmentos_eixo_real(zeros, polos):
    real_values = [float(x.real) for x in list(polos) + list(zeros) if abs(x.imag) < 1e-8]
    if not real_values:
        return []
    boundaries = sorted(set(round(x, 8) for x in real_values), reverse=True)
    segments = []
    for left, right in zip(boundaries[1:], boundaries[:-1]):
        middle = (left + right) / 2
        if sum(x > middle + 1e-10 for x in real_values) % 2:
            segments.append({"from": left, "to": right})
    if len(real_values) % 2:
        segments.append({"from": None, "to": boundaries[-1]})
    return segments


def calcular_assintotas(zeros, polos):
    difference = len(polos) - len(zeros)
    if difference <= 0:
        return None, []
    centroid = (np.sum(polos).real - np.sum(zeros).real) / difference
    angles = [(2 * q + 1) * 180 / difference for q in range(difference)]
    return float(centroid), angles


def achar_breakaway(num, den, polos, zeros):
    d_num = derivada_coeficientes(num)
    d_den = derivada_coeficientes(den)
    equation = np.polysub(np.convolve(num, d_den), np.convolve(den, d_num))
    real_pz = [x.real for x in list(polos) + list(zeros) if abs(x.imag) < 1e-8]
    result = []
    for root in np.roots(equation):
        denominator = np.polyval(num, root)
        if abs(denominator) < 1e-12:
            continue
        gain = -np.polyval(den, root) / denominator
        if abs(root.imag) < 1e-6:
            valid_segment = sum(x > root.real + 1e-10 for x in real_pz) % 2 == 1
            if valid_segment and gain.real > 0:
                result.append({"point": complex_json(root), "gain": float(gain.real)})
        elif abs(gain.imag) < 1e-6 and gain.real > 0:
            result.append({"point": complex_json(root), "gain": float(gain.real)})
    return result


def separar_jw(coefs):
    degree, real, imag = len(coefs) - 1, {}, {}
    for index, coefficient in enumerate(coefs):
        power = degree - index
        remainder = power % 4
        target = real if remainder in (0, 2) else imag
        target[power] = target.get(power, 0) + (coefficient if remainder in (0, 1) else -coefficient)
    def build(values):
        if not values:
            return np.array([0.0])
        highest = max(values)
        output = np.zeros(highest + 1)
        for power, coefficient in values.items():
            output[highest - power] = coefficient
        return output
    return build(real), build(imag)


def cruzamento_jw(den, num):
    re_d, im_d = separar_jw(den)
    re_n, im_n = separar_jw(num)
    cross = np.polysub(np.convolve(re_d, im_n), np.convolve(im_d, re_n))
    while len(cross) > 1 and abs(cross[0]) < 1e-12:
        cross = cross[1:]
    crossings = []
    for root in np.roots(cross) if len(cross) > 1 else []:
        if abs(root.imag) > 1e-6 or root.real < 1e-8:
            continue
        omega = root.real
        im_n_value, im_d_value = np.polyval(im_n, omega), np.polyval(im_d, omega)
        re_n_value, re_d_value = np.polyval(re_n, omega), np.polyval(re_d, omega)
        gain = -im_d_value / im_n_value if abs(im_n_value) > 1e-12 else -re_d_value / re_n_value
        if gain > 1e-10 and not any(abs(gain - x["gain"]) < 1e-4 for x in crossings):
            crossings.append({"gain": float(gain), "omega": float(omega)})
    return crossings


def ordenar_raizes(previous, current):
    output, used = np.zeros(len(current), dtype=complex), set()
    for i in range(len(current)):
        candidates = [(abs(previous[i] - value), j) for j, value in enumerate(current) if j not in used]
        _, index = min(candidates)
        output[i], used = current[index], used | {index}
    return output


def calcular_lgr(num, den):
    order = len(den) - 1
    max_gain = 1000.0
    for gain in (100, 500, 1000, 5000):
        if np.max(np.abs(np.roots(np.polyadd(den, gain * num)))) > 50:
            max_gain = float(gain)
            break
    gains = np.unique(np.concatenate((np.linspace(0, .1, 180), np.logspace(-1, np.log10(max_gain), 900))))
    branches = np.zeros((len(gains), order), dtype=complex)
    for i, gain in enumerate(gains):
        roots = np.roots(np.polyadd(den, gain * num))
        branches[i] = ordenar_raizes(branches[i - 1], roots) if i else roots
    return gains, branches


def testar_ponto(point, zeros, poles):
    pole_angles = [np.degrees(np.angle(point - p)) for p in poles]
    zero_angles = [np.degrees(np.angle(point - z)) for z in zeros]
    angle = sum(zero_angles) - sum(pole_angles)
    normalized = (angle + 180) % 360 - 180
    belongs = abs(abs(normalized) - 180) < 5
    gain = np.prod([abs(point - p) for p in poles]) / (np.prod([abs(point - z) for z in zeros]) if len(zeros) else 1)
    return {"angle": float(angle), "normalized_angle": float(normalized), "belongs": bool(belongs), "gain": float(gain),
            "pole_angles": [float(x) for x in pole_angles], "zero_angles": [float(x) for x in zero_angles]}


def fatorados(values, variable="s"):
    parts = []
    for value in values:
        if abs(value.imag) < 1e-8:
            sign = "-" if value.real >= 0 else "+"
            parts.append(f"({variable} {sign} {abs(value.real):.4g})")
        else:
            parts.append(f"({variable} - ({value.real:.4g} {'+' if value.imag >= 0 else '-'} {abs(value.imag):.4g}j))")
    return " ".join(parts) or "1"


def angulos_extremos(zeros, poles):
    departures, arrivals = [], []
    for pole in poles:
        if abs(pole.imag) < 1e-8:
            continue
        other_poles = [p for p in poles if p is not pole]
        total_poles = sum(np.degrees(np.angle(pole - p)) for p in other_poles)
        total_zeros = sum(np.degrees(np.angle(pole - z)) for z in zeros)
        angle = (180 - total_poles + total_zeros + 180) % 360 - 180
        departures.append({"point": complex_json(pole), "angle": float(angle)})
    for zero in zeros:
        if abs(zero.imag) < 1e-8:
            continue
        other_zeros = [z for z in zeros if z is not zero]
        total_zeros = sum(np.degrees(np.angle(zero - z)) for z in other_zeros)
        total_poles = sum(np.degrees(np.angle(zero - p)) for p in poles)
        angle = (180 + total_poles - total_zeros + 180) % 360 - 180
        arrivals.append({"point": complex_json(zero), "angle": float(angle)})
    return departures, arrivals


def tabela_routh(den, num):
    k = sp.Symbol('K')
    size = max(len(den), len(num))
    d, n = np.pad(den, (size-len(den), 0)), np.pad(num, (size-len(num), 0))
    coefficients = [sp.nsimplify(a) + k * sp.nsimplify(b) for a, b in zip(d, n)]
    degree, columns = len(coefficients)-1, (len(coefficients)+1)//2
    table = [[sp.S.Zero for _ in range(columns)] for _ in range(degree+1)]
    for j in range(columns):
        if 2*j < len(coefficients): table[0][j] = coefficients[2*j]
        if 2*j+1 < len(coefficients): table[1][j] = coefficients[2*j+1]
    for i in range(2, degree+1):
        pivot = table[i-1][0]
        if pivot == 0: continue
        for j in range(columns-1):
            table[i][j] = sp.factor((pivot*table[i-2][j+1] - table[i-2][0]*table[i-1][j+1])/pivot)
    def latex_cell(cell):
        return sp.latex(sp.factor(sp.simplify(cell)))

    return {
        "powers": list(range(degree, -1, -1)),
        "rows": [[latex_cell(cell) for cell in row] for row in table],
    }


def analyze(payload):
    values = [parse_coefs(payload.get(name, "")) for name in ("nG", "dG", "nH", "dH")]
    if any(value is None for value in values):
        raise ValueError("Todos os campos devem conter coeficientes numéricos separados por espaços.")
    n_g, d_g, n_h, d_h = values
    num, den = fazer_passo1(n_g, d_g, n_h, d_h)
    zeros, poles = np.roots(num), np.roots(den)
    gains, branches = calcular_lgr(num, den)
    point = complex(float(payload.get("pointReal", 0)), float(payload.get("pointImag", 0)))
    departures, arrivals = angulos_extremos(zeros, poles)
    centroid, asymptotes = calcular_assintotas(zeros, poles)
    details = {
        "nG": n_g.tolist(), "dG": d_g.tolist(), "nH": n_h.tolist(), "dH": d_h.tolist(),
        "dNumerator": derivada_coeficientes(num).tolist(), "dDenominator": derivada_coeficientes(den).tolist(),
        "poleDistances": [float(abs(point-p)) for p in poles], "zeroDistances": [float(abs(point-z)) for z in zeros],
        "poleAngleSum": float(sum(np.degrees(np.angle(point-p)) for p in poles)),
        "zeroAngleSum": float(sum(np.degrees(np.angle(point-z)) for z in zeros)),
    }
    return {"details": details, "numerator": num.tolist(), "denominator": den.tolist(), "zeros": roots_json(zeros), "poles": roots_json(poles),
            "realSegments": achar_segmentos_eixo_real(zeros, poles), "centroid": calcular_assintotas(zeros, poles)[0],
            "asymptoteAngles": asymptotes, "breakaway": achar_breakaway(num, den, poles, zeros),
            "jwCrossings": cruzamento_jw(den, num), "routh": tabela_routh(den, num), "pointValue": complex_json(point), "point": testar_ponto(point, zeros, poles),
            "departureAngles": departures, "arrivalAngles": arrivals,
            "factorizedNumerator": fatorados(zeros), "factorizedDenominator": fatorados(poles),
            "lgr": [{"gain": float(g), "roots": roots_json(row)} for g, row in zip(gains, branches)]}
