import xml.etree.ElementTree as ET
from typing import List, Union
from pathlib import Path
from .models import DTEData, Item, Referencia, Impuesto
from .ns import x
import re

REL_TIPO_DOC = {
    "30": "Factura",
    "32": "Factura bienes/servicios",
    "35": "Boleta",
    "38": "Boleta Exenta",
    "45": "Factura de Compra",
    "55": "Nota de Débito", "60": "Nota de Crédito",
    "103": "Liquidación", "40": "Liquidación-Factura", "43": "Liquidación-Factura Electrónica",
    "33": "Factura Electrónica", "34": "Factura Exenta Electrónica",
    "39": "Boleta Electrónica", "41": "Boleta Exenta Electrónica",
    "46": "Factura de Compra Electrónica", "56": "Nota de Débito Electrónica",
    "61": "Nota de Crédito Electrónica",
    "50": "Guía de Despacho", "52": "Guía de Despacho Electrónica",
    "110": "Factura de Exportación Electrónica", "111": "Nota de Débito de Exportación",
    "112": "Nota de Crédito de Exportación",
    "801": "Orden de Compra", "802": "Nota de pedido", "803": "Contrato", "804": "Resolución",
    "805": "Proceso ChileCompra", "806": "Ficha ChileCompra", "807": "DUS",
    "808": "B/L", "809": "AWB", "810": "MIC/DTA", "811": "Carta de Porte",
    "812": "Resolución SNA Servicios Exportación", "813": "Pasaporte",
    "814": "Certificado Depósito Bolsa", "815": "Vale de Prenda Bolsa",
    "820": "Registro Plazo de Pago Excepcional",
    "OV": "Orden de Venta",
    "VTA": "Venta",
    "NV": "Nota de Venta"
}

REL_IMP = {
    "14": "IVA margen comercialización", "15": "IVA retenido total", "17": "IVA anticipo faenamiento carne",
    "18": "IVA anticipado carne", "19": "IVA anticipado carne", "27": "DL 825/74 Art.42 a)",
    "30": "IVA retenido legumbres", "31": "IVA retenido silvestres", "32": "IVA retenido ganado",
    "33": "IVA retenido madera", "34": "IVA retenido trigo", "36": "IVA retenido arroz",
    "37": "IVA retenido hidrobiológicas", "38": "IVA retenido chatarra", "39": "IVA retenido PPA",
    "41": "IVA retenido construcción", "23": "Imp. adicional Art 37 a,b,c",
    "44": "Imp. adicional Art 37 e,h,i,l", "45": "Imp. adicional Art 37 j",
    "24": "Imp. Art 42 Ley 825/74 a", "25": "Imp. Art 42 c", "26": "Imp. Art 42 c",
    "27": "Imp. Bebidas Art 42 d,e", "28": "Imp. específico diésel",
    "29": "Recup. específico diésel transportistas", "35": "Imp. específico gasolina",
    "47": "IVA retenido cartones", "48": "IVA retenido frambuesas/pasas", "49": "Factura compra sin retención",
    "50": "IVA margen prepago", "51": "Imp. gas natural comprimido", "52": "Imp. gas licuado",
    "53": "Imp. retenido suplementeros", "60": "IVA retenido factura inicio",
    "271": "DL 825/74, Art.42 a) Inc. 2º"
}

REL_FORMA_PAGO = {
    0: "Sin información",
    1: "Contado",
    2: "Crédito",
    3: "Gratuito"
}


def _text(el):
    return el.text if el is not None and el.text is not None else None


def _int_text(el, default=0):
    try:
        t = _text(el)
        return int(str(t).strip()) if t not in (None, "") else default
    except Exception:
        return default


def _float_text(el, default=0.0):
    try:
        t = _text(el)
        return float(str(t).replace(",", ".").strip()) if t not in (None, "") else default
    except Exception:
        return default


def _forma_pago_palabras(forma: int) -> str:
    return REL_FORMA_PAGO.get(forma, f"Desconocido ({forma})")


