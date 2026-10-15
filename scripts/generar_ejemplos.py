"""
Genera los XML de `examples/input/`: cuatro facturas (DTE 33) **ficticias**.

Hasta octubre de 2026 los ejemplos eran facturas reales de 2021 con los RUT y
nombres cambiados a mano, y la anonimización dejaba pasar datos: RUT reales en el
atributo `ID`, y en la firma XML el certificado de la persona que firmó. Por eso
ahora se generan de cero y nada sale de un documento real.

- Empresas, RUT, direcciones, ítems y montos son inventados. Los RUT son de la
  serie 11111111-1, 22222222-2, … que no corresponde a contribuyentes.
- El CAF y el timbre (TED) se firman con claves RSA que se crean en cada corrida y
  se descartan: `<FRMT>` es una firma válida del `<DD>` (el renderer la verifica
  para elegir qué forma imprimir), pero ni el SII ni nadie emitió ese CAF.
- No llevan firma XML (`<Signature>`): el renderer no la usa, y un certificado,
  aunque sea de prueba, es justo lo que no tiene que volver a colarse.

Uso, desde la raíz del repo:

    python scripts/generar_ejemplos.py
"""

import base64
from pathlib import Path
from xml.sax.saxutils import escape

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

SALIDA = Path(__file__).resolve().parent.parent / "examples" / "input"

RECEPTOR = {
    "rut": "11111111-1",
    "razon": "Constructora Ejemplo S.A.",
    "giro": "Construcción de edificios",
    "direccion": "Av. Ficticia 1234, oficina 56",
    "comuna": "Providencia",
    "ciudad": "Santiago",
}


def _b64(n: int) -> str:
    return base64.b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).decode()


def _firmar(llave, texto: str) -> str:
    firma = llave.sign(texto.encode("iso-8859-1"), padding.PKCS1v15(), hashes.SHA1())
    return base64.b64encode(firma).decode()


def _nueva_llave():
    # 1024 bits, como los CAF que entrega el SII.
    return rsa.generate_private_key(public_exponent=65537, key_size=1024)


def ted(emisor: dict, folio: int, fecha: str, total: int, item1: str, tstamp: str) -> str:
    """El timbre completo, en una línea: es la forma que se firma y la que se imprime."""
    llave_caf, llave_sii = _nueva_llave(), _nueva_llave()
    pub = llave_caf.public_key().public_numbers()
    da = (
        f"<DA><RE>{emisor['rut']}</RE><RS>{escape(emisor['razon'][:40])}</RS><TD>33</TD>"
        f"<RNG><D>{folio}</D><H>{folio + 99}</H></RNG><FA>{fecha}</FA>"
        f"<RSAPK><M>{_b64(pub.n)}</M><E>{_b64(pub.e)}</E></RSAPK><IDK>100</IDK></DA>"
    )
    caf = f'<CAF version="1.0">{da}<FRMA algoritmo="SHA1withRSA">{_firmar(llave_sii, da)}</FRMA></CAF>'
    dd = (
        f"<DD><RE>{emisor['rut']}</RE><TD>33</TD><F>{folio}</F><FE>{fecha}</FE>"
        f"<RR>{RECEPTOR['rut']}</RR><RSR>{escape(RECEPTOR['razon'][:40])}</RSR><MNT>{total}</MNT>"
        f"<IT1>{escape(item1[:40])}</IT1>{caf}<TSTED>{tstamp}</TSTED></DD>"
    )
    return f'<TED version="1.0">{dd}<FRMT algoritmo="SHA1withRSA">{_firmar(llave_caf, dd)}</FRMT></TED>'


def _tag(nombre: str, valor) -> str:
    return f"<{nombre}>{escape(str(valor))}</{nombre}>"


def dte(emisor: dict, folio: int, fecha: str, items: list, *, id_doc_extra: str = "",
        emisor_extra: str = "", receptor_extra: str = "", referencias: list = (),
        hora: str = "10:15:00") -> str:
    """Una factura afecta. Los totales salen de los ítems: cuadran por construcción."""
    detalle = []
    for n, it in enumerate(items, start=1):
        monto = round(it["qty"] * it["precio"])
        it["monto"] = monto
        codigo = (f"<CdgItem><TpoCodigo>INT1</TpoCodigo>{_tag('VlrCodigo', it['codigo'])}</CdgItem>"
                  if it.get("codigo") else "")
        dsc = _tag("DscItem", it["dsc"]) if it.get("dsc") else ""
        unidad = _tag("UnmdItem", it["unidad"]) if it.get("unidad") else ""
        detalle.append(
            f"<Detalle><NroLinDet>{n}</NroLinDet>{codigo}{_tag('NmbItem', it['nombre'])}{dsc}"
            f"<QtyItem>{it['qty']:.2f}</QtyItem>{unidad}<PrcItem>{it['precio']}</PrcItem>"
            f"<MontoItem>{monto}</MontoItem></Detalle>"
        )
    neto = sum(it["monto"] for it in items)
    iva = round(neto * 0.19)
    total = neto + iva

    refs = "".join(
        f"<Referencia><NroLinRef>{n}</NroLinRef>{_tag('TpoDocRef', r[0])}{_tag('FolioRef', r[1])}"
        f"{_tag('FchRef', r[2])}</Referencia>"
        for n, r in enumerate(referencias, start=1)
    )
    timbre = ted(emisor, folio, fecha, total, items[0]["nombre"], f"{fecha}T{hora}")

    return f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<!-- Documento FICTICIO, generado por scripts/generar_ejemplos.py. No es una factura real. -->
