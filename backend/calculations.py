import numpy as np
import sympy as sp
import re


_COMPLEX_NUMBER = r"[+-]?(?:\d+(?:[\.,]\d*)?|\.\d+)(?:e[+-]?\d+)?"


def _parse_real_text(value):
    """Converte um trecho numérico aceitando ponto ou vírgula decimal."""
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("O ponto de teste deve estar no formato 1 + 5j, 1 - 5j ou 1 +- 5j.") from None
    if not np.isfinite(number):
        raise ValueError("O ponto de teste deve conter números finitos.")
    return number


def _parse_single_complex(value):
    """Lê uma coordenada complexa sem usar eval/expressões arbitrárias."""
    text = str(value).strip().lower().replace("−", "-").replace(" ", "")
    text = text.replace(",", ".").replace("i", "j")
    if not text:
        raise ValueError("Informe o ponto de teste no formato 1 + 5j ou 1 +- 5j.")

    if text in {"j", "+j"}:
        return complex(0, 1)
    if text == "-j":
        return complex(0, -1)

    if "j" not in text:
        return complex(_parse_real_text(text), 0)

    if text.count("j") != 1 or not text.endswith("j"):
        raise ValueError("O ponto de teste deve estar no formato 1 + 5j, 1 - 5j ou 1 +- 5j.")
    without_j = text[:-1]
    if without_j in {"", "+", "-"}:
        return complex(0, 1 if without_j != "-" else -1)

    # O Python entende as formas normalizadas 1+5j, 1-5j e 5j, mas a
    # mensagem de erro precisa ser controlada para não vazar detalhes internos.
    if not re.fullmatch(rf"(?:{_COMPLEX_NUMBER}(?:[+-]{_COMPLEX_NUMBER})?|[+-]?{_COMPLEX_NUMBER})", without_j):
        raise ValueError("O ponto de teste deve estar no formato 1 + 5j, 1 - 5j ou 1 +- 5j.")
    try:
        result = complex(text)
    except ValueError:
        raise ValueError("O ponto de teste deve estar no formato 1 + 5j, 1 - 5j ou 1 +- 5j.") from None
    if not np.isfinite(result.real) or not np.isfinite(result.imag):
        raise ValueError("O ponto de teste deve conter números finitos.")
    return result


def parse_test_points(value):
    """Retorna um ponto ou o par conjugado indicado por `+-`/`±`.

    Exemplos aceitos: `1`, `1 + 5j`, `1 - 5j`, `1 +- 5j` e `1 ± 5j`.
    Para manter a API anterior, números reais também são aceitos diretamente.
    """
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = _parse_real_text(value)
        return [complex(number, 0)]
    if value is None:
        raise ValueError("Informe o ponto de teste no formato 1 + 5j ou 1 +- 5j.")

    text = str(value).strip().lower().replace("−", "-").replace(" ", "")
    text = text.replace(",", ".").replace("i", "j")
    marker = next((candidate for candidate in ("+/-", "±", "+-") if candidate in text), None)
    if marker is not None:
        left, right = text.split(marker, 1)
        if not right.endswith("j"):
            raise ValueError("Para indicar o conjugado, use o formato 1 +- 5j.")
        real = _parse_real_text(left)
        magnitude = abs(_parse_single_complex(right).imag)
        if magnitude < 1e-12:
            return [complex(real, 0)]
        return [complex(real, magnitude), complex(real, -magnitude)]

    return [_parse_single_complex(text)]


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
            "pole_angles": [float(x) for x in pole_angles], "zero_angles": [float(x) for x in zero_angles],
            "poleAngleSum": float(sum(pole_angles)), "zeroAngleSum": float(sum(zero_angles))}


