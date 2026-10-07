"""Descuentos, recargos y retenciones en la muestra impresa.

El Set de Pruebas del SII lo pide por escrito: «los descuentos por línea o globales deben ser
indicados en las representaciones impresas. Además, señalar las cifras con separador de miles
con "."». El PDF tenía la columna «Dscto.» y el pie «Descuento/Recargo/Retenciones» fijos en 0,
y la cantidad salía «737.00» — que con el punto de miles chileno se lee 737 mil.

Los tres casos son los del Set de Pruebas de certificación: factura con descuento por línea,
factura con descuento global sobre los afectos, y Factura de Compra con IVA retenido total
(que salía como «Impuestos»). Datos ficticios.

    PYTHONPATH=src python3 -m pytest tests/ -q
"""

from sii_xml_pdf.formatting import format_cantidad
from sii_xml_pdf.parser import parse_xml
from sii_xml_pdf.renderer import render_html

NS = "http://www.sii.cl/SiiDte"


def _dte(tipo: int, totales: str, detalles: str, extra: str = "") -> bytes:
    return f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE xmlns="{NS}" version="1.0"><Documento ID="T{tipo}">
<Encabezado>
  <IdDoc><TipoDTE>{tipo}</TipoDTE><Folio>21</Folio><FchEmis>2026-10-07</FchEmis></IdDoc>
  <Emisor><RUTEmisor>88888888-8</RUTEmisor><RznSoc>EMPRESA SPA</RznSoc>
    <GiroEmis>Arquitectura</GiroEmis><DirOrigen>Calle 1</DirOrigen>
    <CmnaOrigen>Las Condes</CmnaOrigen></Emisor>
  <Receptor><RUTRecep>60803000-K</RUTRecep><RznSocRecep>RECEPTOR</RznSocRecep>
    <GiroRecep>Servicios</GiroRecep><DirRecep>Calle 2</DirRecep>
    <CmnaRecep>Santiago</CmnaRecep></Receptor>
  <Totales>{totales}</Totales>
</Encabezado>
{detalles}{extra}
</Documento></DTE>""".encode("latin-1")


# Descuento por línea: 737 × 5.713 con 9 % de descuento; 681 × 4.765 con 22 %.
DESCUENTO_LINEA = _dte(33, "<MntNeto>6362611</MntNeto><TasaIVA>19</TasaIVA><IVA>1208896</IVA><MntTotal>7571507</MntTotal>", """
<Detalle><NroLinDet>1</NroLinDet><NmbItem>Pañuelo AFECTO</NmbItem><QtyItem>737</QtyItem>
  <PrcItem>5713</PrcItem><DescuentoMonto>378943</DescuentoMonto><MontoItem>3831538</MontoItem></Detalle>
<Detalle><NroLinDet>2</NroLinDet><NmbItem>ITEM 2 AFECTO</NmbItem><QtyItem>681</QtyItem>
  <PrcItem>4765</PrcItem><DescuentoMonto>713892</DescuentoMonto><MontoItem>2531073</MontoItem></Detalle>""")

# Descuento global: 22 % de descuento global sobre los afectos; el exento no entra en la base.
DESCUENTO_GLOBAL = _dte(33, "<MntNeto>2720745</MntNeto><MntExe>13660</MntExe><TasaIVA>19</TasaIVA><IVA>516942</IVA><MntTotal>3251347</MntTotal>", """
<Detalle><NroLinDet>1</NroLinDet><NmbItem>ITEM 1 AFECTO</NmbItem><QtyItem>401</QtyItem>
  <PrcItem>5745</PrcItem><MontoItem>2303745</MontoItem></Detalle>
<Detalle><NroLinDet>2</NroLinDet><NmbItem>ITEM 2 AFECTO</NmbItem><QtyItem>170</QtyItem>
  <PrcItem>6967</PrcItem><MontoItem>1184390</MontoItem></Detalle>
<Detalle><NroLinDet>3</NroLinDet><IndExe>1</IndExe><NmbItem>ITEM 3 SERVICIO EXENTO</NmbItem>
  <QtyItem>2</QtyItem><PrcItem>6830</PrcItem><MontoItem>13660</MontoItem></Detalle>""", """
<DscRcgGlobal><NroLinDR>1</NroLinDR><TpoMov>D</TpoMov><GlosaDR>Descuento global afectos</GlosaDR>
  <TpoValor>%</TpoValor><ValorDR>22</ValorDR></DscRcgGlobal>""")

# Factura de Compra con retención total del IVA (ImptoReten 15).
RETENCION_TOTAL = _dte(46, """<MntNeto>8575050</MntNeto><TasaIVA>19</TasaIVA><IVA>1629260</IVA>
  <ImptoReten><TipoImp>15</TipoImp><TasaImp>19</TasaImp><MontoImp>1629260</MontoImp></ImptoReten>
  <MntTotal>8575050</MntTotal>""", """
<Detalle><NroLinDet>1</NroLinDet><NmbItem>Producto 1</NmbItem><QtyItem>1051</QtyItem>
  <PrcItem>7990</PrcItem><MontoItem>8397490</MontoItem></Detalle>""")


def test_el_descuento_por_linea_se_lee_y_se_imprime():
    d = parse_xml(DESCUENTO_LINEA)
    assert [i.descuento for i in d.items] == [378943, 713892]
    html = render_html(d, timbre_formato="svg", vista_previa=True)
    assert "378.943" in html and "713.892" in html


def test_el_descuento_global_en_porcentaje_va_sobre_los_afectos():
    d = parse_xml(DESCUENTO_GLOBAL)
    # (2.303.745 + 1.184.390) × 22 % = 767.390; el exento de 13.660 no entra.
    assert d.descuento_global == 767390
    assert d.monto_neto == 2303745 + 1184390 - 767390
    assert "767.390" in render_html(d, timbre_formato="svg", vista_previa=True)


def test_la_retencion_total_va_en_retenciones_y_no_en_impuestos():
    d = parse_xml(RETENCION_TOTAL)
    assert d.retenciones == 1629260
    assert d.impuestos == []
    html = render_html(d, timbre_formato="svg", vista_previa=True)
    retenciones = html[html.index("Retenciones:"):][:120]
    assert "1.629.260" in retenciones


def test_la_cantidad_entera_no_lleva_decimales_y_usa_punto_de_miles():
    assert format_cantidad(737) == "737"
    assert format_cantidad(1051) == "1.051"
    assert format_cantidad(2.5) == "2,5"
    assert format_cantidad(1234.125) == "1.234,125"
    assert "737.00" not in render_html(parse_xml(DESCUENTO_LINEA), timbre_formato="svg", vista_previa=True)
