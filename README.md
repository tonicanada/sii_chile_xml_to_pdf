# sii_chile_xml_to_pdf

Este proyecto convierte los documentos electrónicos XML del SII (Servicio de Impuestos Internos) de Chile a PDF. Estos documentos pueden ser facturas, guías de despacho, notas de crédito, etc.

## Comenzando 🚀

El archivo _**script_convierte_xml.py**_ convierte todos los XML guardados en la carpeta _**input**_ y los guarda en _**output/pdf**_.

El archivo _**script_obtiene_excel.py**_ genera un archivo excel llamado _**listado_xml.xlsx**_ que se guarda en _**output**_ (este excel parsea los xml generando una tabla resumen de ellos)