def fatorados(values, variable="s", leading=1.0):
    parts = []
    for value in values:
        if abs(value.imag) < 1e-8:
            sign = "-" if value.real >= 0 else "+"
            parts.append(f"({variable} {sign} {abs(value.real):.4g})")
        else:
            parts.append(f"({variable} - ({value.real:.4g} {'+' if value.imag >= 0 else '-'} {abs(value.imag):.4g}j))")
    coefficient = ""
    if abs(leading - 1) >= 1e-10:
        coefficient = "-" if abs(leading + 1) < 1e-10 else f"{leading:.4g}"
    return f"{coefficient}{' '.join(parts) or '1'}"


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

    conditions = []
    critical_gains = set()
    for index, row in enumerate(table):
        first = sp.factor(sp.simplify(row[0]))
        if not first.has(k):
            continue
        try:
            solution = sp.solve_univariate_inequality(first > 0, k)
            condition = sp.latex(solution)
        except Exception:
            condition = None
        conditions.append({
            "power": degree - index,
            "expression": latex_cell(first),
            "condition": condition,
        })
        try:
            roots = sp.solve(sp.Eq(first, 0), k)
            for root in roots:
                if root.is_real and root.is_positive:
                    critical_gains.add(float(root))
        except Exception:
            pass

    return {
        "powers": list(range(degree, -1, -1)),
        "rows": [[latex_cell(cell) for cell in row] for row in table],
        "conditions": conditions,
        "criticalGains": sorted(critical_gains),
    }


def detalhes_segmentos_reais(zeros, polos):
    real_values = [float(value.real) for value in list(polos) + list(zeros) if abs(value.imag) < 1e-8]
    boundaries = sorted(set(round(value, 8) for value in real_values), reverse=True)
    intervals = []
    for left, right in zip(boundaries[1:], boundaries[:-1]):
        test = (left + right) / 2
        right_count = sum(value > test + 1e-10 for value in real_values)
        intervals.append({
            "from": left, "to": right, "test": test,
            "rightCount": int(right_count), "belongs": bool(right_count % 2),
        })
    if boundaries and len(real_values) % 2:
        test = boundaries[-1] - max(1.0, abs(boundaries[-1]) * 0.1)
        intervals.append({
            "from": None, "to": boundaries[-1], "test": test,
            "rightCount": int(len(real_values)), "belongs": True,
        })
    return intervals


def detalhes_breakaway(num, den, zeros, poles):
    d_num = derivada_coeficientes(num)
    d_den = derivada_coeficientes(den)
    equation = np.polysub(np.convolve(num, d_den), np.convolve(den, d_num))
    while len(equation) > 1 and abs(equation[0]) < 1e-12:
        equation = equation[1:]
    real_pz = [value.real for value in list(poles) + list(zeros) if abs(value.imag) < 1e-8]
    candidates = []
    for root in np.roots(equation) if len(equation) > 1 else []:
        denominator_value = np.polyval(num, root)
        gain = None if abs(denominator_value) < 1e-12 else -np.polyval(den, root) / denominator_value
        real_axis = bool(abs(root.imag) < 1e-6)
        right_count = int(sum(value > root.real + 1e-10 for value in real_pz)) if real_axis else None
        belongs = bool(real_axis and right_count % 2 == 1) if real_axis else False
        gain_real_positive = bool(gain is not None and abs(gain.imag) < 1e-6 and gain.real > 0)
        valid = bool((belongs if real_axis else gain_real_positive) and gain_real_positive)
        candidates.append({
            "root": complex_json(root),
            "gain": None if gain is None else complex_json(gain),
            "realAxis": real_axis,
            "rightCount": right_count,
            "belongs": belongs,
            "gainRealPositive": gain_real_positive,
            "valid": valid,
        })
    return {
        "derivativeNumerator": d_num.tolist(),
        "derivativeDenominator": d_den.tolist(),
        "equation": equation.tolist(),
        "candidates": candidates,
    }


