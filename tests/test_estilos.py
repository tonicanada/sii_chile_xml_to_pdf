"""
Los estilos del PDF: qué hojas se aplican y qué pasa si se pide uno que no existe.

Se prueba el armado de hojas y el HTML, no el PDF: comparar dos PDF byte a byte es
frágil —WeasyPrint mete metadatos que cambian— y lo que importa aquí es qué CSS entra
y qué sale en la plantilla.
"""

import pytest

from sii_xml_pdf.renderer import ESTILOS, _default_css_list


def test_el_estilo_actual_no_anade_nada():
    """El estilo de siempre tiene que seguir siendo el de siempre.

    Si `actual` empezara a añadir una hoja, todos los PDF ya validados con el SII
    cambiarían de aspecto sin que nadie lo hubiera pedido.
    """
    assert ESTILOS["actual"] is None
    assert len(_default_css_list(None)) == 1
    assert len(_default_css_list(None, "actual")) == 1


def test_el_compacto_es_una_capa_encima_y_no_una_copia():
    """Dos hojas, en orden: el base y luego las diferencias.

    Si fuese una copia entera del base, cada arreglo habría que hacerlo dos veces y los
    estilos divergirían en silencio.
    """
    hojas = _default_css_list(None, "compacto")
    assert len(hojas) == 2


def test_un_estilo_desconocido_levanta():
    """Caer al estilo por defecto en silencio entregaría un PDF con un aspecto que
    nadie pidió — y eso no se nota mirándolo, porque el documento sale bien."""
    with pytest.raises(ValueError, match="Estilo desconocido"):
        _default_css_list(None, "no_existe")


def test_una_ruta_de_css_explicita_manda_sobre_el_estilo():
    """`css_path` es la vía de escape para probar una hoja suelta; si el estilo la
    pisara, no serviría para nada."""
    import tempfile
    import pathlib

    with tempfile.TemporaryDirectory() as d:
        ruta = pathlib.Path(d) / "x.css"
        ruta.write_text("body { color: red; }")
        assert len(_default_css_list(str(ruta), "compacto")) == 1


def _dte_minimo():
    """Lo justo para renderizar. Los campos obligatorios se rellenan con lo que pida el
    modelo, sin fingir una factura completa: lo que se prueba es la cabecera."""
    from sii_xml_pdf.models import DTEData

    campos = {}
    for nombre, campo in DTEData.model_fields.items():
        if not campo.is_required():
            continue
        anotacion = str(campo.annotation)
        if "int" in anotacion and "str" not in anotacion:
            campos[nombre] = 0
        elif "list" in anotacion.lower() or "List" in anotacion:
            campos[nombre] = []
        else:
            campos[nombre] = ""
    campos.update(
        tipo_dte=33, numero_factura="54", fecha_emision="2026-09-24",
        razon_social="Emisor SpA", monto_total=119000, timbre_xml="",
    )
    return DTEData(**campos)


def test_el_logo_solo_sale_si_se_manda():
    """Sin logo la cabecera queda como siempre: las empresas que no suban uno no ven
    ningún cambio, y no hay hueco ni icono roto."""
    from sii_xml_pdf.renderer import render_html

    html = render_html(_dte_minimo(), vista_previa=True)
    assert "logo_emisor" not in html

    con_logo = render_html(_dte_minimo(), vista_previa=True, logo_b64="QUJD")
    assert "logo_emisor" in con_logo
    assert "QUJD" in con_logo
