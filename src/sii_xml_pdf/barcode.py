from pdf417 import encode, render_svg
import xml.etree.ElementTree as ET
import re


def clean_ted(ted_xml: str) -> str:
    """
    Limpia el bloque TED para que pueda ser codificado en PDF417.
    - Quita namespaces (ns0:, ns1:, etc)
    - Elimina xmlns="..."
    - Saca saltos de línea y espacios extra
    """
    s = ted_xml.strip()
    # Quitar xmlns y atributos de namespace
    s = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', s)
    # Quitar prefijos tipo ns0:
    s = re.sub(r'\bns\d+:', '', s)
    # Quitar espacios y saltos de línea excesivos
    s = re.sub(r">\s+<", "><", s)
    s = re.sub(r"\s+", " ", s)
    return s


def pdf417_svg_from_ted(ted_str: str, columns: int = 17, scale: int = 2, ratio: int = 3) -> str:
    ted_clean = clean_ted(ted_str)
    
    # # 👇 verificar el tamaño y contenido exacto
    # print("==== TED a codificar ====")
    # print(ted_clean)
    # print("Longitud:", len(ted_clean), "caracteres")
    # # Generar el PDF417
    
    codes = encode(ted_clean, columns=columns, security_level=0)
    svg_tree = render_svg(codes, scale=scale, ratio=ratio)
    root = svg_tree.getroot()

    # Devolver como string para inyectar en el template
    return ET.tostring(root, encoding="unicode")
