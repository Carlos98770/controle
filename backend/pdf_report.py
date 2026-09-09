from io import BytesIO
import os
import re
from xml.sax.saxutils import escape

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BLUE = colors.HexColor("#007aff")
INK = colors.HexColor("#1d1d1f")
MUTED = colors.HexColor("#5f6368")
LIGHT_BLUE = colors.HexColor("#f1f7ff")
LINE = colors.HexColor("#dce6f2")


def _number(value, digits=3):
    value = float(value)
    if abs(value) < 0.0005:
        return "0"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _complex(value):
    real, imag = float(value["real"]), float(value["imag"])
    if abs(imag) <= 0.001:
        return _number(real)
    sign = "+" if imag >= 0 else "-"
    return f"{_number(real)} {sign} {_number(abs(imag))}j"


def _polynomial(values):
    terms = []
    degree = len(values) - 1
    for index, raw_value in enumerate(values):
        value = float(raw_value)
        if abs(value) < 1e-10:
            continue
        power = degree - index
        absolute = abs(value)
        coefficient = "" if power > 0 and abs(absolute - 1) < 1e-10 else _number(absolute)
        term = coefficient
        if power > 0:
            term += "s" if power == 1 else f"s^{power}"
        if not terms:
            terms.append(term if value > 0 else f"- {term}")
        else:
            terms.append(("+ " if value > 0 else "- ") + term)
    return " ".join(terms) or "0"


def _latex_number(value):
    return _number(value)


def _polynomial_latex(values, variable="s"):
    terms = []
    degree = len(values) - 1
    for index, raw_value in enumerate(values):
        value = float(raw_value)
        if abs(value) < 1e-10:
            continue
        power = degree - index
        absolute = abs(value)
        coefficient = "" if power > 0 and abs(absolute - 1) < 1e-10 else _latex_number(absolute)
        term = coefficient
        if power > 0:
            term += variable if power == 1 else f"{variable}^{{{power}}}"
        if not terms:
            terms.append(term if value > 0 else f"-{term}")
        else:
            terms.append(("+" if value > 0 else "-") + term)
    return " ".join(terms) or "0"


def _latex_complex(value):
    real, imag = float(value["real"]), float(value["imag"])
    if abs(imag) <= 0.001:
        return _latex_number(real)
    imaginary = f"{_latex_number(abs(imag))}\\,\\mathrm{{j}}"
    if abs(real) <= 0.0005:
        return ("-" if imag < 0 else "") + imaginary
    return f"{_latex_number(real)} {'-' if imag < 0 else '+'} {imaginary}"


def _factorized_latex(values, roots):
    if not values:
        return "0"
    leading = float(values[0])
    coefficient = ""
    if abs(leading - 1) >= 1e-10:
        coefficient = "-" if abs(leading + 1) < 1e-10 else _latex_number(leading)
    factors = []
    for root in roots:
        real, imag = float(root["real"]), float(root["imag"])
        if abs(imag) <= 0.001:
            if abs(real) <= 0.0005:
                factors.append("s")
            elif real > 0:
                factors.append(f"\\left(s-{_latex_number(real)}\\right)")
            else:
                factors.append(f"\\left(s+{_latex_number(abs(real))}\\right)")
        else:
            factors.append(f"\\left(s-\\left({_latex_complex(root)}\\right)\\right)")
    return coefficient + "\\,".join(factors or ["1"])


def _latex_roots(values, label):
    roots = ",\\;".join(_latex_complex(value) for value in values) or "\\varnothing"
    return f"\\mathrm{{{label}}}:\\;{roots}"


def _latex_segments(segments):
    if not segments:
        return "\\mathrm{Segmentos}:\\;\\varnothing"
    values = []
    for segment in segments:
        left = "-\\infty" if segment["from"] is None else _latex_number(segment["from"])
        values.append(f"\\left({left},{_latex_number(segment['to'])}\\right]")
    return "\\mathrm{Segmentos}:\\;" + ",\\;".join(values)


def _complex_dict(value):
    return {"real": float(np.real(value)), "imag": float(np.imag(value))}


def _real_axis_calculations(data):
    real_values = [
        float(value["real"])
        for value in data.get("poles", []) + data.get("zeros", [])
        if abs(float(value["imag"])) < 1e-8
    ]
    if not real_values:
        return ["\\mathrm{Nenhum\\ polo\\ ou\\ zero\\ real}"]
    boundaries = sorted(set(round(value, 8) for value in real_values), reverse=True)
    formulas = []
    for left, right in zip(boundaries[1:], boundaries[:-1]):
        middle = (left + right) / 2
        count = sum(value > middle + 1e-10 for value in real_values)
        belongs = "\\mathrm{pertence}" if count % 2 else "\\mathrm{nao\\ pertence}"
        formulas.append(
            f"s_{{teste}}={_latex_number(middle)},\\quad N_{{direita}}={count}"
            f"\\;\\Rightarrow\\;{belongs}\\;\\mathrm{{ao\\ LGR}}"
        )
    if len(real_values) % 2:
        count = len(real_values)
        formulas.append(
            f"s_{{teste}}\\in(-\\infty,{_latex_number(boundaries[-1])}),\\quad "
            f"N_{{direita}}={count}\\;\\Rightarrow\\;\\mathrm{{pertence}}"
        )
    return formulas or ["\\mathrm{Nenhum\\ segmento\\ valido}"]


def _separate_jw(values):
    degree = len(values) - 1
    real, imag = {}, {}
    for index, coefficient in enumerate(values):
        power = degree - index
        remainder = power % 4
        target = real if remainder in (0, 2) else imag
        sign = 1 if remainder in (0, 1) else -1
        target[power] = target.get(power, 0) + sign * float(coefficient)

    def build(values_by_power):
        if not values_by_power:
            return np.array([0.0])
        highest = max(values_by_power)
        output = np.zeros(highest + 1)
        for power, coefficient in values_by_power.items():
            output[highest - power] = coefficient
        return output

    return build(real), build(imag)


