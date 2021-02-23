import locale
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from DTE.DTE import DTE
import pandas as pd
from datetime import datetime
from num2words import num2words
from pdf417 import encode, render_image, render_svg
import numpy as np

locale.setlocale(locale.LC_ALL, '')

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template("./templates/invoice.html")


# Función que obtiene el código de barras a partir del texto del timbre
def xml_to_svg(xml_text):
    codes = encode(xml_text, columns=11)
    svg = render_svg(codes)
    svg.write('./templates/barcode.svg')


# Función que convierte documento del SII de XML a PDF
def sii_doc_XMLtoPDF(path):
    dte_parsed = DTE(path)

    # Genera código de barras
    xml_to_svg(dte_parsed.timbre)

    # TABLA ITEMS
    df = pd.json_normalize(dte_parsed.items)
    df["Nro."] = range(1, len(df) + 1)
    df["Código"] = 0
    df["qty"] = df["qty"].astype(float)
    df["P.U."] = df["rate"].astype(float).astype(int).map('{:,}'.format).str.replace(
        ",",
        ".")
    df["Valor Item"] = (df["qty"].astype(float) * df["rate"].astype(float)).astype(int).map('{:,}'.format).str.replace(
        ",",
        ".")
    df["Dscto"] = 0
    df = df[["Nro.", "Código", "descripcion", "Dscto", "qty", "P.U.", "Valor Item"]]
    if len(df) >= 13:
        df = df.reindex(df.index.tolist() + list(range(len(df), 25))).replace(np.nan, 0, regex=True)
    # df.style.format("{:.2%}")

    # TABLA REFERENCIAS
    df_referencias = pd.json_normalize(dte_parsed.referencias)

    # TABLA IMPUESTOS
    df_impuestos = pd.json_normalize(dte_parsed.impuestos)
    # print((df_impuestos))
    monto_impuesto_y_retenciones = df_impuestos["monto"].astype(int).to_numpy().sum() if len(df_impuestos) > 0 else 0

    # TRASPASA VARIABLES AL TEMPLATE
    template_vars = {
        "rut": dte_parsed.rut_proveedor,
        "supplier_name": dte_parsed.razon_social,
        "supplier_activity": dte_parsed.giro_proveedor,
        "bill_no": dte_parsed.numero_factura,
        "purchase_invoice_items": df.to_html(index=False, classes="items_factura"),
        "tipo_documento": dte_parsed.tipo_dte_palabras,
        "fecha_emision": datetime.strftime(datetime.strptime(dte_parsed.fecha_emision, "%Y-%m-%d"), "%d de %B de %Y"),
        "supplier_address_detail": dte_parsed.direccion_proveedor,
        "supplier_address_comuna": dte_parsed.comuna_proveedor,
        "supplier_address_city": dte_parsed.ciudad_proveedor,
        # Dator receptor
        "receptor_razon_social": dte_parsed.receptor_razon_social,
        "receptor_giro": dte_parsed.receptor_giro,
        "receptor_rut": dte_parsed.receptor_rut,
        "receptor_direccion": dte_parsed.receptor_direccion,
        "receptor_ciudad": dte_parsed.receptor_ciudad,
        "receptor_comuna": dte_parsed.receptor_comuna,
        "forma_pago_palabras": dte_parsed.forma_pago_palabras,
        "fecha_vencimiento": dte_parsed.fecha_vencimiento,
        # Referencias
        "referencias_table": "No hay referencias" if dte_parsed.referencias == [] else df_referencias.to_string(
            header=False, index=False,
            col_space=[10, 10, 10],
            columns=["fecha_referencia", "tipo_doc_referencia_palabras",
                     "folio_referencia"]),
        "impuestos_table": "" if dte_parsed.impuestos == [] else df_impuestos.to_html(index=False),

        # Totales
        "monto_total_palabras": num2words(dte_parsed.monto_total, lang="es").upper(),
        "monto_total": f"{int(dte_parsed.monto_total):n}",
        "monto_iva": f"{int(dte_parsed.monto_iva):n}",
        "monto_exento": f"{int(dte_parsed.monto_exento):n}",
        "monto_neto": f"{int(dte_parsed.monto_neto):n}",
        "monto_impuesto_y_retenciones": f"{int(monto_impuesto_y_retenciones):n}",
        "src_timbre": """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <path d="M30,1h40l29,29v40l-29,29h-40l-29-29v-40z" stroke="#000" fill="none"/> 
      <path d="M31,3h38l28,28v38l-28,28h-38l-28-28v-38z" fill="#a23"/> 
      <text x="50" y="68" font-size="48" fill="#FFF" text-anchor="middle"><![CDATA[410]]></text>
    </svg>"""
    }

    invoice_html = template.render(template_vars)

    file_name_output = f"./output/pdf/{dte_parsed.fecha_emision.replace('-', '')} {dte_parsed.tipo_dte_abreviatura} {dte_parsed.razon_social.title().replace('.', '')} {dte_parsed.numero_factura}.pdf"

    HTML(string=invoice_html).write_pdf(file_name_output, stylesheets=["./templates/invoice.css"])


# Función que filtra las OC dentro de las referencias del XML
def obtieneRefOc(referencias):
    for referencia in referencias:
        if referencia["tipo_doc_referencia"] != "801":
            continue
        return referencia["folio_referencia"]


# Función que añade el detalle de un xml a un pandas dataframe como fila
def append_xml_to_df(df, xml_file):
    dte_parsed = DTE(xml_file)
    df = df.append({
        "rut": dte_parsed.rut_proveedor,
        "fecha": dte_parsed.fecha_emision,
        "folio": dte_parsed.numero_factura,
        "montoNeto": dte_parsed.monto_neto,
        "referencias_oc": obtieneRefOc(dte_parsed.referencias),
        "tipoDoc": dte_parsed.tipo_dte,
        "items": dte_parsed.items,
        "comuna": dte_parsed.comuna_proveedor
    },
        ignore_index=True, )
    return df