def _format_rut(rut: str) -> str:
    """
    Formatea un RUT chileno a la forma 12.345.678-9
    """
    if not rut:
        return ""

    rut = rut.strip().upper()   # quita espacios y pone DV en mayúscula
    rut = rut.replace(".", "").replace("-", "")

    if len(rut) < 2:
        return rut  # inválido

    cuerpo, dv = rut[:-1], rut[-1]

    # poner puntos cada 3 dígitos desde la derecha
    cuerpo_formateado = ""
    while len(cuerpo) > 3:
        cuerpo_formateado = "." + cuerpo[-3:] + cuerpo_formateado
        cuerpo = cuerpo[:-3]
    cuerpo_formateado = cuerpo + cuerpo_formateado

    return f"{cuerpo_formateado}-{dv}"


def _proper_case(text: str) -> str:
    if not text:
        return ""

    # Palabras que deben ir en minúscula salvo si son la primera
    lowercase_words = {
        "de", "del", "para", "por", "con", "sin",
        "y", "o", "u", "en", "a", "al", "la", "las",
        "el", "los", "un", "una", "unos", "unas"
    }

    # Siglas conocidas que deben conservar mayúsculas
    keep_upper = {"S.A.", "SA", "SPA", "EIRL", "LTDA"}

    words = text.split()
    result = []

    for i, w in enumerate(words):
        # Si la palabra está en lista de siglas → respetar mayúsculas
        if w.upper() in keep_upper:
            result.append(w.upper())
            continue

        wl = w.lower()
        if i == 0 or wl not in lowercase_words:
            result.append(wl.capitalize())
        else:
            result.append(wl)

    return " ".join(result)


def _tipo_dte_palabras_y_abrev(tipo: int):
    m = {
        33: ("FACTURA ELECTRÓNICA", "FC"),
        34: ("FACTURA EXENTA ELECTRÓNICA", "FC"),
        30: ("AFECTA", "FC"),
        43: ("LIQUIDACIÓN-FACTURA ELECTRÓNICA", "LFE"),
        46: ("FACTURA DE COMPRA ELECTRÓNICA", "FCI"),
        52: ("GUÍA DE DESPACHO ELECTRÓNICA", "GD"),
        56: ("NOTA DE DÉBITO ELECTRÓNICA", "ND"),
        61: ("NOTA DE CRÉDITO ELECTRÓNICA", "NC"),
        110: ("FACTURA DE EXPORTACIÓN", "FEXP"),
        111: ("NOTA DE DÉBITO DE EXPORTACIÓN", "NDE"),
        112: ("NOTA DE CRÉDITO DE EXPORTACIÓN", "NCE"),
    }
    return m.get(tipo, (str(tipo), f"T{tipo}"))


def _forma_pago_palabras(forma: int) -> str:
    return REL_FORMA_PAGO.get(forma, f"Desconocido ({forma})")