def _breakaway_calculations(data):
    numerator = np.asarray(data["numerator"], dtype=float)
    denominator = np.asarray(data["denominator"], dtype=float)
    derivative_numerator = np.polyder(numerator)
    derivative_denominator = np.polyder(denominator)
    equation = np.polysub(
        np.convolve(numerator, derivative_denominator),
        np.convolve(denominator, derivative_numerator),
    )
    while len(equation) > 1 and abs(equation[0]) < 1e-12:
        equation = equation[1:]
    candidates = []
    real_pz = [
        float(value["real"])
        for value in data.get("poles", []) + data.get("zeros", [])
        if abs(float(value["imag"])) < 1e-8
    ]
    for root in np.roots(equation) if len(equation) > 1 else []:
        denominator_value = np.polyval(numerator, root)
        gain = None if abs(denominator_value) < 1e-12 else -np.polyval(denominator, root) / denominator_value
        on_real_axis = abs(root.imag) < 1e-6
        right_count = None
        on_lgr = False
        if on_real_axis:
            right_count = sum(value > root.real + 1e-10 for value in real_pz)
            on_lgr = right_count % 2 == 1
        positive_gain = gain is not None and abs(gain.imag) < 1e-6 and gain.real > 0
        valid = (on_lgr if on_real_axis else True) and positive_gain
        candidates.append({
            "root": _complex_dict(root),
            "gain": None if gain is None else _complex_dict(gain),
            "on_lgr": on_lgr,
            "right_count": right_count,
            "positive_gain": positive_gain,
            "valid": valid,
        })
    return derivative_numerator, derivative_denominator, equation, candidates


def _plain_latex(value):
    """Converte as células simbólicas de Routh para uma forma legível no PDF."""
    text = str(value)
    text = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", text)
    text = text.replace("\\left", "").replace("\\right", "")
    text = text.replace("\\,", " ").replace("\\quad", "  ")
    text = text.replace("\\mathrm{j}", "j").replace("\\omega", "omega")
    text = text.replace("\\infty", "infinity").replace("\\text{", "").replace("}", "")
    text = re.sub(r"\^\{([^{}]*)\}", r"^\1", text)
    return text.replace("\\", "")


def _root_list(values, label):
    if not values:
        return f"{label}: nenhum"
    return f"{label}: " + ", ".join(_complex(value) for value in values)


def _segment_list(segments):
    if not segments:
        return "nenhum intervalo"
    values = []
    for segment in segments:
        left = "-infinity" if segment["from"] is None else _number(segment["from"])
        values.append(f"({left}, {_number(segment['to'])}]")
    return "; ".join(values)


def _plot_limits(data):
    points = data.get("poles", []) + data.get("zeros", [])
    points.extend(data.get("pointValues") or ([data["pointValue"]] if data.get("pointValue") else []))
    if data.get("centroid") is not None:
        points.append({"real": data["centroid"], "imag": 0})
    if not points:
        return (-1, 1), (-1, 1)
    real_values = [float(point["real"]) for point in points]
    imag_values = [float(point["imag"]) for point in points]
    spread = max(max(real_values) - min(real_values), max(imag_values) - min(imag_values), 1.0)
    # Deixa uma folga maior que a usada no gráfico da tela. Isso evita que os
    # marcadores e as retas auxiliares fiquem colados nas bordas no PDF.
    margin = max(1.5, 0.75 * spread)
    x_limits = (min(real_values) - margin, max(real_values) + margin)
    y_limit = max(max(abs(value) for value in imag_values) + 0.75 * margin, margin)
    return x_limits, (-y_limit, y_limit)