<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
<Documento ID="F{folio}T33">
<Encabezado>
<IdDoc><TipoDTE>33</TipoDTE><Folio>{folio}</Folio><FchEmis>{fecha}</FchEmis>{id_doc_extra}</IdDoc>
<Emisor>{_tag('RUTEmisor', emisor['rut'])}{_tag('RznSoc', emisor['razon'])}{_tag('GiroEmis', emisor['giro'])}{emisor_extra}{_tag('DirOrigen', emisor['direccion'])}{_tag('CmnaOrigen', emisor['comuna'])}{_tag('CiudadOrigen', emisor['ciudad'])}</Emisor>
<Receptor>{_tag('RUTRecep', RECEPTOR['rut'])}{_tag('RznSocRecep', RECEPTOR['razon'])}{_tag('GiroRecep', RECEPTOR['giro'])}{receptor_extra}{_tag('DirRecep', RECEPTOR['direccion'])}{_tag('CmnaRecep', RECEPTOR['comuna'])}{_tag('CiudadRecep', RECEPTOR['ciudad'])}</Receptor>
<Totales><MntNeto>{neto}</MntNeto><MntExe>0</MntExe><TasaIVA>19</TasaIVA><IVA>{iva}</IVA><MntTotal>{total}</MntTotal></Totales>
</Encabezado>
{chr(10).join(detalle)}
{refs}
{timbre}
<TmstFirma>{fecha}T{hora}</TmstFirma>
</Documento>
</DTE>
"""


# ── los cuatro ejemplos ─────────────────────────────────────────────────────────────

FERRETERIA = {
    "rut": "77777777-7", "razon": "Ferretería La Esquina S.A.",
    "giro": "Venta de materiales de construcción", "direccion": "Camino Ejemplo 8000",
    "comuna": "Quilicura", "ciudad": "Santiago",
}
LIBRERIA = {
    "rut": "88888888-8", "razon": "Librería Ejemplo SpA", "giro": "Librería",
    "direccion": "Calle Inventada 297", "comuna": "Coquimbo", "ciudad": "Coquimbo",
}
CENTRO = {
    "rut": "22222222-2", "razon": "Centro Hermanos SpA",
    "giro": "Ferretería y materiales de construcción", "direccion": "Pasaje Modelo 4201",
    "comuna": "Renca", "ciudad": "Santiago",
}

HERRAMIENTAS = [
    ("000101", "Llave punta corona 6 mm", 6, 1290),
    ("000102", "Llave punta corona 8 mm", 6, 1390),
    ("000201", "Dado 1/2 hexagonal 6 mm", 3, 1190),
    ("000202", "Dado 1/2 hexagonal 18 mm", 3, 1300),
    ("000203", "Dado 1/2 hexagonal 19 mm", 3, 1374),
    ("000301", "Broca escalonada 6-30 mm", 1, 45990),
    ("000401", "Cuchillo cartonero 18 mm", 10, 1990),
    ("000402", "Hoja cuchillo 18 mm x10", 3, 490),
    ("000501", "Aceite penetrante 311 g", 2, 5340),
    ("000502", "Diluyente xileno 1 L", 6, 1350),
    ("000601", "Lima plana 8 pulgadas", 1, 1920),
    ("000602", "Lima redonda 8 pulgadas", 1, 2195),
    ("000603", "Sacaclavos 12 pulgadas", 2, 1950),
    ("000604", "Maceta de goma 24 oz", 2, 5040),
    ("000301", "Broca escalonada 6-30 mm", 4, 45990),
    ("000701", "Casco de seguridad amarillo", 12, 3890),
    ("000702", "Guante de cabritilla (par)", 24, 1490),
    ("000703", "Lente de seguridad claro", 24, 990),
    ("000704", "Tapón auditivo (caja 100)", 2, 12990),
    ("000801", "Huincha de medir 5 m", 6, 3490),
    ("000802", "Nivel de aluminio 24 pulgadas", 3, 10412),
    ("000803", "Escuadra 12 pulgadas", 2, 4290),
    ("000901", "Disco de corte metal 9 pulgadas", 10, 2261),
    ("000902", "Disco de desbaste 4,5 pulgadas", 10, 1590),
    ("001001", "Clavo corriente 4 pulg. 1 kg", 20, 1529),
    ("001002", "Tornillo volcanita x100", 8, 2190),
    ("001003", "Tarugo 8 mm x100", 5, 1890),
    ("001101", "Silicona transparente 280 ml", 12, 2990),
    ("001102", "Cinta de enmascarar 48 mm", 12, 1290),
    ("001103", "Manga plástica negra 4x10 m", 2, 9235),
    ("001104", "Brocha 3 pulgadas", 6, 1690),
]

REFERENCIAS = [
    ("802", "NP-1207", "2026-08-31"),
    ("801", "OC-4471", "2026-08-31"),
    ("NV", "2318", "2026-08-31"),
    ("52", "10452", "2026-09-04"),
    ("52", "10467", "2026-09-06"),
]

CREDITO = ("<FmaPago>2</FmaPago><TermPagoCdg>9</TermPagoCdg>"
           "<TermPagoGlosa>Cuenta corriente 30 días</TermPagoGlosa><TermPagoDias>30</TermPagoDias>"
           "<FchVenc>2026-10-30</FchVenc>")
CONTACTOS_CENTRO = ("<Telefono>220000000</Telefono><CorreoEmisor>ventas@ejemplo.cl</CorreoEmisor>"
                    "<Acteco>475201</Acteco><CdgVendedor>6</CdgVendedor>")
CONTACTO_RECEPTOR = "<Contacto>Encargado de compras</Contacto><CorreoRecep>compras@ejemplo.cl</CorreoRecep>"


def _items(filas):
    return [{"codigo": c, "nombre": n, "qty": q, "precio": p, "unidad": "Unid"} for c, n, q, p in filas]


EJEMPLOS = {
    # Factura simple de servicios y venta, con descripción adicional en cada línea.
    "T33_factura_ejemplo_1.xml": lambda: dte(
        FERRETERIA, 1520, "2026-09-05",
        [
            {"nombre": 'NIVEL 24" ALUMINIO', "dsc": "Marca genérica, modelo 42-074", "qty": 1, "precio": 10412},
            {"nombre": "MANGA PLÁSTICA NEGRA 4X10 M", "dsc": "Rollo de 40 m2", "qty": 1, "precio": 9235},
            {"nombre": "LÁPIZ BICOLOR GRUESO", "dsc": "Rojo y azul", "qty": 2, "precio": 1488},
            {"nombre": 'DISCO CORTE FIERRO 9"', "dsc": "9 x 1/8 x 7/8 pulgadas", "qty": 5, "precio": 2261},
            {"nombre": "CLAVO CORRIENTE 4 X 8", "dsc": "Paquete de 1 kg", "qty": 20, "precio": 1529},
        ],
        id_doc_extra="<IndServicio>2</IndServicio><TpoTranVenta>1</TpoTranVenta><FmaPago>1</FmaPago>",
        emisor_extra="<Acteco>475201</Acteco><CdgSIISucur>81000001</CdgSIISucur>",
    ),
    # Contado, pocas líneas, sin códigos de ítem.
    "T33_factura_ejemplo_2.xml": lambda: dte(
        LIBRERIA, 87, "2026-09-02",
        [
            {"nombre": "SEPARADOR OFICIO", "qty": 2, "precio": 840},
            {"nombre": "ARCHIVADOR OFICIO", "qty": 2, "precio": 1513},
            {"nombre": "SEPARADOR DE HOJAS", "qty": 1, "precio": 714},
            {"nombre": "LÁPIZ PASTA AZUL", "qty": 2, "precio": 294},
        ],
        id_doc_extra="<TpoTranCompra>1</TpoTranCompra><TpoTranVenta>1</TpoTranVenta><FmaPago>1</FmaPago>",
        emisor_extra="<CdgSIISucur>81000002</CdgSIISucur>",
    ),
    # Crédito a 30 días, con referencias y códigos de ítem: la del README.
    "T33_factura_ejemplo_3.xml": lambda: dte(
        CENTRO, 3401, "2026-09-30", _items(HERRAMIENTAS[:10]),
        id_doc_extra=CREDITO, emisor_extra=CONTACTOS_CENTRO, receptor_extra=CONTACTO_RECEPTOR,
        referencias=REFERENCIAS, hora="11:49:26",
    ),
    # La misma, con 31 líneas: sirve para ver el salto de página.
    "T33_factura_ejemplo_4.xml": lambda: dte(
        CENTRO, 3402, "2026-09-30", _items(HERRAMIENTAS),
        id_doc_extra=CREDITO, emisor_extra=CONTACTOS_CENTRO, receptor_extra=CONTACTO_RECEPTOR,
        referencias=REFERENCIAS, hora="11:52:03",
    ),
}


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, generar in EJEMPLOS.items():
        (SALIDA / nombre).write_bytes(generar().encode("iso-8859-1"))
        print(f"escrito {SALIDA / nombre}")


if __name__ == "__main__":
    main()