def parse_xml(xml: Union[str, bytes, Path]) -> DTEData:
    if isinstance(xml, (str, Path)):
        tree = ET.parse(str(xml))
    else:
        # bytes → usar fromstring
        root = ET.fromstring(xml)
        tree = ET.ElementTree(root)

    root = tree.getroot()

    # Emisor
    rut_proveedor = _format_rut(_text(root.find(f".//{x('RUTEmisor')}")) or "")
    razon_social = _text(root.find(f".//{x('RznSoc')}")) or ""
    giro_proveedor = _proper_case(_text(root.find(f".//{x('GiroEmis')}")))
    direccion_proveedor = _proper_case(
        _text(root.find(f".//{x('DirOrigen')}")))
    ciudad_proveedor = _proper_case(
        _text(root.find(f".//{x('CiudadOrigen')}")))
    comuna_proveedor = _proper_case(_text(root.find(f".//{x('CmnaOrigen')}")))

    # Receptor
    receptor_rut  = _format_rut(_text(root.find(f".//{x('RUTRecep')}")) or "")
    receptor_razon_social = _text(root.find(f".//{x('RznSocRecep')}")) or ""
    receptor_giro = _proper_case(_text(root.find(f".//{x('GiroRecep')}")))
    receptor_direccion = _proper_case(_text(root.find(f".//{x('DirRecep')}")))
    receptor_ciudad = _proper_case(
        _text(root.find(f".//{x('CiudadRecep')}")) or "")
    receptor_comuna = _proper_case(
        _text(root.find(f".//{x('CmnaRecep')}")) or "")

    # Encabezado
    forma_pago = _int_text(root.find(f".//{x('FmaPago')}"), default=0)
    fecha_vencimiento = _text(root.find(f".//{x('FchVenc')}"))
    monto_neto = _int_text(root.find(f".//{x('MntNeto')}"))
    monto_total = _int_text(root.find(f".//{x('MntTotal')}"))
    numero_factura = (
        _text(root.find(f".//{x('Folio')}")) or "").lstrip("0") or "0"
    fecha_emision = _text(root.find(f".//{x('FchEmis')}")) or ""
    tipo_dte = _int_text(root.find(f".//{x('TipoDTE')}"))
    monto_iva = _int_text(root.find(f".//{x('IVA')}"))
    monto_exento = _int_text(root.find(f".//{x('MntExe')}"))

    tipo_pal, abrev = _tipo_dte_palabras_y_abrev(tipo_dte)
    forma_pal = _forma_pago_palabras(forma_pago)

    # Extraer todo el nodo TED
    ted_el = root.find(f".//{x('TED')}")
    timbre_str = ""
    if ted_el is not None:
        timbre_str = ET.tostring(ted_el, encoding="unicode", method="xml")
        # elimina xmlns y prefijos ns0:
        timbre_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', timbre_str)
        timbre_str = re.sub(r'\bns\d+:', '', timbre_str)

    # Items
    items: List[Item] = []
    for det in root.findall(f".//{x('Detalle')}"):
        cod = _text(det.find(f".//{x('VlrCodigo')}")) or "0"
        qty = _float_text(det.find(x("QtyItem")), default=1.0)
        rate = _float_text(det.find(x("PrcItem")), default=0.0)
        total = _int_text(det.find(x("MontoItem")),
                          default=int(round(qty * rate)))

        nmb = _text(det.find(x("NmbItem"))) or ""
        dsc = _text(det.find(x("DscItem"))) or ""

        if nmb and dsc:
            desc = f"{nmb} - {dsc}"
        else:
            desc = nmb or dsc

        items.append(Item(qty=qty, rate=rate, descripcion=desc,
                     total=total, codigo=cod))

    # Referencias
    refs: List[Referencia] = []
    for r in root.findall(f".//{x('Referencia')}"):
        tpo = _text(r.find(x("TpoDocRef"))) or ""
        folio = _text(r.find(x("FolioRef"))) or ""
        fch = _text(r.find(x("FchRef"))) or ""
        refs.append(Referencia(
            tipo_doc_referencia=tpo,
            tipo_doc_referencia_palabras=REL_TIPO_DOC.get(str(tpo), str(tpo)),
            folio_referencia=folio,
            fecha_referencia=fch,
        ))

    # Impuestos
    imps: List[Impuesto] = []
    for i in root.findall(f".//{x('ImptoReten')}"):
        tipo = _text(i.find(x("TipoImp"))) or ""
        monto = _int_text(i.find(x("MontoImp")), default=0)
        imps.append(
            Impuesto(tipo=tipo, tipo_palabras=REL_IMP.get(tipo, tipo), monto=monto))

    return DTEData(
        rut_proveedor=rut_proveedor,
        razon_social=razon_social,
        giro_proveedor=giro_proveedor,
        direccion_proveedor=direccion_proveedor,
        ciudad_proveedor=ciudad_proveedor,
        comuna_proveedor=comuna_proveedor,
        receptor_rut=receptor_rut,
        receptor_razon_social=receptor_razon_social,
        receptor_giro=receptor_giro,
        receptor_direccion=receptor_direccion,
        receptor_ciudad=receptor_ciudad,
        receptor_comuna=receptor_comuna,
        forma_pago=forma_pago,
        forma_pago_palabras=forma_pal,
        fecha_vencimiento=fecha_vencimiento,
        monto_neto=monto_neto,
        monto_total=monto_total,
        monto_iva=monto_iva,
        monto_exento=monto_exento,
        numero_factura=numero_factura,
        fecha_emision=fecha_emision,
        tipo_dte=tipo_dte,
        tipo_dte_palabras=tipo_pal,
        tipo_dte_abreviatura=abrev,
        timbre_xml=timbre_str,
        items=items,
        referencias=refs,
        impuestos=imps,
    )
