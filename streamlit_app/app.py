"""Panel del Caribe colombiano -- versión Streamlit del notebook EDA.ipynb.

Ejecutar con:  streamlit run streamlit_app/app.py
"""
import pandas as pd
import streamlit as st

from data import (
    NOMBRES_CORTOS_SECTOR,
    NOMBRES_RAMA_CORTOS,
    ORDEN_GRUPOS_EDAD,
    filtrar_geojson,
    geojson_municipios_de,
    load_all,
)
from charts import (
    build_department_map,
    build_evolution_line,
    build_municipios_map,
    build_pastel,
    build_pastel_municipal,
    build_pastel_participacion,
    build_pyramid,
    build_radar,
    calcular_colores_municipios,
    COLOR_LINEA_DEFECTO,
)

st.set_page_config(page_title="Caribe Colombiano — Panel departamental", layout="wide")

data = load_all()
mun = data["mun"]
dep = data["dep"]
dep_nacional = data["dep_nacional"]
idc_pilares = data["idc_pilares"]
icc_pilares = data["icc_pilares"]
pib_sector_caribe = data["pib_sector_caribe"]
piramide_dep = data["piramide_dep"]
piramide_mun = data["piramide_mun"]
geih_tasas = data["geih_tasas"]
geih_ocupados_rama = data["geih_ocupados_rama"]
capitales = data["capitales"]
pilares_disponibles = data["pilares_disponibles"]
departamentos_pais = data["departamentos_pais"]
ciudades_icc = data["ciudades_icc"]
anios_disponibles = data["anios_disponibles"]
caribe = data["caribe"]

mapa_caribe_geo = filtrar_geojson(data["mapa_dep_geo"], lambda p: p["nombre_entidad"] in caribe)

