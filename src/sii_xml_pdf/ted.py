"""
Elegir qué forma del TED va impresa en el código de barras.

El emisor firma el `<DD>` en un momento y su software guarda el XML en otro: la
mayoría firma la forma compacta y después indenta el archivo, pero algunos —Banco
de Chile, Verisure— firman con espacios que una normalización destruye. Ninguna de
las dos formas sirve siempre, así que no se elige a ciegas: se elige **la que la
firma del emisor valida**.

Se puede verificar sin nada externo porque el TED lleva dentro, en su propio CAF,
la clave pública del emisor (`<RSAPK>`): `<FRMT>` es la firma RSA-SHA1 del `<DD>`
hecha con la privada correspondiente.

Garantía de no regresión: se prueba **primero la forma que este servicio ya venía
imprimiendo**. Si esa valida, la otra ni se consulta. El conjunto de PDF con timbre
verificable solo puede crecer.

Si `cryptography` no está disponible, `elegir_ted` devuelve la forma de siempre:
la mejora se apaga sola en vez de romper el renderizado.
"""

import base64
import re

_RE_DD = re.compile(r"<DD>.*?</DD>", re.S)
_RE_FRMT = re.compile(r"<FRMT[^>]*>(.*?)</FRMT>", re.S)
_RE_MOD = re.compile(r"<M>(.*?)</M>", re.S)
_RE_EXP = re.compile(r"<E>(.*?)</E>", re.S)

# El SII firma y espera el TED en ISO-8859-1; el DD se pasa a bytes con esa misma
# codificación para verificar sobre exactamente lo que se firmó (ver barcode.py).
_ENCODING_TED = "iso-8859-1"


def dd_valida(ted: str) -> bool:
    """¿La firma del emisor cuadra con el `<DD>` que trae este TED?

    False también cuando falta algo o no se puede verificar: quien llama solo lo
    usa para preferir una forma sobre otra, nunca para rechazar un documento.
    """
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ImportError:
        return False

    dd = _RE_DD.search(ted)
    frmt = _RE_FRMT.search(ted)
    mod = _RE_MOD.search(ted)
    exp = _RE_EXP.search(ted)
    if not (dd and frmt and mod and exp):
        return False

    def _n(b64: str) -> int:
        return int.from_bytes(base64.b64decode(b64.strip()), "big")

    try:
        pub = rsa.RSAPublicNumbers(_n(exp.group(1)), _n(mod.group(1))).public_key()
        pub.verify(
            base64.b64decode(frmt.group(1).strip()),
            dd.group(0).encode(_ENCODING_TED),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return True
    except Exception:
        return False


def _sin_saltos_entre_tags(ted: str) -> str:
    """Quita la indentación **entre** tags y deja intacto el texto de cada campo.

    Es la forma que firman emisores como Banco de Chile: compactan el XML al
    firmar pero su glosa lleva espacios propios (`SERVICIO  `) que `clean_ted`
    colapsa junto con la indentación, rompiendo el timbre.
    """
    return re.sub(r">\s+<", "><", ted.strip())


def variantes(ted_normalizado: str, ted_crudo: str):
    """Las formas candidatas, en orden de preferencia.

    La primera es siempre la que este servicio ya venía imprimiendo: si esa
    valida, ninguna otra llega a probarse y el PDF sale idéntico al de antes.
    """
    yield ted_normalizado
    if ted_crudo:
        yield _sin_saltos_entre_tags(ted_crudo)
        yield ted_crudo


def elegir_ted(ted_normalizado: str, ted_crudo: str = "", cabe=None) -> str:
    """La forma del TED que se imprime: la primera que la firma del emisor valide.

    `cabe` permite a quien llama descartar una forma que no entre en el símbolo
    PDF417 (tope de 928 palabras de código); sin él no se descarta ninguna.
    """
    if not ted_crudo or ted_crudo == ted_normalizado:
        return ted_normalizado
    for cand in variantes(ted_normalizado, ted_crudo):
        if dd_valida(cand) and (cabe is None or cabe(cand)):
            return cand
    return ted_normalizado


def extraer_teds_crudos(xml: bytes) -> dict:
    """`{(tipo_dte, folio): TED tal cual está en el XML}`.

    Se saca con expresión regular sobre los bytes originales a propósito: parsear
    y volver a serializar es justamente lo que pierde el formato que la firma
    cubre. Se indexa por (tipo, folio) —los dos campos del propio DD— para que un
    sobre con varios documentos empareje cada TED con el suyo y no por posición.
    """
    salida = {}
    for m in re.finditer(rb"<TED[ >].*?</TED>", xml, re.S):
        crudo = m.group(0).decode(_ENCODING_TED)
        dd = _RE_DD.search(crudo)
        if not dd:
            continue
        td = re.search(r"<TD>(\d+)</TD>", dd.group(0))
        folio = re.search(r"<F>(\d+)</F>", dd.group(0))
        if td and folio:
            salida[(td.group(1), folio.group(1))] = crudo
    return salida
