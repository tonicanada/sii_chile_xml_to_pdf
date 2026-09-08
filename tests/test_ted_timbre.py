"""
Qué forma del TED se imprime en el código de barras.

Los DTE de estos tests se firman aquí mismo, con un par de claves generado al
vuelo: así se prueba la regla —no una muestra concreta— y no entran al repo datos
tributarios de terceros.
"""

import base64
import re

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from sii_xml_pdf.barcode import _ted_a_imprimir, clean_ted
from sii_xml_pdf.ted import dd_valida, elegir_ted, extraer_teds_crudos


def _ted(dd: str, clave) -> str:
    """Un TED cuyo FRMT firma exactamente el `dd` que se le pasa."""
    firma = clave.sign(dd.encode("iso-8859-1"), padding.PKCS1v15(), hashes.SHA1())
    nums = clave.public_key().public_numbers()

    def _b64(n: int) -> str:
        return base64.b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).decode()

    # La RSAPK va DENTRO del DD (en el CAF), así que el DD ya la trae: aquí solo
    # se envuelve el DD firmado con su FRMT.
    return f'<TED version="1.0">{dd}<FRMT algoritmo="SHA1withRSA">' + \
        base64.b64encode(firma).decode() + "</FRMT></TED>"


def _dd(it1: str, clave, indentado: bool = False) -> str:
    nums = clave.public_key().public_numbers()

    def _b64(n: int) -> str:
        return base64.b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).decode()

    caf = (
        '<CAF version="1.0"><DA><RE>76000000-0</RE><RS>EMISOR SPA</RS><TD>33</TD>'
        f"<RNG><D>1</D><H>100</H></RNG><FA>2026-01-01</FA>"
        f"<RSAPK><M>{_b64(nums.n)}</M><E>{_b64(nums.e)}</E></RSAPK><IDK>100</IDK></DA></CAF>"
    )
    cuerpo = (
        "<RE>76000000-0</RE><TD>33</TD><F>42</F><FE>2026-01-01</FE>"
        f"<RR>77000000-0</RR><RSR>RECEPTOR SPA</RSR><MNT>1000</MNT><IT1>{it1}</IT1>"
        f"{caf}<TSTED>2026-01-01T10:00:00</TSTED>"
    )
    if indentado:
        cuerpo = cuerpo.replace("><", ">\n<")
    return f"<DD>{cuerpo}</DD>"


@pytest.fixture(scope="module")
def clave():
    return rsa.generate_private_key(public_exponent=65537, key_size=1024)


def test_emisor_que_firma_con_espacios_significativos(clave):
    """El caso que rompía: la glosa lleva dos espacios y normalizar los come."""
    dd = _dd("COMISION POR SERVICIO  ", clave)  # dos espacios al final
    ted = _ted(dd, clave)

    assert not dd_valida(clean_ted(ted)), "normalizar debería romper este timbre"
    assert dd_valida(ted), "el TED crudo es el que la firma respalda"
    assert dd_valida(_ted_a_imprimir(ted, ted, 17)), "se imprime el que valida"


def test_emisor_que_firma_compacto_y_guarda_indentado(clave):
    """El caso mayoritario: normalizar es justo lo que recupera la forma firmada."""
    dd_firmado = _dd("SERVICIO", clave)
    ted_firmado = _ted(dd_firmado, clave)
    # el XML guardado después, con saltos de línea entre tags
    ted_indentado = ted_firmado.replace("><", ">\n<")

    assert not dd_valida(ted_indentado), "el crudo indentado no valida"
    assert dd_valida(clean_ted(ted_indentado)), "normalizar lo recupera"
    assert dd_valida(_ted_a_imprimir(ted_indentado, ted_indentado, 17))


def test_emisor_que_compacta_al_firmar_pero_deja_espacios_en_la_glosa(clave):
    """El caso del Banco de Chile: ni el crudo ni el normalizado sirven.

    Firma el DD compactado —sin indentación— pero su glosa lleva dos espacios que
    `clean_ted` colapsa. La forma buena es la intermedia: quitar la indentación
    entre tags y no tocar el texto de los campos.
    """
    dd_firmado = _dd("COMISION POR SERVICIO  ", clave)
    ted_firmado = _ted(dd_firmado, clave)
    ted_guardado = ted_firmado.replace("><", ">\n<")  # el XML se indenta después

    assert not dd_valida(ted_guardado), "el crudo indentado no valida"
    assert not dd_valida(clean_ted(ted_guardado)), "normalizar come el doble espacio"
    assert dd_valida(_ted_a_imprimir(ted_guardado, ted_guardado, 17))


def test_nunca_empeora_cuando_ninguna_forma_valida(clave):
    """Sin forma válida se imprime lo de siempre: el cambio no altera este caso."""
    ted = _ted(_dd("GLOSA", clave), clave).replace("<MNT>1000</MNT>", "<MNT>9999</MNT>")
    assert _ted_a_imprimir(ted, ted, 17) == clean_ted(ted)


def test_sin_ted_crudo_se_comporta_como_antes(clave):
    ted = _ted(_dd("GLOSA", clave), clave)
    assert _ted_a_imprimir(ted, "", 17) == clean_ted(ted)


def test_elegir_prefiere_lo_que_ya_se_imprimia(clave):
    """Si el normalizado valida, el crudo ni se consulta."""
    dd = _dd("SERVICIO", clave)
    ted = _ted(dd, clave)
    assert elegir_ted(clean_ted(ted), "cualquier cosa") == clean_ted(ted)


def test_teds_crudos_se_emparejan_por_tipo_y_folio(clave):
    """En un sobre con varios DTE, cada TED va con su documento, no por posición."""
    a = _ted(_dd("UNO", clave), clave)
    b = _ted(_dd("DOS", clave), clave).replace("<F>42</F>", "<F>43</F>")
    sobre = f"<SetDTE>{a}{b}</SetDTE>".encode("iso-8859-1")

    crudos = extraer_teds_crudos(sobre)
    assert set(crudos) == {("33", "42"), ("33", "43")}
    assert "UNO" in crudos[("33", "42")] and "DOS" in crudos[("33", "43")]