# ------------------------------------------------------------------
# ESTADO
# ------------------------------------------------------------------
def _init_estado():
    defaults = {
        "departamento_actual": "BOLÍVAR",
        "variable_activa": "Población",
        "vista_municipios": False,
        "municipio_actual": None,
        "comparar_con": "Ninguno",
        "sector_actual": None,
        "interactuado": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _procesar_click(evento, nombres, key_ultimo):
    """Devuelve el nombre recién clickeado, o None si no hay nada nuevo
    (evita reprocesar la misma selección en cada rerun posterior)."""
    puntos = evento["selection"]["points"] if evento and evento.get("selection") else []
    if not puntos:
        return None
    idx = puntos[0].get("point_index")
    if idx is None or idx >= len(nombres):
        return None
    nombre = nombres[idx]
    if nombre == st.session_state.get(key_ultimo):
        return None
    st.session_state[key_ultimo] = nombre
    return nombre


_init_estado()

anio_sel = st.select_slider("Año", options=anios_disponibles, value=anios_disponibles[-1], key="anio_sel")

if st.session_state["vista_municipios"]:
    opciones_comparar = ["Ninguno"] + ciudades_icc
else:
    opciones_comparar = ["Ninguno"] + departamentos_pais
if st.session_state["comparar_con"] not in opciones_comparar:
    st.session_state["comparar_con"] = "Ninguno"

st.title("Tablero Caribe")
st.caption("Seleccione un departamento y un año para explorar su perfil.")

col_mapa, col_grafico = st.columns([1, 1])

# ------------------------------------------------------------------
# MAPA
# ------------------------------------------------------------------
with col_mapa:
    if not st.session_state["vista_municipios"]:
        nombres_caribe = [f["properties"]["nombre_entidad"] for f in mapa_caribe_geo["features"]]
        comparar_dep = (
            st.session_state["comparar_con"]
            if st.session_state["variable_activa"] == "Competitividad" and st.session_state["comparar_con"] != "Ninguno"
            else None
        )
        fig_mapa = build_department_map(
            mapa_caribe_geo, caribe, st.session_state["departamento_actual"], comparar_dep
        )
        evento_mapa = st.plotly_chart(fig_mapa, on_select="rerun", key="click_mapa_dep", selection_mode="points")
        nuevo_dep = _procesar_click(evento_mapa, nombres_caribe, "_ultimo_click_mapa_dep")
        if nuevo_dep:
            st.session_state["interactuado"] = True
            st.session_state["departamento_actual"] = nuevo_dep
            st.session_state["municipio_actual"] = None
            st.session_state["sector_actual"] = None
            st.rerun()
    else:
        mapa_mun_geo = geojson_municipios_de(data["mapa_mun_geo"], mun, st.session_state["departamento_actual"])
        colores, nombres_mun = calcular_colores_municipios(
            mun, mapa_mun_geo, st.session_state["departamento_actual"], anio_sel, st.session_state["variable_activa"],
            geih_tasas=geih_tasas,
        )
        fig_municipios = build_municipios_map(mapa_mun_geo, colores, st.session_state["departamento_actual"])
        evento_mun = st.plotly_chart(fig_municipios, on_select="rerun", key="click_mapa_mun", selection_mode="points")
        nuevo_mun = _procesar_click(evento_mun, nombres_mun, "_ultimo_click_mapa_mun")
        if nuevo_mun:
            st.session_state["municipio_actual"] = nuevo_mun
            st.session_state["sector_actual"] = None
            st.rerun()

        # leyenda del mapa municipal
        if st.session_state["variable_activa"] == "PIB":
            st.caption("Color = actividad predominante · intensidad = su participación en el valor agregado")
        elif st.session_state["variable_activa"] == "Población":
            st.caption("Color = densidad poblacional (escala logarítmica), más oscuro = más denso")
        elif st.session_state["variable_activa"] == "Competitividad":
            st.caption("El ICC solo evalúa la ciudad capital de cada departamento — el resto queda en gris.")
        elif st.session_state["variable_activa"] == "Mercado laboral":
            st.caption("La GEIH solo evalúa la ciudad capital de cada departamento — el resto queda en gris.")

    if st.button(
        "◀ Volver al mapa departamental" if st.session_state["vista_municipios"] else "Ver municipios ▶",
        width="stretch",
    ):
        st.session_state["vista_municipios"] = not st.session_state["vista_municipios"]
        st.session_state["municipio_actual"] = None
        st.session_state["sector_actual"] = None
        st.session_state["comparar_con"] = "Ninguno"
        st.rerun()

# ------------------------------------------------------------------
# TARJETAS (Población / PIB / Competitividad / Municipios)
# ------------------------------------------------------------------
nombre_dep = st.session_state["departamento_actual"]
fila_dep = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]

if fila_dep.empty:
    poblacion_fmt, pib_fmt, competitividad_fmt = "—", "—", "—"
else:
    f = fila_dep.iloc[0]
    poblacion_fmt = f"{f['poblacion_total']:,.0f}"
    pib_fmt = f"${f['pib'] / 1e12:,.1f} billones"
    competitividad_fmt = f"{f['indice_competitividad']:.2f} / 10" if pd.notna(f.get("indice_competitividad")) else "—"

if not st.session_state["interactuado"]:
    municipios_fmt = mun["nombre_entidad"].nunique()
else:
    municipios_fmt = mun[mun["nombre_departamento"] == nombre_dep]["nombre_entidad"].nunique()

# La GEIH (mercado laboral) solo cubre la ciudad capital de cada
# departamento -- si hay un municipio seleccionado que NO es la capital, no
# hay dato (igual que Competitividad/ICC, pero sin ni siquiera un valor
# departamental de respaldo: la GEIH no publica agregados por departamento).
capital_dep = capitales.get(nombre_dep)
ciudad_ml = st.session_state["municipio_actual"]
if ciudad_ml and ciudad_ml != capital_dep:
    ciudad_ml = None
elif not ciudad_ml:
    ciudad_ml = capital_dep

