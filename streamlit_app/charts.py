"""Constructores de gráficos Plotly -- funciones puras: reciben datos y
devuelven una go.Figure nueva. A diferencia del notebook (donde se mutaban
FigureWidgets en el lugar), en Streamlit el script se re-ejecuta completo en
cada interacción, así que no hace falta (ni sirve) mantener estado dentro de
las figuras.
"""
import colorsys
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from data import NOMBRES_CORTOS_SECTOR, NOMBRES_RAMA_CORTOS, ORDEN_GRUPOS_EDAD

def _a_rgb(color):
    """Acepta "#rrggbb" o "rgb(r, g, b)" (así vienen las paletas
    qualitative de Plotly, ej. Set3) y devuelve una tupla (r, g, b)."""
    color = color.strip()
    if color.startswith("#"):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\(([^)]+)\)", color)
    if m:
        return tuple(round(float(x)) for x in m.group(1).split(",")[:3])
    raise ValueError(f"Formato de color no soportado: {color!r}")


def _mas_opaco(color, l_max=0.60, s_min=0.55):
    """"Set3" es una paleta pastel: varios de sus colores son casi blancos
    (L muy alto) o, en un caso, gris puro (S=0). En la dona se ven demasiado
    parecidos entre sí -- y al amarillo -- así que se les baja el tope de
    luminosidad y se les sube el piso de saturación antes de usarlos, sin
    tocar el matiz (el sector sigue siendo "el mismo color", solo más sólido)."""
    r, g, b = _a_rgb(color)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = min(l, l_max)
    s = max(s, s_min)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


# Color fijo por sector/rama -- no por posición. Si el color saliera de
# "px.colors.qualitative.Set3" indexado por la posición de cada uno en la
# dona, un mismo sector cambiaría de color entre departamentos (u ordenado
# por valor) según dónde caiga ese día. Se arma una sola vez, en el orden
# natural de cada diccionario, y de ahí en adelante todos los que dibujen
# esa dona -- sin importar cómo estén ordenados los datos -- usan el mismo
# color para el mismo sector/rama.
#
# Set3 solo trae 12 colores, pero el PIB tiene 13 sectores y la GEIH 14
# ramas -- sin más colores, el ciclo se repite y dos sectores/ramas sin
# nada que ver (ej. "Impuestos" y "Agricultura, ganadería, caza...") caen
# en el MISMO color exacto. Se completa con Set1 (9 colores más) para que
# nunca haga falta repetir.
def _mapa_color_fijo(nombres_cortos):
    paleta = [_mas_opaco(c) for c in px.colors.qualitative.Set3 + px.colors.qualitative.Set1]
    unicos = list(dict.fromkeys(nombres_cortos))
    return {nombre: paleta[i % len(paleta)] for i, nombre in enumerate(unicos)}


COLOR_SECTORES_PIB = _mapa_color_fijo(NOMBRES_CORTOS_SECTOR.values())
COLOR_RAMA_GEIH = _mapa_color_fijo(NOMBRES_RAMA_CORTOS.values())

COLOR_ACTIVO = "#2563EB"
COLOR_COMPARAR = "#F59E0B"
COLOR_INACTIVO = "#E5E7EB"

COLOR_PRIMARIAS = "#2a78d6"
COLOR_SECUNDARIAS = "#eb6834"
COLOR_TERCIARIAS = "#1baf7a"
COLOR_DENSIDAD = "#2a78d6"
COLOR_COMPETITIVIDAD = "#4a3aa7"
COLOR_SIN_DATO = "#d9d9d9"
COLOR_NEUTRO = "#93C5FD"
COLOR_LINEA_DEFECTO = "#262c60"
COLOR_PUNTO_ANIO = "#F59E0B"


