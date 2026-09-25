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


#: Estilos disponibles y la hoja que cada uno AÑADE sobre `invoice.css`.
#: `actual` no añade nada: es el estilo de siempre, byte por byte.
ESTILOS = {
    "actual": None,
    "compacto": "templates/invoice_compacto.css",
}


def _leer_css(nombre: str) -> str:
    with resources.files("sii_xml_pdf").joinpath(nombre).open("r", encoding="utf-8") as f:
        return f.read()


def _default_css_list(css_path: Optional[str], estilo: str = "actual") -> List[CSS]:
    """Las hojas de estilo, en orden de aplicación.

    Un estilo distinto del base se monta COMO CAPA encima, no como copia: WeasyPrint
    aplica en orden y la última gana, así que el compacto solo declara sus diferencias.
    Duplicar las 331 líneas del base habría obligado a arreglar cada cosa dos veces y
    dejado que los dos estilos divergieran sin que se notara.

    Un `estilo` desconocido **levanta**. Caer al de por defecto en silencio significaría
    entregar un PDF con un aspecto que nadie pidió, y eso no se nota mirando: el
    documento sale bien, solo que no es el que se quería.
    """
    if estilo not in ESTILOS:
        raise ValueError(
            f"Estilo desconocido: {estilo!r}. Disponibles: {', '.join(sorted(ESTILOS))}"
        )
    if css_path:
        return [CSS(filename=css_path)]
    hojas = [CSS(string=_leer_css("templates/invoice.css"))]
    extra = ESTILOS[estilo]
    if extra:
        hojas.append(CSS(string=_leer_css(extra)))
    return hojas


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
    vista_previa: bool = False,
    logo_b64: Optional[str] = None,
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
        "vista_previa": vista_previa,
        # El logo NO sale del XML: ese XML es el documento tributario firmado y meterle
        # una imagen lo invalidaría. Llega como dato aparte y solo se pinta si viene.
        "logo_b64": logo_b64,
    }
    # Un documento sin timbrar no tiene TED, y el PDF417 no se puede dibujar: el
    # codificador levanta «Data too short». Se trata igual que `vista_previa` explícita
    # —marcarlo y seguir— porque un PDF sin sello y con hueco donde va el timbre parece
    # un documento válido al que se le estropeó la imagen, y eso es lo peligroso.
    sin_timbre = vista_previa or not (dte.timbre_xml or "").strip()
    ctx["vista_previa"] = sin_timbre
    if not sin_timbre:
        if timbre_formato == "png":
            ctx["barcode_png_b64"] = pdf417_png_base64_from_ted(
                dte.timbre_xml, ted_crudo=dte.timbre_xml_crudo
            )
        else:
            ctx["barcode_svg"] = pdf417_svg_from_ted(
                dte.timbre_xml, ted_crudo=dte.timbre_xml_crudo
            )
    return tmpl.render(**ctx)


def render_pdf(
    dte: DTEData,
    css_path: Optional[str] = None,
    cedible: bool = False,
    acuse_recibo: bool = False,
    timbre_formato: str = "png",
    vista_previa: bool = False,
    estilo: str = "actual",
    logo_b64: Optional[str] = None,
) -> bytes:
    html = render_html(
        dte, cedible=cedible, acuse_recibo=acuse_recibo, timbre_formato=timbre_formato,
        vista_previa=vista_previa, logo_b64=logo_b64,
    )
    styles = _default_css_list(css_path, estilo)
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
    vista_previa: bool = False,
    estilo: str = "actual",
    logo_b64: Optional[str] = None,
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

    `estilo`: `"actual"` (por defecto, el de siempre) o `"compacto"` —
    tipografía y espaciado más densos, y logo del emisor en la cabecera si se
    manda `logo_b64`. Se monta como capa sobre el CSS base, así que el estilo
    por defecto no cambia. Un estilo desconocido levanta en vez de caer al
    base: un PDF con el aspecto equivocado sale bien y no se nota.

    `logo_b64`: imagen del emisor en base64 (data URI sin prefijo) para la
    cabecera. No sale del XML —es un documento tributario firmado y meterle una
    imagen lo invalidaría— sino que llega como dato aparte. Si no se manda, la
    cabecera queda como siempre.

    `vista_previa`: marca el documento como borrador — el folio se imprime
    como "SIN FOLIO" y, en lugar del timbre, va un sello VISTA PREVIA. Sirve
    para enseñar cómo va a quedar un documento ANTES de timbrarlo, que es
    cuando todavía no hay folio ni TED. Se activa solo también cuando el XML
    no trae TED, porque sin él no se puede dibujar el PDF417 y un PDF con el
    hueco vacío pasaría por un documento válido mal impreso.

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
        vista_previa=vista_previa,
        estilo=estilo,
        logo_b64=logo_b64,
    )
