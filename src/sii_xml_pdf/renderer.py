from jinja2 import Environment, PackageLoader, select_autoescape
from weasyprint import HTML, CSS
from num2words import num2words
from typing import Optional, List
from importlib import resources
import io

from .models import DTEData
from .formatting import format_clp, fecha_es_larga
from .barcode import pdf417_svg_from_ted

env = Environment(
    loader=PackageLoader("sii_xml_pdf", "templates"),
    autoescape=select_autoescape(["html"])
)
env.filters["clp"] = format_clp

def _default_css_list(css_path: Optional[str]) -> List[CSS]:
    if css_path:
        return [CSS(filename=css_path)]
    # Cargar el CSS del paquete si no se pasa ruta
    with resources.files("sii_xml_pdf").joinpath("templates/invoice.css").open("r", encoding="utf-8") as f:
        css_text = f.read()
    return [CSS(string=css_text)]

def render_html(dte: DTEData) -> str:
    tmpl = env.get_template("invoice.html")
    barcode_svg = pdf417_svg_from_ted(dte.timbre_xml)
    monto_imp_ret = sum(i.monto for i in dte.impuestos) if dte.impuestos else 0
    ctx = {
        "d": dte,
        "fecha_emision_larga": fecha_es_larga(dte.fecha_emision),
        "barcode_svg": barcode_svg,
        "monto_total_palabras": num2words(dte.monto_total, lang="es").upper(),
        "monto_impuesto_y_retenciones": monto_imp_ret,
        "verificacion_url": "http://www.sii.cl",  # visible en el pie
    }
    return tmpl.render(**ctx)

def render_pdf(dte: DTEData, css_path: Optional[str] = None) -> bytes:
    html = render_html(dte)
    styles = _default_css_list(css_path)
    out = io.BytesIO()
    HTML(string=html).write_pdf(out, stylesheets=styles)
    return out.getvalue()