def _mezclar_con_blanco(color_hex, t):
    r, g, b = _a_rgb(color_hex)
    r = round(255 + (r - 255) * t)
    g = round(255 + (g - 255) * t)
    b = round(255 + (b - 255) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ------------------------------------------------------------------
# Mapa departamental
# ------------------------------------------------------------------
def build_department_map(mapa_caribe_geo, caribe, departamento_actual, comparar_con=None, colores_pib=None, todos_activos=False):
    nombres = [f["properties"]["nombre_entidad"] for f in mapa_caribe_geo["features"]]

    if colores_pib is not None:
        # Vista PIB: cada departamento con su propio color exacto (la mezcla
        # ponderada de sus sectores), no el esquema fijo de 3 colores. La
        # selección se marca con el borde, no con el relleno. En la vista
        # Total (todos_activos) los 7 quedan con el borde de "seleccionado".
        colores_lista = [colores_pib.get(n, COLOR_SIN_DATO) for n in nombres]
        colorscale, z = _construir_colorscale_categorico(colores_lista)
        anchos = [3.5 if (todos_activos or n == departamento_actual) else 1.2 for n in nombres]
        lineas = ["#111827" if (todos_activos or n == departamento_actual) else "white" for n in nombres]
        fig = go.Figure(
            go.Choropleth(
                geojson=mapa_caribe_geo,
                locations=nombres,
                z=z,
                zmin=0, zmax=max(len(colores_lista), 1),
                featureidkey="properties.nombre_entidad",
                colorscale=colorscale,
                showscale=False,
                marker_line_color=lineas,
                marker_line_width=anchos,
                hovertemplate="<b>%{location}</b><extra></extra>",
            )
        )
    else:
        colores_z = []
        for nombre in nombres:
            if todos_activos or nombre == departamento_actual:
                colores_z.append(1)
            elif comparar_con and nombre == comparar_con:
                colores_z.append(2)
            else:
                colores_z.append(0)

        fig = go.Figure(
            go.Choropleth(
                geojson=mapa_caribe_geo,
                locations=nombres,
                z=colores_z,
                featureidkey="properties.nombre_entidad",
                colorscale=[[0, "#E5E7EB"], [0.5, "#2563EB"], [1, "#F59E0B"]],
                zmin=0, zmax=2,
                showscale=False,
                marker_line_color="white",
                marker_line_width=1.5,
                hovertemplate="<b>%{location}</b><extra></extra>",
            )
        )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title="Caribe Colombiano",
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def _mezclar_colores_ponderados(pares, boost_saturacion=2.2):
    """pares: lista de (color_hex, peso). Promedio ponderado por canal RGB
    -- no es "el color del sector dominante aclarado", es una mezcla real de
    todos los sectores según cuánto pesa cada uno.

    Set3 (la paleta de los sectores) es pastel: satura poco (~0.15-0.45),
    así que mezclar 13 de sus colores por promedio simple converge a tonos
    muy parecidos entre sí -- el matiz (hue) sí varía según la composición
    real de cada departamento, pero queda casi invisible bajo tan poca
    saturación. Se reescala la saturación hacia arriba después de mezclar
    (mismo matiz, mismo peso relativo, más contraste) para que la huella
    de cada departamento se distinga a simple vista."""
    total = sum(peso for _, peso in pares if peso and peso > 0)
    if not total:
        return COLOR_SIN_DATO
    r = g = b = 0.0
    for color_hex, peso in pares:
        if not peso or peso <= 0:
            continue
        rr, gg, bb = _a_rgb(color_hex)
        w = peso / total
        r += rr * w
        g += gg * w
        b += bb * w
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    s = min(1.0, s * boost_saturacion)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def calcular_colores_departamentos_pib(pib_sector_caribe, caribe, anio_sel):
    """Un color por departamento: mezcla ponderada de los colores fijos de
    cada sector (COLOR_SECTORES_PIB) según su participación real en el PIB
    de ese departamento y año -- la huella de su estructura económica.
    Departamentos con composición sectorial parecida terminan con colores
    parecidos; uno muy diversificado tiende a un color más "promedio/gris".
    """
    colores = {}
    for nombre_dep in caribe:
        datos = pib_sector_caribe[
            (pib_sector_caribe["Departamento"] == nombre_dep) & (pib_sector_caribe["Año"] == anio_sel)
        ]
        sectores = datos[~datos["Sector"].isin(["Valor agregado total", "Producto Interno Bruto"])]
        pares = []
        for _, fila in sectores.iterrows():
            nombre_corto = NOMBRES_CORTOS_SECTOR.get(fila["Sector"], fila["Sector"])
            color = COLOR_SECTORES_PIB.get(nombre_corto)
            valor = fila["Valor_miles_millones_COP"]
            if color and pd.notna(valor) and valor > 0:
                pares.append((color, valor))
        colores[nombre_dep] = _mezclar_colores_ponderados(pares) if pares else COLOR_SIN_DATO
    return colores


def calcular_colores_departamentos_ml(geih_ocupados_rama, caribe, capitales, anio_sel):
    """Igual que calcular_colores_departamentos_pib, pero para Mercado
    laboral: mezcla ponderada de los colores fijos de cada rama
    (COLOR_RAMA_GEIH) según cuántos ocupados tiene en ese año -- la huella
    de su estructura laboral. La GEIH solo cubre la ciudad capital de cada
    departamento, así que la composición de la capital hace de proxy del
    departamento entero (igual que ya se hace en las tarjetas y el mapa
    municipal)."""
    colores = {}
    for nombre_dep in caribe:
        capital = capitales.get(nombre_dep)
        fila = geih_ocupados_rama[
            (geih_ocupados_rama["nombre_entidad"] == capital) & (geih_ocupados_rama["anio"] == anio_sel)
        ]
        pares = []
        if not fila.empty:
            f = fila.iloc[0]
            for rama_original, rama_corta in NOMBRES_RAMA_CORTOS.items():
                valor = f.get(rama_original)
                color = COLOR_RAMA_GEIH.get(rama_corta)
                if color and pd.notna(valor) and valor > 0:
                    pares.append((color, valor))
        colores[nombre_dep] = _mezclar_colores_ponderados(pares) if pares else COLOR_SIN_DATO
    return colores


# ------------------------------------------------------------------
# Mapa de municipios (drill-down)
# ------------------------------------------------------------------
def _construir_colorscale_categorico(colores):
    n = len(colores)
    if n == 0:
        return [[0, COLOR_SIN_DATO], [1, COLOR_SIN_DATO]], []
    escala = []
    for i, color in enumerate(colores):
        escala.append([i / n, color])
        escala.append([(i + 1) / n, color])
    z = [i + 0.5 for i in range(n)]
    return escala, z


def _color_actividad_municipio(fila):
    columnas = {
        "actividades_primarias": COLOR_PRIMARIAS,
        "actividades_secundarias": COLOR_SECUNDARIAS,
        "actividades_terciarias": COLOR_TERCIARIAS,
    }
    valores = fila[list(columnas.keys())]
    if valores.isna().all() or valores.fillna(0).sum() == 0:
        return COLOR_SIN_DATO
    valores = valores.fillna(0)
    total = valores.sum()
    dominante = valores.idxmax()
    participacion = valores[dominante] / total
    t = max(0.0, (participacion - 1 / 3) / (1 - 1 / 3))
    return _mezclar_con_blanco(columnas[dominante], t)


COLOR_MERCADO_LABORAL = "#008300"  # verde


def calcular_colores_municipios(mun, mapa_geo, nombre_departamento, anio_sel, variable, geih_tasas=None):
    nombres_mun = [f["properties"]["nombre_entidad"] for f in mapa_geo["features"]]
    datos_anio = mun[
        (mun["nombre_departamento"] == nombre_departamento) & (mun["anio"] == anio_sel)
    ].set_index("nombre_entidad")

    if variable == "PIB":
        colores = []
        for nombre_mun in nombres_mun:
            if nombre_mun in datos_anio.index:
                colores.append(_color_actividad_municipio(datos_anio.loc[nombre_mun]))
            else:
                colores.append(COLOR_SIN_DATO)
        return colores, nombres_mun

    if variable == "Población":
        log_densidades = datos_anio["log_densidad"].replace([np.inf, -np.inf], np.nan)
        minimo, maximo = log_densidades.min(), log_densidades.max()
        rango = (maximo - minimo) if pd.notna(maximo) and pd.notna(minimo) and maximo > minimo else None
        colores = []
        for nombre_mun in nombres_mun:
            if nombre_mun not in datos_anio.index or pd.isna(datos_anio.loc[nombre_mun, "log_densidad"]):
                colores.append(COLOR_SIN_DATO)
                continue
            valor = datos_anio.loc[nombre_mun, "log_densidad"]
            t = 0.5 if rango is None else (valor - minimo) / rango
            colores.append(_mezclar_con_blanco(COLOR_DENSIDAD, max(0.15, min(1.0, t))))
        return colores, nombres_mun

    if variable == "Competitividad":
        colores = []
        for nombre_mun in nombres_mun:
            if nombre_mun not in datos_anio.index or pd.isna(datos_anio.loc[nombre_mun, "indice_competitividad"]):
                colores.append(COLOR_SIN_DATO)
                continue
            valor = datos_anio.loc[nombre_mun, "indice_competitividad"]
            t = min(1.0, max(0.0, valor / 10))
            colores.append(_mezclar_con_blanco(COLOR_COMPETITIVIDAD, t))
        return colores, nombres_mun

    if variable == "Mercado laboral":
        # La GEIH solo cubre la ciudad capital -- escala absoluta (0%-30% de
        # tasa de desocupación, un techo realista para el rango observado en
        # Colombia) igual razonamiento que Competitividad: con un solo dato
        # disponible no hay contra qué normalizar con un min-max relativo.
        datos_geih_anio = (
            geih_tasas[geih_tasas["anio"] == anio_sel].set_index("nombre_entidad")
            if geih_tasas is not None else pd.DataFrame()
        )
        TECHO_TD = 30
        colores = []
        for nombre_mun in nombres_mun:
            if nombre_mun not in datos_geih_anio.index or pd.isna(datos_geih_anio.loc[nombre_mun, "td"]):
                colores.append(COLOR_SIN_DATO)
                continue
            valor = datos_geih_anio.loc[nombre_mun, "td"]
            t = min(1.0, max(0.0, valor / TECHO_TD))
            colores.append(_mezclar_con_blanco(COLOR_MERCADO_LABORAL, t))
        return colores, nombres_mun

    return [COLOR_NEUTRO] * len(nombres_mun), nombres_mun


def build_municipios_map(mapa_geo, colores, nombre_departamento):
    nombres_mun = [f["properties"]["nombre_entidad"] for f in mapa_geo["features"]]
    colorscale, z = _construir_colorscale_categorico(colores)
    fig = go.Figure(
        go.Choropleth(
            geojson=mapa_geo,
            locations=nombres_mun,
            z=z,
            zmin=0,
            zmax=max(len(colores), 1),
            featureidkey="properties.nombre_entidad",
            colorscale=colorscale,
            showscale=False,
            marker_line_color="white",
            marker_line_width=1,
            hovertemplate="<b>%{location}</b><extra></extra>",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title=f"Municipios de {nombre_departamento}",
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


# ------------------------------------------------------------------
# Línea de evolución (Población / PIB, departamental o municipal / por sector)
# ------------------------------------------------------------------
def build_evolution_line(x, y, anio_actual, titulo, y_titulo, color_linea=COLOR_LINEA_DEFECTO, unidad=""):
    colores_puntos = [COLOR_PUNTO_ANIO if a == anio_actual else color_linea for a in x]
    tamanos_puntos = [14 if a == anio_actual else 8 for a in x]
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color=color_linea, width=3),
            marker=dict(size=tamanos_puntos, color=colores_puntos),
            hovertemplate=f"<b>Año %{{x}}</b><br>{y_titulo}: %{{y:,.0f}}{unidad}<extra></extra>",
        )
    )
    fig.update_layout(
        title=titulo,
        xaxis_title="Año",
        yaxis_title=y_titulo,
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        plot_bgcolor="white",
    )
    return fig