def detalhes_jw(den, num):
    re_d, im_d = separar_jw(den)
    re_n, im_n = separar_jw(num)
    cross = np.polysub(np.convolve(re_d, im_n), np.convolve(im_d, re_n))
    while len(cross) > 1 and abs(cross[0]) < 1e-12:
        cross = cross[1:]
    candidates = []
    for root in np.roots(cross) if len(cross) > 1 else []:
        if abs(root.imag) > 1e-6:
            candidates.append({"root": complex_json(root), "valid": False})
            continue
        omega = float(root.real)
        im_n_value, im_d_value = np.polyval(im_n, omega), np.polyval(im_d, omega)
        re_n_value, re_d_value = np.polyval(re_n, omega), np.polyval(re_d, omega)
        gain = -im_d_value / im_n_value if abs(im_n_value) > 1e-12 else (
            -re_d_value / re_n_value if abs(re_n_value) > 1e-12 else np.nan
        )
        candidates.append({
            "root": complex_json(root), "omega": omega,
            "reD": float(re_d_value), "imD": float(im_d_value),
            "reN": float(re_n_value), "imN": float(im_n_value),
            "gain": float(gain) if np.isfinite(gain) else None,
            "valid": bool(omega >= 0 and np.isfinite(gain) and gain > 1e-10),
        })
    return {
        "reDenominator": re_d.tolist(), "imDenominator": im_d.tolist(),
        "reNumerator": re_n.tolist(), "imNumerator": im_n.tolist(),
        "cross": cross.tolist(), "candidates": candidates,
    }


def detalhes_angulos(zeros, poles):
    departures, arrivals = [], []
    for index, pole in enumerate(poles):
        if abs(pole.imag) < 1e-8:
            continue
        other_poles = [other for other_index, other in enumerate(poles) if other_index != index]
        pole_terms = [{"other": complex_json(other), "difference": complex_json(pole - other),
                       "angle": float(np.degrees(np.angle(pole - other)))} for other in other_poles]
        zero_terms = [{"zero": complex_json(zero), "difference": complex_json(pole - zero),
                       "angle": float(np.degrees(np.angle(pole - zero)))} for zero in zeros]
        pole_sum, zero_sum = sum(item["angle"] for item in pole_terms), sum(item["angle"] for item in zero_terms)
        angle = (180 - pole_sum + zero_sum + 180) % 360 - 180
        departures.append({"point": complex_json(pole), "poleTerms": pole_terms,
                           "zeroTerms": zero_terms, "poleSum": float(pole_sum),
                           "zeroSum": float(zero_sum), "angle": float(angle)})
    for index, zero in enumerate(zeros):
        if abs(zero.imag) < 1e-8:
            continue
        other_zeros = [other for other_index, other in enumerate(zeros) if other_index != index]
        zero_terms = [{"other": complex_json(other), "difference": complex_json(zero - other),
                       "angle": float(np.degrees(np.angle(zero - other)))} for other in other_zeros]
        pole_terms = [{"pole": complex_json(pole), "difference": complex_json(zero - pole),
                       "angle": float(np.degrees(np.angle(zero - pole)))} for pole in poles]
        zero_sum, pole_sum = sum(item["angle"] for item in zero_terms), sum(item["angle"] for item in pole_terms)
        angle = (180 - zero_sum + pole_sum + 180) % 360 - 180
        arrivals.append({"point": complex_json(zero), "zeroTerms": zero_terms,
                         "poleTerms": pole_terms, "zeroSum": float(zero_sum),
                         "poleSum": float(pole_sum), "angle": float(angle)})
    return {"departures": departures, "arrivals": arrivals}


def detalhes_ponto(point, zeros, poles):
    pole_terms, zero_terms = [], []
    for index, pole in enumerate(poles, start=1):
        difference = point - pole
        pole_terms.append({"index": index, "root": complex_json(pole), "difference": complex_json(difference),
                           "angle": float(np.degrees(np.angle(difference))), "distance": float(abs(difference))})
    for index, zero in enumerate(zeros, start=1):
        difference = point - zero
        zero_terms.append({"index": index, "root": complex_json(zero), "difference": complex_json(difference),
                           "angle": float(np.degrees(np.angle(difference))), "distance": float(abs(difference))})
    pole_product = float(np.prod([item["distance"] for item in pole_terms])) if pole_terms else 1.0
    zero_product = float(np.prod([item["distance"] for item in zero_terms])) if zero_terms else 1.0
    return {"poles": pole_terms, "zeros": zero_terms, "poleProduct": pole_product,
            "zeroProduct": zero_product, "gain": float(pole_product / zero_product)}


