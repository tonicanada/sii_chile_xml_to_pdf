"""La guía de despacho (TD52) imprime su tipo de traslado.

El Set de Pruebas del SII lo exige: «se debe señalar el tipo de traslado en todos los
documentos de Guía de Despacho Electrónica». Antes el PDF no lo mostraba: la guía de un
traslado entre bodegas y la de una venta se veían iguales.

    PYTHONPATH=src python3 -m pytest tests/ -q
"""

from sii_xml_pdf.parser import parse_xml
from sii_xml_pdf.renderer import render_html

from test_referencias import FIRMA, NS

_GUIA = """<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE xmlns="{NS}" version="1.0"><Documento ID="F7T52">
<Encabezado>
  <IdDoc><TipoDTE>52</TipoDTE><Folio>7</Folio><FchEmis>2024-01-17</FchEmis>{id_doc}</IdDoc>
  <Emisor><RUTEmisor>22222222-2</RUTEmisor><RznSoc>EMPRESA DE PRUEBA SPA</RznSoc>
    <GiroEmis>Arriendo</GiroEmis><DirOrigen>Calle 1</DirOrigen>
    <CmnaOrigen>Las Condes</CmnaOrigen></Emisor>
  <Receptor><RUTRecep>11111111-1</RUTRecep><RznSocRecep>CLIENTE SPA</RznSocRecep>
    <GiroRecep>Servicios</GiroRecep><DirRecep>Calle 2</DirRecep>
    <CmnaRecep>Santiago</CmnaRecep></Receptor>
  {transporte}
  <Totales><MntTotal>0</MntTotal></Totales>
</Encabezado>
<Detalle><NroLinDet>1</NroLinDet><NmbItem>Camioneta</NmbItem><QtyItem>1</QtyItem>
  <MontoItem>0</MontoItem></Detalle>
</Documento>
{FIRMA}</DTE>"""


def _guia(id_doc: str, transporte: str = ""):
    xml = _GUIA.format(NS=NS, id_doc=id_doc, transporte=transporte, FIRMA=FIRMA)
    return parse_xml(xml.encode("latin-1"))


def test_traslado_y_despacho_en_palabras():
    dte = _guia("<TipoDespacho>2</TipoDespacho><IndTraslado>1</IndTraslado>")
    assert dte.tipo_traslado == "Operación constituye venta"
    assert dte.tipo_despacho == "Por cuenta del emisor a instalaciones del comprador"


def test_el_pdf_muestra_el_traslado_y_el_destino():
    dte = _guia("<IndTraslado>5</IndTraslado>",
                "<Transporte><Patente>PLCT12</Patente><DirDest>Bodega 3</DirDest>"
                "<CmnaDest>Cerrillos</CmnaDest></Transporte>")
    html = render_html(dte)
    assert "Traslado interno" in html
    assert "Bodega 3, Cerrillos" in html
    assert "PLCT12" in html
    assert "Despacho:" not in html


def test_una_factura_no_muestra_filas_de_traslado():
    from test_referencias import _dte
    html = render_html(parse_xml(_dte()))
    assert "Traslado:" not in html
    assert "Destino:" not in html
