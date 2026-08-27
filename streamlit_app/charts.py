"""Constructores de gráficos Plotly -- funciones puras: reciben datos y
devuelven una go.Figure nueva. A diferencia del notebook (donde se mutaban
FigureWidgets en el lugar), en Streamlit el script se re-ejecuta completo en
cada interacción, así que no hace falta (ni sirve) mantener estado dentro de
las figuras.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from data import ORDEN_GRUPOS_EDAD

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
    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i:i + 2], 16) for i in (0, 2, 4))
    r = round(255 + (r - 255) * t)
    g = round(255 + (g - 255) * t)
    b = round(255 + (b - 255) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ------------------------------------------------------------------
# Mapa departamental
# ------------------------------------------------------------------
def build_department_map(mapa_caribe_geo, caribe, departamento_actual, comparar_con=None):
    nombres = [f["properties"]["nombre_entidad"] for f in mapa_caribe_geo["features"]]
    colores_z = []
    for nombre in nombres:
        if nombre == departamento_actual:
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
def build_pastel(labels, values, titulo):
    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.35,
            marker=dict(colors=px.colors.qualitative.Set3),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} miles de millones COP<br>%{percent}<extra></extra>",
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