# Si hay un municipio seleccionado, PIB y Competitividad se sobreescriben con
# el dato municipal (igual que en el notebook); Población se queda a nivel
# departamental salvo la pirámide, que sí tiene su propio overlay municipal.
municipio_actual = st.session_state["municipio_actual"]
if municipio_actual:
    fila_mun = mun[
        (mun["nombre_entidad"] == municipio_actual)
        & (mun["nombre_departamento"] == nombre_dep)
        & (mun["anio"] == anio_sel)
    ]
    if not fila_mun.empty:
        fm = fila_mun.iloc[0]
        pib_fmt = (
            f"${fm['valor_agregado'] / 1e9:,.1f} miles de millones" if pd.notna(fm.get("valor_agregado")) else "—"
        )
        competitividad_fmt = (
            f"{fm['indice_competitividad']:.2f} / 10" if pd.notna(fm.get("indice_competitividad")) else "—"
        )
    else:
        pib_fmt, competitividad_fmt = "—", "—"

st.subheader(nombre_dep if not municipio_actual else f"{municipio_actual} — {nombre_dep}")
st.caption(f"Perfil {'municipal' if municipio_actual else 'departamental'} — {anio_sel}")

c1, c2, c3, c4, c5 = st.columns(5)


def _tarjeta(col, etiqueta, valor, activa, key):
    with col:
        tipo = "primary" if activa else "secondary"
        texto = f"{etiqueta}\n{valor}" if valor else etiqueta
        return st.button(texto, key=key, type=tipo, width="stretch")


if _tarjeta(c1, "Población", poblacion_fmt, st.session_state["variable_activa"] == "Población", "tab_poblacion"):
    st.session_state["variable_activa"] = "Población"
    st.rerun()
if _tarjeta(c2, "PIB", pib_fmt, st.session_state["variable_activa"] == "PIB", "tab_pib"):
    st.session_state["variable_activa"] = "PIB"
    st.rerun()
if _tarjeta(c3, "Competitividad", competitividad_fmt, st.session_state["variable_activa"] == "Competitividad", "tab_competitividad"):
    st.session_state["variable_activa"] = "Competitividad"
    st.rerun()
if _tarjeta(c4, "Mercado laboral", "", st.session_state["variable_activa"] == "Mercado laboral", "tab_mercado_laboral"):
    st.session_state["variable_activa"] = "Mercado laboral"
    st.rerun()
with c5:
    st.button(f"Municipios\n{municipios_fmt}", disabled=True, width="stretch")

st.divider()

# ------------------------------------------------------------------
# CONTENIDO: Población (línea + pirámide) / PIB (línea + dona) / Competitividad (radar)
# ------------------------------------------------------------------
variable_activa = st.session_state["variable_activa"]
col_izq, col_der = st.columns(2)

if variable_activa == "Competitividad":
    comparar_con = st.selectbox("Comparar con:", opciones_comparar, key="comparar_con")

    if municipio_actual:
        fila_pil = icc_pilares[(icc_pilares["nombre_entidad"] == municipio_actual) & (icc_pilares["anio"] == anio_sel)]
        titulo_radar = municipio_actual
    else:
        fila_pil = idc_pilares[(idc_pilares["nombre_entidad"] == nombre_dep) & (idc_pilares["anio"] == anio_sel)]
        titulo_radar = nombre_dep

    if fila_pil.empty:
        valores = [0] * len(pilares_disponibles)
    else:
        valores = fila_pil.iloc[0][pilares_disponibles].tolist()

    valores_comp = None
    if comparar_con != "Ninguno":
        tabla_comp = icc_pilares if municipio_actual else idc_pilares
        fila_comp = tabla_comp[(tabla_comp["nombre_entidad"] == comparar_con) & (tabla_comp["anio"] == anio_sel)]
        if not fila_comp.empty:
            valores_comp = fila_comp.iloc[0][pilares_disponibles].tolist()

    fig_radar = build_radar(pilares_disponibles, valores, titulo_radar, comparar_con if valores_comp else None, valores_comp)
    st.plotly_chart(fig_radar, width="stretch")

