"""Las referencias del DTE: qué documento se referencia, qué se le hace y por qué.

Dos cosas que faltaban y que se descubrieron intentando imprimir una nota de crédito real
de Constructora Tecton (61-157, que anula la factura 33-1932):

1. **`CodRef` y `RazonRef` se descartaban.** El PDF decía a qué documento apunta la nota,
   pero no si lo anula ni por qué. En una nota de crédito eso es justo lo que la explica, y
   las 41 que Tecton ha emitido lo llevan.
2. **El XML sin namespace no se parseaba.** El SII exporta los DTE sin declarar `xmlns`;
   los 1.219 descargados del portal vienen así. El parser buscaba con namespace, no
   encontraba nada y reventaba al formatear una fecha vacía — sin decir qué pasaba.

    PYTHONPATH=src python3 -m pytest tests/ -q
"""

import pytest

from sii_xml_pdf.parser import parse_xml

NS = "http://www.sii.cl/SiiDte"


def _dte(referencia: str = "", con_namespace: bool = True) -> bytes:
    """Un DTE mínimo pero completo: lo que el parser necesita para no fallar por otra cosa."""
    xmlns = f' xmlns="{NS}"' if con_namespace else ""
    return _PLANTILLA.format(xmlns=xmlns, referencia=referencia, FIRMA=FIRMA).encode("latin-1")


_PLANTILLA = """<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE{xmlns} version="1.0"><Documento ID="F157T61">
<Encabezado>
  <IdDoc><TipoDTE>61</TipoDTE><Folio>157</Folio><FchEmis>2024-01-17</FchEmis></IdDoc>
  <Emisor><RUTEmisor>76407152-2</RUTEmisor><RznSoc>EMPRESA DE PRUEBA SPA</RznSoc>
    <GiroEmis>Construcci&#243;n</GiroEmis><DirOrigen>Calle 1</DirOrigen>
    <CmnaOrigen>Las Condes</CmnaOrigen></Emisor>
  <Receptor><RUTRecep>77594467-6</RUTRecep><RznSocRecep>CLIENTE SPA</RznSocRecep>
    <GiroRecep>Servicios</GiroRecep><DirRecep>Calle 2</DirRecep>
    <CmnaRecep>Santiago</CmnaRecep></Receptor>
  <Totales><MntNeto>1000</MntNeto><TasaIVA>19</TasaIVA><IVA>190</IVA>
    <MntTotal>1190</MntTotal></Totales>
</Encabezado>
{referencia}
<Detalle><NroLinDet>1</NroLinDet><NmbItem>Servicio</NmbItem><QtyItem>1</QtyItem>
  <PrcItem>1000</PrcItem><MontoItem>1000</MontoItem></Detalle>
</Documento>
{FIRMA}</DTE>"""


# La firma va en el fixture y no es decoración: en un DTE del SII el documento viene **sin**
# namespace y la firma **con el suyo** (`xmldsig`). Un árbol mixto, entonces. Normalizar sin
# mirar qué nodo es le pondría el namespace del SII encima a la firma y la dejaría corrupta.
FIRMA = '''<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
  </SignedInfo><SignatureValue>QUJD</SignatureValue></Signature>'''


REF_NOTA_CREDITO = """<Referencia><NroLinRef>1</NroLinRef><TpoDocRef>33</TpoDocRef>
  <FolioRef>1932</FolioRef><FchRef>2024-01-02</FchRef><CodRef>1</CodRef>
  <RazonRef>Documento rechazado por cliente</RazonRef></Referencia>"""

REF_ORDEN_DE_COMPRA = """<Referencia><NroLinRef>1</NroLinRef><TpoDocRef>801</TpoDocRef>
  <FolioRef>PUR-ORD-2026-00001</FolioRef><FchRef>2026-01-15</FchRef></Referencia>"""


# ── qué le hace al documento, y por qué ────────────────────────────────────────


def test_la_nota_de_credito_dice_que_anula_y_por_que():
    ref = parse_xml(_dte(REF_NOTA_CREDITO)).referencias[0]
    assert ref.folio_referencia == "1932"
    assert ref.tipo_doc_referencia_palabras == "Factura Electrónica"
    assert ref.codigo_referencia == "1"
    assert ref.codigo_referencia_palabras == "Anula documento de referencia"
    assert ref.razon_referencia == "Documento rechazado por cliente"


@pytest.mark.parametrize("cod,glosa", [
    ("1", "Anula documento de referencia"),
    ("2", "Corrige texto del documento de referencia"),
    ("3", "Corrige montos"),
])
def test_los_tres_codigos_del_sii(cod, glosa):
    ref = parse_xml(_dte(REF_NOTA_CREDITO.replace("<CodRef>1<", f"<CodRef>{cod}<"))).referencias[0]
    assert ref.codigo_referencia_palabras == glosa


def test_un_codigo_que_el_sii_no_define_no_se_inventa():
    """Se imprime el número crudo antes que adivinar qué significa."""
    ref = parse_xml(_dte(REF_NOTA_CREDITO.replace("<CodRef>1<", "<CodRef>9<"))).referencias[0]
    assert ref.codigo_referencia == "9"
    assert ref.codigo_referencia_palabras == ""


def test_una_orden_de_compra_no_le_hace_nada_al_documento():
    """`CodRef` es opcional: una referencia a una OC no anula ni corrige nada. Los campos
    quedan vacíos, y la plantilla oculta la columna «Motivo» cuando ninguna los trae."""
    ref = parse_xml(_dte(REF_ORDEN_DE_COMPRA)).referencias[0]
    assert ref.tipo_doc_referencia_palabras == "Orden de Compra"
    assert ref.folio_referencia == "PUR-ORD-2026-00001", "el folio de referencia es texto"
    assert (ref.codigo_referencia, ref.codigo_referencia_palabras, ref.razon_referencia) == ("", "", "")


# ── el XML tal como lo exporta el SII ──────────────────────────────────────────


def test_el_xml_sin_namespace_se_parsea_igual():
    """Así exporta el SII: `<DTE version="1.0">`, sin `xmlns`. Antes salía todo vacío."""
    dte = parse_xml(_dte(REF_NOTA_CREDITO, con_namespace=False))
    assert dte.fecha_emision == "2024-01-17", "sin esto revienta al formatear la fecha"
    assert dte.rut_proveedor == "76.407.152-2"
    assert dte.monto_total == 1190
    assert dte.referencias[0].razon_referencia == "Documento rechazado por cliente"


def test_la_firma_conserva_su_propio_namespace():
    """El documento viene sin namespace y la firma con el suyo (`xmldsig`): es un árbol
    MIXTO. Normalizar sin mirar qué nodo es le pondría encima el del SII y la rompería."""
    import xml.etree.ElementTree as ET

    from sii_xml_pdf.parser import _arbol

    root = _arbol(_dte(REF_NOTA_CREDITO, con_namespace=False))
    firmas = [n for n in root.iter() if n.tag.endswith("}Signature") or n.tag == "Signature"]
    assert len(firmas) == 1, "la firma sigue estando"
    assert firmas[0].tag == "{http://www.w3.org/2000/09/xmldsig#}Signature"
    assert not any("}{" in n.tag for n in root.iter()), "ningún tag con dos namespaces"
    assert ET.tostring(root), "el árbol sigue siendo serializable"


def test_con_y_sin_namespace_dan_el_mismo_resultado():
    con = parse_xml(_dte(REF_NOTA_CREDITO, con_namespace=True))
    sin = parse_xml(_dte(REF_NOTA_CREDITO, con_namespace=False))
    assert con.model_dump() == sin.model_dump()
