from jinja2 import Environment, PackageLoader, select_autoescape
from weasyprint import HTML, CSS
from num2words import num2words
from typing import Optional, List
from importlib import resources
import io

from .models import DTEData
from .formatting import format_clp, fecha_es_larga
from .barcode import pdf417_svg_from_ted, pdf417_png_base64_from_ted
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


def render_html(
    dte: DTEData,
    cedible: bool = False,
    acuse_recibo: bool = False,
    timbre_formato: str = "png",
) -> str:
    tmpl = env.get_template("invoice.html")
    monto_imp_ret = sum(i.monto for i in dte.impuestos) if dte.impuestos else 0
    # `cedible`/`acuse_recibo` son opt-in (default False = sin cambios).
    # `timbre_formato` SÍ cambia el default (ver docstring de
    # render_pdf_from_xml) — es una excepción deliberada: el vector no es
    # confiable para el portal de Muestras Impresas del SII.
    elegible = dte.tipo_dte in TIPOS_CON_ACUSE_RECIBO
    mostrar_acuse_recibo = (acuse_recibo or cedible) and elegible
    cedible_texto = (
        "CEDIBLE CON SU FACTURA" if dte.tipo_dte == _TIPO_GUIA_DESPACHO else "CEDIBLE"
    )
    ctx = {
        "d": dte,
        "fecha_emision_larga": fecha_es_larga(dte.fecha_emision),
        "monto_total_palabras": num2words(dte.monto_total, lang="es").upper(),
        "monto_impuesto_y_retenciones": monto_imp_ret,
        "verificacion_url": "http://www.sii.cl",  # visible en el pie
        "mostrar_acuse_recibo": mostrar_acuse_recibo,
        "mostrar_cedible": cedible and elegible,
        "cedible_texto": cedible_texto,
        "timbre_formato": timbre_formato,
    }
    if timbre_formato == "png":
        ctx["barcode_png_b64"] = pdf417_png_base64_from_ted(dte.timbre_xml)
    else:
        ctx["barcode_svg"] = pdf417_svg_from_ted(dte.timbre_xml)
    return tmpl.render(**ctx)


def render_pdf(
    dte: DTEData,
    css_path: Optional[str] = None,
    cedible: bool = False,
    acuse_recibo: bool = False,
    timbre_formato: str = "png",
) -> bytes:
    html = render_html(
        dte, cedible=cedible, acuse_recibo=acuse_recibo, timbre_formato=timbre_formato
    )
    styles = _default_css_list(css_path)
    out = io.BytesIO()
    HTML(string=html).write_pdf(out, stylesheets=styles)
    return out.getvalue()


def render_pdf_from_xml(
    xml_bytes: bytes,
    css_path: Optional[str] = None,
    cedible: bool = False,
    acuse_recibo: bool = False,
    timbre_formato: str = "png",
    indice: Optional[int] = None,
) -> bytes:
    """
    Recibe XML en bytes, devuelve el PDF en bytes.

    `indice` selecciona el documento cuando el XML es un sobre con varios: sin él,
    un sobre multi-documento **levanta** en vez de renderizar uno mal. Ver
    `parser.parse_xml`.

    `cedible` y `acuse_recibo` son opt-in (default False) — sin pasarlos,
    esa parte del PDF es idéntica a la de antes de agregar esos dos
    parámetros; no rompen integraciones existentes.

    `acuse_recibo`: agrega el cuadro "Acuse de Recibo" (Nombre/Rut/Fecha/
    Recinto/Firma + texto legal Ley 19.983) — usar para la copia TRIBUTARIA
    de Factura/Factura Exenta/Guía/Factura de Compra/Liquidación-Factura.

    `cedible`: además del cuadro de Acuse de Recibo, agrega la leyenda
    "CEDIBLE" (o "CEDIBLE CON SU FACTURA" en Guía de Despacho) en la esquina
    inferior derecha — usar para la copia CEDIBLE de esos mismos tipos.

    Ambos se ignoran silenciosamente en TipoDTE que no llevan estos
    elementos (ej. Notas de Crédito/Débito — el manual del SII las excluye
    explícitamente).

    `timbre_formato`: default **"png"** — incrusta el timbre PDF417 como
    imagen rasterizada. Este SÍ es un cambio de comportamiento por
    defecto respecto a versiones anteriores de esta librería (antes era
    "svg", vector): se probó contra el portal real de Muestras Impresas
    del SII y el vector no es legible por su software de validación
    automática ("Timbre ilegible"), mientras que PNG sí — coincide con lo
    que recomienda el Manual de Muestras Impresas (secc. 1.5, pág. 12):
    "Lo ideal es que se utilicen imágenes incrustadas de tipo PNG, ya que
    nuestro software los reconoce en forma más rápida". Pasar "svg"
    explícitamente para recuperar el comportamiento vectorial anterior.
    """
    # 1. Parsear el XML a un objeto DTEData
    dte = parse_xml(xml_bytes, indice)

    # 2. Generar PDF a partir del DTEData
    return render_pdf(
        dte,
        css_path=css_path,
        cedible=cedible,
        acuse_recibo=acuse_recibo,
        timbre_formato=timbre_formato,
    )
