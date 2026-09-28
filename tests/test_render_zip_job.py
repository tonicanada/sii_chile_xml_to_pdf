"""El job de `render-zip` con sobres de varios documentos y con archivos que fallan.

Desde que `parse_xml` levanta ante un sobre multi-documento, el job —que solo usaba
`parse_xml`— tumbaba el trabajo entero con un `Archivo_Intercambio` de 2 documentos: el
"fallback" volvía a parsear igual y reventaba de nuevo, y el correo no llegaba, ni siquiera
con los PDF que sí habían salido.

    PYTHONPATH=src python3 -m pytest tests/ -q
"""

import asyncio
import io
import os
import zipfile
from pathlib import Path
from unittest import mock

os.environ.setdefault("SMTP_USER", "x")
os.environ.setdefault("SMTP_PASS", "x")

from service import jobs  # noqa: E402

SOBRE = Path(__file__).parent / "fixtures" / "envio_4_documentos.xml"


def _correr(archivos):
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, "w") as zf:
		for nombre, data in archivos.items():
			zf.writestr(nombre, data)

	enviado = {}

	def _mensaje(**kw):
		# El adjunto es un archivo temporal que el job borra después de enviar:
		# se lee aquí, mientras existe.
		enviado["body"] = kw["body"]
		with zipfile.ZipFile(kw["attachments"][0]) as zf:
			enviado["pdfs"] = zf.namelist()

	with mock.patch.object(jobs, "MessageSchema", _mensaje), \
		mock.patch.object(jobs, "FastMail") as fm:
		fm.return_value.send_message = mock.AsyncMock()
		asyncio.run(jobs.process_zip_and_send(buf.getvalue(), "a@tecton.cl", "compacto"))
	return enviado


def test_un_sobre_de_varios_documentos_da_un_pdf_por_documento():
	enviado = _correr({"sobre.xml": SOBRE.read_bytes()})
	assert len(enviado["pdfs"]) == 4
	assert "No se pudieron" not in enviado["body"]


def test_un_archivo_roto_no_impide_el_correo_con_los_demas():
	enviado = _correr({"sobre.xml": SOBRE.read_bytes(), "roto.xml": b"<no es un DTE"})
	assert len(enviado["pdfs"]) == 4
	assert "roto.xml" in enviado["body"]
