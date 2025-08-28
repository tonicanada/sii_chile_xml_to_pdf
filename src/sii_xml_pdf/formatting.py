from datetime import datetime

def format_clp(n: int) -> str:
    # CLP típico sin decimales, miles con punto
    s = f"{int(n):,}"
    return s.replace(",", ".")

def fecha_es_larga(yyyy_mm_dd: str) -> str:
    dt = datetime.strptime(yyyy_mm_dd, "%Y-%m-%d")
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio",
             "agosto","septiembre","octubre","noviembre","diciembre"]
    return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