# ------------------------------------------------------------------
# Dona de PIB por sector
# ------------------------------------------------------------------
def build_pastel(labels, values, titulo, unidad="miles de millones COP", colores=None):
    # Listas planas de Python, no Series/arrays de pandas o numpy: cuando
    # "values" trae un dtype numérico, Plotly serializa el trace como un
    # array binario (base64 + dtype) en vez de JSON plano -- el componente
    # plotly_events (usado para el click en la dona sectorial) trae una
    # versión de Plotly.js más vieja que no sabe decodificar ese formato, y
    # sin values legibles Plotly.js dibuja las porciones todas del mismo
    # tamaño en vez de proporcionales. Con listas planas siempre va como
    # JSON normal, sin importar qué motor la renderice.
    labels = list(labels)
    values = [float(v) for v in values]
    total = sum(values) or 1
    hovertext = [
        f"<b>{etiqueta}</b><br>{valor:,.0f} {unidad}<br>{valor / total * 100:.1f}%<extra></extra>"
        for etiqueta, valor in zip(labels, values)
    ]
    if colores is None:
        paleta = [_mas_opaco(c) for c in px.colors.qualitative.Set3]
        colores = [paleta[i % len(paleta)] for i in range(len(labels))]
    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.35, sort=False,
            marker=dict(colors=colores),
            textinfo="none",
            hovertemplate=hovertext,
        )
    )
    fig.update_layout(title=titulo, height=420, margin=dict(l=20, r=20, t=50, b=20), showlegend=True)
    return fig


