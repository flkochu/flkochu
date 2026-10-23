#!/usr/bin/env python3
"""Genera los SVG del README del perfil con la misma paleta neón del portafolio.

    pip install fonttools brotli      (Python 3.8 o más nuevo)
    python3 tools/generar_svgs.py

Las fuentes (Tektur, Archivo y JetBrains Mono) se bajan de Google Fonts la primera vez
y se guardan en tools/.fuentes/. Cada SVG lleva incrustado solo el subconjunto de letras
que usa, porque GitHub muestra los SVG como imágenes y no deja cargar fuentes externas.

Los dibujos de los proyectos vienen de tools/dibujos.json, exportados del portafolio
(flkochu.github.io), así el perfil y la página usan exactamente los mismos planos: cada
clave ALL-xx guarda el viewBox y el contenido del <svg class="dw"> de su tarjeta, y "hero"
los grupos del dibujo grande. Si cambia un dibujo en el portafolio, abre la página en el
navegador y copia ese SVG al JSON. tools/proton-render.jpg es una captura de proton/
(1100 × 649) con la pose "Alcance al frente".
Los textos que cambian seguido están en las constantes de abajo. La salida es
reproducible: correrlo dos veces deja los mismos archivos.
"""
import base64, html, io, json, math, re, urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
TOOLS = ROOT / "tools"
CACHE = TOOLS / ".fuentes"

# ---------- paleta (la misma del portafolio) ----------
FILM, SHEET, SHEET2 = "#07050F", "#100B20", "#171030"
INK, INK2 = "#EFE9FF", "#A99FCC"
RULE, RULE2, LINE = "#3A2E66", "#1F1840", "#5B4AA6"
CYAN, MAGENTA, YELLOW, VIOLET = "#2DE2F0", "#FF3B8D", "#F5E642", "#A47BFF"
ORANGE, MINT, SKY = "#FF8C42", "#3CF5B1", "#5B8CFF"
TERM = "#0B0817"

# ---------- textos ----------
EYEBROW = "Abierto a prácticas en robótica · CDMX"
NAME = ("Adán López", "Lozano")
SUBTITLE = "Ingeniería Mecatrónica y Sistemas Ciberfísicos · Ibero"
TAGLINE = [("Diseño y construyo ", INK), ("robots", CYAN), (", del chasis al nodo de ", INK), ("ROS 2", CYAN), (".", INK)]
AREAS = [("Robótica", VIOLET), ("Embebidos", ORANGE), ("Visión e IA", CYAN), ("Diseño mecánico", MINT), ("Programación", YELLOW)]
REV = "E"

PROJECTS = [  # archivo, número en el portafolio, pluma, título, subtítulo, estado, chips
    ("proton", "ALL-01", MAGENTA, "PROTÓN · Plague Bot VR", "First Prize, Huawei ICT Competition 2025–2026", ("ok", "First Prize"), ["ESP32", "BTS7960", "ROS 2", "MoveIt2"]),
    ("atlas", "ALL-04", MINT, "Atlas: guiado multi-robot", "Mecanum omnidireccional manejado desde realidad mixta", ("ok", "Funcionando"), ["Python", "OpenCV", "ArUco", "MQTT"]),
    ("slam", "ALL-11", VIOLET, "SLAM 2D con ROS 2", "RPLIDAR C1, slam_toolbox y odometría en micro-ROS", ("wip", "Probado en PC"), ["ROS 2", "micro-ROS", "C++"]),
    ("motor", "ALL-10", ORANGE, "Controlador de motores ESP32", "SPI con DMA, PWM a 20 kHz y rampas en dos núcleos", ("ok", "27 pruebas"), ["ESP-IDF", "FreeRTOS", "C++"]),
    ("paper", "ALL-02", YELLOW, "Paper de Plague Bot VR", "Aceptado en el Congreso Mexicano de Robótica", ("ok", "Aceptado"), ["LaTeX", "IEEE", "YOLOv8"]),
    ("sumo", "ALL-06", MAGENTA, "Mini Sumo Autónomo Pro", "RobotChallenge CGC World Cup México 2026", ("ok", "Compitió 2026"), ["Fusion 360", "Teensy 4.1", "ToF"]),
]
GUIDES = [  # archivo, número, título, subtítulo
    ("mecanismos", "ALL-07", "Mecanismos y Actuadores", "Cuatro barras con Freudenstein"),
    ("senales", "ALL-08", "Procesamiento de Señales", "Filtros, DFT y transformada Z"),
    ("materiales", "ALL-09", "Selección de Materiales", "21 problemas y 49 preguntas"),
]
HEADERS = [  # archivo, número, título, nota a la derecha, pluma de la nota
    ("h-proton", "01", "PROTÓN en 3D", "SIMULACIÓN EN EL NAVEGADOR", MAGENTA),
    ("h-proyectos", "02", "Proyectos destacados", "PLANOS: 6 DE 12", CYAN),
    ("h-guias", "03", "Guías y comunidad", "PUBLICADAS EN GITHUB PAGES", SKY),
    ("h-herramientas", "04", "Herramientas", "MÓDULOS CARGADOS: 14", VIOLET),
    ("h-telemetria", "05", "Telemetría", "EN VIVO DESDE GITHUB", MINT),
    ("h-contacto", "06", "Contacto", "CDMX · ES / EN", YELLOW),
]