def analyze(payload):
    values = [parse_coefs(payload.get(name, "")) for name in ("nG", "dG", "nH", "dH")]
    if any(value is None for value in values):
        raise ValueError("Todos os campos devem conter coeficientes numéricos separados por espaços.")
    n_g, d_g, n_h, d_h = values
    num, den = fazer_passo1(n_g, d_g, n_h, d_h)
    zeros, poles = np.roots(num), np.roots(den)
    gains, branches = calcular_lgr(num, den)
    point_input = payload.get("point")
    if point_input is None or str(point_input).strip() == "":
        # Compatibilidade com clientes que ainda enviam as duas coordenadas.
        try:
            point = complex(float(payload.get("pointReal", 0)), float(payload.get("pointImag", 0)))
        except (TypeError, ValueError):
            raise ValueError("As coordenadas do ponto de teste devem ser numéricas.") from None
        test_points = [point]
    else:
        test_points = parse_test_points(point_input)
        point = test_points[0]
    departures, arrivals = angulos_extremos(zeros, poles)
    centroid, asymptotes = calcular_assintotas(zeros, poles)
    routh = tabela_routh(den, num)
    real_axis_details = detalhes_segmentos_reais(zeros, poles)
    breakaway_details = detalhes_breakaway(num, den, zeros, poles)
    jw_details = detalhes_jw(den, num)
    angle_details = detalhes_angulos(zeros, poles)
    point_results = [testar_ponto(test_point, zeros, poles) for test_point in test_points]
    point_details = [detalhes_ponto(test_point, zeros, poles) for test_point in test_points]
    details = {
        "nG": n_g.tolist(), "dG": d_g.tolist(), "nH": n_h.tolist(), "dH": d_h.tolist(),
        "dNumerator": derivada_coeficientes(num).tolist(), "dDenominator": derivada_coeficientes(den).tolist(),
        "poleDistances": [float(abs(point-p)) for p in poles], "zeroDistances": [float(abs(point-z)) for z in zeros],
        "poleAngleSum": float(sum(np.degrees(np.angle(point-p)) for p in poles)),
        "zeroAngleSum": float(sum(np.degrees(np.angle(point-z)) for z in zeros)),
    }
    return {"details": details, "numerator": num.tolist(), "denominator": den.tolist(), "zeros": roots_json(zeros), "poles": roots_json(poles),
            "realSegments": achar_segmentos_eixo_real(zeros, poles), "centroid": centroid,
            "asymptoteAngles": asymptotes, "breakaway": achar_breakaway(num, den, poles, zeros),
            "jwCrossings": cruzamento_jw(den, num), "routh": routh, "pointValue": complex_json(point),
            "pointValues": [complex_json(test_point) for test_point in test_points],
            "point": point_results[0], "points": point_results,
            "pointConjugate": len(test_points) == 2,
            "departureAngles": departures, "arrivalAngles": arrivals,
            "factorizedNumerator": fatorados(zeros, leading=num[0]), "factorizedDenominator": fatorados(poles, leading=den[0]),
            "stepCalculations": {
                "realAxis": real_axis_details,
                "breakaway": breakaway_details,
                "jw": jw_details,
                "angles": angle_details,
                # Mantém `point` no singular para consumidores antigos; a
                # lista completa atende à entrada com pontos conjugados.
                "point": point_details[0],
                "points": point_details,
            },
            "lgr": [{"gain": float(g), "roots": roots_json(row)} for g, row in zip(gains, branches)]}