def build_ranking_barras(etiquetas, valores, titulo, colores=None, unidad="", seleccionado=None):
    """Ranking horizontal de barras -- usado en Mercado laboral para "PIB
    por trabajador" en vez de una dona. Dos razones: 1) una dona ya no
    tiene sentido para un valor que no es "parte de un todo" (PIB por
    trabajador no suma 100% entre ramas); 2) al usar el mismo
    st.plotly_chart nativo que la vista de Tasa de desocupación (en vez
    del componente plotly_events, necesario solo para las donas por el
    bug de selección en Pie/dona de Streamlit), el título deja de saltar
    de posición al alternar entre las dos vistas.

    Se ordena ascendente antes de graficar: Plotly dibuja las barras
    horizontales de abajo hacia arriba, así que la primera del arreglo
    (el valor más chico) queda abajo y la más grande arriba -- el orden
    natural de un ranking.
    """
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    etiquetas_o = [etiquetas[i] for i in orden]
    valores_o = [float(valores[i]) for i in orden]
    colores_o = [colores[i] for i in orden] if colores is not None else None
    lineas = ["#111827" if seleccionado and e == seleccionado else "rgba(0,0,0,0)" for e in etiquetas_o]
    anchos = [3 if seleccionado and e == seleccionado else 0 for e in etiquetas_o]
    hovertext = [f"<b>{e}</b><br>{v:,.0f} {unidad}<extra></extra>" for e, v in zip(etiquetas_o, valores_o)]
    fig = go.Figure(
        go.Bar(
            x=valores_o, y=etiquetas_o, orientation="h",
            marker=dict(color=colores_o, line=dict(color=lineas, width=anchos)),
            hovertemplate=hovertext,
        )
    )
    fig.update_layout(
        title=titulo, height=420, margin=dict(l=20, r=20, t=50, b=20),
        yaxis=dict(automargin=True),
    )
    return fig


