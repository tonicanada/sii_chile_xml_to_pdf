from jinja2 import Environment, PackageLoader, select_autoescape
from weasyprint import HTML, CSS
from num2words import num2words
from typing import Optional, List
from importlib import resources
import io

from .models import DTEData
from .formatting import format_clp, fecha_es_larga
from .barcode import pdf417_svg_from_ted
from .parser import parse_xml 

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


# TipoDTE que llevan cuadro de Acuse de Recibo y (opcionalmente) copia
# cedible, según el Manual de Muestras Impresas del SII, secc. 1.4: Factura
# Electrónica, Factura No Afecta o Exenta, Guía de Despacho, Factura de
# Compra y Liquidación-Factura. Notas de Crédito/Débito quedan
# explícitamente excluidas ("NO deben incluir cuadro de Acuse de Recibo ni
# ejemplar cedible").
TIPOS_CON_ACUSE_RECIBO = {33, 34, 43, 46, 52}

# Guía de Despacho Electrónica usa una leyenda distinta a las demás.
_TIPO_GUIA_DESPACHO = 52

# A partir de este largo, "SON <monto en palabras>" hace wrap a 2 líneas en
# el recuadro (con el ancho/fuente actuales de invoice.css) — más allá de
# esto es solo una heurística por conteo de caracteres, WeasyPrint no
# expone el ancho real renderizado del texto en tiempo de armado del HTML.
_LARGO_MONTO_DOS_LINEAS = 60


def render_html(dte: DTEData, cedible: bool = False, acuse_recibo: bool = False) -> str:
    tmpl = env.get_template("invoice.html")
    barcode_svg = pdf417_svg_from_ted(dte.timbre_xml)
    monto_imp_ret = sum(i.monto for i in dte.impuestos) if dte.impuestos else 0
    # Ambos son opt-in y por defecto False: sin pedirlos explícitamente el
    # PDF sale idéntico al de antes de este cambio (ninguna integración
    # existente ve un layout distinto sin actualizar su llamada).
    elegible = dte.tipo_dte in TIPOS_CON_ACUSE_RECIBO
    mostrar_acuse_recibo = (acuse_recibo or cedible) and elegible
    cedible_texto = (
        "CEDIBLE CON SU FACTURA" if dte.tipo_dte == _TIPO_GUIA_DESPACHO else "CEDIBLE"
    )
    monto_total_palabras = num2words(dte.monto_total, lang="es").upper()
    ctx = {
        "d": dte,
        "fecha_emision_larga": fecha_es_larga(dte.fecha_emision),
        "barcode_svg": barcode_svg,
        "monto_total_palabras": monto_total_palabras,
        "monto_impuesto_y_retenciones": monto_imp_ret,
        "verificacion_url": "http://www.sii.cl",  # visible en el pie
        "mostrar_acuse_recibo": mostrar_acuse_recibo,
        "mostrar_cedible": cedible and elegible,
        "cedible_texto": cedible_texto,
        # Monto en palabras largo (montos de cientos de millones): el
        # recuadro "SON..." crece a 2 líneas — se libera un poco del
        # min-height artificial del `.content` para que siga cabiendo en 1
        # página (ver invoice.css, body.has-long-monto). Sin esto, algunos
        # documentos con montos grandes pasarían a 2 páginas sin necesidad.
        "monto_texto_largo": len(monto_total_palabras) > _LARGO_MONTO_DOS_LINEAS,
    }
    return tmpl.render(**ctx)


def render_pdf(
    dte: DTEData,
    css_path: Optional[str] = None,
    cedible: bool = False,
    acuse_recibo: bool = False,
) -> bytes:
    html = render_html(dte, cedible=cedible, acuse_recibo=acuse_recibo)
    styles = _default_css_list(css_path)
    out = io.BytesIO()
    HTML(string=html).write_pdf(out, stylesheets=styles)
    return out.getvalue()


def render_pdf_from_xml(
    xml_bytes: bytes,
    css_path: Optional[str] = None,
    cedible: bool = False,
    acuse_recibo: bool = False,
) -> bytes:
    """
    Recibe XML en bytes, devuelve el PDF en bytes.

    Ambos parámetros son opt-in (default False) — sin pasarlos, el PDF es
    idéntico al que generaba esta librería antes de agregar el cuadro de
    Acuse de Recibo/Cedible; no rompe integraciones existentes.

    `acuse_recibo`: agrega el cuadro "Acuse de Recibo" (Nombre/Rut/Fecha/
    Recinto/Firma + texto legal Ley 19.983) — usar para la copia TRIBUTARIA
    de Factura/Factura Exenta/Guía/Factura de Compra/Liquidación-Factura.

    `cedible`: además del cuadro de Acuse de Recibo, agrega la leyenda
    "CEDIBLE" (o "CEDIBLE CON SU FACTURA" en Guía de Despacho) en la esquina
    inferior derecha — usar para la copia CEDIBLE de esos mismos tipos.

    Ambos se ignoran silenciosamente en TipoDTE que no llevan estos
    elementos (ej. Notas de Crédito/Débito — el manual del SII las excluye
    explícitamente).
    """
    # 1. Parsear el XML a un objeto DTEData
    dte = parse_xml(xml_bytes)

    # 2. Generar PDF a partir del DTEData
    return render_pdf(dte, css_path=css_path, cedible=cedible, acuse_recibo=acuse_recibo)
