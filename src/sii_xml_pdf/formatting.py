from datetime import datetime

def format_clp(n: int) -> str:
    # CLP típico sin decimales, miles con punto
    s = f"{int(n):,}"
    return s.replace(",", ".")

def format_cantidad(q: float) -> str:
    """Cantidad con punto de miles y coma decimal, sin decimales si es entera:
    737 → «737», 1051 → «1.051», 2.5 → «2,5». Antes salía «737.00», que con el punto
    de miles chileno se lee como setecientos treinta y siete mil."""
    if float(q).is_integer():
        return format_clp(int(q))
    entero, dec = f"{q:.6f}".rstrip("0").split(".")
    return f"{format_clp(int(entero))},{dec}"

def fecha_es_larga(yyyy_mm_dd: str) -> str:
    dt = datetime.strptime(yyyy_mm_dd, "%Y-%m-%d")
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio",
             "agosto","septiembre","octubre","noviembre","diciembre"]
    return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