# ------------------------------------------------------------------
# Dona de PARTICIPACIÓN (regional/nacional) -- 3 porciones: el "resto" del
# universo mayor (contraste), el "resto" del universo intermedio (color
# base), y la entidad resaltada (versión clara del color base). Ej. a nivel
# departamental: resto de Colombia / resto del Caribe / este departamento.
# A nivel municipal: resto del Caribe / resto del departamento / este municipio.
# ------------------------------------------------------------------
COLOR_PARTICIPACION_BASE = "#2a78d6"       # azul -- "el contenedor" (región o departamento)
COLOR_PARTICIPACION_CONTRASTE = "#eb6834"  # naranja -- el resto del universo mayor (país o región)


def build_pastel_participacion(etiqueta_resaltada, etiqueta_resto_medio, etiqueta_resto_mayor,
                                valor_resaltado, valor_resto_medio, valor_resto_mayor, titulo,
                                texto_hover_resaltado, texto_hover_medio=None):
    labels = [etiqueta_resto_mayor, etiqueta_resto_medio, etiqueta_resaltada]
    values = [valor_resto_mayor, valor_resto_medio, valor_resaltado]
    colores = [
        COLOR_PARTICIPACION_CONTRASTE,
        COLOR_PARTICIPACION_BASE,
        _mezclar_con_blanco(COLOR_PARTICIPACION_BASE, 0.45),
    ]
    hovertext = [
        f"<b>{etiqueta_resto_mayor}</b><br>{valor_resto_mayor:,.0f}<extra></extra>",
        texto_hover_medio or f"<b>{etiqueta_resto_medio}</b><br>{valor_resto_medio:,.0f}<extra></extra>",
        texto_hover_resaltado,
    ]
    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.35, sort=False,
            marker=dict(colors=colores),
            textinfo="none",
            hovertemplate=[h if h.endswith("<extra></extra>") else h + "<extra></extra>" for h in hovertext],
        )
    )
    fig.update_layout(title=titulo, height=420, margin=dict(l=20, r=20, t=50, b=20), showlegend=True)
    return fig


