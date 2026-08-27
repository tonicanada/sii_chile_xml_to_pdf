"""Un `EnvioDTE` puede llevar varios documentos, y hasta ahora se renderizaban mal.

Todas las búsquedas del parser son `.//`, así que estaban atadas al sobre en vez de al
documento: la cabecera salía del **primero** y `Detalle`, `Referencia` e `ImptoReten`
acumulaban los de **todos**. No lanzaba error — devolvía un PDF plausible con montos que no
cuadraban con su propia cabecera, que es el peor modo de fallo posible.

Lo normal en el intercambio B2B es una factura por correo (el único DTE real recibido que
tenemos trae `NroDTE=1`), pero los sobres multi-documento existen: los sets de certificación
del SII llegan a 20.

    PYTHONPATH=src python3 -m pytest tests/ -q
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sii_xml_pdf.parser import parse_envio, parse_xml

SOBRE = Path(__file__).parent / "fixtures" / "envio_4_documentos.xml"
NS = "{http://www.sii.cl/SiiDte}"

# Los hechos del fixture, leídos del XML. Emisor 88888888-8 ("Empresa Ejemplo SpA"), o sea
# que se puede commitear tal cual: no hay nada que anonimizar.
PARES = [(33, "1"), (33, "2"), (61, "1"), (56, "1")]
TOTALES = [119000, 238000, 11900, 0]
ITEMS_POR_DOC = [1, 1, 1, 1]
REFS_POR_DOC = [1, 1, 2, 2]


def _cuantos(tag: str) -> int:
	"""Cuántos `tag` hay en TODO el sobre — el número que el bug metía en el documento 1."""
	return len(ET.parse(SOBRE).getroot().findall(f".//{NS}{tag}"))


class TestElSobreNoSeRenderizaSolo:
	def test_sin_indice_levanta_en_vez_de_devolver_un_pdf_mal(self):
		with pytest.raises(ValueError) as e:
			parse_xml(SOBRE)
		# El mensaje tiene que decir cuántos hay y por dónde salir.
		assert "4 documentos" in str(e.value)
		assert "parse_envio" in str(e.value)

	def test_con_indice_devuelve_el_que_se_pide(self):
		for i, (tipo, folio) in enumerate(PARES):
			d = parse_xml(SOBRE, indice=i)
			assert (d.tipo_dte, d.numero_factura) == (tipo, folio), f"índice {i}"


class TestParseEnvio:
	def test_devuelve_un_dte_por_documento(self):
		assert [(d.tipo_dte, d.numero_factura) for d in parse_envio(SOBRE)] == PARES

	def test_el_folio_se_lee_del_documento_y_no_del_sobre(self):
		"""El folio es único **por tipo**, no en absoluto: aquí `1` sale tres veces.

		Si el folio se leyera del sobre, los cuatro documentos dirían `1`.
		"""
		assert [d.numero_factura for d in parse_envio(SOBRE)] == ["1", "2", "1", "1"]

	def test_cada_documento_lleva_su_propio_total(self):
		"""Con el bug los cuatro reportaban 119000, el `MntTotal` del primero."""
		assert [d.monto_total for d in parse_envio(SOBRE)] == TOTALES


class TestNadaSeAcumulaEnElPrimerDocumento:
	"""El corazón del bug: las listas del documento 1 se llevaban las de todos.

	Cada test comprueba las dos mitades — que el reparto es el correcto **y** que el total
	del sobre es mayor que lo que le toca al primero. Sin la segunda mitad, el test pasaría
	igual con el bug puesto si el sobre tuviera un solo documento.
	"""

	def test_los_items(self):
		docs = parse_envio(SOBRE)
		assert [len(d.items) for d in docs] == ITEMS_POR_DOC
		assert sum(len(d.items) for d in docs) == _cuantos("Detalle")
		assert len(docs[0].items) < _cuantos("Detalle")

	def test_las_referencias(self):
		docs = parse_envio(SOBRE)
		assert [len(d.referencias) for d in docs] == REFS_POR_DOC
		assert sum(len(d.referencias) for d in docs) == _cuantos("Referencia")
		assert len(docs[0].referencias) < _cuantos("Referencia")

	def test_cada_documento_lleva_SU_timbre(self):
		"""El TED es lo que va al PDF impreso: el del vecino invalidaría el documento."""
		docs = parse_envio(SOBRE)
		assert all(d.timbre_xml for d in docs)
		# Cuatro timbres distintos, no cuatro copias del primero.
		assert len({d.timbre_xml for d in docs}) == 4


class TestNoRegresionUnSoloDocumento:
	"""El caso de siempre —y el 99 % del volumen real— tiene que seguir igual."""

	def test_un_sobre_de_un_documento_no_necesita_indice(self):
		d = parse_xml(SOBRE, indice=0)
		assert parse_envio(SOBRE)[0] == d

	def test_un_documento_suelto_sin_sobre_tambien_parsea(self):
		"""Un `<Documento>` como raíz, sin `EnvioDTE` alrededor."""
		doc = ET.parse(SOBRE).getroot().find(f".//{NS}Documento")
		suelto = ET.tostring(doc, encoding="utf-8")
		d = parse_xml(suelto)
		assert (d.tipo_dte, d.numero_factura, d.monto_total) == (33, "1", 119000)
