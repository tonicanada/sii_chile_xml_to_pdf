from pydantic import BaseModel
from typing import List, Optional

class Item(BaseModel):
    qty: float
    rate: float
    descripcion: str
    total: int
    codigo: str = "0"
    # DescuentoMonto / RecargoMonto de la línea. MontoItem ya viene neto de ellos; sin
    # imprimirlos, la línea no cuadra (cantidad × precio ≠ valor) y el Set de Pruebas del
    # SII lo exige: «los descuentos por línea o globales deben ser indicados en las
    # representaciones impresas».
    descuento: int = 0
    recargo: int = 0
    exento: bool = False

class Referencia(BaseModel):
    tipo_doc_referencia: str
    tipo_doc_referencia_palabras: str
    folio_referencia: str
    fecha_referencia: str
    # `CodRef` y `RazonRef` del XSD: qué le hace al documento referenciado y por qué.
    # Son opcionales en el esquema —una referencia a una orden de compra no "le hace"
    # nada—, pero en una nota de crédito son lo que la explica: sin ellos el PDF dice
    # qué documento corrige y no si lo anula ni por qué motivo.
    codigo_referencia: str = ""
    codigo_referencia_palabras: str = ""
    razon_referencia: str = ""

class Impuesto(BaseModel):
    tipo: str
    tipo_palabras: str
    monto: int

class DTEData(BaseModel):
    # Emisor
    rut_proveedor: str
    razon_social: str
    giro_proveedor: Optional[str] = None
    direccion_proveedor: Optional[str] = None
    ciudad_proveedor: Optional[str] = None
    comuna_proveedor: Optional[str] = None

    # Receptor
    receptor_rut: str
    receptor_razon_social: str
    receptor_giro: Optional[str] = None
    receptor_direccion: Optional[str] = None
    receptor_ciudad: Optional[str] = None
    receptor_comuna: Optional[str] = None

    # Encabezado
    forma_pago: int
    forma_pago_palabras: str
    fecha_vencimiento: Optional[str] = None
    monto_neto: int
    monto_total: int
    monto_iva: int
    monto_exento: int
    # Crédito Especial Empresas Constructoras (Totales/CredEC del DTE,
    # Art. 21 DL 910). Opcional: solo lo traen las facturas que lo usan.
    # MntTotal ya viene neteado de este crédito, así que sin imprimirlo
    # la muestra impresa no cuadra: neto + exento + IVA - CredEC = total.
    credito_especial_constructora: int = 0
    # DscRcgGlobal: el monto ya resuelto (si viene en %, sobre los ítems que afecta).
    descuento_global: int = 0
    recargo_global: int = 0
    # ImptoReten de retención (15 = IVA retenido total, 30-41 = retenciones de productos
    # específicos). No se suman al total: se restan. Van aparte de los demás impuestos para
    # que el PDF no diga «Impuestos» por algo que el comprador retiene.
    retenciones: int = 0
    numero_factura: str
    fecha_emision: str
    tipo_dte: int
    tipo_dte_palabras: str
    tipo_dte_abreviatura: str

    # Otros
    timbre_xml: str
    # El TED tal como está en el XML, byte a byte. El de arriba pasa por
    # ET.tostring() y pierde el formato que la firma del emisor cubre.
    timbre_xml_crudo: str = ""

    # Detalles
    items: List[Item]
    referencias: List[Referencia]
    impuestos: List[Impuesto]