def build_pastel_participacion_total(etiqueta_resaltada, etiqueta_resto, valor_resaltado, valor_resto, titulo,
                                      texto_hover_resaltado, texto_hover_resto=None):
    """Versión de 2 porciones de build_pastel_participacion -- para la vista
    Total de la Región Caribe, donde ya no hay un nivel intermedio (un
    departamento) entre la región y el país."""
    labels = [etiqueta_resto, etiqueta_resaltada]
    values = [valor_resto, valor_resaltado]
    colores = [COLOR_PARTICIPACION_CONTRASTE, COLOR_PARTICIPACION_BASE]
    hovertext = [
        texto_hover_resto or f"<b>{etiqueta_resto}</b><br>{valor_resto:,.0f}<extra></extra>",
        texto_hover_resaltado,
    ]
    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.35, sort=False,
            marker=dict(colors=colores),
            textinfo="none",
            hovertemplate=[h if h.endswith("<extra></extra>") else h + "<extra></extra>" for h in hovertext],
        )
    )
    fig.update_layout(title=titulo, height=420, margin=dict(l=20, r=20, t=50, b=20), showlegend=True)
    return fig


def build_pastel_municipal(fila, titulo):
    columnas = ["actividades_primarias", "actividades_secundarias", "actividades_terciarias"]
    etiquetas = {"actividades_primarias": "Actividades primarias",
                 "actividades_secundarias": "Actividades secundarias",
                 "actividades_terciarias": "Actividades terciarias"}
    valores = fila[columnas].dropna() if fila is not None else pd.Series(dtype=float)
    return build_pastel([etiquetas[c] for c in valores.index], valores.values, titulo)