elif variable_activa == "PIB":
    # Los toggles se leen de session_state ANTES de instanciar el widget (que
    # se instancia más abajo, debajo de cada gráfico, para que aparezca ahí
    # visualmente) -- Streamlit ya resuelve el valor del widget en
    # session_state al inicio del rerun, así que esto es seguro.
    modo_linea = st.session_state.get("modo_linea_pib", "Absoluto")
    modo_part = st.session_state.get("modo_participacion_pib", "Sectorial")

    with col_izq:
        if municipio_actual:
            serie = (
                mun[(mun["nombre_entidad"] == municipio_actual) & (mun["nombre_departamento"] == nombre_dep)]
                .dropna(subset=["valor_agregado"])
                .sort_values("anio")
            )
            if modo_linea == "Per cápita":
                y, y_titulo = serie["valor_agregado"] / serie["poblacion_total"], "PIB municipal per cápita"
            else:
                y, y_titulo = serie["valor_agregado"], "PIB municipal (valor agregado)"
            fig_linea = build_evolution_line(
                serie["anio"], y, anio_sel, f"Evolución de PIB municipal — {municipio_actual}", y_titulo,
            )
        else:
            # El toggle Absoluto/Per cápita solo aplica al PIB total -- el PIB
            # per cápita de UN sector no es una métrica estándar, así que si
            # hay un sector elegido se sigue mostrando en valor absoluto.
            sector_actual = st.session_state["sector_actual"] if modo_part == "Sectorial" else None
            if sector_actual:
                nombre_original = next(
                    (o for o, c in NOMBRES_CORTOS_SECTOR.items() if c == sector_actual["nombre"]), sector_actual["nombre"]
                )
                serie = (
                    pib_sector_caribe[
                        (pib_sector_caribe["Departamento"] == nombre_dep) & (pib_sector_caribe["Sector"] == nombre_original)
                    ]
                    .dropna(subset=["Valor_miles_millones_COP"])
                    .sort_values("Año")
                )
                fig_linea = build_evolution_line(
                    serie["Año"], serie["Valor_miles_millones_COP"], anio_sel,
                    f"Evolución de {sector_actual['nombre']} — {nombre_dep}",
                    f"{sector_actual['nombre']} (miles de millones COP)",
                    color_linea=sector_actual["color"],
                )
            else:
                serie = dep[dep["nombre_entidad"] == nombre_dep].dropna(subset=["pib"]).sort_values("anio")
                if modo_linea == "Per cápita":
                    y, y_titulo = serie["pib"] / serie["poblacion_total"], "PIB per cápita"
                else:
                    y, y_titulo = serie["pib"], "PIB"
                fig_linea = build_evolution_line(
                    serie["anio"], y, anio_sel, f"Evolución de {y_titulo} — {nombre_dep}", y_titulo,
                )
        st.plotly_chart(fig_linea, width="stretch")
        st.segmented_control(
            "Vista de la línea", ["Absoluto", "Per cápita"], default="Absoluto",
            key="modo_linea_pib", label_visibility="collapsed",
        )

    with col_der:
        if modo_part == "Sectorial":
            if municipio_actual:
                fila_mun_anio = mun[
                    (mun["nombre_entidad"] == municipio_actual)
                    & (mun["nombre_departamento"] == nombre_dep)
                    & (mun["anio"] == anio_sel)
                ]
                fila_serie = fila_mun_anio.iloc[0] if not fila_mun_anio.empty else None
                fig_pastel = build_pastel_municipal(fila_serie, f"Composición del PIB — {municipio_actual} ({anio_sel})")
            else:
                datos = pib_sector_caribe[
                    (pib_sector_caribe["Departamento"] == nombre_dep) & (pib_sector_caribe["Año"] == anio_sel)
                ]
                sectores = datos[~datos["Sector"].isin(["Valor agregado total", "Producto Interno Bruto"])].copy()
                sectores["Sector_corto"] = sectores["Sector"].map(NOMBRES_CORTOS_SECTOR).fillna(sectores["Sector"])
                fig_pastel = build_pastel(
                    sectores["Sector_corto"], sectores["Valor_miles_millones_COP"],
                    f"Composición del PIB por sector — {nombre_dep} ({anio_sel})",
                )

            evento_pastel = st.plotly_chart(fig_pastel, on_select="rerun", key="click_pastel", selection_mode="points")
            if not municipio_actual:
                etiquetas_sector = list(sectores["Sector_corto"])
                colores_sector = list(fig_pastel.data[0].marker.colors)
                puntos = evento_pastel["selection"]["points"] if evento_pastel and evento_pastel.get("selection") else []
                if puntos:
                    idx = puntos[0].get("point_index")
                    if idx is not None and idx < len(etiquetas_sector):
                        sector_click = etiquetas_sector[idx]
                        color_click = colores_sector[idx % len(colores_sector)]
                        if st.session_state.get("_ultimo_click_pastel") != (nombre_dep, anio_sel, sector_click):
                            st.session_state["_ultimo_click_pastel"] = (nombre_dep, anio_sel, sector_click)
                            actual = st.session_state["sector_actual"]
                            if actual and actual["nombre"] == sector_click:
                                st.session_state["sector_actual"] = None
                            else:
                                st.session_state["sector_actual"] = {"nombre": sector_click, "color": color_click}
                            st.rerun()

        else:  # Regional / Nacional -- participación dentro de un universo mayor
            fila_dep_anio = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
            valor_dep = fila_dep_anio["pib"].iloc[0] if not fila_dep_anio.empty else 0
            valor_caribe = dep[dep["anio"] == anio_sel]["pib"].sum()

            if municipio_actual:
                fila_mun_anio = mun[
                    (mun["nombre_entidad"] == municipio_actual)
                    & (mun["nombre_departamento"] == nombre_dep)
                    & (mun["anio"] == anio_sel)
                ]
                hay_dato_mun = not fila_mun_anio.empty and pd.notna(fila_mun_anio["valor_agregado"].iloc[0])
                if not hay_dato_mun:
                    # El PIB municipal suele llegar con un año de rezago frente
                    # al departamental -- evitamos mostrar un 0% engañoso.
                    fig_pastel = None
                    st.info(f"No hay dato de PIB municipal para {municipio_actual} en {anio_sel}.")
                else:
                    valor_mun = fila_mun_anio["valor_agregado"].iloc[0]
                    resto_dep = max(valor_dep - valor_mun, 0)
                    resto_caribe = max(valor_caribe - valor_dep, 0)
                    pct_dep = (valor_mun / valor_dep * 100) if valor_dep else 0
                    pct_caribe = (valor_mun / valor_caribe * 100) if valor_caribe else 0
                    hover = (
                        f"<b>{municipio_actual}</b><br>{pct_dep:.1f}% de {nombre_dep}<br>"
                        f"{pct_caribe:.1f}% de la Región Caribe<extra></extra>"
                    )
                    fig_pastel = build_pastel_participacion(
                        municipio_actual, f"Resto de {nombre_dep}", "Resto de la Región Caribe",
                        valor_mun, resto_dep, resto_caribe,
                        f"Participación de {municipio_actual} en {nombre_dep} y la Región Caribe ({anio_sel})",
                        hover,
                    )
            else:
                valor_nacional = dep_nacional[dep_nacional["anio"] == anio_sel]["pib"].sum()
                resto_caribe = max(valor_caribe - valor_dep, 0)
                resto_nacional = max(valor_nacional - valor_caribe, 0)
                pct_nacional = (valor_dep / valor_nacional * 100) if valor_nacional else 0
                pct_caribe = (valor_dep / valor_caribe * 100) if valor_caribe else 0
                hover = (
                    f"<b>{nombre_dep}</b><br>{pct_nacional:.1f}% de Colombia<br>"
                    f"{pct_caribe:.1f}% de la Región Caribe<extra></extra>"
                )
                fig_pastel = build_pastel_participacion(
                    nombre_dep, "Resto de la Región Caribe", "Resto de Colombia",
                    valor_dep, resto_caribe, resto_nacional,
                    f"Participación de {nombre_dep} en la Región Caribe y Colombia ({anio_sel})",
                    hover,
                )
            if fig_pastel is not None:
                st.plotly_chart(fig_pastel, width="stretch")

        st.segmented_control(
            "Vista de participación", ["Sectorial", "Regional/Nacional"], default="Sectorial",
            key="modo_participacion_pib", label_visibility="collapsed",
        )

