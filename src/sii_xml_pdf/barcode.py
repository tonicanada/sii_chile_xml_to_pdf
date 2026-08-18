from pdf417 import encode, render_svg, render_image
import xml.etree.ElementTree as ET
import base64
import io
import re


def clean_ted(ted_xml: str) -> str:
    """
    Limpia el bloque TED para que pueda ser codificado en PDF417.
    - Quita namespaces (ns0:, ns1:, etc)
    - Elimina xmlns="..."
    - Saca saltos de línea y espacios extra
    """
    s = ted_xml.strip()
    # Quitar xmlns y atributos de namespace
    s = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', s)
    # Quitar prefijos tipo ns0:
    s = re.sub(r'\bns\d+:', '', s)
    # Quitar espacios y saltos de línea excesivos
    s = re.sub(r">\s+<", "><", s)
    s = re.sub(r"\s+", " ", s)
    return s


# El paquete `pdf417` usa UTF-8 por defecto (encoding.py: DEFAULT_ENCODING =
# 'utf-8') al convertir el string del TED a bytes antes de codificarlo en el
# símbolo PDF417. El SII firma y espera el TED en ISO-8859-1 (misma
# codificación que el resto del XML DTE) — con UTF-8, cualquier carácter con
# tilde (ej. "Cajón") pasa a ocupar 2 bytes en vez de 1, cambiando los bytes
# de <DD> respecto a los que se firmaron y el SII rechaza con "Firma TED del
# timbre no coincide con firma TED del XML". Hay que forzar ISO-8859-1
# explícitamente en ambas funciones de este módulo.
_ENCODING_TED = "iso-8859-1"


def pdf417_svg_from_ted(ted_str: str, columns: int = 17, scale: int = 2, ratio: int = 3) -> str:
    ted_clean = clean_ted(ted_str)
    codes = encode(ted_clean, columns=columns, security_level=0, encoding=_ENCODING_TED)
    svg_tree = render_svg(codes, scale=scale, ratio=ratio)
    root = svg_tree.getroot()

    # Devolver como string para inyectar en el template
    return ET.tostring(root, encoding="unicode")


def pdf417_png_base64_from_ted(
    ted_str: str, columns: int = 17, scale: int = 3, ratio: int = 3
) -> str:
    """
    Igual que pdf417_svg_from_ted, pero devuelve el timbre como imagen PNG
    rasterizada (codificada en base64, para incrustar vía
    `<img src="data:image/png;base64,...">`) en vez de vector SVG.

    El Manual de Muestras Impresas del SII (secc. 1.5, pág. 12) permite
    ambos métodos, pero recomienda explícitamente PNG incrustado porque
    "nuestro software los reconoce en forma más rápida" — la versión
    vectorial (pdf417_svg_from_ted) sigue siendo válida y se mantiene sin
    cambios; esta es una alternativa, no un reemplazo.
    """
    ted_clean = clean_ted(ted_str)
    codes = encode(ted_clean, columns=columns, security_level=0, encoding=_ENCODING_TED)
    img = render_image(codes, scale=scale, ratio=ratio)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