# ------------------------------------------------------------------
# Radar de competitividad (departamental o municipal, con comparación)
# ------------------------------------------------------------------
def build_radar(pilares, valores, titulo, comparar_nombre=None, valores_comparar=None):
    fig = go.Figure()
    valores_cerrados = list(valores) + [valores[0]]
    fig.add_trace(go.Scatterpolar(
        r=valores_cerrados, theta=pilares + [pilares[0]],
        fill="toself", line=dict(color="#2563EB"), marker=dict(size=5, color="#2563EB"),
        name=titulo,
    ))
    if valores_comparar is not None:
        comp_cerrados = list(valores_comparar) + [valores_comparar[0]]
        fig.add_trace(go.Scatterpolar(
            r=comp_cerrados, theta=pilares + [pilares[0]],
            fill="toself", line=dict(color="#F59E0B"), marker=dict(size=5, color="#F59E0B"),
            name=comparar_nombre,
        ))
    fig.update_layout(
        title="Pilares de competitividad",
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=True,
        height=420,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


# ------------------------------------------------------------------
# Pirámide poblacional (con overlay municipal sobre el departamento)
# ------------------------------------------------------------------
def build_pyramid(hombres_frente, mujeres_frente, titulo, hombres_fondo=None, mujeres_fondo=None):
    hombres_frente = list(hombres_frente)
    mujeres_frente = list(mujeres_frente)
    hay_fondo = hombres_fondo is not None

    if hay_fondo:
        hombres_fondo = list(hombres_fondo)
        mujeres_fondo = list(mujeres_fondo)
        max_val = max(hombres_fondo + mujeres_fondo + [1])
    else:
        max_val = max(hombres_frente + mujeres_frente + [1])
        hombres_fondo = [0] * len(ORDEN_GRUPOS_EDAD)
        mujeres_fondo = [0] * len(ORDEN_GRUPOS_EDAD)

    pasos = 4
    tickvals = [round(-max_val + i * (2 * max_val / pasos)) for i in range(pasos + 1)]
    ticktext = [f"{abs(v):,.0f}" for v in tickvals]

    fig = go.Figure()
    if hay_fondo:
        # El fondo (departamento) siempre reporta, en su hover, los mismos
        # valores del frente (municipal) -- ver nota en el notebook: es
        # puramente decorativo/de escala, nunca debe mostrar el dato
        # departamental si hay un municipio seleccionado.
        fig.add_trace(go.Bar(
            y=ORDEN_GRUPOS_EDAD, x=[-v for v in hombres_fondo], orientation="h",
            name="Hombres (departamento)", marker=dict(color="#2a78d6", opacity=0.25),
            customdata=hombres_frente,
            hovertemplate="<b>%{y} años</b><br>Hombres: %{customdata:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=ORDEN_GRUPOS_EDAD, x=mujeres_fondo, orientation="h",
            name="Mujeres (departamento)", marker=dict(color="#eb6834", opacity=0.25),
            customdata=mujeres_frente,
            hovertemplate="<b>%{y} años</b><br>Mujeres: %{customdata:,.0f}<extra></extra>",
        ))

    fig.add_trace(go.Bar(
        y=ORDEN_GRUPOS_EDAD, x=[-v for v in hombres_frente], orientation="h",
        name="Hombres", marker_color="#2a78d6", customdata=hombres_frente,
        hovertemplate="<b>%{y} años</b><br>Hombres: %{customdata:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=ORDEN_GRUPOS_EDAD, x=mujeres_frente, orientation="h",
        name="Mujeres", marker_color="#eb6834", customdata=mujeres_frente,
        hovertemplate="<b>%{y} años</b><br>Mujeres: %{customdata:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="overlay",
        title=titulo,
        height=420,
        margin=dict(l=60, r=20, t=50, b=40),
        xaxis=dict(title="Población", range=[-max_val * 1.05, max_val * 1.05], tickvals=tickvals, ticktext=ticktext),
        yaxis=dict(title="Grupo de edad"),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


# ------------------------------------------------------------------
# Dispersión tipo "strip plot" -- un punto por municipio, agrupados por
# departamento en el eje Y. Inspirado en los gráficos de Bruegel/Eurostat
# de PIB per cápita regional (países en Y, regiones como puntos), pero sin
# los cuadrantes de "más/menos desarrollado que el promedio" ni el resto de
# la decoración -- acá solo importa dónde cae cada municipio.
# ------------------------------------------------------------------
def build_dispersion_municipios(departamentos, municipios, valores, titulo, x_titulo, color="#2a78d6",
                                 capitales=None, promedios_departamento=None, promedio_regional=None):
    departamentos = list(departamentos)
    municipios = list(municipios)
    valores = [float(v) for v in valores]
    orden = sorted(set(departamentos))
    hovertext = [f"<b>{m}</b><br>{d}<br>${v:,.0f}<extra></extra>" for d, m, v in zip(departamentos, municipios, valores)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valores, y=departamentos, mode="markers",
        marker=dict(size=10, color=color, opacity=0.75, line=dict(width=1, color="white")),
        hovertemplate=hovertext, name="Municipios",
    ))

    # Capitales: mismo punto, pero con un puntito oscuro encima para
    # distinguirlas del resto de municipios del departamento.
    if capitales:
        idx_cap = [i for i, m in enumerate(municipios) if m == capitales.get(departamentos[i])]
        if idx_cap:
            fig.add_trace(go.Scatter(
                x=[valores[i] for i in idx_cap], y=[departamentos[i] for i in idx_cap],
                mode="markers", marker=dict(size=4, color="#111827"),
                hovertext=[f"<b>{municipios[i]}</b> (capital)<br>{departamentos[i]}<br>${valores[i]:,.0f}" for i in idx_cap],
                hovertemplate="%{hovertext}<extra></extra>", name="Capital",
            ))

    # Promedio departamental: un cuadrado por fila, en el PIB per cápita
    # real del departamento (no el promedio simple de sus municipios).
    if promedios_departamento:
        deps_p = [d for d in orden if d in promedios_departamento]
        vals_p = [promedios_departamento[d] for d in deps_p]
        fig.add_trace(go.Scatter(
            x=vals_p, y=deps_p, mode="markers",
            marker=dict(size=12, color="#eb6834", symbol="square", line=dict(width=1, color="white")),
            hovertemplate="<b>%{y}</b><br>Promedio departamental<br>$%{x:,.0f}<extra></extra>",
            name="Promedio departamental",
        ))

    if promedio_regional is not None:
        fig.add_vline(
            x=promedio_regional, line=dict(color="#111827", width=1.5, dash="dash"),
            annotation_text="Promedio Región Caribe", annotation_position="top",
        )

    fig.update_layout(
        title=titulo,
        height=max(560, 110 + 75 * len(orden)),
        margin=dict(l=20, r=20, t=50, b=40),
        xaxis=dict(title=x_titulo),
        yaxis=dict(categoryorder="array", categoryarray=orden, autorange="reversed"),
        legend=dict(orientation="h", y=-0.1),
    )
    return fig