elif variable_activa == "Mercado laboral":
    if not ciudad_ml:
        st.info(
            f"La GEIH no tiene dato para este municipio -- solo cubre la ciudad capital "
            f"({capital_dep or 'sin capital definida'})."
        )
    else:
        with col_izq:
            serie = geih_tasas[geih_tasas["nombre_entidad"] == ciudad_ml].dropna(subset=["td"]).sort_values("anio")
            fig_linea = build_evolution_line(
                serie["anio"], serie["td"], anio_sel,
                f"Evolución de la Tasa de Desocupación — {ciudad_ml}", "Tasa de desocupación (%)",
                unidad="%",
            )
            st.plotly_chart(fig_linea, width="stretch")
            st.caption("Trimestre móvil Oct-Dic de cada año (GEIH, DANE).")

        with col_der:
            fila_rama = geih_ocupados_rama[
                (geih_ocupados_rama["nombre_entidad"] == ciudad_ml) & (geih_ocupados_rama["anio"] == anio_sel)
            ]
            if fila_rama.empty:
                st.info(f"Sin dato de ocupados por sector para {ciudad_ml} en {anio_sel}.")
            else:
                fila = fila_rama.iloc[0]
                ramas = list(NOMBRES_RAMA_CORTOS.keys())
                valores_rama = fila[ramas].dropna()
                etiquetas = [NOMBRES_RAMA_CORTOS[c] for c in valores_rama.index]
                fig_pastel_ml = build_pastel(
                    etiquetas, valores_rama.values, f"Ocupados por sector — {ciudad_ml} ({anio_sel})",
                    unidad="miles de personas",
                )
                st.plotly_chart(fig_pastel_ml, width="stretch")
                st.caption("Miles de personas, trimestre móvil Oct-Dic (GEIH, DANE).")

