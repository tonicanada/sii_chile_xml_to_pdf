from xml_to_pdf_functions import append_xml_to_df
import pandas as pd
import os

path = "./input"

# Genera un excel con el detalle de los XML de la carpeta "input"
df = pd.DataFrame(
    columns=["rut", "fecha", "folio", "montoNeto", "referencias_oc", "tipoDoc", "items", "comuna"]
)
for filename in os.listdir(path):
    df = append_xml_to_df(df, f"{path}/{filename}")
df.to_excel("./output/listado_xml.xlsx")