# sii_chile_xml_to_pdf

Este proyecto convierte los documentos electrónicos XML del SII (Servicio de Impuestos Internos) de Chile a PDF. Estos documentos pueden ser facturas, guías de despacho, notas de crédito, etc.

## Requisitos

Para clonar el repositorio es necesario ejecutar el siguiente comando

```shell
git clone https://github.com/tonicanada/sii_chile_xml_to_pdf
cd sii_chile_xml_to_pdf/
```

Para en el caso de estar bajo ubuntu se necesitan ejecutar los siguiente comandos con antelacion

```shell

sudo apt install python3-pip
python3 setuptools launchpadlib
sudo apt install python3-testresources
sudo apt-get install -y libcairo2
sudo apt-get install libpangocairo-1.0-0
pip install -r requirements.txt

```

## Comenzando 🚀

El archivo _**script_convierte_xml.py**_ convierte todos los XML guardados en la carpeta _**input**_ y los guarda en _**output/pdf**_.

```shell
python3 script_convierte_xml.py
```

El archivo _**script_obtiene_excel.py**_ genera un archivo excel llamado _**listado_xml.xlsx**_ que se guarda en _**output**_ (este excel parsea los xml generando una tabla resumen de ellos)

## Aspectos a mejorar:
* Parsear el descuento de los items, si es que tienen.
* Evitar las filas de 0 en el caso de documentos de más de una página.
* Formatear en tabla las referencias.