# ---------- fuentes ----------
FACES = {  # clave: (familia en Google Fonts, peso, nombre CSS)
    "TK5": ("Tektur", 500, "TK"), "TK6": ("Tektur", 600, "TK"), "TK7": ("Tektur", 700, "TK"),
    "AR4": ("Archivo", 400, "AR"), "AR6": ("Archivo", 600, "AR"),
    "JM4": ("JetBrains Mono", 400, "JM"), "JM7": ("JetBrains Mono", 700, "JM"),
}
_fonts = {}


def font_path(key):
    fam, wt, _ = FACES[key]
    p = CACHE / f"{fam.replace(' ', '')}-{wt}.ttf"
    if not p.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        q = f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:wght@{wt}"
        css = urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "curl/8"})).read().decode()
        url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
        p.write_bytes(urllib.request.urlopen(url).read())
    return p


def font(key):
    if key not in _fonts:
        f = TTFont(font_path(key))
        _fonts[key] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    return _fonts[key]


def tw(text, key, size, ls=0.0):
    """Ancho aproximado del texto (sin kerning), en px."""
    cmap, hm, upm = font(key)
    w = sum(hm[cmap.get(ord(c), cmap.get(32))][0] for c in text) * size / upm
    return w + ls * size * max(0, len(text) - 1)


def fit(text, key, size, maxw, ls=0.0):
    w = tw(text, key, size, ls)
    return size if w <= maxw else math.floor(size * maxw / w * 10) / 10


def font_css(keys, text):
    css = ""
    for key in sorted(keys):
        fam, wt, name = FACES[key]
        f = TTFont(font_path(key), recalcTimestamp=False)
        o = subset.Options()
        o.flavor = "woff2"
        o.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk"]
        o.name_IDs = []
        s = subset.Subsetter(o)
        s.populate(text=text + " 0123456789")
        s.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css += f"@font-face{{font-family:{name};font-weight:{wt};src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
    return css


# ---------- piezas comunes ----------
def esc(s):
    return html.escape(s, quote=True)


def rgba(hexc, a):
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


DW_CSS = f"""
.dw .k{{fill:none;stroke:var(--lc);stroke-width:1.5;vector-effect:non-scaling-stroke;stroke-linecap:round;stroke-linejoin:round}}
.dw .t{{fill:none;stroke:{INK2};stroke-width:1;opacity:.75;vector-effect:non-scaling-stroke}}
.dw .c{{fill:none;stroke:{INK2};opacity:.7;stroke-width:1;stroke-dasharray:12 3 2 3;vector-effect:non-scaling-stroke}}
.dw .d{{fill:none;stroke:{INK2};stroke-width:1;vector-effect:non-scaling-stroke}}
.dw .dash{{stroke-dasharray:5 4}}
.dw .f,.dw .fb{{fill:var(--lc);stroke:none}}
.dw .pw{{fill:{SHEET};stroke:none}}
.dw .w{{fill:var(--lw);stroke:var(--lc);stroke-width:1;vector-effect:non-scaling-stroke}}
.dw .hf{{fill:url(#hatch);stroke:var(--lc);stroke-width:1.5;vector-effect:non-scaling-stroke}}
.dw .hs{{fill:url(#hatch);stroke:none}}
.dw .bar{{fill:{RULE};stroke:none}}
.dw .lo{{stroke:var(--lc);stroke-linecap:round;vector-effect:non-scaling-stroke;fill:none}}
.dw .li{{stroke:{SHEET};stroke-linecap:round;vector-effect:non-scaling-stroke;fill:none}}
.dw .jt{{fill:{SHEET};stroke:var(--lc);stroke-width:1.5;vector-effect:non-scaling-stroke}}
.dw .bln{{fill:{SHEET};stroke:{YELLOW};stroke-width:1.2;vector-effect:non-scaling-stroke}}
.dw text{{font-family:AR,Arial,sans-serif;font-size:11px;fill:{INK2}}}
.dw .lbl{{fill:var(--lc);font-size:12px;font-weight:600}}
.dw .cap{{fill:{INK};font-family:TK,Arial,sans-serif;font-size:13px;font-weight:600}}
.dw .tiny{{font-size:9px}}
.dw .stamp{{fill:var(--lc);font-family:TK,Arial,sans-serif;font-size:13px;font-weight:700;letter-spacing:.06em}}
.dw .bal{{font-size:10.5px;font-weight:600;fill:{INK}}}
.hp{{stroke:{RULE};stroke-width:1}}
"""
DW_FACES = {"AR4", "AR6", "TK6", "TK7"}

BASE_DEFS = f"""<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="hp" x1="0" y1="0" x2="0" y2="6"/></pattern>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{LINE}" stroke-opacity=".16"/></pattern>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="glow-s" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="blur" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="14"/></filter>
<linearGradient id="neon" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>"""

REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def doc(w, h, title, css, body, faces, defs=""):
    text = html.unescape(re.sub(r"<[^>]+>", "", body)) + title
    style = font_css(faces, text) + css
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
            f"<title>{esc(title)}</title><style>{style}</style><defs>{BASE_DEFS}{defs}</defs>{body}</svg>")


def write(name, svg):
    (OUT / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"{name:28s} {len(svg) / 1024:6.1f} KB")


def T(x, y, s, cls="", anchor="start", extra=""):
    c = f' class="{cls}"' if cls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text{c} x="{x:.1f}" y="{y:.1f}"{a}{extra}>{esc(s)}</text>'


def corners(x, y, w, h, c, n=16, inset=8):
    x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
    d = f"M{x0} {y0 + n}V{y0}H{x0 + n}M{x1 - n} {y0}H{x1}V{y0 + n}M{x1} {y1 - n}V{y1}H{x1 - n}M{x0 + n} {y1}H{x0}V{y1 - n}"
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2" filter="url(#glow-s)"/>'


def status_glyph(st, cx, cy, delay=0.0):
    if st == "ok":
        return (f'<circle cx="{cx:.1f}" cy="{cy}" r="5" fill="{MINT}"/>'
                f'<circle class="ping" cx="{cx:.1f}" cy="{cy}" r="5" fill="none" stroke="{MINT}" style="animation-delay:{delay}s"/>')
    return (f'<circle cx="{cx:.1f}" cy="{cy}" r="5" fill="none" stroke="{YELLOW}" stroke-width="1.5"/>'
            f'<path d="M{cx:.1f} {cy - 5} A5 5 0 0 1 {cx:.1f} {cy + 5}Z" fill="{YELLOW}"/>')


PING = (".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.6s ease-out infinite}"
        "@keyframes ping{0%{transform:scale(1);opacity:.8}70%,100%{transform:scale(2.4);opacity:0}}")


def chevron(x, y, c, s=1.0):
    return f'<path d="M{x} {y - 5 * s}l{4.5 * s} {5 * s}-{4.5 * s} {5 * s}" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="square"/>'


DRAW = json.loads((TOOLS / "dibujos.json").read_text(encoding="utf-8"))


def drawing(pid, x, y, w, h, pen, extra_cls=""):
    d = DRAW[pid]
    return (f'<svg class="dw {extra_cls}" x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{d["viewBox"]}" '
            f'style="--lc:{pen};--lw:{rgba(pen, .14)}" filter="url(#glow-s)">{d["inner"]}</svg>')


def sheet_bg(w, h, glow_c, gx, gy, gr, gid):
    return (f'<radialGradient id="{gid}" cx="{gx}" cy="{gy}" r="{gr}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{glow_c}" stop-opacity=".16"/><stop offset="1" stop-color="{glow_c}" stop-opacity="0"/></radialGradient>',
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="{SHEET}"/><rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="url(#grid)" opacity=".7"/>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="url(#{gid})"/>')


# ---------- banner ----------
def banner():
    W, H = 1200, 440
    defs = (f'<radialGradient id="gm" cx="0" cy="0" r="620" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{MAGENTA}" stop-opacity=".16"/><stop offset="1" stop-color="{MAGENTA}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="gc" cx="1200" cy="440" r="620" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{CYAN}" stop-opacity=".12"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="gv" cx="930" cy="220" r="300" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".16"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{CYAN}" stop-opacity=".6"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>')
    b = f'<rect width="{W}" height="{H}" fill="{FILM}"/>'
    b += f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="{SHEET}" stroke="{RULE}"/>'
    b += f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="url(#grid)"/>'
    b += f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="url(#gm)"/><rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="url(#gc)"/><rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="url(#gv)"/>'
    # marco con zonas, como un plano
    zx0, zx1, zy0, zy1 = 26, W - 26, 26, H - 26
    for i, ch in enumerate("ABCDEF"):
        cx = zx0 + (zx1 - zx0) * (i + .5) / 6
        b += T(cx, 21, ch, "zn", "middle")
        if i:
            x = zx0 + (zx1 - zx0) * i / 6
            b += f'<line x1="{x:.1f}" y1="8" x2="{x:.1f}" y2="26" stroke="{RULE}"/>'
    for i, ch in enumerate("1234"):
        cy = zy0 + (zy1 - zy0) * (i + .5) / 4
        b += T(17, cy + 4, ch, "zn", "middle")
        if i:
            y = zy0 + (zy1 - zy0) * i / 4
            b += f'<line x1="8" y1="{y:.1f}" x2="26" y2="{y:.1f}" stroke="{RULE}"/>'
    b += f'<rect x="{zx0}" y="{zy0}" width="{zx1 - zx0}" height="{zy1 - zy0}" fill="none" stroke="{LINE}"/>'

    x0 = 70
    # etiqueta "abierto a prácticas"
    ew = tw(EYEBROW, "TK5", 14, .03)
    b += f'<rect x="{x0}" y="58" width="{ew + 46:.1f}" height="30" fill="{rgba(MINT, .07)}" stroke="{rgba(MINT, .4)}"/>'
    b += f'<circle cx="{x0 + 17}" cy="73" r="4.5" fill="{MINT}"/><circle class="ping" cx="{x0 + 17}" cy="73" r="4.5" fill="none" stroke="{MINT}"/>'
    b += T(x0 + 32, 78, EYEBROW, "eb")
    # nombre
    halo = f' style="fill:{VIOLET}"'
    b += f'<g filter="url(#blur)" opacity=".45">{T(x0, 172, NAME[0], "nm", extra=halo)}{T(x0, 252, NAME[1], "nm", extra=halo)}</g>'
    b += T(x0, 172, NAME[0], "nm")
    w2 = tw(NAME[1], "TK6", 80, -.01)
    b += f'<linearGradient id="ng" x1="{x0}" x2="{x0 + w2:.0f}" y1="0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>'
    b += T(x0, 252, NAME[1], "nm", extra=' style="fill:url(#ng)"')
    b += T(x0, 296, SUBTITLE, "sub")
    b += f'<text class="tag" x="{x0}" y="326">' + "".join(f'<tspan fill="{c}">{esc(s)}</tspan>' for s, c in TAGLINE) + "</text>"
    # áreas, cada una con la pluma de su capa
    x = x0
    for label, c in AREAS:
        w = tw(label, "TK5", 13, .02) + 40
        b += f'<rect x="{x}" y="350" width="{w:.1f}" height="28" fill="{rgba(c, .07)}" stroke="{rgba(c, .45)}"/>'
        b += f'<rect x="{x + 10}" y="363" width="12" height="2" fill="{c}" filter="url(#glow-s)"/>'
        b += T(x + 29, 368.5, label, "ar")
        x += w + 8
    # dibujo de PROTÓN, el mismo del portafolio
    hero = DRAW["hero"]
    gs = "".join(f'<g class="bd" style="animation-delay:{.2 + i * .28:.2f}s">{g}</g>' for i, g in enumerate(hero["groups"]))
    b += (f'<svg class="dw hero" x="690" y="42" width="480" height="369" viewBox="{hero["viewBox"]}" style="--lc:{CYAN};--lw:{rgba(CYAN, .14)}" filter="url(#glow)">'
          f'{gs}<rect class="scan" x="20" y="0" width="520" height="2" fill="url(#scan)"/></svg>')
    b += T(W - 40, H - 34, f"ALL-00 · REV {REV} · ESCALA 1:1", "tb", "end")
    css = (f".zn{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:10px;fill:{INK2}}}"
           f".eb{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:14px;letter-spacing:.03em;fill:{INK}}}"
           f".nm{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:80px;letter-spacing:-.01em;fill:{INK}}}"
           f".sub{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:19px;fill:{INK2}}}"
           f".tag{{font-family:AR,Arial,sans-serif;font-weight:600;font-size:18px}}"
           f".ar{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:13px;letter-spacing:.02em;fill:{INK}}}"
           f".tb{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:11px;letter-spacing:.14em;fill:{INK2}}}"
           + DW_CSS +
           f".hero .k{{stroke:{VIOLET}}}.hero .lo{{stroke:{CYAN}}}.hero .jt{{stroke:{MAGENTA}}}.hero .f{{fill:{MAGENTA}}}.hero .d{{stroke:{YELLOW}}}.hero .lbl,.hero .bal{{fill:{YELLOW}}}"
           ".bd{animation:bd .6s ease-out both}@keyframes bd{from{opacity:0;transform:translateY(6px)}}"
           ".hero .dash{animation:march 1.4s linear infinite}@keyframes march{to{stroke-dashoffset:-18}}"
           ".scan{animation:scan 6s cubic-bezier(.45,0,.55,1) 1.6s infinite both}@keyframes scan{0%{transform:translateY(0);opacity:0}8%,92%{opacity:1}100%{transform:translateY(420px);opacity:0}}"
           + PING + REDUCED)
    write("banner.svg", doc(W, H, "Adán López Lozano, Ingeniería Mecatrónica y Sistemas Ciberfísicos, Ibero", css, b,
                            {"TK5", "TK6", "AR4", "AR6"} | DW_FACES, defs))


# ---------- terminal ----------
def terminal():
    W = 1200
    X, LH, CW = 44, 36, None
    size = 18
    CW = tw("M", "JM4", size)  # monoespaciada
    t = .35
    rows, y, keys = [], 100, []

    def prompt(cmd):
        nonlocal t, y
        px = X + CW * len("adan@ibero:~$ ")
        s = (f'<g class="ln" style="animation-delay:{t:.2f}s"><text x="{X}" y="{y}"><tspan class="u">adan</tspan><tspan class="h">@ibero</tspan>'
             f'<tspan class="mu">:~$</tspan><tspan class="cmd"> {esc(cmd)}</tspan></text>')
        if cmd:
            dur = .045 * len(cmd) + .1
            k, dx = f"ty{len(keys)}", CW * len(cmd)
            keys.append(f"@keyframes {k}{{to{{transform:translateX({dx:.1f}px)}}}}")
            s += (f'<g class="ty" style="animation:{k} {dur:.2f}s steps({len(cmd)}) {t + .2:.2f}s both,off .01s linear {t + .2 + dur:.2f}s both">'
                  f'<rect x="{px:.1f}" y="{y - 20}" width="{CW * len(cmd) + 4:.1f}" height="27" fill="{TERM}"/><rect class="cur" x="{px:.1f}" y="{y - 17}" width="11" height="21"/></g>')
            t += .2 + dur + .15
        rows.append(s + "</g>")
        y += LH

    def out(inner, h=LH):
        nonlocal t, y
        rows.append(f'<g class="ln" style="animation-delay:{t:.2f}s">{inner}</g>')
        t += .1
        y += h

    prompt("whoami")
    out(f'<text x="{X}" y="{y}"><tspan class="ar">›</tspan><tspan class="cmd"> Adán López Lozano</tspan><tspan class="mu">  ·  Ingeniería Mecatrónica y Sistemas Ciberfísicos, Ibero</tspan></text>')
    prompt("cat intereses.txt")
    chips, x = "", X
    for label, c in [("ROBÓTICA", VIOLET), ("ROS 2", SKY), ("SISTEMAS EMBEBIDOS", ORANGE), ("VISIÓN", CYAN), ("DISEÑO MECÁNICO", MINT), ("CONTROL", YELLOW)]:
        w = tw(label, "JM4", 15, .06) + 26
        chips += f'<rect x="{x:.1f}" y="{y - 24}" width="{w:.1f}" height="32" fill="{rgba(c, .08)}" stroke="{c}" stroke-opacity=".7"/>'
        chips += f'<text class="chip" x="{x + w / 2:.1f}" y="{y - 3}" text-anchor="middle">{esc(label)}</text>'
        x += w + 12
    out(chips, LH + 6)
    prompt("ros2 node list")
    nodes = ["/proton/control_chasis", "/proton/brazo_6gdl", "/atlas/vision_aruco", "/base_mecanum/odometria", "/slam_toolbox", "/comunidad/guias"]
    for r in range(2):
        out("".join(f'<text class="node" x="{X + c * 370}" y="{y}">{esc(nodes[r * 3 + c])}</text>' for c in range(3)))
    prompt("cat logros.log")
    out(f'<text x="{X}" y="{y}"><tspan class="ok">◆</tspan><tspan class="yl"> First Prize</tspan><tspan class="cmd"> · Huawei ICT Competition 2025–2026 · con PROTÓN y mi equipo</tspan></text>')
    out(f'<text x="{X}" y="{y}"><tspan class="ok">◆</tspan><tspan class="cmd"> Paper de Plague Bot VR aceptado en COMRob</tspan></text>')
    prompt("cat mision.log")
    out(f'<text x="{X}" y="{y}"><tspan class="ar">›</tspan><tspan class="cmd"> Diseñar y construir robots completos: del cálculo y el CAD al firmware y ROS 2.</tspan></text>')
    out(f'<text x="{X}" y="{y}"><tspan class="ar">›</tspan><tspan class="cmd"> Documentar cada proyecto y compartir lo que aprendo.</tspan></text>')
    last_y = y
    prompt("")
    px = X + CW * len("adan@ibero:~$ ")
    rows.append(f'<g class="ln" style="animation-delay:{t:.2f}s"><rect class="cur blink" x="{px:.1f}" y="{last_y - 17}" width="11" height="21"/></g>')
    H = last_y + 34
    defs = (f'<linearGradient id="bd" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset=".5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>')
    b = f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="12" fill="none" stroke="url(#bd)" stroke-width="6" opacity=".25" filter="url(#blur)"/>'
    b += f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="12" fill="{TERM}" stroke="url(#bd)" stroke-opacity=".75" stroke-width="1.5"/>'
    b += f'<path d="M1.5 48H{W - 1.5}" stroke="{RULE}"/>'
    for i, c in enumerate([MAGENTA, YELLOW, MINT]):
        b += f'<circle cx="{28 + i * 24}" cy="25" r="6.5" fill="{c}" filter="url(#glow-s)"/>'
    b += T(W / 2, 30, "adan@ibero: ~/ros2_ws", "ttl", "middle") + T(W - 26, 30, "zsh · tty1", "ttl", "end")
    b += "".join(rows)
    css = (f"text{{font-family:JM,Menlo,Consolas,monospace;font-weight:400;font-size:{size}px;fill:{INK}}}"
           f".ttl{{font-size:14px;fill:{INK2}}}.u{{fill:{CYAN};font-weight:700}}.h{{fill:{VIOLET};font-weight:700}}.mu{{fill:{INK2}}}.cmd{{fill:{INK}}}"
           f".ar{{fill:{VIOLET}}}.ok{{fill:{MINT};font-weight:700}}.yl{{fill:{YELLOW};font-weight:700}}.node{{fill:{MINT}}}"
           f".chip{{font-size:15px;letter-spacing:.06em;fill:{INK}}}.cur{{fill:{CYAN}}}"
           ".ln{animation:ln .25s ease-out both}@keyframes ln{from{opacity:0}to{opacity:1}}"
           + "".join(keys) + "@keyframes off{from{opacity:1}to{opacity:0}}"
           ".blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
           "@media (prefers-reduced-motion:reduce){.ln,.blink{animation:none!important}.ty{display:none}}")
    write("terminal.svg", doc(W, H, "Terminal: quién soy, intereses, logros y misión", css, b, {"JM4", "JM7"}, defs))


# ---------- encabezados de sección ----------
def header(name, no, title, note, nc):
    W, H = 1200, 108
    gdef, bg = sheet_bg(W, H, CYAN, 0, 54, 520, "hg")
    b = bg + f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" fill="none" stroke="{RULE}" stroke-width="1.5"/>'
    b += f'<rect x="0" y="0" width="3" height="{H}" fill="url(#neon-v)" filter="url(#glow-s)"/>'
    b += T(30, 34, no, "no") + f'<rect x="66" y="28.5" width="44" height="1.5" fill="url(#kl)"/>'
    b += T(28, 78, title, "h")
    b += f'<rect x="30" y="91" width="64" height="2.5" fill="url(#neon)" filter="url(#glow-s)"/>'
    nw = tw(note, "TK5", 13, .16)
    b += f'<rect x="{W - 30 - nw - 30:.1f}" y="72" width="16" height="2" fill="{nc}" filter="url(#glow-s)"/>'
    b += T(W - 30, 78, note, "r", "end")
    defs = gdef + (f'<linearGradient id="kl" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
                   f'<linearGradient id="neon-v" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>')
    css = (f".no{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:15px;letter-spacing:.22em;fill:{CYAN};filter:url(#glow-s)}}"
           f".h{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:36px;letter-spacing:-.005em;fill:{INK}}}"
           f".r{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:13px;letter-spacing:.16em;fill:{INK2}}}")
    write(f"{name}.svg", doc(W, H, title, css, b, {"TK5", "TK6"}, defs))


# ---------- tarjetas de proyecto ----------
CARD_CSS = (f".pid{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:15px;letter-spacing:.08em}}"
            f".st{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:15px;fill:{INK2}}}"
            f".tt{{font-family:TK,Arial,sans-serif;font-weight:600;fill:{INK}}}"
            f".sb{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:15.5px;fill:{INK2}}}"
            f".cp{{font-family:AR,Arial,sans-serif;font-weight:600;font-size:13.5px;fill:{INK}}}"
            f".go{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:15px;letter-spacing:.04em}}"
            f".ly{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:13px;letter-spacing:.04em}}"
            ".scan{animation:7s cubic-bezier(.45,0,.55,1) infinite both}.sp{animation-name:sp}.sg{animation-name:sg}"
            "@keyframes sp{0%{transform:translateY(0);opacity:0}8%,92%{opacity:1}100%{transform:translateY(212px);opacity:0}}"
            "@keyframes sg{0%{transform:translateY(0);opacity:0}8%,92%{opacity:1}100%{transform:translateY(190px);opacity:0}}"
            + PING + DW_CSS + REDUCED)


def card(i, fname, pid, pen, title, sub, status, chips):
    W, H = 640, 400
    gdef, bg = sheet_bg(W, H, pen, 320, 150, 260, "cg")
    defs = gdef + f'<linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="{pen}" stop-opacity="0"/><stop offset=".5" stop-color="{pen}" stop-opacity=".55"/><stop offset="1" stop-color="{pen}" stop-opacity="0"/></linearGradient>'
    b = bg + f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" fill="none" stroke="{RULE}" stroke-width="1.5"/>'
    b += corners(0, 0, W, H, pen)
    b += T(30, 42, pid, "pid", extra=f' fill="{pen}"')
    st, stxt = status
    sw = tw(stxt, "AR4", 15)
    b += status_glyph(st, W - 30 - sw - 12, 37, i * .4) + T(W - 30, 42, stxt, "st", "end")
    b += drawing(pid, 155, 56, 330, 214.5, pen)
    b += f'<rect class="scan sp" x="140" y="56" width="360" height="1.5" fill="url(#sg)" style="animation-delay:{i * 1.1:.1f}s"/>'
    b += f'<line x1="30" y1="282" x2="{W - 30}" y2="282" stroke="{RULE}"/>'
    fs = fit(title, "TK6", 26, W - 60)
    b += T(30, 316, title, "tt", extra=f' style="font-size:{fs}px"')
    b += T(30, 342, sub, "sb", extra=f' style="font-size:{fit(sub, "AR4", 15.5, W - 60)}px"')
    x = 30
    for c in chips:
        w = tw(c, "AR6", 13.5) + 22
        b += f'<rect x="{x:.1f}" y="356" width="{w:.1f}" height="26" fill="{rgba(pen, .06)}" stroke="{rgba(pen, .35)}"/>'
        b += T(x + w / 2, 373.5, c, "cp", "middle")
        x += w + 7
    go = "Abrir plano"
    b += T(W - 46, 374, go, "go", "end", extra=f' fill="{pen}"') + chevron(W - 38, 369, pen)
    write(f"cards/{fname}.svg", doc(W, H, f"{title}. {sub}", CARD_CSS, b, {"TK5", "TK6", "AR4", "AR6"} | DW_FACES, defs))


def guide(i, fname, pid, title, sub):
    W, H = 400, 360
    pen = SKY
    gdef, bg = sheet_bg(W, H, pen, 200, 140, 190, "cg")
    defs = gdef + f'<linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="{pen}" stop-opacity="0"/><stop offset=".5" stop-color="{pen}" stop-opacity=".55"/><stop offset="1" stop-color="{pen}" stop-opacity="0"/></linearGradient>'
    b = bg + f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" fill="none" stroke="{RULE}" stroke-width="1.5"/>'
    b += corners(0, 0, W, H, pen, 14, 7)
    b += T(24, 38, pid, "pid", extra=f' fill="{pen}"')
    sw = tw("Publicada", "AR4", 15)
    b += status_glyph("ok", W - 24 - sw - 12, 33, i * .5) + T(W - 24, 38, "Publicada", "st", "end")
    b += drawing(pid, 52, 52, 296, 192.4, pen)
    b += f'<rect class="scan sg" x="40" y="52" width="320" height="1.5" fill="url(#sg)" style="animation-delay:{1 + i * 1.3:.1f}s"/>'
    b += f'<line x1="24" y1="256" x2="{W - 24}" y2="256" stroke="{RULE}"/>'
    b += T(24, 290, title, "tt", extra=f' style="font-size:{fit(title, "TK6", 23, W - 48)}px"')
    b += T(24, 315, sub, "sb", extra=f' style="font-size:{fit(sub, "AR4", 16, W - 48)}px"')
    b += f'<rect x="24" y="334" width="9" height="2" fill="{pen}" filter="url(#glow-s)"/><rect x="35" y="334" width="2" height="2" fill="{pen}"/><rect x="39" y="334" width="2" height="2" fill="{pen}"/>'
    b += T(48, 340, "Comunidad", "ly", extra=f' fill="{pen}"')
    b += T(W - 38, 340, "Abrir guía", "go", "end", extra=f' fill="{pen}"') + chevron(W - 30, 335, pen)
    write(f"cards/{fname}.svg", doc(W, H, f"Guía de {title}. {sub}", CARD_CSS, b, {"TK5", "TK6", "AR4", "AR6"} | DW_FACES, defs))


# ---------- PROTÓN en 3D ----------
def proton():
    img = base64.b64encode((TOOLS / "proton-render.jpg").read_bytes()).decode()
    W, ix, iy, iw = 1200, 24, 64, 1152
    ih = round(iw * 649 / 1100)  # proton-render.jpg mide 1100 × 649
    fy = iy + ih + 38
    H = fy + 26

    def P(x, y):  # de la captura original (1238 × 820, recortada 30 px arriba) al marco
        return ix + x * 1100 / 1238 * iw / 1100, iy + (y - 30) * 1100 / 1238 * iw / 1100

    gdef, bg = sheet_bg(W, H, MAGENTA, 600, 380, 640, "cg")
    b = bg + f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" fill="none" stroke="{RULE}" stroke-width="1.5"/>'
    b += T(28, 41, "ALL-01", "pid", extra=f' fill="{MAGENTA}"') + T(110, 41, "PROTÓN · Plague Bot VR", "hd")
    b += status_glyph("ok", W - 28 - tw("First Prize · Huawei ICT 2025–2026", "AR4", 15) - 12, 36) + T(W - 28, 41, "First Prize · Huawei ICT 2025–2026", "st", "end")
    b += f'<image x="{ix}" y="{iy}" width="{iw}" height="{ih}" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{img}" href="data:image/jpeg;base64,{img}"/>'
    b += f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="none" stroke="{RULE}"/>'
    b += corners(ix, iy, iw, ih, CYAN, 18, 10)
    # llamadas como en un plano
    calls = [((640, 250), (905, 120), "Brazo de 6 GDL", "piezas CAD reales", MAGENTA),
             ((343, 268), (130, 120), "Cámara RealSense", "campo de visión", CYAN),
             ((885, 395), (975, 330), "Chasis de aluminio", "manejable con WASD", VIOLET)]
    for i, ((ax, ay), (lx, ly), t1, t2, c) in enumerate(calls):
        (px, py), (qx, qy) = P(ax, ay), P(lx, ly)
        b += f'<g class="co" style="animation-delay:{.4 + i * .35:.2f}s">'
        w = max(tw(t1, "TK6", 17), tw(t2, "AR4", 14)) + 22
        ex, kx = (qx + w, qx + w + 12) if px > qx + w else (qx, qx - 12)
        b += f'<path d="M{px:.1f} {py:.1f}L{kx:.1f} {qy + 7:.1f}H{ex:.1f}" fill="none" stroke="{c}" stroke-width="1.5" filter="url(#glow-s)"/>'
        b += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{SHEET}" stroke="{c}" stroke-width="2"/><circle cx="{px:.1f}" cy="{py:.1f}" r="1.8" fill="{c}"/>'
        b += f'<rect x="{qx:.1f}" y="{qy - 18:.1f}" width="{w:.1f}" height="50" fill="{rgba(SHEET, .82)}" stroke="{rgba(c, .6)}"/>'
        b += T(qx + 11, qy + 3, t1, "c1") + T(qx + 11, qy + 23, t2, "c2", extra=f' fill="{c}"')
        b += "</g>"
    b += T(28, fy, "Brazo con las piezas CAD reales · chasis manejable · ROS 2 Jazzy + MoveIt2", "ft")
    b += T(W - 44, fy, "Abrir la simulación", "go", "end", extra=f' fill="{CYAN}"') + chevron(W - 36, fy - 5, CYAN)
    css = (f".pid{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:16px;letter-spacing:.08em}}"
           f".hd{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:20px;fill:{INK}}}"
           f".st{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:15px;fill:{INK2}}}"
           f".c1{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:17px;fill:{INK}}}"
           f".c2{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:14px}}"
           f".ft{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:17px;fill:{INK2}}}"
           f".go{{font-family:TK,Arial,sans-serif;font-weight:500;font-size:17px;letter-spacing:.04em}}"
           ".co{animation:co .5s ease-out both}@keyframes co{from{opacity:0;transform:translateY(6px)}}"
           + PING + REDUCED)
    write("proton-3d.svg", doc(W, H, "PROTÓN en 3D: brazo de 6 GDL con las piezas CAD reales sobre el chasis de aluminio", css, b,
                               {"TK5", "TK6", "AR4"}, gdef))


# ---------- contacto con cajetín ----------
def contact():
    W, H = 1200, 220
    gdef, bg = sheet_bg(W, H, VIOLET, 300, 110, 420, "cg")
    b = bg + f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" fill="none" stroke="{RULE}" stroke-width="1.5"/>'
    l1, l2 = "Busco prácticas y becas de investigación en", "robótica, sistemas embebidos y automatización."
    fs = min(fit(l1, "TK6", 31, 690), fit(l2, "TK6", 31, 690))
    b += T(36, 74, l1, "big", extra=f' style="font-size:{fs}px"')
    w2 = tw(l2, "TK6", fs)
    b += f'<linearGradient id="lg" x1="36" x2="{36 + w2:.0f}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>'
    b += T(36, 114, l2, "big", extra=f' style="fill:url(#lg);font-size:{fs}px"')
    b += T(36, 160, "lopezlozanoadan1@gmail.com", "ml") + T(36, 186, "linkedin.com/in/adan-lopez-lozano-586b75325", "ml")
    # cajetín, como el pie del portafolio
    x0, y0, cw = 760, 1.5, W - 761.5
    rows = [[("Dibujó", "Adán López Lozano", 4)], [("Plano", "ALL-00", 1), ("Escala", "1:1", 1), ("Hoja", "1/1", 1), ("Rev.", REV, 1)],
            [("Institución", "Ibero · Ciudad de México", 3), ("Proyectos", "12", 1)]]
    rh = (H - 3) / 3
    b += f'<rect x="{x0}" y="{y0}" width="{cw}" height="{H - 3}" fill="{SHEET2}"/><line x1="{x0}" y1="0" x2="{x0}" y2="{H}" stroke="{LINE}"/>'
    for r, row in enumerate(rows):
        y = y0 + r * rh
        if r:
            b += f'<line x1="{x0}" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" stroke="{RULE}"/>'
        x = x0
        for k, v, span in row:
            if x > x0:
                b += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y + rh:.1f}" stroke="{RULE}"/>'
            b += T(x + 14, y + 24, k, "k") + T(x + 14, y + 52, v, "vb" if r == 0 else "v", extra=f' style="fill:{MAGENTA}"' if k == "Rev." else "")
            x += cw * span / 4
    css = (f".big{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:31px;fill:{INK}}}"
           f".ml{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:17px;fill:{INK2}}}"
           f".k{{font-family:AR,Arial,sans-serif;font-weight:400;font-size:13px;fill:{INK2}}}"
           f".v{{font-family:TK,Arial,sans-serif;font-weight:600;font-size:19px;fill:{INK}}}"
           f".vb{{font-family:TK,Arial,sans-serif;font-weight:700;font-size:24px;fill:{INK}}}")
    write("contacto.svg", doc(W, H, "Busco prácticas y becas de investigación en robótica, sistemas embebidos y automatización", css, b,
                              {"TK6", "TK7", "AR4"}, gdef))


if __name__ == "__main__":
    banner()
    terminal()
    for h in HEADERS:
        header(*h)
    for i, p in enumerate(PROJECTS):
        card(i, *p)
    for i, g in enumerate(GUIDES):
        guide(i, *g)
    proton()
    contact()
