SII = {"sii": "http://www.sii.cl/SiiDte"}
def x(tag: str) -> str:
    return f"{{{SII['sii']}}}{tag}"