def _make_plot(data, mode="full"):
    # O gráfico é gerado em uma tela quadrada e é inserido no PDF com a mesma
    # proporção. Assim, uma unidade no eixo real vale exatamente o mesmo que
    # uma unidade no eixo imaginário.
    figure, axis = plt.subplots(figsize=(8, 8), dpi=220)
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    figure.subplots_adjust(left=0.14, right=0.96, bottom=0.12, top=0.91)
    x_limits, y_limits = _plot_limits(data)

    show_branches = mode in {"full", "asymptotes", "breakaway", "jw", "angles", "point"}
    if show_branches:
        lgr = data.get("lgr", [])
        for branch_index in range(len(data.get("poles", []))):
            roots = [sample["roots"][branch_index] for sample in lgr if len(sample.get("roots", [])) > branch_index]
            if roots:
                axis.plot(
                    [root["real"] for root in roots],
                    [root["imag"] for root in roots],
                    color="#007aff",
                    linewidth=2.0,
                    alpha=0.9,
                )

    poles = data.get("poles", [])
    zeros = data.get("zeros", [])
    if poles:
        axis.scatter(
            [point["real"] for point in poles],
            [point["imag"] for point in poles],
            marker="x",
            s=90,
            linewidths=2,
            color="#ff375f",
            label="Polos",
            zorder=4,
        )
    if zeros:
        axis.scatter(
            [point["real"] for point in zeros],
            [point["imag"] for point in zeros],
            marker="o",
            s=90,
            facecolors="none",
            edgecolors="#34c759",
            linewidths=2,
            label="Zeros",
            zorder=4,
        )

    if mode in {"full", "asymptotes", "breakaway", "angles"} and data.get("centroid") is not None:
        line_length = max(x_limits[1] - x_limits[0], y_limits[1] - y_limits[0]) * 1.4
        for angle in data.get("asymptoteAngles", []):
            radians = np.radians(angle)
            axis.plot(
                [data["centroid"], data["centroid"] + line_length * np.cos(radians)],
                [0, line_length * np.sin(radians)],
                color="#ff9f0a",
                linestyle="--",
                linewidth=1.4,
                alpha=0.9,
                label="Assíntotas" if angle == data.get("asymptoteAngles", [None])[0] else None,
            )

        axis.scatter(
            [data["centroid"]], [0], marker="+", s=110, linewidths=2,
            color="#111827", label=f"Centroide ({data['centroid']:.2f})", zorder=5,
        )

    for index, pole in enumerate(poles, start=1):
        axis.annotate(
            f"p{index}", (pole["real"], pole["imag"]), xytext=(7, 7),
            textcoords="offset points", fontsize=9, color="#b4233d", weight="bold",
        )
    for index, zero in enumerate(zeros, start=1):
        axis.annotate(
            f"z{index}", (zero["real"], zero["imag"]), xytext=(7, -13),
            textcoords="offset points", fontsize=9, color="#16803c", weight="bold",
        )

    test_points = data.get("pointValues") or ([data["pointValue"]] if data.get("pointValue") else [])
    if test_points and mode in {"full", "point"}:
        axis.scatter(
            [point["real"] for point in test_points],
            [point["imag"] for point in test_points],
            marker="+",
            s=110,
            linewidths=1.5,
            color="#d97706",
            label="Pontos de teste" if len(test_points) > 1 else f"Ponto de teste ({test_points[0]['real']:.2f}, {test_points[0]['imag']:.2f})",
            zorder=5,
        )

    if mode in {"full", "real", "asymptotes", "breakaway", "angles"}:
        for segment in data.get("realSegments", []):
            left = x_limits[0] if segment["from"] is None else max(float(segment["from"]), x_limits[0])
            right = min(float(segment["to"]), x_limits[1])
            axis.plot([left, right], [0, 0], color="#007aff", linewidth=4, alpha=0.65, solid_capstyle="round", label="Eixo real válido" if segment is data.get("realSegments", [None])[0] else None)

    if mode == "breakaway" and data.get("breakaway"):
        valid_breakaway = [item["point"] for item in data["breakaway"]]
        axis.scatter(
            [item["real"] for item in valid_breakaway], [item["imag"] for item in valid_breakaway],
            marker="D", s=70, color="#af52de", edgecolors="#5b217a", linewidths=1, label="Breakaway / break-in", zorder=5,
        )
        for item in data["breakaway"]:
            axis.annotate(
                f"K={_number(item['gain'])}", (item["point"]["real"], item["point"]["imag"]),
                xytext=(7, 7), textcoords="offset points", fontsize=8, color="#5b217a",
            )

    if mode == "jw" and data.get("jwCrossings"):
        crossing_points = [{"real": 0, "imag": item["omega"]} for item in data["jwCrossings"]]
        crossing_points += [{"real": 0, "imag": -item["omega"]} for item in data["jwCrossings"]]
        axis.scatter(
            [item["real"] for item in crossing_points], [item["imag"] for item in crossing_points],
            marker="s", s=65, color="#ff9f0a", edgecolors="#9a5b00", linewidths=1, label="Cruzamento jω", zorder=5,
        )

    point = test_points[0] if test_points else None
    if mode == "point" and point:
        for test_point in test_points:
            for root in data.get("poles", []):
                axis.plot([test_point["real"], root["real"]], [test_point["imag"], root["imag"]], color="#ff375f", linestyle=":", linewidth=0.9, alpha=0.8)
            for root in data.get("zeros", []):
                axis.plot([test_point["real"], root["real"]], [test_point["imag"], root["imag"]], color="#34c759", linestyle=":", linewidth=0.9, alpha=0.8)

    if mode == "angles":
        angle_data = data.get("stepCalculations", {}).get("angles", {})
        roots = data.get("poles", []) + data.get("zeros", [])
        span = max(1.0, *(abs(float(value)) for root in roots for value in (root["real"], root["imag"])))
        arrow_length = max(0.45, span * 0.28)
        for item in angle_data.get("departures", []):
            radians = np.radians(item["angle"])
            point_x, point_y = item["point"]["real"], item["point"]["imag"]
            end = (point_x + arrow_length * np.cos(radians), point_y + arrow_length * np.sin(radians))
            axis.annotate("", xy=end, xytext=(point_x, point_y), arrowprops={"arrowstyle": "->", "color": "#b4233d", "lw": 1.8})
            axis.text(end[0], end[1], f"{item['angle'] % 360:.1f}°", color="#b4233d", fontsize=8)
        for item in angle_data.get("arrivals", []):
            radians = np.radians(item["angle"])
            point_x, point_y = item["point"]["real"], item["point"]["imag"]
            end = (point_x + arrow_length * np.cos(radians), point_y + arrow_length * np.sin(radians))
            axis.annotate("", xy=end, xytext=(point_x, point_y), arrowprops={"arrowstyle": "->", "color": "#16803c", "lw": 1.8})
            axis.text(end[0], end[1], f"{item['angle'] % 360:.1f}°", color="#16803c", fontsize=8)

    axis.axhline(0, color="#475569", linewidth=0.8)
    axis.axvline(0, color="#475569", linewidth=0.8)
    axis.grid(color="#cbd5e1", linewidth=0.65, alpha=0.8)
    axis.set_xlim(x_limits)
    axis.set_ylim(y_limits)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel(r"Parte real ($\sigma$)", color="#111827", fontsize=10, labelpad=7)
    axis.set_ylabel(r"Parte imaginária ($j\omega$)", color="#111827", fontsize=10, labelpad=7)
    axis.tick_params(colors="#111827", labelsize=9, width=0.8)
    for spine in axis.spines.values():
        spine.set_color("#64748b")
        spine.set_linewidth(0.8)
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(
            handles, labels, loc="best", facecolor="white", labelcolor="#111827",
            edgecolor="#94a3b8", framealpha=0.95, fontsize=8,
        )
    titles = {
        "full": "Lugar geométrico das raízes",
        "poles": "Polos e zeros no plano s",
        "real": "Segmentos válidos do eixo real",
        "asymptotes": "Centroide e assíntotas",
        "breakaway": "Pontos de breakaway / break-in",
        "jw": "Cruzamento com o eixo imaginário",
        "angles": "Ângulos de partida e chegada",
        "point": "Critério de ângulo no ponto de teste",
    }
    axis.set_title(titles.get(mode, titles["full"]), color="#111827", fontsize=12, pad=10)
    output = BytesIO()
    figure.savefig(output, format="png", facecolor=figure.get_facecolor())
    plt.close(figure)
    output.seek(0)
    return output


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22,
            leading=27, textColor=INK, alignment=TA_CENTER, spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=styles["Normal"], fontSize=10, leading=14,
            textColor=MUTED, alignment=TA_CENTER, spaceAfter=18,
        ),
        "heading": ParagraphStyle(
            "StepHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13,
            leading=17, textColor=BLUE, spaceBefore=8, spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "ReportBody", parent=styles["BodyText"], fontSize=9.2, leading=13,
            textColor=INK, spaceAfter=5,
        ),
        "formula": ParagraphStyle(
            "ReportFormula", parent=styles["BodyText"], fontName="Courier", fontSize=8.7,
            leading=12, textColor=colors.HexColor("#1769aa"), backColor=LIGHT_BLUE,
            borderColor=LINE, borderWidth=0.5, borderPadding=7, spaceBefore=4, spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "ReportSmall", parent=styles["BodyText"], fontSize=8, leading=10,
            textColor=MUTED, spaceAfter=4,
        ),
    }


