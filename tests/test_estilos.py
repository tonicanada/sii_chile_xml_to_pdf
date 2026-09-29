"""
Los estilos del PDF: qué hojas se aplican y qué pasa si se pide uno que no existe.

Se prueba el armado de hojas y el HTML, no el PDF: comparar dos PDF byte a byte es
frágil —WeasyPrint mete metadatos que cambian— y lo que importa aquí es qué CSS entra
y qué sale en la plantilla.
"""

import re

import pytest

from sii_xml_pdf.renderer import ESTILOS, _default_css_list, _leer_css


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


# ── anchos de las columnas de cifras ───────────────────────────────────────────

def _anchos_de_columnas(css: str, columnas: range) -> dict[int, str]:
    """El `width` declarado para cada `#item_table td:nth-child(N)` de esa hoja.

    Se lee del CSS y no del PDF a propósito: «las cuatro columnas miden lo mismo» es una
    propiedad de la hoja de estilo, y medirla sobre el PDF renderizado significaría
    reconstruir el cálculo de WeasyPrint para comprobar lo que el CSS ya dice.
    """
    anchos = {}
    for n in columnas:
        # El width puede venir en una regla agrupada con otras columnas, así que se busca
        # el bloque que menciona esta y se lee su `width`.
        for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
            selector, cuerpo = m.group(1), m.group(2)
            if f"td:nth-child({n})" in selector and "width:" in cuerpo:
                anchos[n] = re.search(r"width:\s*([\d.]+%)", cuerpo).group(1)
    return anchos


def test_en_el_compacto_las_cuatro_columnas_de_cifras_miden_lo_mismo():
    """Dscto., Cantidad, Precio Unit. y Valor Item, parejas. A 7,5pt caben: comprobado con
    el peor caso real que Tecton ha emitido, `10.601.964.727` — 13 caracteres con puntos."""
    anchos = _anchos_de_columnas(_leer_css(ESTILOS["compacto"]), range(4, 8))
    assert set(anchos) == {4, 5, 6, 7}, "las cuatro tienen que estar declaradas"
    assert len(set(anchos.values())) == 1, f"no miden lo mismo: {anchos}"


def test_el_base_las_deja_desiguales_a_proposito():
    """Con la fuente del base, a Precio Unit. y Valor Item les hace falta más sitio: con 11%
    los montos en pesos se desbordaban sobre la columna vecina. Igualarlas ahí volvería a
    romper eso, y no se nota mirando el CSS."""
    anchos = _anchos_de_columnas(_leer_css("templates/invoice.css"), range(4, 8))
    assert anchos[6] == anchos[7], "Precio Unit. y Valor Item sí van iguales entre sí"
    assert anchos[4] != anchos[6], "pero no con Dscto."


def test_el_compacto_no_toca_las_columnas_de_texto():
    """Nro., Código y Descripción siguen viniendo del base: lo que se pidió fue emparejar
    las cifras, no rehacer la tabla."""
    compacto = _leer_css(ESTILOS["compacto"])
    assert _anchos_de_columnas(compacto, range(1, 4)) == {}
