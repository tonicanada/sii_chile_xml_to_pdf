#!/usr/bin/python
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import json


class DTE:

    def __init__(self, tree_path):

        try:
            self.tree_path = tree_path
            self.tree = ET.parse(tree_path)
            self.es_respuesta()
            self.parse_encabezado()
            self.asignar_tipo_dte_palabras()
            self.asignar_forma_pago_palabras()
            self.parse_items()
            self.parse_referencias()
            self.parse_impuestos()
            self.bien_formado = 1
        except:
            print("ERROR AL LEER EL XML")
            self.bien_formado = 0

    def asignar_tipo_dte_palabras(self):
        if self.tipo_dte == 33:
            self.tipo_dte_palabras = "FACTURA ELECTRÓNICA"
            self.tipo_dte_abreviatura = "FC"
        elif self.tipo_dte == 34:
            self.tipo_dte_palabras = "ELECTRÓNICA EXENTA"
            self.tipo_dte_abreviatura = "FC"
        elif self.tipo_dte == 30:
            self.tipo_dte_palabras = "AFECTA"
            self.tipo_dte_abreviatura = "FC"
        elif self.tipo_dte == 43:
            self.tipo_dte_palabras = "Liquidación-Factura Electrónica"
            self.tipo_dte_abreviatura = "LFE"
        elif self.tipo_dte == 46:
            self.tipo_dte_palabras = "FACTURA DE COMPRA ELECTRÓNICA"
            self.tipo_dte_abreviatura = "FCI"  # Factura de compra Interna
        elif self.tipo_dte == 52:
            self.tipo_dte_palabras = "GUÍA DE DESPACHO ELECTRÓNICA"
            self.tipo_dte_abreviatura = "GD"
        elif self.tipo_dte == 56:
            self.tipo_dte_palabras = "NOTA DE DÉBITO ELECTRÓNICA"
            self.tipo_dte_abreviatura = "ND"
        elif self.tipo_dte == 61:
            self.tipo_dte_palabras = "NOTA DE CRÉDITO ELECTRÓNICA"
            self.tipo_dte_abreviatura = "NC"
        elif self.tipo_dte == 110:
            self.tipo_dte_palabras = "Factura de Exportación"
            self.tipo_dte_abreviatura = "FEXP"
        elif self.tipo_dte == 111:
            self.tipo_dte_palabras = "Nota de Débito de Exportación"
            self.tipo_dte_abreviatura = "NDE"
        elif self.tipo_dte == 112:
            self.tipo_dte_palabras = "Nota de Crédito de Exportación"
            self.tipo_dte_abreviatura = "NCE"

    def asignar_forma_pago_palabras(self):
        if self.forma_pago == 2:
            self.forma_pago_palabras = "CRÉDITO"
        else:
            self.forma_pago_palabras = "NO CRÉDITO"

    def parse_encabezado(self):
        # Datos emisor
        self.rut_proveedor = self.tree.find('.//{http://www.sii.cl/SiiDte}RUTEmisor').text
        self.razon_social = self.tree.find('.//{http://www.sii.cl/SiiDte}RznSoc').text
        self.giro_proveedor = self.tree.find('.//{http://www.sii.cl/SiiDte}GiroEmis').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}GiroEmis') is not None else 0
        self.direccion_proveedor = self.tree.find('.//{http://www.sii.cl/SiiDte}DirOrigen').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}DirOrigen') is not None else 0
        self.ciudad_proveedor = self.tree.find('.//{http://www.sii.cl/SiiDte}CiudadOrigen').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}CiudadOrigen') is not None else 0
        self.comuna_proveedor = self.tree.find('.//{http://www.sii.cl/SiiDte}CmnaOrigen').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}CmnaOrigen').text is not None else 0
        # # Datos receptor
        self.receptor_rut = self.tree.find('.//{http://www.sii.cl/SiiDte}RUTRecep').text
        self.receptor_razon_social = self.tree.find('.//{http://www.sii.cl/SiiDte}RznSocRecep').text
        self.receptor_giro = self.tree.find('.//{http://www.sii.cl/SiiDte}GiroRecep').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}GiroRecep') is not None else 0
        self.receptor_direccion = self.tree.find('.//{http://www.sii.cl/SiiDte}DirRecep').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}DirRecep') is not None else 0
        self.receptor_ciudad = self.tree.find('.//{http://www.sii.cl/SiiDte}CiudadRecep').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}CiudadRecep') is not None else 0
        self.receptor_comuna = self.tree.find('.//{http://www.sii.cl/SiiDte}CmnaRecep').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}CmnaRecep') is not None else 0
        # # Datos forma de pago
        self.forma_pago = int(self.tree.find('.//{http://www.sii.cl/SiiDte}FmaPago').text) if self.tree.find(
            './/{http://www.sii.cl/SiiDte}FmaPago') is not None else 0
        self.fecha_vencimiento = self.tree.find('.//{http://www.sii.cl/SiiDte}FchVenc').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}FchVenc') is not None else 0
        self.monto_neto = self.tree.find('.//{http://www.sii.cl/SiiDte}MntNeto').text \
            if self.tree.find('.//{http://www.sii.cl/SiiDte}MntNeto') is not None else 0
        self.monto_total = self.tree.find('.//{http://www.sii.cl/SiiDte}MntTotal').text \
            if self.tree.find('.//{http://www.sii.cl/SiiDte}MntTotal') is not None else 0
        self.numero_factura = self.tree.find('.//{http://www.sii.cl/SiiDte}Folio').text.lstrip("0")
        self.fecha_emision = self.tree.find('.//{http://www.sii.cl/SiiDte}FchEmis').text
        self.tipo_dte = int(self.tree.find('.//{http://www.sii.cl/SiiDte}TipoDTE').text)
        self.monto_iva = self.tree.find('.//{http://www.sii.cl/SiiDte}IVA').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}IVA') is not None else 0
        self.monto_exento = self.tree.find('.//{http://www.sii.cl/SiiDte}MntExe').text if self.tree.find(
            './/{http://www.sii.cl/SiiDte}MntExe') is not None else 0
        # Otros datos
        self.timbre = ET.tostring(self.tree.find('.//{http://www.sii.cl/SiiDte}TED'), encoding="unicode").replace(
            "ns0:", "").replace(' xmlns:ns0="http://www.sii.cl/SiiDte"', "").replace("  ", "").replace("\n",
                                                                                                       "").replace("\t",
                                                                                                                   "")

    def parse_items(self):

        self.items = []

        for i in self.tree.findall('.//{http://www.sii.cl/SiiDte}Detalle'):
            qty = i.find("{http://www.sii.cl/SiiDte}QtyItem")
            rate = i.find("{http://www.sii.cl/SiiDte}PrcItem")
            description = i.find("{http://www.sii.cl/SiiDte}NmbItem").text
            total = i.find("{http://www.sii.cl/SiiDte}MontoItem").text

            qtytext = qty.text if qty is not None else str(1)
            ratetext = rate.text if rate is not None else total

            # print (
            #    "qty = " + qtytext + ", rate = " + ratetext + ", description = " + description + ", total = " + total)

            # "warehouse": "Bodega Generica - T",

            self.items.append(
                {"qty": qtytext,
                 "rate": ratetext,
                 "item_code": "Item Generico",
                 "project": "Oficina",
                 "cost_center": "Oficina - T",
                 "descripcion": description}
            )

    def parse_referencias(self):

        self.referencias = []
        relaciones_referencias = {
            "30": "Factura",
            "32": "Factura de venta bienes y servicios",
            "35": "Boleta",
            "38": "Boleta Exenta",
            "45": "Factura de Compra",
            "55": "Nota de Débito",
            "60": "Nota de Crédito",
            "103": "Liquidación",
            "40": "Liquidación-Factura",
            "43": "Liquidación-Factura Electrónica",
            "33": "Factura Electrónica",
            "34": "Factura No Afecta o Exenta Electrónica",
            "39": "Boleta Electrónica",
            "41": "Boleta Exenta Electrónica",
            "46": "Factura de Compra Electrónica",
            "56": "Nota de Débito Electrónica",
            "61": "Nota de Crédito Electrónica",
            "50": "Guía de Despacho",
            "52": "Guía de Despacho Electrónica",
            "110": "Factura de Exportación Electrónica",
            "111": "Nota de Débito de Exportación",
            "112": "Nota de Crédito de Exportación",
            "801": "Orden de Compra",
            "802": "Nota de pedido",
            "803": "Contrato",
            "804": "Resolución",
            "805": "Proceso ChileCompra",
            "806": "Ficha ChileCompra",
            "807": "DUS",
            "808": "B/L (Conocimiento de embarque)",
            "809": "AWB (AirWill Bill)",
            "810": "MIC/DTA",
            "811": "Carta de Porte",
            "812": "Resolución del SNA donde califica Servicios de Exportación",
            "813": "Pasaporte",
            "814": "Certificado de Depósito Bolsa Prod. Chile",
            "815": "Vale de Prenda Bolsa Prod. Chile",
            "820": "Código de Inscripción en el Registro de Acuerdos con Plazo de Pago Excepcional",
            "OV": "Orden de Venta",
            "VTA": "Venta",
            "NV": "Nota de Venta"
        }

        for r in self.tree.findall('.//{http://www.sii.cl/SiiDte}Referencia'):
            tipo_doc_referencia = r.find('{http://www.sii.cl/SiiDte}TpoDocRef').text if r.find(
                '{http://www.sii.cl/SiiDte}TpoDocRef') is not None else ""
            folio_referencia = r.find('{http://www.sii.cl/SiiDte}FolioRef').text if r.find(
                '{http://www.sii.cl/SiiDte}FolioRef') is not None else ""
            fecha_referencia = r.find('{http://www.sii.cl/SiiDte}FchRef').text if r.find(
                '{http://www.sii.cl/SiiDte}FchRef') is not None else ""

            self.referencias.append({"tipo_doc_referencia": tipo_doc_referencia,
                                     "tipo_doc_referencia_palabras": relaciones_referencias[
                                         str(tipo_doc_referencia)] if str(
                                         tipo_doc_referencia) in relaciones_referencias else tipo_doc_referencia,
                                     "folio_referencia": folio_referencia,
                                     "fecha_referencia": fecha_referencia})

    def parse_impuestos(self):
        self.impuestos = []

        relaciones_impuestos = {
            "14": "IVA de margen de comercialización",
            "15": "IVA retenido total",
            "17": "IVA anticipo faenamiento carne",
            "18": "IVA anticipado carne",
            "19": "IVA anticipado carne",
            "27": "DL 825/74, ART. 42, letra a)",
            "30": "IVA retenido legumbres",
            "31": "IVA retenido silvestres",
            "32": "IVA retenido ganado",
            "33": "IVA retenido madera",
            "34": "IVA retenido trigo",
            "36": "IVA retenido arroz",
            "37": "IVA retenido hidrobiológicas",
            "38": "IVA retenido chatarra",
            "39": "IVA retenido PPA",
            "41": "IVA retenido construcción",
            "23": "Impuesto adicional Art 37 Letras a, b, c",
            "44": "Impuesto adicional Art 37 Letras e, h, i, l",
            "45": "Impuesto adicional Art 37 Letras j",
            "24": "Impuesto Art 42 Ley 825/74 letra a",
            "25": "Impuesto Art 42, letra c",
            "26": "Impuesto Art 42, letra c",
            "27": "Impuesto Bebidas Art 42, letra d y e",
            "28": "Impuesto específico diesel",
            "29": "Recuperación Impuesto Específico Diesel Transportistas",
            "35": "Impuesto específico gasolina",
            "47": "IVA retenido cartones",
            "48": "IVA retenido frambuesas y pasas",
            "49": "Factura de compra sin retención",
            "50": "IVA de margen de comercialización de instrumentos de prepago",
            "51": "Impuesto gas natural comprimido",
            "52": "Impueso gas licuado de petróleo",
            "53": "Impuesto retenido Suplementeros Art 74 nº5 Ley de la Renta",
            "60": "Impuesto retenido factura de inicio",
            "271": "DL 825/74, ART. 42, letra a) Inciso Segundo"
        }

        for i in self.tree.findall('.//{http://www.sii.cl/SiiDte}ImptoReten'):
            tipo_impuesto = i.find('{http://www.sii.cl/SiiDte}TipoImp').text if i.find(
                '{http://www.sii.cl/SiiDte}TipoImp') is not None else ""
            monto_impuesto = i.find('{http://www.sii.cl/SiiDte}MontoImp').text if i.find(
                '{http://www.sii.cl/SiiDte}MontoImp') is not None else ""

            self.impuestos.append({"##imp": tipo_impuesto,
                                   "tipo impuesto": relaciones_impuestos[tipo_impuesto],
                                   "monto": monto_impuesto})

    def numero_referencias_GD(self):
        n_ref = 0
        for r in self.referencias:
            if r["tipo_doc_referencia"] == "50" or r["tipo_doc_referencia"] == "52":
                n_ref += 1

        return n_ref

    def numero_referencias_OC(self):
        n_ref = 0
        for r in self.referencias:
            if r["tipo_doc_referencia"] == "801":
                n_ref += 1

        return n_ref

    def es_respuesta(self):
        return not self.tree.find('.//{http://www.sii.cl/SiiDte}NmbEnvio') is None
