import io
import zipfile
import tempfile
import os
import logging
import re
from fastapi_mail import FastMail, MessageSchema
from .config import MAIL_CONF
from sii_xml_pdf.renderer import parse_xml, render_pdf, render_pdf_from_xml  # 👈 añadimos el fallback

logger = logging.getLogger(__name__)

MAX_RAZON_LEN = 40  # 👈 límite de caracteres para razón social


def sanitize_name(text: str, max_len: int = MAX_RAZON_LEN) -> str:
    """Normaliza y acorta la razón social."""
    clean = text.title().replace(".", "").strip()
    clean = re.sub(r"[^A-Za-z0-9\s\-]", "", clean)  # quitar caracteres raros
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip() + "..."
    return clean


async def process_zip_and_send(zip_bytes: bytes, email: str):
    logger.info("📦 Procesando ZIP para %s", email)

    pdfs = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".xml"):
                continue
            logger.info("➡️ Convirtiendo %s", name)
            data = zf.read(name)

            try:
                # 👉 Intentar parsear XML
                dte = parse_xml(data)
                fecha = dte.fecha_emision.replace("-", "")
                tipo = dte.tipo_dte_abreviatura
                razon = sanitize_name(dte.razon_social)
                folio = dte.numero_factura
                pdf_name = f"{fecha} {tipo} {razon} {folio}.pdf"

                pdf_bytes = render_pdf(dte)
            except Exception as e:
                # 👉 Si falla el parseo, usar fallback
                logger.warning(
                    "No se pudo parsear %s (%s), usando nombre base",
                    name,
                    str(e),
                )
                pdf_name = name.replace(".xml", ".pdf")
                pdf_bytes = render_pdf_from_xml(data)

            pdfs.append((pdf_name, pdf_bytes))

    logger.info("✅ Generados %s PDFs, creando ZIP final", len(pdfs))

    # Crear ZIP final en memoria
    out_zip = io.BytesIO()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, pdf in pdfs:
            zf.writestr(fname, pdf)
    out_zip.seek(0)

    # Guardar ZIP en archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(out_zip.getvalue())
        tmp_path = tmp.name

    logger.info("📧 Enviando email a %s con adjunto %s", email, tmp_path)

    try:
        message = MessageSchema(
            subject="PDFs generados",
            recipients=[email],
            body="Adjunto los PDFs generados desde tus XML.",
            subtype="plain",
            attachments=[tmp_path],
        )
        fm = FastMail(MAIL_CONF)
        await fm.send_message(message)
        logger.info("✅ Email enviado a %s", email)
    except Exception as e:
        logger.error("❌ Error enviando email: %s", str(e))
        raise
    finally:
        try:
            os.remove(tmp_path)
            logger.info("🧹 Archivo temporal eliminado: %s", tmp_path)
        except Exception as e:
            logger.warning(
                "No se pudo borrar el archivo temporal %s: %s", tmp_path, str(e)
            )
