"""
Las fuentes que el documento necesita tienen que estar en la imagen.

Esto no es una prueba de estilo: cuando falta una fuente, WeasyPrint **no falla**.
Cae a la siguiente de la lista y, si no hay ninguna, a DejaVu — y el PDF sale bien,
solo que con otra letra. Es exactamente lo que estuvo pasando: el CSS pedía Inter
desde el principio y la imagen no traía ninguna fuente instalada, así que todos los
documentos salían en DejaVu sin que nada lo indicara.
"""

import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fonts"

#: Las que se distribuyen con el repo. Inter viene del paquete `fonts-inter` de
#: Debian, así que no está aquí.
VENDORIZADAS = ["Sora.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf"]


@pytest.mark.parametrize("nombre", VENDORIZADAS)
def test_la_fuente_esta_en_el_repo(nombre):
	"""Van en el repo y no se descargan en el build: una descarga ataría cada
	construcción a que GitHub responda, y dos builds del mismo commit podrían dar
	imágenes distintas."""
	archivo = FUENTES / nombre
	assert archivo.is_file(), f"falta {nombre} en fonts/"
	assert archivo.stat().st_size > 10_000, f"{nombre} parece truncada"


def test_las_licencias_viajan_con_las_fuentes():
	"""Sora y DM Mono son OFL: la licencia tiene que distribuirse con ellas."""
	for licencia in ("OFL-Sora.txt", "OFL-DMMono.txt"):
		texto = (FUENTES / licencia).read_text(encoding="utf-8", errors="replace")
		assert "SIL OPEN FONT LICENSE" in texto.upper()


def test_el_dockerfile_las_instala_y_refresca_el_cache():
	"""Copiarlas no basta: sin `fc-cache` fontconfig no las ve y WeasyPrint cae al
	respaldo sin decir nada."""
	dockerfile = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
	assert "fonts/*.ttf" in dockerfile
	assert "fc-cache" in dockerfile
	assert "fonts-inter" in dockerfile


def test_cada_familia_declara_un_respaldo():
	"""Si mañana falta una fuente en la imagen, el documento debe caer en algo
	elegido, no en lo que haya."""
	css = (RAIZ / "src/sii_xml_pdf/templates/invoice_compacto.css").read_text(
		encoding="utf-8"
	)
	for familia in ('"Sora"', '"Inter"', '"DM Mono"'):
		assert familia in css, f"{familia} no se declara en el estilo compacto"
	# Ninguna declaración puede quedarse sin alternativa detrás.
	for linea in css.splitlines():
		if "font-family:" in linea:
			assert "," in linea, f"sin respaldo: {linea.strip()}"