else:  # Población
    with col_izq:
        if municipio_actual:
            serie = (
                mun[(mun["nombre_entidad"] == municipio_actual) & (mun["nombre_departamento"] == nombre_dep)]
                .dropna(subset=["poblacion_total"])
                .sort_values("anio")
            )
            fig_linea = build_evolution_line(
                serie["anio"], serie["poblacion_total"], anio_sel,
                f"Evolución de Población — {municipio_actual}", "Población",
            )
        else:
            serie = dep[dep["nombre_entidad"] == nombre_dep].dropna(subset=["poblacion_total"]).sort_values("anio")
            fig_linea = build_evolution_line(
                serie["anio"], serie["poblacion_total"], anio_sel, f"Evolución de Población — {nombre_dep}", "Población",
            )
        st.plotly_chart(fig_linea, width="stretch")

    with col_der:
        datos_dep_pir = piramide_dep[(piramide_dep["nombre_entidad"] == nombre_dep) & (piramide_dep["anio"] == anio_sel)]
        datos_dep_pir = datos_dep_pir.set_index("grupo_edad").reindex(ORDEN_GRUPOS_EDAD).fillna(0)

        if municipio_actual:
            datos_mun_pir = piramide_mun[
                (piramide_mun["nombre_entidad"] == municipio_actual)
                & (piramide_mun["nombre_departamento"] == nombre_dep)
                & (piramide_mun["anio"] == anio_sel)
            ]
            datos_mun_pir = datos_mun_pir.set_index("grupo_edad").reindex(ORDEN_GRUPOS_EDAD).fillna(0)
            fig_piramide = build_pyramid(
                datos_mun_pir["hombres"], datos_mun_pir["mujeres"],
                f"Pirámide poblacional — {municipio_actual} dentro de {nombre_dep} ({anio_sel})",
                hombres_fondo=datos_dep_pir["hombres"], mujeres_fondo=datos_dep_pir["mujeres"],
            )
        else:
            fig_piramide = build_pyramid(
                datos_dep_pir["hombres"], datos_dep_pir["mujeres"], f"Pirámide poblacional — {nombre_dep} ({anio_sel})",
            )
        st.plotly_chart(fig_piramide, width="stretch")
