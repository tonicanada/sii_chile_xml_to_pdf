import argparse
import pathlib
import sys
import pandas as pd
import json

from sii_xml_pdf.parser import parse_xml
from sii_xml_pdf.renderer import render_pdf


def convert_file(xml_path, out=None, css=None):
    xml_path = pathlib.Path(xml_path).resolve()
    if not xml_path.exists():
        raise SystemExit(f"❌ No existe el XML: {xml_path}")

    dte = parse_xml(str(xml_path))
    pdf_bytes = render_pdf(dte, css_path=css)

    # Construir ruta de salida
    if out is None:
        out_path = pathlib.Path(
            "output/pdf") / f"{dte.fecha_emision.replace('-', '')} {dte.tipo_dte_abreviatura} {dte.razon_social.title().replace('.', '')} {dte.numero_factura}.pdf"
    else:
        out_candidate = pathlib.Path(out)
        if out_candidate.is_dir() or str(out).endswith("/"):
            out_path = out_candidate / \
                f"{dte.fecha_emision.replace('-', '')} {dte.tipo_dte_abreviatura} {dte.razon_social.title().replace('.', '')} {dte.numero_factura}.pdf"
        else:
            out_path = out_candidate

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"✅ PDF generado: {out_path}")


def convert_folder(folder, out=None, css=None):
    folder = pathlib.Path(folder).resolve()
    if not folder.exists():
        raise SystemExit(f"❌ No existe la carpeta: {folder}")

    for xml_file in folder.glob("*.xml"):
        try:
            convert_file(xml_file, out=out, css=css)
        except Exception as e:
            print(
                f"⚠️ Error convirtiendo {xml_file.name}: {e}", file=sys.stderr)


def extract_excel(folder, out="output/listado_xml.xlsx"):
    """Genera un Excel con info de los XML, incluyendo los ítems como JSON."""
    folder = pathlib.Path(folder).resolve()
    rows = []
    for xml_file in folder.glob("*.xml"):
        try:
            dte = parse_xml(str(xml_file))

            # Convertir los objetos Item a dict
            items_dicts = []
            for it in dte.items:
                if hasattr(it, "dict"):   # Pydantic
                    items_dicts.append(it.dict())
                elif hasattr(it, "__dict__"):  # dataclass/simple object
                    items_dicts.append(it.__dict__)
                else:  # fallback
                    items_dicts.append(str(it))

            rows.append({
                "archivo": xml_file.name,
                "rut": dte.rut_proveedor,
                "fecha": dte.fecha_emision,
                "folio": dte.numero_factura,
                "montoNeto": dte.monto_neto,
                "tipoDoc": dte.tipo_dte,
                "razon_social": dte.razon_social,
                "items_json": json.dumps(items_dicts, ensure_ascii=False)
            })
        except Exception as e:
            print(f"⚠️ Error procesando {xml_file.name}: {e}", file=sys.stderr)

    if not rows:
        print("⚠️ No se generó ningún dato")
        return

    df = pd.DataFrame(rows)
    out_path = pathlib.Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False)
    print(f"✅ Excel generado: {out_path}")


def main():
    ap = argparse.ArgumentParser(prog="sii_xml_pdf")
    subparsers = ap.add_subparsers(dest="command")

    # convert
    ap_convert = subparsers.add_parser(
        "convert", help="Convierte un XML a PDF")
    ap_convert.add_argument("xml", help="Ruta al XML DTE")
    ap_convert.add_argument(
        "-o", "--out", help="Ruta de salida (archivo .pdf o directorio)")
    ap_convert.add_argument(
        "--css", help="Ruta a invoice.css (opcional)", default=None)

    # convert-folder
    ap_folder = subparsers.add_parser(
        "convert-folder", help="Convierte todos los XML de una carpeta a PDF")
    ap_folder.add_argument("folder", help="Carpeta con XMLs")
    ap_folder.add_argument("-o", "--out", help="Directorio de salida")
    ap_folder.add_argument(
        "--css", help="Ruta a invoice.css (opcional)", default=None)

    # extract-excel
    ap_excel = subparsers.add_parser(
        "extract-excel", help="Extrae info de XMLs y genera Excel")
    ap_excel.add_argument("folder", help="Carpeta con XMLs")
    ap_excel.add_argument(
        "-o", "--out", help="Ruta de salida Excel", default="output/listado_xml.xlsx")

    args = ap.parse_args()

    if args.command == "convert":
        convert_file(args.xml, out=args.out, css=args.css)
    elif args.command == "convert-folder":
        convert_folder(args.folder, out=args.out, css=args.css)
    elif args.command == "extract-excel":
        extract_excel(args.folder, out=args.out)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