def _paragraph(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>").replace("  ", "&nbsp; "), style)


def _formula(text, styles):
    """Renderiza a expressão em mathtext, a sintaxe LaTeX matemática do Matplotlib."""
    try:
        dpi = 180
        figure = plt.figure(figsize=(12, 0.55), dpi=dpi)
        figure.patch.set_facecolor("#f1f7ff")
        figure.text(0.015, 0.48, f"${text}$", color="#1769aa", fontsize=11, va="center")
        image_data = BytesIO()
        figure.savefig(
            image_data,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.08,
            facecolor=figure.get_facecolor(),
        )
        plt.close(figure)
        image_data.seek(0)
        image_reader = ImageReader(image_data)
        pixel_width, pixel_height = image_reader.getSize()
        width = min(17.8 * cm, pixel_width * 72 / dpi)
        height = width * pixel_height / pixel_width
        return Image(image_data, width=width, height=height)
    except Exception:
        # Mantém o documento gerável se uma expressão simbólica excepcional não
        # for suportada pelo mathtext da versão instalada no servidor.
        return _paragraph(text, styles["formula"])


def _step(story, styles, number, title, body, formulas=()):
    opening = [Paragraph(f"Passo {number} — {escape(title)}", styles["heading"])]
    opening.extend(_paragraph(line, styles["body"]) for line in body)
    story.append(KeepTogether(opening))
    for line in formulas:
        story.append(_formula(line, styles))


def _step_plot(story, data, mode):
    plot = _make_plot(data, mode)
    width = 17.5 * cm
    pixel_width, pixel_height = ImageReader(plot).getSize()
    plot.seek(0)
    height = width * pixel_height / pixel_width
    story.append(Spacer(1, 3))
    # Mantém a proporção original do PNG. Fixar largura e altura diferentes
    # deformava a escala do plano s e fazia o LGR parecer fora de simetria.
    story.append(Image(plot, width=width, height=height))
    story.append(Spacer(1, 6))


def _draw_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(1.5 * cm, 1.25 * cm, A4[0] - 1.5 * cm, 1.25 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.5 * cm, 0.8 * cm, "LGR Studio · Resolução do lugar geométrico das raízes")
    canvas.drawRightString(A4[0] - 1.5 * cm, 0.8 * cm, f"Página {document.page}")
    canvas.restoreState()


def generate_pdf(data):
    styles = _styles()
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.65 * cm,
        title="Resolução do Lugar Geométrico das Raízes",
        author="LGR Studio",
    )
    details = data["details"]
    numerator = data["numerator"]
    denominator = data["denominator"]
    factorized_numerator = _factorized_latex(numerator, data.get("zeros", []))
    factorized_denominator = _factorized_latex(denominator, data.get("poles", []))
    point = data["pointValue"]
    test_points = data.get("pointValues") or [point]
    point_results = data.get("points") or [data["point"]]
    branches = max(len(data.get("poles", [])), len(data.get("zeros", [])))
    story = []

    story.append(Paragraph("Lugar Geométrico das Raízes", styles["title"]))
    story.append(Paragraph("Resolução completa gerada pelo LGR Studio", styles["subtitle"]))
    story.append(_paragraph("Dados de entrada", styles["heading"]))
    story.append(_formula(f"G(s)=K\\,\\frac{{{_polynomial_latex(details['nG'])}}}{{{_polynomial_latex(details['dG'])}}}", styles))
    story.append(_formula(f"H(s)=\\frac{{{_polynomial_latex(details['nH'])}}}{{{_polynomial_latex(details['dH'])}}}", styles))
    story.append(_formula(f"P(s)=\\frac{{{_polynomial_latex(numerator)}}}{{{_polynomial_latex(denominator)}}}", styles))
    story.append(_paragraph(_root_list(data.get("poles", []), "Polos") + " · " + _root_list(data.get("zeros", []), "Zeros"), styles["small"]))
    test_point_text = " · ".join(_complex(value) for value in test_points)
    story.append(_paragraph(f"Ponto(s) de teste: {test_point_text}", styles["small"]))

    plot = _make_plot(data)
    width = 17.8 * cm
    pixel_width, pixel_height = ImageReader(plot).getSize()
    plot.seek(0)
    height = width * pixel_height / pixel_width
    image = Image(plot, width=width, height=height)
    story.append(image)
    story.append(_paragraph("O gráfico reúne os ramos do LGR, polos, zeros, assíntotas e o ponto de teste.", styles["small"]))
    story.append(PageBreak())

    story.append(_paragraph("Resumo do ponto de teste (s₀)", styles["heading"]))
    if len(test_points) > 1:
        point_formula = "s_0\\in\\left\\{" + ",\\;".join(_latex_complex(value) for value in test_points) + "\\right\\}"
    else:
        point_formula = f"s_0={_latex_complex(test_points[0])}"
    story.append(_formula(point_formula, styles))
    for point_index, test_point in enumerate(test_points):
        point_result = point_results[point_index] if point_index < len(point_results) else point_results[0]
        point_label = f"s₀({point_index + 1})" if len(test_points) > 1 else "s₀"
        normalized_angle = ((-float(point_result["normalized_angle"]) % 360) + 360) % 360
        status = "Pertence ao LGR" if point_result["belongs"] else "Não pertence ao LGR"
        story.append(_paragraph(f"{point_label} = {_complex(test_point)} — {status}", styles["body"]))
        story.append(_formula(
            f"K={_latex_number(point_result['gain'])}\\qquad"
            f"\\Delta\\theta_{{\\mathrm{{norm}}}}={_latex_number(normalized_angle)}^\\circ",
            styles,
        ))

    _step(
        story, styles, 1, "Montar a função de transferência e o polinômio característico",
        ["Multiplicamos os numeradores e denominadores de G(s) e H(s). Para realimentação negativa, a equação característica é 1 + K P(s) = 0."],
        [
            f"G(s)=K\\,\\frac{{{_polynomial_latex(details['nG'])}}}{{{_polynomial_latex(details['dG'])}}}",
            f"H(s)=\\frac{{{_polynomial_latex(details['nH'])}}}{{{_polynomial_latex(details['dH'])}}}",
            f"G(s)H(s)=K\\,\\frac{{{_polynomial_latex(details['nG'])}\\,\\cdot\\,{_polynomial_latex(details['nH'])}}}{{{_polynomial_latex(details['dG'])}\\,\\cdot\\,{_polynomial_latex(details['dH'])}}}=K\\,\\frac{{N(s)}}{{D(s)}}=K\\,P(s)",
            f"N(s)={_polynomial_latex(numerator)}",
            f"D(s)={_polynomial_latex(denominator)}",
            f"1+K\\,P(s)=0\\;\\Longrightarrow\\;P(s,K)=D(s)+K\\,N(s)=0",
            f"P(s,K)={_polynomial_latex(denominator)}+K\\left({_polynomial_latex(numerator)}\\right)=0",
            f"D(s)={factorized_denominator}",
            f"N(s)={factorized_numerator}",
            f"P(s,K)={factorized_denominator}+K\\left({factorized_numerator}\\right)=0",
            "P(s,K)=a(K)\\prod_{i=1}^{n_p}\\left(s-s_i(K)\\right),\\quad P(s_i(K),K)=0",
        ],
    )
    _step(
        story, styles, 2, "Forma fatorada de P(s)",
        ["Fatoramos separadamente o numerador e o denominador usando suas raízes; o ganho líder é mantido nos dois polinômios."],
        [
            f"N(s)={_polynomial_latex(numerator)}\\;\\Longrightarrow\\;N(s)={factorized_numerator}",
            f"D(s)={_polynomial_latex(denominator)}\\;\\Longrightarrow\\;D(s)={factorized_denominator}",
            f"P(s)=\\frac{{N(s)}}{{D(s)}}=\\frac{{{factorized_numerator}}}{{{factorized_denominator}}}",
        ],
    )
    _step(
        story, styles, 3, "Identificar polos e zeros",
        ["Os polos são as raízes de D(s)=0 e os zeros são as raízes de N(s)=0."],
        [
            f"D(s)=0\\;\\Longrightarrow\\;{_latex_roots(data.get('poles', []), 'Polos')}",
            f"N(s)=0\\;\\Longrightarrow\\;{_latex_roots(data.get('zeros', []), 'Zeros')}",
        ],
    )
    _step_plot(story, data, "poles")
    _step(
        story, styles, 4, "Determinar os segmentos do eixo real",
        ["Em cada intervalo, escolhemos um ponto de teste, contamos polos e zeros reais à direita e aplicamos a regra da quantidade ímpar."],
        _real_axis_calculations(data) + [_latex_segments(data.get("realSegments", []))],
    )
    _step(
        story, styles, 5, "Calcular o número de ramos",
        ["Cada ramo começa em um polo e termina em um zero ou no infinito."],
        [
            f"n_p={len(data.get('poles', []))},\\quad n_z={len(data.get('zeros', []))}",
            f"L=\\max(n_p,n_z)=\\max({len(data.get('poles', []))},{len(data.get('zeros', []))})={branches}\\;\\mathrm{{ramos}}",
        ],
    )
    _step_plot(story, data, "real")
    _step(
        story, styles, 6, "Verificar simetria",
        ["Como os coeficientes são reais, raízes complexas aparecem em pares conjugados; por isso o LGR é simétrico em relação ao eixo real."],
        ["s\\in\\mathcal{L}\\Rightarrow s^*\\in\\mathcal{L}"],
    )

    asymptote_formulas = []
    asymptote_count = len(data.get("poles", [])) - len(data.get("zeros", []))
    if data.get("centroid") is None:
        asymptote_formulas.append("n_a=n_p-n_z=0\\Rightarrow\\mathrm{sem\\ assintotas}")
    else:
        pole_real_parts = [float(value["real"]) for value in data.get("poles", [])]
        zero_real_parts = [float(value["real"]) for value in data.get("zeros", [])]
        pole_sum = sum(pole_real_parts)
        zero_sum = sum(zero_real_parts)
        pole_terms = "+".join(f"({_latex_number(value)})" for value in pole_real_parts) or "0"
        zero_terms = "+".join(f"({_latex_number(value)})" for value in zero_real_parts) or "0"
        asymptote_formulas.extend([
            f"n_a=n_p-n_z={len(data.get('poles', []))}-{len(data.get('zeros', []))}={asymptote_count}",
            "\\sigma_a=\\frac{\\sum\\operatorname{Re}(p_i)-\\sum\\operatorname{Re}(z_j)}{n_p-n_z}",
            f"\\sum\\operatorname{{Re}}(p_i)={pole_terms}={_latex_number(pole_sum)}",
            f"\\sum\\operatorname{{Re}}(z_j)={zero_terms}={_latex_number(zero_sum)}",
            f"\\sigma_a=\\frac{{({_latex_number(pole_sum)})-({_latex_number(zero_sum)})}}{{{asymptote_count}}}="
            f"\\frac{{{_latex_number(pole_sum-zero_sum)}}}{{{asymptote_count}}}={_latex_number(data['centroid'])}",
            f"\\phi_q=\\frac{{(2q+1)180^\\circ}}{{n_a}}=\\frac{{(2q+1)180^\\circ}}{{{asymptote_count}}}",
        ])
        asymptote_formulas.extend(
            f"q={index}:\\quad \\phi_q=\\frac{{(2\\cdot{index}+1)180^\\circ}}{{{asymptote_count}}}={_latex_number(angle)}^\\circ"
            for index, angle in enumerate(data.get("asymptoteAngles", []))
        )
    _step(
        story, styles, 7, "Encontrar centroide e assíntotas",
        ["Calculamos o número de assíntotas, o centroide e cada ângulo a partir das somas das partes reais dos polos e zeros."],
        asymptote_formulas,
    )
    _step_plot(story, data, "asymptotes")

    derivative_numerator, derivative_denominator, breakaway_equation, breakaway_candidates = _breakaway_calculations(data)
    breakaway_formulas = [
        "K(s)=-\\frac{D(s)}{N(s)}",
        f"K(s)=-\\frac{{{_polynomial_latex(denominator)}}}{{{_polynomial_latex(numerator)}}}",
        "\\frac{dK}{ds}=-\\frac{D'(s)N(s)-D(s)N'(s)}{N(s)^2}=0",
        "D'(s)N(s)-D(s)N'(s)=0",
        f"N'(s)={_polynomial_latex(derivative_numerator)}",
        f"D'(s)={_polynomial_latex(derivative_denominator)}",
        f"{_polynomial_latex(breakaway_equation)}=0",
    ]
    for candidate in breakaway_candidates:
        root = candidate["root"]
        gain = candidate["gain"]
        root_text = _latex_complex(root)
        if gain is None:
            gain_text = "\\infty"
        else:
            gain_text = _latex_complex(gain)
        if candidate["valid"]:
            status = "valido"
        elif abs(root["imag"]) >= 1e-6:
            status = "K\\;nao\\ real\\ ou\\ positivo"
        elif not candidate["on_lgr"]:
            status = f"N_{{direita}}={candidate['right_count']}\\;\\mathrm{{par}}\\;\\Rightarrow\\;fora\\ do\\ LGR"
        else:
            status = "K\\;nao\\ positivo"
        right_count = "" if candidate["right_count"] is None else f",\\quad N_{{direita}}={candidate['right_count']}"
        breakaway_formulas.append(f"s={root_text},\\quad K={gain_text}{right_count},\\quad \\mathrm{{{status}}}")
    _step(
        story, styles, 8, "Localizar pontos de breakaway / break-in",
        ["Isolamos K(s), derivamos e resolvemos a equação resultante. Depois verificamos o segmento do eixo real e o sinal de K."],
        breakaway_formulas,
    )
    _step_plot(story, data, "breakaway")

    _step(
        story, styles, 9, "Aplicar o critério de estabilidade de Routh-Hurwitz e verificar cruzamento em jω",
        ["Construímos a tabela a partir da equação característica. Para estabilidade, os elementos da primeira coluna devem ser positivos."],
        ["D(s)+K\\,N(s)=0,\\quad K>0"],
    )
    routh = data.get("routh", {})
    rows = routh.get("rows", [])
    powers = routh.get("powers", [])
    if rows:
        columns = max(len(row) for row in rows)
        table_data = [["s^n"] + [f"C{i + 1}" for i in range(columns)]]
        for index, row in enumerate(rows):
            table_data.append([f"s^{powers[index]}"] + [_plain_latex(cell) for cell in row] + [""] * (columns - len(row)))
        table = Table(table_data, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, LINE),
            ("FONTNAME", (0, 0), (-1, -1), "Courier"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BLUE),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

        conditions = routh.get("conditions", [])
        if conditions:
            for condition in conditions:
                expression = condition["expression"]
                implication = f"\\;\\Longrightarrow\\;{condition['condition']}" if condition.get("condition") else ""
                story.append(_formula(f"s^{{{condition['power']}}}:\\quad {expression}>0{implication}", styles))
        else:
            for index, row in enumerate(rows):
                if row:
                    story.append(_formula(f"s^{{{powers[index]}}}:\\quad {row[0]} > 0", styles))
        for critical_gain in routh.get("criticalGains", []):
            story.append(_formula(f"K_{{\\mathrm{{crit}}}}={_latex_number(critical_gain)}", styles))

    re_denominator, im_denominator = _separate_jw(denominator)
    re_numerator, im_numerator = _separate_jw(numerator)
    jw_cross = np.polysub(
        np.convolve(re_denominator, im_numerator),
        np.convolve(im_denominator, re_numerator),
    )
    while len(jw_cross) > 1 and abs(jw_cross[0]) < 1e-12:
        jw_cross = jw_cross[1:]
    jw_formulas = [
        "s=j\\omega",
        f"\\operatorname{{Re}}D(\\omega)={_polynomial_latex(re_denominator, variable='\\omega')}",
        f"\\operatorname{{Im}}D(\\omega)={_polynomial_latex(im_denominator, variable='\\omega')}",
        f"\\operatorname{{Re}}N(\\omega)={_polynomial_latex(re_numerator, variable='\\omega')}",
        f"\\operatorname{{Im}}N(\\omega)={_polynomial_latex(im_numerator, variable='\\omega')}",
        "\\operatorname{Re}D\\,\\operatorname{Im}N-\\operatorname{Im}D\\,\\operatorname{Re}N=0",
        f"{_polynomial_latex(jw_cross, variable='\\omega')}=0",
    ]
    jw_roots = np.roots(jw_cross) if len(jw_cross) > 1 else []
    for root in jw_roots:
        if abs(root.imag) > 1e-6:
            jw_formulas.append(f"\\omega={_latex_complex(_complex_dict(root))}\\;\\Rightarrow\\;\\mathrm{{raiz\\ nao\\ real}}")
        elif root.real < 1e-8:
            jw_formulas.append(f"\\omega={_latex_number(root.real)}\\;\\Rightarrow\\;\\mathrm{{nao\\ gera\\ K>0}}")
    crossings = data.get("jwCrossings", [])
    if crossings:
        for item in crossings:
            omega = float(item["omega"])
            im_n_value = np.polyval(im_numerator, omega)
            im_d_value = np.polyval(im_denominator, omega)
            jw_formulas.extend([
                f"\\omega={_latex_number(omega)}\\;\\Longrightarrow\\;K=-\\frac{{\\operatorname{{Im}}D({_latex_number(omega)})}}{{\\operatorname{{Im}}N({_latex_number(omega)})}}=-\\frac{{{_latex_number(im_d_value)}}}{{{_latex_number(im_n_value)}}}={_latex_number(item['gain'])}",
                f"s=\\pm{_latex_number(omega)}\\,\\mathrm{{j}},\\quad K={_latex_number(item['gain'])}",
            ])
    else:
        jw_formulas.append("\\mathrm{nenhum\\ cruzamento\\ positivo}")
    for formula in jw_formulas:
        story.append(_formula(formula, styles))
    _step_plot(story, data, "jw")

    departure_arrival_formulas = [
        "\\theta_d=180^\\circ-\\sum_{j\\ne k}\\angle(p_k-p_j)+\\sum_j\\angle(p_k-z_j)",
        "\\theta_a=180^\\circ-\\sum_{j\\ne k}\\angle(z_k-z_j)+\\sum_j\\angle(z_k-p_j)",
    ]
    complex_poles = [complex(value["real"], value["imag"]) for value in data.get("poles", []) if float(value["imag"]) > 1e-8]
    complex_zeros = [complex(value["real"], value["imag"]) for value in data.get("zeros", []) if float(value["imag"]) > 1e-8]
    all_poles = [complex(value["real"], value["imag"]) for value in data.get("poles", [])]
    all_zeros = [complex(value["real"], value["imag"]) for value in data.get("zeros", [])]
    for pole in complex_poles:
        pole_angles = [np.degrees(np.angle(pole - other)) for other in all_poles if abs(pole - other) > 1e-10]
        zero_angles = [np.degrees(np.angle(pole - zero)) for zero in all_zeros]
        pole_sum = sum(pole_angles)
        zero_sum = sum(zero_angles)
        departure_arrival_formulas.append(f"p_k={_latex_complex(_complex_dict(pole))}")
        departure_arrival_formulas.extend(
            f"\\angle(p_k-p_j)=\\angle({_latex_complex(_complex_dict(pole))}-({_latex_complex(_complex_dict(other))}))={_latex_number(angle)}^\\circ"
            for other, angle in zip([other for other in all_poles if abs(pole - other) > 1e-10], pole_angles)
        )
        departure_arrival_formulas.extend(
            f"\\angle(p_k-z_j)=\\angle({_latex_complex(_complex_dict(pole))}-({_latex_complex(_complex_dict(zero))}))={_latex_number(angle)}^\\circ"
            for zero, angle in zip(all_zeros, zero_angles)
        )
        result = ((180 - pole_sum + zero_sum + 180) % 360) - 180
        departure_arrival_formulas.extend([
            f"\\sum\\angle(p_k-p_j)={_latex_number(pole_sum)}^\\circ,\\quad \\sum\\angle(p_k-z_j)={_latex_number(zero_sum)}^\\circ",
            f"\\theta_d=180^\\circ-({_latex_number(pole_sum)}^\\circ)+({_latex_number(zero_sum)}^\\circ)={_latex_number(result % 360)}^\\circ",
        ])
    for zero in complex_zeros:
        zero_angles = [np.degrees(np.angle(zero - other)) for other in all_zeros if abs(zero - other) > 1e-10]
        pole_angles = [np.degrees(np.angle(zero - pole)) for pole in all_poles]
        zero_sum = sum(zero_angles)
        pole_sum = sum(pole_angles)
        departure_arrival_formulas.append(f"z_k={_latex_complex(_complex_dict(zero))}")
        departure_arrival_formulas.extend(
            f"\\angle(z_k-z_j)={_latex_number(angle)}^\\circ" for angle in zero_angles
        )
        departure_arrival_formulas.extend(
            f"\\angle(z_k-p_j)={_latex_number(angle)}^\\circ" for angle in pole_angles
        )
        result = ((180 - zero_sum + pole_sum + 180) % 360) - 180
        departure_arrival_formulas.extend([
            f"\\sum\\angle(z_k-z_j)={_latex_number(zero_sum)}^\\circ,\\quad \\sum\\angle(z_k-p_j)={_latex_number(pole_sum)}^\\circ",
            f"\\theta_a=180^\\circ-({_latex_number(zero_sum)}^\\circ)+({_latex_number(pole_sum)}^\\circ)={_latex_number(result % 360)}^\\circ",
        ])
    _step(
        story, styles, 10, "Calcular ângulos de partida e chegada",
        ["Aplicamos a condição de fase em cada polo e zero complexo, calculando separadamente todos os ângulos e seus somatórios. O gráfico específico desta etapa aparece logo abaixo."],
        departure_arrival_formulas + ["P(s,K)=D(s)+K\\,N(s)=0", f"N_K={len(data.get('lgr', []))}\\;\\mathrm{{valores\\ de\\ K}}"],
    )
    _step_plot(story, data, "angles")

    angle_formulas = [
        "\\sum\\angle(s_0-z_j)-\\sum\\angle(s_0-p_i)=\\pm180^\\circ(2q+1)",
    ]
    for point_index, test_point in enumerate(test_points):
        point_result = point_results[point_index] if point_index < len(point_results) else point_results[0]
        point_label = f"s_0^{{({point_index + 1})}}" if len(test_points) > 1 else "s_0"
        s_test = complex(test_point["real"], test_point["imag"])
        angle_formulas.append(f"{point_label}={_latex_complex(test_point)}")
        pole_angle_values = []
        for index, pole in enumerate(all_poles, start=1):
            difference = s_test - pole
            angle = np.degrees(np.angle(difference))
            pole_angle_values.append(angle)
            angle_formulas.append(
                f"\\theta_{{p,{index}}}=\\angle({point_label}-p_{{{index}}})=\\angle({_latex_complex(test_point)}-({_latex_complex(_complex_dict(pole))}))="
                f"\\angle({_latex_complex(_complex_dict(difference))})={_latex_number(angle)}^\\circ"
            )
        zero_angle_values = []
        for index, zero in enumerate(all_zeros, start=1):
            difference = s_test - zero
            angle = np.degrees(np.angle(difference))
            zero_angle_values.append(angle)
            angle_formulas.append(
                f"\\theta_{{z,{index}}}=\\angle({point_label}-z_{{{index}}})=\\angle({_latex_complex(test_point)}-({_latex_complex(_complex_dict(zero))}))="
                f"\\angle({_latex_complex(_complex_dict(difference))})={_latex_number(angle)}^\\circ"
            )
        angle_formulas.extend([
            f"\\sum\\theta_p={_latex_number(sum(pole_angle_values))}^\\circ,\\quad \\sum\\theta_z={_latex_number(sum(zero_angle_values))}^\\circ",
            f"\\Delta\\theta=\\sum\\theta_p-\\sum\\theta_z={_latex_number(sum(pole_angle_values))}-({_latex_number(sum(zero_angle_values))})={_latex_number(-point_result['angle'])}^\\circ",
            f"\\Delta\\theta_{{\\mathrm{{norm}}}}={_latex_number((-point_result['angle']) % 360)}^\\circ",
        ])
    _step(
        story, styles, 11, "Testar o critério de ângulo",
        ["Somamos os ângulos formados com todos os polos e zeros e comparamos o resultado com um múltiplo ímpar de 180 graus. Para uma entrada conjugada, repetimos o cálculo para os dois pontos; os resultados são simétricos."],
        angle_formulas,
    )
    _step_plot(story, data, "point")

    module_formulas = [
        "K=\\frac{\\prod_i\\left|s_0-p_i\\right|}{\\prod_j\\left|s_0-z_j\\right|}",
    ]
    for point_index, test_point in enumerate(test_points):
        point_result = point_results[point_index] if point_index < len(point_results) else point_results[0]
        point_label = f"s_0^{{({point_index + 1})}}" if len(test_points) > 1 else "s_0"
        s_test = complex(test_point["real"], test_point["imag"])
        pole_distances = []
        zero_distances = []
        module_formulas.append(f"{point_label}={_latex_complex(test_point)}")
        for index, pole in enumerate(all_poles, start=1):
            difference = s_test - pole
            distance = abs(difference)
            pole_distances.append(distance)
            module_formulas.append(
                f"\\left|{point_label}-p_{{{index}}}\\right|=\\left|{_latex_complex(test_point)}-({_latex_complex(_complex_dict(pole))})\\right|="
                f"\\left|{_latex_complex(_complex_dict(difference))}\\right|={_latex_number(distance)}"
            )
        for index, zero in enumerate(all_zeros, start=1):
            difference = s_test - zero
            distance = abs(difference)
            zero_distances.append(distance)
            module_formulas.append(
                f"\\left|{point_label}-z_{{{index}}}\\right|=\\left|{_latex_complex(test_point)}-({_latex_complex(_complex_dict(zero))})\\right|="
                f"\\left|{_latex_complex(_complex_dict(difference))}\\right|={_latex_number(distance)}"
            )
        product_poles = float(np.prod(pole_distances)) if pole_distances else 1.0
        product_zeros = float(np.prod(zero_distances)) if zero_distances else 1.0
        module_formulas.extend([
            f"\\prod_i\\left|{point_label}-p_i\\right|={_latex_number(product_poles)}",
            f"\\prod_j\\left|{point_label}-z_j\\right|={_latex_number(product_zeros)}",
            f"K=\\frac{{{_latex_number(product_poles)}}}{{{_latex_number(product_zeros)}}}={_latex_number(point_result['gain'])}",
        ])
    _step(
        story, styles, 12, "Aplicar o critério de módulo",
        ["Calculamos cada distância, os dois produtos e finalmente o ganho K para cada ponto de teste."],
        module_formulas,
    )

    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    output.seek(0)
    return output
