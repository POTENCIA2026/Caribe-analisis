"""Panel del Caribe colombiano -- versión Streamlit del notebook EDA.ipynb.

Ejecutar con:  streamlit run streamlit_app/app.py
"""
import pandas as pd
import streamlit as st
from streamlit_plotly_events import plotly_events

from data import (
    NOMBRES_CORTOS_SECTOR,
    NOMBRES_RAMA_CORTOS,
    ORDEN_GRUPOS_EDAD,
    RAMA_A_SECTOR_PIB,
    RAMAS_SECTOR_COMBINADO,
    filtrar_geojson,
    geojson_municipios_caribe,
    geojson_municipios_de,
    load_all,
)
from charts import (
    build_department_map,
    build_dispersion_municipios,
    build_evolution_line,
    build_hemiciclo,
    build_municipios_map,
    build_municipios_map_region,
    build_pastel,
    build_pastel_municipal,
    build_pastel_participacion,
    build_pastel_participacion_total,
    build_ranking_barras,
    build_pyramid,
    build_radar,
    calcular_colores_departamentos_composicion,
    calcular_colores_departamentos_ml,
    calcular_colores_departamentos_pib,
    calcular_colores_departamentos_poblacion,
    calcular_colores_municipios,
    calcular_colores_municipios_region,
    colores_hemiciclo,
    NOMBRE_OTROS_PARTIDOS,
    nombre_legible_partido,
    COLOR_DENSIDAD_RURAL,
    COLOR_DENSIDAD_URBANA,
    COLOR_LINEA_DEFECTO,
    COLOR_RAMA_GEIH,
    COLOR_SECTORES_PIB,
)

st.set_page_config(page_title="Caribe Colombiano — Panel departamental", layout="wide")

data = load_all()
mun = data["mun"]
mun_nacional = data["mun_nacional"]
dep = data["dep"]
dep_nacional = data["dep_nacional"]
idc_pilares = data["idc_pilares"]
icc_pilares = data["icc_pilares"]
pib_sector_caribe = data["pib_sector_caribe"]
piramide_dep = data["piramide_dep"]
piramide_mun = data["piramide_mun"]
geih_tasas = data["geih_tasas"]
geih_ocupados_rama = data["geih_ocupados_rama"]
composicion_asamblea = data["composicion_asamblea"]
composicion_concejo = data["composicion_concejo"]
capitales = data["capitales"]
pilares_disponibles = data["pilares_disponibles"]
departamentos_pais = data["departamentos_pais"]
ciudades_icc = data["ciudades_icc"]
anios_disponibles = data["anios_disponibles"]
caribe = data["caribe"]

mapa_caribe_geo = filtrar_geojson(data["mapa_dep_geo"], lambda p: p["nombre_entidad"] in caribe)
mapa_caribe_municipios_geo = geojson_municipios_caribe(data["mapa_mun_geo"], mun)

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
        "sector_actual_ml": None,
        "partido_actual": None,
        "modo_total": False,
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

# Composición política de la asamblea -- siempre la vigente (2024-2027), sin
# importar el año del slider (las asambleas se eligen cada 4 años). Se
# calcula acá arriba (no solo más abajo, junto al resto del contenido de la
# pestaña) porque el mapa también la necesita para colorear por partido.
PERIODO_ASAMBLEA_VIGENTE = "2024-2027"
comp_vigente = composicion_asamblea[composicion_asamblea["periodo"] == PERIODO_ASAMBLEA_VIGENTE]

col_mapa, col_grafico = st.columns([1, 1])

# ------------------------------------------------------------------
# MAPA
# ------------------------------------------------------------------
with col_mapa:
    col_mapa_viz, col_mapa_lista = st.columns([3, 2])

    with col_mapa_viz:
        if not st.session_state["vista_municipios"]:
            nombres_caribe = [f["properties"]["nombre_entidad"] for f in mapa_caribe_geo["features"]]
            comparar_dep = (
                st.session_state["comparar_con"]
                if st.session_state["variable_activa"] == "Competitividad" and st.session_state["comparar_con"] != "Ninguno"
                else None
            )
            colores_pib_dep = (
                calcular_colores_departamentos_pib(pib_sector_caribe, caribe, anio_sel)
                if st.session_state["variable_activa"] == "PIB" else None
            )
            colores_ml_dep = (
                calcular_colores_departamentos_ml(geih_ocupados_rama, caribe, capitales, anio_sel)
                if st.session_state["variable_activa"] == "Mercado laboral" else None
            )
            colores_pob_dep = (
                calcular_colores_departamentos_poblacion(dep, caribe, anio_sel)
                if st.session_state["variable_activa"] == "Población" else None
            )
            colores_comp_dep = (
                calcular_colores_departamentos_composicion(comp_vigente, caribe)
                if st.session_state["variable_activa"] == "Composición Política" else None
            )
            hover_pob_dep = None
            if colores_pob_dep is not None:
                datos_dens_anio = dep[dep["anio"] == anio_sel].dropna(subset=["densidad_pob"]).set_index("nombre_entidad")
                hover_pob_dep = {
                    n: f"{datos_dens_anio.loc[n, 'densidad_pob']:,.1f} hab/km²" for n in datos_dens_anio.index
                }
            colores_dep = (
                colores_pib_dep if colores_pib_dep is not None
                else colores_ml_dep if colores_ml_dep is not None
                else colores_pob_dep if colores_pob_dep is not None
                else colores_comp_dep
            )
            fig_mapa = build_department_map(
                mapa_caribe_geo, caribe, st.session_state["departamento_actual"], comparar_dep, colores_dep,
                todos_activos=st.session_state["modo_total"], hover_extra=hover_pob_dep,
            )
            if colores_pib_dep is not None:
                st.caption("Color = mezcla ponderada de los sectores del PIB (huella económica) · borde oscuro = seleccionado")
            elif colores_ml_dep is not None:
                st.caption(
                    "Color = mezcla ponderada de las ramas de ocupación en la capital (huella laboral) · "
                    "borde oscuro = seleccionado"
                )
            elif colores_pob_dep is not None:
                st.caption("Color = densidad poblacional (escala logarítmica) · más oscuro = más denso · borde oscuro = seleccionado")
            elif colores_comp_dep is not None:
                st.caption(
                    "Color = mezcla ponderada de los partidos de la asamblea, según sus curules · "
                    "borde oscuro = seleccionado"
                )
            evento_mapa = st.plotly_chart(fig_mapa, on_select="rerun", key="click_mapa_dep", selection_mode="points")
            nuevo_dep = _procesar_click(evento_mapa, nombres_caribe, "_ultimo_click_mapa_dep")
            if nuevo_dep:
                st.session_state["interactuado"] = True
                st.session_state["departamento_actual"] = nuevo_dep
                st.session_state["municipio_actual"] = None
                st.session_state["sector_actual"] = None
                st.session_state["sector_actual_ml"] = None
                st.session_state["partido_actual"] = None
                st.session_state["modo_total"] = False
                st.rerun()
        else:
            mapa_mun_geo = geojson_municipios_de(data["mapa_mun_geo"], mun, st.session_state["departamento_actual"])
            colores, nombres_mun = calcular_colores_municipios(
                mun, mapa_mun_geo, st.session_state["departamento_actual"], anio_sel, st.session_state["variable_activa"],
                geih_tasas=geih_tasas, composicion_concejo=composicion_concejo,
            )
            fig_municipios = build_municipios_map(mapa_mun_geo, colores, st.session_state["departamento_actual"])
            evento_mun = st.plotly_chart(fig_municipios, on_select="rerun", key="click_mapa_mun", selection_mode="points")
            nuevo_mun = _procesar_click(evento_mun, nombres_mun, "_ultimo_click_mapa_mun")
            if nuevo_mun:
                st.session_state["municipio_actual"] = nuevo_mun
                st.session_state["sector_actual"] = None
                st.session_state["sector_actual_ml"] = None
                st.session_state["partido_actual"] = None
                st.rerun()

            # leyenda del mapa municipal
            if st.session_state["variable_activa"] == "PIB":
                st.caption("Color = actividad predominante · intensidad = su participación en el valor agregado")
                cols_actividad = ["actividades_primarias", "actividades_secundarias", "actividades_terciarias"]
                sin_dato_anio = mun[mun["anio"] == anio_sel][cols_actividad].isna().all(axis=None)
                if sin_dato_anio:
                    st.caption(f"⚠️ Todavía no hay datos de composición del PIB por actividad para {anio_sel} -- por eso el mapa se ve gris. Pruebe con un año anterior.")
            elif st.session_state["variable_activa"] == "Población":
                st.caption("Color = densidad poblacional (escala logarítmica), más oscuro = más denso")
            elif st.session_state["variable_activa"] == "Competitividad":
                st.caption("El ICC solo evalúa la ciudad capital de cada departamento — el resto queda en gris.")
            elif st.session_state["variable_activa"] == "Mercado laboral":
                st.caption("La GEIH solo evalúa la ciudad capital de cada departamento — el resto queda en gris.")
            elif st.session_state["variable_activa"] == "Composición Política":
                st.caption(
                    "Color = mezcla ponderada de los partidos del concejo, según sus curules · gris = todavía sin "
                    "datos registrados para ese municipio."
                )

        if st.button(
            "◀ Volver al mapa departamental" if st.session_state["vista_municipios"] else "Ver municipios ▶",
            width="stretch",
        ):
            st.session_state["vista_municipios"] = not st.session_state["vista_municipios"]
            st.session_state["municipio_actual"] = None
            st.session_state["sector_actual"] = None
            st.session_state["sector_actual_ml"] = None
            st.session_state["partido_actual"] = None
            st.session_state["comparar_con"] = "Ninguno"
            st.session_state["modo_total"] = False
            st.rerun()

    # Lista clickeable -- la misma selección que se hace tocando el mapa,
    # pero como botones normales (sin desplegable) para quien prefiera
    # buscar el nombre en vez de ubicarlo en el mapa.
    with col_mapa_lista:
        if not st.session_state["vista_municipios"]:
            st.caption("Departamentos")
            activo_total = st.session_state["modo_total"]
            if st.button(
                "REGIÓN CARIBE", key="btn_total_caribe",
                type="primary" if activo_total else "secondary", width="stretch",
            ):
                if not activo_total:
                    st.session_state["interactuado"] = True
                    st.session_state["modo_total"] = True
                    st.session_state["municipio_actual"] = None
                    st.session_state["sector_actual"] = None
                    st.session_state["sector_actual_ml"] = None
                    st.session_state["partido_actual"] = None
                    st.rerun()
            for nombre in sorted(caribe):
                activo = nombre == st.session_state["departamento_actual"] and not activo_total
                if st.button(nombre, key=f"btn_dep_{nombre}", type="primary" if activo else "secondary", width="stretch"):
                    if not activo:
                        st.session_state["interactuado"] = True
                        st.session_state["departamento_actual"] = nombre
                        st.session_state["municipio_actual"] = None
                        st.session_state["sector_actual"] = None
                        st.session_state["sector_actual_ml"] = None
                        st.session_state["partido_actual"] = None
                        st.session_state["modo_total"] = False
                        st.rerun()
        else:
            dep_lista = st.session_state["departamento_actual"]
            nombres_mun_lista = sorted(mun[mun["nombre_departamento"] == dep_lista]["nombre_entidad"].unique())
            st.caption(f"Municipios de {dep_lista}")
            with st.container(height=430):
                for nombre in nombres_mun_lista:
                    activo = nombre == st.session_state["municipio_actual"]
                    if st.button(nombre, key=f"btn_mun_{nombre}", type="primary" if activo else "secondary", width="stretch"):
                        if not activo:
                            st.session_state["municipio_actual"] = nombre
                            st.session_state["sector_actual"] = None
                            st.session_state["sector_actual_ml"] = None
                            st.session_state["partido_actual"] = None
                            st.rerun()

# ------------------------------------------------------------------
# TARJETAS (Población / PIB / Competitividad / Municipios)
# ------------------------------------------------------------------
nombre_dep = st.session_state["departamento_actual"]
modo_total = st.session_state["modo_total"]

if modo_total:
    # Vista Total: los 7 departamentos del Caribe combinados en una sola
    # "hoja" -- población y PIB se suman, competitividad se promedia (es un
    # índice, no algo que tenga sentido sumar).
    dep_anio_total = dep[dep["anio"] == anio_sel]
    poblacion_fmt = f"{dep_anio_total['poblacion_total'].sum():,.0f}"
    pib_fmt = f"${dep_anio_total['pib'].sum() / 1e12:,.1f} billones"
    comp_serie_total = dep_anio_total["indice_competitividad"].dropna()
    competitividad_fmt = f"{comp_serie_total.mean():.2f} / 10" if not comp_serie_total.empty else "—"
else:
    fila_dep = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
    if fila_dep.empty:
        poblacion_fmt, pib_fmt, competitividad_fmt = "—", "—", "—"
    else:
        f = fila_dep.iloc[0]
        poblacion_fmt = f"{f['poblacion_total']:,.0f}"
        pib_fmt = f"${f['pib'] / 1e12:,.1f} billones"
        competitividad_fmt = f"{f['indice_competitividad']:.2f} / 10" if pd.notna(f.get("indice_competitividad")) else "—"

if modo_total or not st.session_state["interactuado"]:
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

if modo_total:
    # Tasa de desocupación regional = desocupados ÷ fuerza de trabajo,
    # sumados entre las 7 capitales -- no el promedio simple de las 7 tasas
    # (eso pesaría igual a Riohacha que a Barranquilla).
    capitales_caribe = list(capitales.values())
    fila_ml_total = geih_tasas[
        geih_tasas["nombre_entidad"].isin(capitales_caribe) & (geih_tasas["anio"] == anio_sel)
    ]
    fuerza_total = fila_ml_total["fuerza_trabajo"].sum()
    mercado_laboral_fmt = (
        f"{fila_ml_total['desocupados'].sum() / fuerza_total * 100:.1f}%" if fuerza_total else "—"
    )
elif ciudad_ml:
    fila_ml = geih_tasas[(geih_tasas["nombre_entidad"] == ciudad_ml) & (geih_tasas["anio"] == anio_sel)]
    mercado_laboral_fmt = f"{fila_ml.iloc[0]['td']:.1f}%" if not fila_ml.empty and pd.notna(fila_ml.iloc[0].get("td")) else "—"
else:
    mercado_laboral_fmt = "—"

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

if modo_total:
    st.subheader("Región Caribe — Total")
    st.caption(f"Perfil regional (7 departamentos) — {anio_sel}")
else:
    st.subheader(nombre_dep if not municipio_actual else f"{municipio_actual} — {nombre_dep}")
    st.caption(f"Perfil {'municipal' if municipio_actual else 'departamental'} — {anio_sel}")


if modo_total:
    comp_dep_actual = comp_vigente[comp_vigente["nombre_departamento"].isin(caribe)]
    total_curules = comp_dep_actual["curules"].sum()
elif municipio_actual:
    # Igual que PIB/Competitividad: si hay un municipio seleccionado y ya
    # se registró su concejo, la tarjeta muestra sus curules en vez de las
    # de la asamblea departamental.
    total_curules = composicion_concejo[composicion_concejo["nombre_municipio"] == municipio_actual]["curules"].sum()
else:
    comp_dep_actual = comp_vigente[comp_vigente["nombre_departamento"] == nombre_dep]
    total_curules = comp_dep_actual["curules"].sum()
composicion_fmt = f"{total_curules} curules" if total_curules else "—"

c1, c2, c3, c4, c5, c6 = st.columns(6)


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
if _tarjeta(c4, "Mercado laboral", mercado_laboral_fmt, st.session_state["variable_activa"] == "Mercado laboral", "tab_mercado_laboral"):
    st.session_state["variable_activa"] = "Mercado laboral"
    st.rerun()
if _tarjeta(c5, "Composición Política", composicion_fmt, st.session_state["variable_activa"] == "Composición Política", "tab_composicion_politica"):
    st.session_state["variable_activa"] = "Composición Política"
    st.rerun()
with c6:
    st.button(f"Municipios\n{municipios_fmt}", disabled=True, width="stretch")

st.divider()

# ------------------------------------------------------------------
# CONTENIDO: Población (línea + pirámide) / PIB (línea + dona) / Competitividad (radar)
# ------------------------------------------------------------------
variable_activa = st.session_state["variable_activa"]
col_izq, col_der = st.columns(2)

if variable_activa == "Competitividad":
    if not municipio_actual:
        st.subheader("La competitividad como medida de desarrollo", divider="gray")

    if modo_total:
        fila_pil_total = idc_pilares[idc_pilares["nombre_entidad"].isin(caribe) & (idc_pilares["anio"] == anio_sel)]
        valores = [0] * len(pilares_disponibles) if fila_pil_total.empty else fila_pil_total[pilares_disponibles].mean().tolist()
        fig_radar = build_radar(pilares_disponibles, valores, "Región Caribe (promedio)")
        st.plotly_chart(fig_radar, width="stretch")
        st.caption("Promedio simple de los 7 departamentos del Caribe en cada pilar del ICC.")
    else:
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
    # Los widgets se instancian AQUÍ (antes de construir los gráficos) y se
    # usa directamente su valor de retorno -- NO st.session_state.get(key)
    # leído por adelantado. Ese atajo parecía seguro ("Streamlit resuelve el
    # valor del widget en session_state al inicio del rerun") pero solo
    # funciona cuando el rerun lo dispara el propio widget: si lo dispara
    # OTRO control (ej. cambiar de departamento, que hace su propio
    # st.rerun()), la lectura anticipada devuelve el valor por defecto en
    # vez del último elegido, y el toggle "se olvida" de su estado. Para
    # mantener el toggle visualmente DEBAJO del gráfico (como antes) sin
    # volver a ese atajo, se reserva el espacio del gráfico con st.empty()
    # antes de instanciar el widget, y se llena después.
    with col_izq:
        slot_izq = st.empty()
        modo_linea = st.segmented_control(
            "Vista de la línea", ["Absoluto", "Per cápita"], default="Absoluto",
            key="modo_linea_pib", label_visibility="collapsed", persist_state="session",
        )
        if not municipio_actual and st.session_state.get("sector_actual"):
            # Volver a hacer click en la misma porción de la dona no siempre
            # dispara un nuevo evento (el componente no reenvía un valor
            # idéntico al anterior) -- este botón siempre funciona.
            if st.button(f"✕ Quitar {st.session_state['sector_actual']['nombre']}", key="quitar_sector"):
                st.session_state["sector_actual"] = None
                st.rerun()
    with col_der:
        slot_der = st.empty()
        if modo_linea == "Per cápita":
            # En modo Per cápita el gráfico de al lado deja de ser la
            # composición sectorial (no tiene sentido por-cápita) y pasa a
            # ser el ranking de departamentos -- no hay nada que alternar.
            modo_part = None
        else:
            modo_part = st.segmented_control(
                "Vista de participación", ["Sectorial", "Regional/Nacional"], default="Sectorial",
                key="modo_participacion_pib", label_visibility="collapsed", persist_state="session",
            )

    ambito_pib = "Región Caribe" if modo_total else nombre_dep

    with slot_izq.container():
        if modo_total:
            sector_actual = st.session_state["sector_actual"] if modo_part == "Sectorial" else None
            if sector_actual:
                nombre_original = next(
                    (o for o, c in NOMBRES_CORTOS_SECTOR.items() if c == sector_actual["nombre"]), sector_actual["nombre"]
                )
                serie = (
                    pib_sector_caribe[pib_sector_caribe["Sector"] == nombre_original]
                    .groupby("Año", as_index=False)["Valor_miles_millones_COP"].sum()
                    .dropna(subset=["Valor_miles_millones_COP"])
                    .sort_values("Año")
                )
                if modo_linea == "Per cápita":
                    poblacion_por_anio = dep.groupby("anio")["poblacion_total"].sum()
                    y = serie["Valor_miles_millones_COP"] * 1e9 / serie["Año"].map(poblacion_por_anio)
                    y_titulo = f"{sector_actual['nombre']} per cápita"
                else:
                    y = serie["Valor_miles_millones_COP"]
                    y_titulo = f"{sector_actual['nombre']} (miles de millones COP)"
                fig_linea = build_evolution_line(
                    serie["Año"], y, anio_sel, f"Evolución de {y_titulo} — {ambito_pib}", y_titulo,
                    color_linea=sector_actual["color"],
                )
            else:
                serie = dep.groupby("anio", as_index=False).agg(pib=("pib", "sum"), poblacion_total=("poblacion_total", "sum"))
                serie = serie.dropna(subset=["pib"]).sort_values("anio")
                if modo_linea == "Per cápita":
                    y, y_titulo = serie["pib"] / serie["poblacion_total"], "PIB per cápita"
                else:
                    y, y_titulo = serie["pib"], "PIB"
                fig_linea = build_evolution_line(
                    serie["anio"], y, anio_sel, f"Evolución de {y_titulo} — {ambito_pib}", y_titulo,
                )
        elif municipio_actual:
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
                if modo_linea == "Per cápita":
                    # Valor_miles_millones_COP está en miles de millones de COP;
                    # lo llevamos a COP planos antes de dividir por población.
                    poblacion_por_anio = dep[dep["nombre_entidad"] == nombre_dep].set_index("anio")["poblacion_total"]
                    y = serie["Valor_miles_millones_COP"] * 1e9 / serie["Año"].map(poblacion_por_anio)
                    y_titulo = f"{sector_actual['nombre']} per cápita"
                else:
                    y = serie["Valor_miles_millones_COP"]
                    y_titulo = f"{sector_actual['nombre']} (miles de millones COP)"
                fig_linea = build_evolution_line(
                    serie["Año"], y, anio_sel, f"Evolución de {y_titulo} — {nombre_dep}", y_titulo,
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

    with slot_der.container():
        if modo_linea == "Per cápita":
            dep_anio_rank = dep[dep["anio"] == anio_sel].dropna(subset=["pib", "poblacion_total"])
            if dep_anio_rank.empty:
                st.info(f"No hay datos de PIB per cápita departamental para {anio_sel}.")
            else:
                etiquetas_rank = dep_anio_rank["nombre_entidad"].tolist()
                valores_rank = (dep_anio_rank["pib"] / dep_anio_rank["poblacion_total"]).tolist()
                fig_rank_dep = build_ranking_barras(
                    etiquetas_rank, valores_rank,
                    f"PIB per cápita por departamento — Región Caribe ({anio_sel})",
                    colores=["#2a78d6"] * len(etiquetas_rank), unidad="COP",
                    seleccionado=None if modo_total else nombre_dep,
                )
                st.plotly_chart(fig_rank_dep, width="stretch")
                st.caption("PIB departamental ÷ población del departamento.")
        elif modo_part == "Sectorial":
            if modo_total:
                datos = pib_sector_caribe[pib_sector_caribe["Año"] == anio_sel]
                sectores = (
                    datos[~datos["Sector"].isin(["Valor agregado total", "Producto Interno Bruto"])]
                    .groupby("Sector", as_index=False)["Valor_miles_millones_COP"].sum()
                )
                sectores["Sector_corto"] = sectores["Sector"].map(NOMBRES_CORTOS_SECTOR).fillna(sectores["Sector"])
                sectores = sectores.sort_values("Valor_miles_millones_COP", ascending=False)
                fig_pastel = build_pastel(
                    sectores["Sector_corto"], sectores["Valor_miles_millones_COP"],
                    f"Composición del PIB por sector — {ambito_pib} ({anio_sel})",
                    colores=[COLOR_SECTORES_PIB.get(s, "#cccccc") for s in sectores["Sector_corto"]],
                )
                puntos = plotly_events(
                    fig_pastel, click_event=True, override_height=420, override_width="100%",
                    key="click_pastel",
                )
                etiquetas_sector = list(sectores["Sector_corto"])
                colores_sector = list(fig_pastel.data[0].marker.colors)
                if puntos:
                    idx = puntos[0].get("pointNumber")
                    if idx is not None and idx < len(etiquetas_sector):
                        sector_click = etiquetas_sector[idx]
                        color_click = colores_sector[idx % len(colores_sector)]
                        if st.session_state.get("_ultimo_click_pastel") != ("TOTAL", anio_sel, sector_click):
                            st.session_state["_ultimo_click_pastel"] = ("TOTAL", anio_sel, sector_click)
                            actual = st.session_state["sector_actual"]
                            if actual and actual["nombre"] == sector_click:
                                st.session_state["sector_actual"] = None
                            else:
                                st.session_state["sector_actual"] = {"nombre": sector_click, "color": color_click}
                            st.rerun()
            elif municipio_actual:
                fila_mun_anio = mun[
                    (mun["nombre_entidad"] == municipio_actual)
                    & (mun["nombre_departamento"] == nombre_dep)
                    & (mun["anio"] == anio_sel)
                ]
                fila_serie = fila_mun_anio.iloc[0] if not fila_mun_anio.empty else None
                columnas_actividad = ["actividades_primarias", "actividades_secundarias", "actividades_terciarias"]
                sin_dato_actividad = fila_serie is None or fila_serie[columnas_actividad].isna().all()
                if sin_dato_actividad:
                    # Igual que el PIB municipal: la composición por actividad
                    # también llega con un año de rezago frente al departamental.
                    st.info(f"No hay dato de composición del PIB para {municipio_actual} en {anio_sel}.")
                else:
                    fig_pastel = build_pastel_municipal(fila_serie, f"Composición del PIB — {municipio_actual} ({anio_sel})")
                    st.plotly_chart(fig_pastel, width="stretch")
            else:
                datos = pib_sector_caribe[
                    (pib_sector_caribe["Departamento"] == nombre_dep) & (pib_sector_caribe["Año"] == anio_sel)
                ]
                sectores = datos[~datos["Sector"].isin(["Valor agregado total", "Producto Interno Bruto"])].copy()
                sectores["Sector_corto"] = sectores["Sector"].map(NOMBRES_CORTOS_SECTOR).fillna(sectores["Sector"])
                # Orden fijo (mayor a menor) en los datos, no en el trace de
                # Plotly -- así el orden visual queda igual sin importar el
                # motor de render (st.plotly_chart vs. plotly_events).
                sectores = sectores.sort_values("Valor_miles_millones_COP", ascending=False)
                fig_pastel = build_pastel(
                    sectores["Sector_corto"], sectores["Valor_miles_millones_COP"],
                    f"Composición del PIB por sector — {nombre_dep} ({anio_sel})",
                    colores=[COLOR_SECTORES_PIB.get(s, "#cccccc") for s in sectores["Sector_corto"]],
                )

                # st.plotly_chart(on_select=...) no dispara selección de forma
                # confiable en gráficos de tipo Pie/dona (limitación conocida
                # de Streamlit, no del código -- ver issues #8933/#8760 del
                # repo de streamlit). plotly_events sí funciona: usa un
                # componente propio con un listener real de "plotly_click".
                puntos = plotly_events(
                    fig_pastel, click_event=True, override_height=420, override_width="100%",
                    key="click_pastel",
                )
                etiquetas_sector = list(sectores["Sector_corto"])
                colores_sector = list(fig_pastel.data[0].marker.colors)
                if puntos:
                    idx = puntos[0].get("pointNumber")
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
            valor_caribe = dep[dep["anio"] == anio_sel]["pib"].sum()

            if modo_total:
                # Ya no hay un departamento en el medio -- el equivalente
                # "de zoom" del pastel de 3 porciones es Caribe vs. resto de
                # Colombia, sin más.
                valor_nacional = dep_nacional[dep_nacional["anio"] == anio_sel]["pib"].sum()
                resto_nacional = max(valor_nacional - valor_caribe, 0)
                pct_nacional = (valor_caribe / valor_nacional * 100) if valor_nacional else 0
                hover = f"<b>Región Caribe</b><br>{pct_nacional:.1f}% de Colombia<extra></extra>"
                fig_pastel = build_pastel_participacion_total(
                    "Región Caribe", "Resto de Colombia", valor_caribe, resto_nacional,
                    f"Participación de la Región Caribe en Colombia ({anio_sel})", hover,
                )
            elif municipio_actual:
                fila_dep_anio = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
                valor_dep = fila_dep_anio["pib"].iloc[0] if not fila_dep_anio.empty else 0
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
                fila_dep_anio = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
                valor_dep = fila_dep_anio["pib"].iloc[0] if not fila_dep_anio.empty else 0
                valor_nacional = dep_nacional[dep_nacional["anio"] == anio_sel]["pib"].sum()
                resto_caribe = max(valor_caribe - valor_dep, 0)
                resto_nacional = max(valor_nacional - valor_caribe, 0)
                pct_nacional = (valor_dep / valor_nacional * 100) if valor_nacional else 0
                pct_caribe = (valor_dep / valor_caribe * 100) if valor_caribe else 0
                pct_caribe_nacional = (valor_caribe / valor_nacional * 100) if valor_nacional else 0
                hover = (
                    f"<b>{nombre_dep}</b><br>{pct_nacional:.1f}% de Colombia<br>"
                    f"{pct_caribe:.1f}% de la Región Caribe<extra></extra>"
                )
                # El segmento azul oscuro ("Resto de la Región Caribe") siempre
                # informa, al pasar el mouse, qué tanto pesa toda la Región
                # Caribe (no solo el departamento) en el PIB nacional.
                hover_medio = f"<b>Región Caribe</b><br>{pct_caribe_nacional:.1f}% de Colombia<extra></extra>"
                fig_pastel = build_pastel_participacion(
                    nombre_dep, "Resto de la Región Caribe", "Resto de Colombia",
                    valor_dep, resto_caribe, resto_nacional,
                    f"Participación de {nombre_dep} en la Región Caribe y Colombia ({anio_sel})",
                    hover, texto_hover_medio=hover_medio,
                )
            if fig_pastel is not None:
                st.plotly_chart(fig_pastel, width="stretch")

    if modo_linea == "Per cápita":
        st.divider()
        st.subheader("PIB per cápita municipal — Región Caribe", divider="gray")
        incluir_nacional = st.checkbox("Incluir el resto de Colombia", key="incluir_nacional_disp")
        base_mun_disp = mun_nacional if incluir_nacional else mun
        base_dep_disp = dep_nacional if incluir_nacional else dep
        ambito_disp = "Colombia" if incluir_nacional else "Región Caribe"
        etiqueta_promedio_disp = "Promedio Colombia" if incluir_nacional else "Promedio Región Caribe"

        datos_disp = base_mun_disp[base_mun_disp["anio"] == anio_sel][
            ["nombre_entidad", "nombre_departamento", "valor_agregado", "poblacion_total"]
        ].dropna()
        datos_disp = datos_disp[datos_disp["poblacion_total"] > 0]
        if datos_disp.empty:
            st.info(f"No hay datos de PIB municipal per cápita para {anio_sel}.")
        else:
            datos_disp = datos_disp.assign(pib_percapita=datos_disp["valor_agregado"] / datos_disp["poblacion_total"])
            dep_anio_disp = base_dep_disp[base_dep_disp["anio"] == anio_sel].dropna(subset=["pib", "poblacion_total"])
            promedios_departamento = {
                fila["nombre_entidad"]: fila["pib"] / fila["poblacion_total"] for _, fila in dep_anio_disp.iterrows()
            }
            promedio_regional = (
                dep_anio_disp["pib"].sum() / dep_anio_disp["poblacion_total"].sum() if not dep_anio_disp.empty else None
            )
            if incluir_nacional:
                # Con las 33 en pantalla, hay que distinguir la Región
                # Caribe del resto del país -- verde para el Caribe, amarillo
                # para el departamento activo en el mapa (ninguno en modo
                # Total, ahí ya están todos resaltados).
                seleccionado_disp = None if modo_total else nombre_dep
                color_disp = [
                    "#f5c518" if d == seleccionado_disp else ("#22a559" if d in caribe else "#2a78d6")
                    for d in datos_disp["nombre_departamento"]
                ]
            else:
                color_disp = "#2a78d6"
            fig_disp = build_dispersion_municipios(
                datos_disp["nombre_departamento"], datos_disp["nombre_entidad"], datos_disp["pib_percapita"],
                f"PIB per cápita municipal — {ambito_disp} ({anio_sel})", "PIB per cápita (COP)",
                color=color_disp,
                capitales=capitales, promedios_departamento=promedios_departamento, promedio_regional=promedio_regional,
                etiqueta_promedio=etiqueta_promedio_disp,
            )
            st.plotly_chart(fig_disp, width="stretch")
            aviso_colores = (
                " Verde = departamentos de la Región Caribe · amarillo = el departamento activo en el mapa."
                if incluir_nacional else ""
            )
            st.caption(
                "Punto pequeño = ciudad capital · cuadrado = PIB per cápita del departamento · línea vertical = "
                f"promedio de {ambito_disp}." + aviso_colores + " Cada punto es un municipio; el PIB municipal "
                "(valor agregado) suele llegar con un año de rezago frente al departamental, así que puede faltar "
                "el año más reciente."
            )

elif variable_activa == "Mercado laboral":
    # El widget se instancia una sola vez aquí (antes de construir el
    # gráfico) y se usa directamente su valor de retorno -- leerlo por
    # adelantado vía st.session_state.get(key) parecía seguro pero se
    # "olvida" del valor elegido en cuanto el rerun lo dispara OTRO control
    # (cambiar de departamento/ciudad, que hace su propio st.rerun()) en vez
    # del propio widget. st.empty() reserva el lugar del gráfico para que el
    # toggle se siga viendo debajo, como antes.
    if modo_total or ciudad_ml:
        with col_izq:
            slot_izq_ml = st.empty()
            modo_linea_ml = st.segmented_control(
                "Vista de la línea", ["Tasa de desocupación", "PIB por trabajador"], default="Tasa de desocupación",
                key="modo_linea_ml", label_visibility="collapsed", persist_state="session",
            )
            if st.session_state.get("sector_actual_ml"):
                if st.button(f"✕ Quitar {st.session_state['sector_actual_ml']['nombre']}", key="quitar_sector_ml"):
                    st.session_state["sector_actual_ml"] = None
                    st.session_state["partido_actual"] = None
                    st.rerun()

    if modo_total:
        # Vista Total: se agregan las 7 ciudades capitales (la GEIH no cubre
        # nada más). El click por sector sí está disponible -- se suma el
        # PIB de ese sector en los 7 departamentos y los ocupados de esa
        # rama en las 7 capitales.
        capitales_caribe = list(capitales.values())
        sector_actual_ml = st.session_state.get("sector_actual_ml") if modo_linea_ml == "PIB por trabajador" else None
        with slot_izq_ml.container():
            if modo_linea_ml == "PIB por trabajador":
                if sector_actual_ml:
                    nombre_original_rama = next(
                        (o for o, c in NOMBRES_RAMA_CORTOS.items() if c == sector_actual_ml["nombre"]),
                        sector_actual_ml["nombre"],
                    )
                    sector_pib_original = RAMA_A_SECTOR_PIB.get(nombre_original_rama)
                    serie_pib_sector = (
                        pib_sector_caribe[pib_sector_caribe["Sector"] == sector_pib_original]
                        .groupby("Año", as_index=False)["Valor_miles_millones_COP"].sum()
                        .rename(columns={"Año": "anio"})
                    )
                    serie_ocup = (
                        geih_ocupados_rama[geih_ocupados_rama["nombre_entidad"].isin(capitales_caribe)]
                        [["anio", nombre_original_rama]]
                        .groupby("anio", as_index=False)[nombre_original_rama].sum()
                        .rename(columns={nombre_original_rama: "ocupados"})
                    )
                    serie = serie_pib_sector.merge(serie_ocup, on="anio", how="inner")
                    serie = serie[serie["ocupados"] > 0].sort_values("anio")
                    y = serie["Valor_miles_millones_COP"] * 1e9 / (serie["ocupados"] * 1000)
                    fig_linea = build_evolution_line(
                        serie["anio"], y, anio_sel,
                        f"Evolución de PIB por trabajador — {sector_actual_ml['nombre']} (Región Caribe)",
                        "PIB por trabajador (COP)", color_linea=sector_actual_ml["color"],
                    )
                    st.plotly_chart(fig_linea, width="stretch")
                    aviso_combinado = (
                        " El PIB de este sector incluye además otras ramas de la GEIH que no están contadas "
                        "en estos ocupados (comercio, alojamiento y transporte van juntos en un solo sector "
                        "de PIB) -- el número sale inflado."
                        if nombre_original_rama in RAMAS_SECTOR_COMBINADO else ""
                    )
                    st.caption(
                        "PIB del sector en los 7 departamentos ÷ ocupados en esa rama en las 7 capitales "
                        "-- mezcla dos niveles geográficos distintos, es una aproximación." + aviso_combinado
                    )
                else:
                    base = mun[mun["nombre_entidad"].isin(capitales_caribe)][["anio", "nombre_entidad", "valor_agregado"]].dropna()
                    ocup = geih_tasas[geih_tasas["nombre_entidad"].isin(capitales_caribe)][["anio", "nombre_entidad", "ocupados"]].dropna()
                    merge = base.merge(ocup, on=["anio", "nombre_entidad"])
                    serie = merge.groupby("anio", as_index=False).agg(valor_agregado=("valor_agregado", "sum"), ocupados=("ocupados", "sum"))
                    serie = serie[serie["ocupados"] > 0].sort_values("anio")
                    y = serie["valor_agregado"] / (serie["ocupados"] * 1000)
                    fig_linea = build_evolution_line(
                        serie["anio"], y, anio_sel,
                        "Evolución del PIB por trabajador — Región Caribe (7 capitales)", "PIB por trabajador (COP)",
                    )
                    st.plotly_chart(fig_linea, width="stretch")
                    st.caption(
                        "Suma del PIB municipal (valor agregado) de las 7 capitales ÷ suma de sus ocupados (GEIH) "
                        "-- productividad laboral agregada."
                    )
            else:
                serie = geih_tasas[geih_tasas["nombre_entidad"].isin(capitales_caribe)].groupby(
                    "anio", as_index=False
                ).agg(desocupados=("desocupados", "sum"), fuerza_trabajo=("fuerza_trabajo", "sum"))
                serie = serie[serie["fuerza_trabajo"] > 0].sort_values("anio")
                td = serie["desocupados"] / serie["fuerza_trabajo"] * 100
                fig_linea = build_evolution_line(
                    serie["anio"], td, anio_sel,
                    "Evolución de la Tasa de Desocupación — Región Caribe (7 capitales)", "Tasa de desocupación (%)",
                    unidad="%",
                )
                st.plotly_chart(fig_linea, width="stretch")
                st.caption("Desocupados ÷ fuerza de trabajo, sumados entre las 7 ciudades capitales (GEIH, DANE).")
        with col_der:
            fila_rama_total = geih_ocupados_rama[
                geih_ocupados_rama["nombre_entidad"].isin(capitales_caribe) & (geih_ocupados_rama["anio"] == anio_sel)
            ]
            if fila_rama_total.empty:
                st.info(f"Sin dato de ocupados por sector para la Región Caribe en {anio_sel}.")
            elif modo_linea_ml == "PIB por trabajador":
                ocupados_por_rama = fila_rama_total[list(NOMBRES_RAMA_CORTOS.keys())].sum()
                fila_pib_anio_total = pib_sector_caribe[pib_sector_caribe["Año"] == anio_sel].groupby("Sector")[
                    "Valor_miles_millones_COP"
                ].sum()
                filas_ranking = []
                for rama_original, rama_corto in NOMBRES_RAMA_CORTOS.items():
                    ocupados = ocupados_por_rama.get(rama_original)
                    pib = fila_pib_anio_total.get(RAMA_A_SECTOR_PIB.get(rama_original))
                    if pd.notna(ocupados) and ocupados > 0 and pd.notna(pib):
                        filas_ranking.append({"rama": rama_corto, "valor": pib * 1e9 / (ocupados * 1000)})
                if not filas_ranking:
                    st.info(f"Sin dato de PIB por trabajador por sector para la Región Caribe en {anio_sel}.")
                else:
                    ranking = pd.DataFrame(filas_ranking).sort_values("valor")
                    fig_ranking = build_ranking_barras(
                        list(ranking["rama"]), list(ranking["valor"]),
                        f"PIB por trabajador por sector — Región Caribe ({anio_sel})",
                        colores=[COLOR_RAMA_GEIH.get(r, "#cccccc") for r in ranking["rama"]],
                        unidad="COP", seleccionado=sector_actual_ml["nombre"] if sector_actual_ml else None,
                    )
                    evento_ranking = st.plotly_chart(
                        fig_ranking, on_select="rerun", key="click_ranking_ml", selection_mode="points", width="stretch",
                    )
                    puntos = evento_ranking["selection"]["points"] if evento_ranking and evento_ranking.get("selection") else []
                    ramas_ranking = list(ranking["rama"])
                    if puntos:
                        idx = puntos[0].get("point_index")
                        if idx is not None and idx < len(ramas_ranking):
                            rama_click = ramas_ranking[idx]
                            if st.session_state.get("_ultimo_click_ranking_ml") != ("TOTAL", anio_sel, rama_click):
                                st.session_state["_ultimo_click_ranking_ml"] = ("TOTAL", anio_sel, rama_click)
                                actual = st.session_state.get("sector_actual_ml")
                                if actual and actual["nombre"] == rama_click:
                                    st.session_state["sector_actual_ml"] = None
                                else:
                                    st.session_state["sector_actual_ml"] = {
                                        "nombre": rama_click, "color": COLOR_RAMA_GEIH.get(rama_click, "#cccccc"),
                                    }
                                st.rerun()
                    st.caption(
                        f"PIB del sector en los 7 departamentos ÷ ocupados en esa rama en las 7 capitales, "
                        f"para {anio_sel} -- mezcla dos niveles geográficos distintos, es una aproximación."
                    )
            else:
                ramas = list(NOMBRES_RAMA_CORTOS.keys())
                valores_rama = fila_rama_total[ramas].sum().sort_values(ascending=False)
                etiquetas = [NOMBRES_RAMA_CORTOS[c] for c in valores_rama.index]
                fig_pastel_ml = build_pastel(
                    etiquetas, valores_rama.values, f"Ocupados por sector — Región Caribe ({anio_sel})",
                    unidad="miles de personas",
                    colores=[COLOR_RAMA_GEIH.get(e, "#cccccc") for e in etiquetas],
                )
                st.plotly_chart(fig_pastel_ml, width="stretch")
                st.caption("Miles de personas, suma de las 7 capitales, trimestre móvil Oct-Dic (GEIH, DANE).")
    elif not ciudad_ml:
        st.info(
            f"La GEIH no tiene dato para este municipio -- solo cubre la ciudad capital "
            f"({capital_dep or 'sin capital definida'})."
        )
    else:
        # El click en la dona solo tiene sentido en modo "PIB por trabajador"
        # -- no existe una tasa de desocupación por rama (los desocupados no
        # tienen rama: por definición no están trabajando en ninguna). En
        # modo "Tasa de desocupación" cualquier sector elegido se ignora.
        sector_actual_ml = st.session_state.get("sector_actual_ml") if modo_linea_ml == "PIB por trabajador" else None

        with slot_izq_ml.container():
            if modo_linea_ml == "PIB por trabajador":
                # Productividad laboral: PIB (valor agregado) dividido entre
                # ocupados (GEIH) -- estándar de "productividad laboral"
                # (OCDE/OIT/DANE), no confundir con productividad total de
                # los factores (esa necesita capital).
                serie_ocup_rama = geih_ocupados_rama[geih_ocupados_rama["nombre_entidad"] == ciudad_ml]

                if sector_actual_ml:
                    nombre_original_rama = next(
                        (o for o, c in NOMBRES_RAMA_CORTOS.items() if c == sector_actual_ml["nombre"]),
                        sector_actual_ml["nombre"],
                    )
                    sector_pib_original = RAMA_A_SECTOR_PIB.get(nombre_original_rama)
                    serie_pib_sector = pib_sector_caribe[
                        (pib_sector_caribe["Departamento"] == nombre_dep)
                        & (pib_sector_caribe["Sector"] == sector_pib_original)
                    ][["Año", "Valor_miles_millones_COP"]].rename(columns={"Año": "anio"}).dropna()
                    serie_ocup = serie_ocup_rama[["anio", nombre_original_rama]].rename(
                        columns={nombre_original_rama: "ocupados"}
                    ).dropna()
                    serie = serie_pib_sector.merge(serie_ocup, on="anio", how="inner")
                    serie = serie[serie["ocupados"] > 0].sort_values("anio")
                    y = serie["Valor_miles_millones_COP"] * 1e9 / (serie["ocupados"] * 1000)
                    fig_linea = build_evolution_line(
                        serie["anio"], y, anio_sel,
                        f"Evolución de PIB por trabajador — {sector_actual_ml['nombre']} ({ciudad_ml})",
                        "PIB por trabajador (COP)", color_linea=sector_actual_ml["color"],
                    )
                    st.plotly_chart(fig_linea, width="stretch")
                    aviso_combinado = (
                        " El PIB de este sector en el departamento incluye además otras ramas de la GEIH "
                        "que no están contadas en estos ocupados (comercio, alojamiento y transporte van "
                        "juntos en un solo sector de PIB) -- el número sale inflado."
                        if nombre_original_rama in RAMAS_SECTOR_COMBINADO else ""
                    )
                    st.caption(
                        f"PIB del sector en {nombre_dep} (departamento) ÷ ocupados en esa rama en "
                        f"{ciudad_ml} (solo la capital) -- mezcla dos niveles geográficos distintos, "
                        f"es una aproximación." + aviso_combinado
                    )
                else:
                    serie_pib = mun[
                        (mun["nombre_entidad"] == ciudad_ml) & (mun["nombre_departamento"] == nombre_dep)
                    ][["anio", "valor_agregado"]].dropna()
                    serie_ocup = geih_tasas[geih_tasas["nombre_entidad"] == ciudad_ml][["anio", "ocupados"]].dropna()
                    serie = serie_pib.merge(serie_ocup, on="anio", how="inner")
                    serie = serie[serie["ocupados"] > 0].sort_values("anio")
                    y = serie["valor_agregado"] / (serie["ocupados"] * 1000)
                    fig_linea = build_evolution_line(
                        serie["anio"], y, anio_sel,
                        f"Evolución del PIB por trabajador — {ciudad_ml}", "PIB por trabajador (COP)",
                    )
                    st.plotly_chart(fig_linea, width="stretch")
                    st.caption(
                        "PIB municipal (valor agregado) ÷ ocupados (GEIH, trimestre móvil Oct-Dic) -- "
                        "productividad laboral, no productividad total (no incorpora capital). "
                        "Cada serie tiene su propio rezago de datos, así que puede faltar el último año."
                    )
            else:
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
            elif modo_linea_ml == "PIB por trabajador":
                # Ranking en vez de dona: PIB por trabajador no es "parte de
                # un todo" (no tiene sentido que las ramas sumen 100%), y al
                # usar el mismo st.plotly_chart nativo que la vista de Tasa
                # de desocupación (en vez de plotly_events, que solo hace
                # falta para el click en donas) el título no salta de
                # posición al alternar entre las dos vistas.
                fila = fila_rama.iloc[0]
                fila_pib_anio = pib_sector_caribe[
                    (pib_sector_caribe["Departamento"] == nombre_dep) & (pib_sector_caribe["Año"] == anio_sel)
                ].set_index("Sector")["Valor_miles_millones_COP"]
                filas_ranking = []
                for rama_original, rama_corto in NOMBRES_RAMA_CORTOS.items():
                    ocupados = fila.get(rama_original)
                    pib = fila_pib_anio.get(RAMA_A_SECTOR_PIB.get(rama_original))
                    if pd.notna(ocupados) and ocupados > 0 and pd.notna(pib):
                        filas_ranking.append({"rama": rama_corto, "valor": pib * 1e9 / (ocupados * 1000)})
                if not filas_ranking:
                    st.info(f"Sin dato de PIB por trabajador por sector para {ciudad_ml} en {anio_sel}.")
                else:
                    ranking = pd.DataFrame(filas_ranking).sort_values("valor")
                    fig_ranking = build_ranking_barras(
                        list(ranking["rama"]), list(ranking["valor"]),
                        f"PIB por trabajador por sector — {ciudad_ml} ({anio_sel})",
                        colores=[COLOR_RAMA_GEIH.get(r, "#cccccc") for r in ranking["rama"]],
                        unidad="COP", seleccionado=sector_actual_ml["nombre"] if sector_actual_ml else None,
                    )
                    evento_ranking = st.plotly_chart(
                        fig_ranking, on_select="rerun", key="click_ranking_ml", selection_mode="points", width="stretch",
                    )
                    puntos = evento_ranking["selection"]["points"] if evento_ranking and evento_ranking.get("selection") else []
                    ramas_ranking = list(ranking["rama"])
                    if puntos:
                        idx = puntos[0].get("point_index")
                        if idx is not None and idx < len(ramas_ranking):
                            rama_click = ramas_ranking[idx]
                            if st.session_state.get("_ultimo_click_ranking_ml") != (ciudad_ml, anio_sel, rama_click):
                                st.session_state["_ultimo_click_ranking_ml"] = (ciudad_ml, anio_sel, rama_click)
                                actual = st.session_state.get("sector_actual_ml")
                                if actual and actual["nombre"] == rama_click:
                                    st.session_state["sector_actual_ml"] = None
                                else:
                                    st.session_state["sector_actual_ml"] = {
                                        "nombre": rama_click, "color": COLOR_RAMA_GEIH.get(rama_click, "#cccccc"),
                                    }
                                st.rerun()
                    st.caption(
                        f"PIB del sector en {nombre_dep} (departamento) ÷ ocupados en esa rama en {ciudad_ml} "
                        f"(solo la capital), para {anio_sel} -- mezcla dos niveles geográficos distintos, es "
                        "una aproximación."
                    )
            else:
                fila = fila_rama.iloc[0]
                ramas = list(NOMBRES_RAMA_CORTOS.keys())
                valores_rama = fila[ramas].dropna().sort_values(ascending=False)
                etiquetas = [NOMBRES_RAMA_CORTOS[c] for c in valores_rama.index]
                fig_pastel_ml = build_pastel(
                    etiquetas, valores_rama.values, f"Ocupados por sector — {ciudad_ml} ({anio_sel})",
                    unidad="miles de personas",
                    colores=[COLOR_RAMA_GEIH.get(e, "#cccccc") for e in etiquetas],
                )
                st.plotly_chart(fig_pastel_ml, width="stretch")
                st.caption("Miles de personas, trimestre móvil Oct-Dic (GEIH, DANE).")

elif variable_activa == "Composición Política":
    # A nivel departamental es la asamblea (no depende del año del slider --
    # se elige cada 4 años). Si hay un municipio seleccionado y ya se
    # registró su concejo, se muestra el concejo de ese municipio en su
    # lugar -- por ahora solo las 7 capitales, se irán sumando más a medida
    # que se registren.
    es_concejo = bool(municipio_actual) and not modo_total
    if es_concejo:
        comp_agrupada = composicion_concejo[composicion_concejo["nombre_municipio"] == municipio_actual][
            ["partido", "partido_normalizado", "curules"]
        ].copy()
        titulo_hemiciclo = f"Concejo de {municipio_actual}"
    elif modo_total:
        comp = comp_vigente[comp_vigente["nombre_departamento"].isin(caribe)]
        comp_agrupada = comp.groupby(["partido", "partido_normalizado"], as_index=False)["curules"].sum()
        titulo_hemiciclo = "Asambleas de la Región Caribe (combinadas)"
    else:
        comp_agrupada = comp_vigente[comp_vigente["nombre_departamento"] == nombre_dep][
            ["partido", "partido_normalizado", "curules"]
        ].copy()
        titulo_hemiciclo = f"Asamblea de {nombre_dep}"

    if comp_agrupada.empty or comp_agrupada["curules"].sum() == 0:
        if es_concejo:
            st.info(
                f"Todavía no hay datos de composición del concejo para {municipio_actual} -- se irán sumando más "
                "municipios a medida que se registren."
            )
        else:
            st.info("No hay datos de composición política para esta selección.")
    else:
        comp_agrupada = comp_agrupada.sort_values("curules", ascending=False)
        colores_wedge = colores_hemiciclo(comp_agrupada["partido_normalizado"], comp_agrupada["partido"])
        # Nombre a mostrar: el nombre completo ya conocido para partidos
        # nacionales, o el nombre/sigla expandida vía glosario para lo que cae
        # en "Otros" (coaliciones/movimientos regionales).
        nombres_mostrar = [
            normalizado if normalizado != NOMBRE_OTROS_PARTIDOS else nombre_legible_partido(raw)
            for raw, normalizado in zip(comp_agrupada["partido"], comp_agrupada["partido_normalizado"])
        ]
        partido_actual = st.session_state.get("partido_actual")
        if partido_actual not in nombres_mostrar:
            # Cambió de selección (departamento/municipio) o el partido ya no
            # está en esta composición -- no dejar una selección "fantasma".
            partido_actual = None
            st.session_state["partido_actual"] = None
        opacidades_wedge = [1.0 if n == partido_actual else 0.15 for n in nombres_mostrar] if partido_actual else None

        with col_izq:
            if partido_actual:
                # Volver a hacer click en la misma barra no siempre dispara
                # un nuevo evento de selección (Plotly no reenvía un valor
                # idéntico al anterior) -- este botón siempre funciona.
                if st.button(f"✕ Quitar {partido_actual}", key="quitar_partido"):
                    st.session_state["partido_actual"] = None
                    st.rerun()
            fig_hemiciclo = build_hemiciclo(
                nombres_mostrar, comp_agrupada["curules"], colores_wedge, titulo_hemiciclo,
                subtitulo=f"Período {PERIODO_ASAMBLEA_VIGENTE} · {int(comp_agrupada['curules'].sum())} curules",
                opacidades=opacidades_wedge,
            )
            st.plotly_chart(fig_hemiciclo, width="stretch")
            if es_concejo:
                st.caption(
                    "Situación actual del concejo -- incorpora renuncias, vacancias y reemplazos detectados en "
                    "prensa hasta la fecha de corte, no la posesión inicial de enero de 2024. Colores: los "
                    "tradicionales de cada partido nacional; coaliciones y movimientos regionales llevan un color "
                    "asignado automáticamente solo para distinguirlos entre sí."
                )
            else:
                st.caption(
                    "Elecciones regionales de octubre de 2023. Colores: los tradicionales de cada partido nacional "
                    "(rojo liberal, azul conservador, etc.); coaliciones y movimientos regionales llevan un color "
                    "asignado automáticamente solo para distinguirlos entre sí."
                )
        with col_der:
            fig_rank_partidos = build_ranking_barras(
                nombres_mostrar, comp_agrupada["curules"],
                f"Curules por partido — {titulo_hemiciclo}", colores=colores_wedge, unidad="curules",
                seleccionado=partido_actual,
            )
            evento_rank_comp = st.plotly_chart(
                fig_rank_partidos, on_select="rerun", key="click_ranking_comp", selection_mode="points", width="stretch",
            )
            # build_ranking_barras reordena las barras de menor a mayor para
            # dibujarlas -- el point_index del click cae en ESE orden, no en
            # el de nombres_mostrar (descendente), así que hay que rearmar la
            # misma lista ascendente para traducirlo de vuelta al nombre.
            orden_ranking = sorted(range(len(nombres_mostrar)), key=lambda i: comp_agrupada["curules"].iloc[i])
            nombres_ranking_orden = [nombres_mostrar[i] for i in orden_ranking]
            puntos_rank_comp = (
                evento_rank_comp["selection"]["points"] if evento_rank_comp and evento_rank_comp.get("selection") else []
            )
            if puntos_rank_comp:
                idx = puntos_rank_comp[0].get("point_index")
                if idx is not None and idx < len(nombres_ranking_orden):
                    partido_click = nombres_ranking_orden[idx]
                    if st.session_state.get("_ultimo_click_ranking_comp") != (titulo_hemiciclo, partido_click):
                        st.session_state["_ultimo_click_ranking_comp"] = (titulo_hemiciclo, partido_click)
                        st.session_state["partido_actual"] = None if partido_actual == partido_click else partido_click
                        st.rerun()
            if es_concejo:
                st.caption(
                    "Fuente: directorios oficiales de cada Concejo y prensa regional -- dato colaborativo, sin una "
                    "base centralizada única; contrastar directamente con cada Concejo antes de un uso oficial."
                )
            else:
                st.caption(
                    "Fuente: Wikipedia (es), \"Asamblea Departamental (Colombia)\" -- dato colaborativo; "
                    "contrastar con registraduria.gov.co para usos que requieran exactitud certificada."
                )

else:  # Población
    with col_izq:
        if modo_total:
            serie = dep.groupby("anio", as_index=False)["poblacion_total"].sum().dropna(subset=["poblacion_total"]).sort_values("anio")
            fig_linea = build_evolution_line(
                serie["anio"], serie["poblacion_total"], anio_sel, "Evolución de Población — Región Caribe", "Población",
            )
        elif municipio_actual:
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
        # st.empty() reserva el lugar del gráfico para llenarlo más abajo,
        # después de leer el valor del toggle -- así el toggle queda
        # visualmente debajo del gráfico (mismo truco que en PIB/Mercado
        # laboral) en vez de encima.
        slot_der_pob = st.empty()
        modo_pob = st.segmented_control(
            "Vista de población", ["Pirámide", "Participación poblacional"], default="Pirámide",
            key="modo_vista_poblacion", label_visibility="collapsed", persist_state="session",
        )

    with slot_der_pob.container():
        if modo_pob == "Pirámide":
            if modo_total:
                datos_pir_total = piramide_dep[piramide_dep["nombre_entidad"].isin(caribe) & (piramide_dep["anio"] == anio_sel)]
                datos_pir_total = datos_pir_total.groupby("grupo_edad")[["hombres", "mujeres"]].sum().reindex(ORDEN_GRUPOS_EDAD).fillna(0)
                fig_piramide = build_pyramid(
                    datos_pir_total["hombres"], datos_pir_total["mujeres"], f"Pirámide poblacional — Región Caribe ({anio_sel})",
                )
            else:
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

        else:  # Participación poblacional -- mismo esquema de colores y de
            # "zoom" (resaltado / resto de la región / resto del país) que la
            # vista Regional/Nacional de PIB, aplicado a población en vez de
            # PIB.
            valor_caribe_pob = dep[dep["anio"] == anio_sel]["poblacion_total"].sum()

            if modo_total:
                valor_nacional_pob = dep_nacional[dep_nacional["anio"] == anio_sel]["poblacion_total"].sum()
                resto_nacional_pob = max(valor_nacional_pob - valor_caribe_pob, 0)
                pct_nacional_pob = (valor_caribe_pob / valor_nacional_pob * 100) if valor_nacional_pob else 0
                hover_pob = f"<b>Región Caribe</b><br>{pct_nacional_pob:.1f}% de Colombia<extra></extra>"
                fig_pastel_pob = build_pastel_participacion_total(
                    "Región Caribe", "Resto de Colombia", valor_caribe_pob, resto_nacional_pob,
                    f"Participación poblacional de la Región Caribe en Colombia ({anio_sel})", hover_pob,
                )
                st.plotly_chart(fig_pastel_pob, width="stretch")
            elif municipio_actual:
                fila_dep_anio_pob = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
                valor_dep_pob = fila_dep_anio_pob["poblacion_total"].iloc[0] if not fila_dep_anio_pob.empty else 0
                fila_mun_anio_pob = mun[
                    (mun["nombre_entidad"] == municipio_actual)
                    & (mun["nombre_departamento"] == nombre_dep)
                    & (mun["anio"] == anio_sel)
                ]
                hay_dato_mun_pob = not fila_mun_anio_pob.empty and pd.notna(fila_mun_anio_pob["poblacion_total"].iloc[0])
                if not hay_dato_mun_pob:
                    st.info(f"No hay dato de población para {municipio_actual} en {anio_sel}.")
                else:
                    valor_mun_pob = fila_mun_anio_pob["poblacion_total"].iloc[0]
                    resto_dep_pob = max(valor_dep_pob - valor_mun_pob, 0)
                    resto_caribe_pob = max(valor_caribe_pob - valor_dep_pob, 0)
                    pct_dep_pob = (valor_mun_pob / valor_dep_pob * 100) if valor_dep_pob else 0
                    pct_caribe_pob = (valor_mun_pob / valor_caribe_pob * 100) if valor_caribe_pob else 0
                    hover_pob = (
                        f"<b>{municipio_actual}</b><br>{pct_dep_pob:.1f}% de {nombre_dep}<br>"
                        f"{pct_caribe_pob:.1f}% de la Región Caribe<extra></extra>"
                    )
                    fig_pastel_pob = build_pastel_participacion(
                        municipio_actual, f"Resto de {nombre_dep}", "Resto de la Región Caribe",
                        valor_mun_pob, resto_dep_pob, resto_caribe_pob,
                        f"Participación poblacional de {municipio_actual} en {nombre_dep} y la Región Caribe ({anio_sel})",
                        hover_pob,
                    )
                    st.plotly_chart(fig_pastel_pob, width="stretch")
            else:
                fila_dep_anio_pob = dep[(dep["nombre_entidad"] == nombre_dep) & (dep["anio"] == anio_sel)]
                valor_dep_pob = fila_dep_anio_pob["poblacion_total"].iloc[0] if not fila_dep_anio_pob.empty else 0
                valor_nacional_pob = dep_nacional[dep_nacional["anio"] == anio_sel]["poblacion_total"].sum()
                resto_caribe_pob = max(valor_caribe_pob - valor_dep_pob, 0)
                resto_nacional_pob = max(valor_nacional_pob - valor_caribe_pob, 0)
                pct_nacional_pob = (valor_dep_pob / valor_nacional_pob * 100) if valor_nacional_pob else 0
                pct_caribe_pob = (valor_dep_pob / valor_caribe_pob * 100) if valor_caribe_pob else 0
                pct_caribe_nacional_pob = (valor_caribe_pob / valor_nacional_pob * 100) if valor_nacional_pob else 0
                hover_pob = (
                    f"<b>{nombre_dep}</b><br>{pct_nacional_pob:.1f}% de Colombia<br>"
                    f"{pct_caribe_pob:.1f}% de la Región Caribe<extra></extra>"
                )
                hover_medio_pob = f"<b>Región Caribe</b><br>{pct_caribe_nacional_pob:.1f}% de Colombia<extra></extra>"
                fig_pastel_pob = build_pastel_participacion(
                    nombre_dep, "Resto de la Región Caribe", "Resto de Colombia",
                    valor_dep_pob, resto_caribe_pob, resto_nacional_pob,
                    f"Participación poblacional de {nombre_dep} en la Región Caribe y Colombia ({anio_sel})",
                    hover_pob, texto_hover_medio=hover_medio_pob,
                )
                st.plotly_chart(fig_pastel_pob, width="stretch")

    # Población urbana / rural -- sección nueva, todavía por desarrollar.
    # Primeros gráficos: mapas de los 193 municipios del Caribe de una sola
    # vez (no uno por departamento), con los bordes departamentales
    # resaltados encima -- mismo estilo que un mapa de referencia de
    # ruralidad municipal. Tasa (% de la población del municipio), no
    # densidad -- urbanidad y ruralidad son complementarias (suman 100%).
    st.divider()
    st.subheader("Población urbana", divider="gray")

    datos_tasa_anio = mun[mun["anio"] == anio_sel].copy()
    datos_tasa_anio["clave"] = (
        datos_tasa_anio["nombre_entidad"] + "|" + datos_tasa_anio["codigo_dane"].astype(str).str.zfill(5).str[-3:]
    )
    colores_urbana_mun = calcular_colores_municipios_region(
        mun, mapa_caribe_municipios_geo, anio_sel, "tasa_urbanidad", COLOR_DENSIDAD_URBANA, techo=100,
    )
    hover_urbana_mun = datos_tasa_anio.dropna(subset=["tasa_urbanidad"]).set_index("clave")["tasa_urbanidad"].apply(
        lambda v: f"{v:.1f}% urbana"
    ).to_dict()
    fig_mapa_urbano = build_municipios_map_region(
        mapa_caribe_municipios_geo, colores_urbana_mun, mapa_caribe_geo,
        f"Tasa de urbanidad — municipios del Caribe ({anio_sel})", hover_extra=hover_urbana_mun,
    )
    col_mapa_urbano, _ = st.columns([3, 2])
    with col_mapa_urbano:
        st.plotly_chart(fig_mapa_urbano, width="stretch")
        st.caption(
            "Color = tasa de urbanidad por municipio (población urbana ÷ población total, %) · más oscuro = más "
            "urbano · líneas gruesas = límites departamentales."
        )

    # Población rural -- misma tasa, de espejo (100 - urbanidad), en verde
    # en vez de azul.
    st.subheader("Población rural", divider="gray")

    colores_rural_mun = calcular_colores_municipios_region(
        mun, mapa_caribe_municipios_geo, anio_sel, "tasa_ruralidad", COLOR_DENSIDAD_RURAL, techo=100,
    )
    hover_rural_mun = datos_tasa_anio.dropna(subset=["tasa_ruralidad"]).set_index("clave")["tasa_ruralidad"].apply(
        lambda v: f"{v:.1f}% rural"
    ).to_dict()
    fig_mapa_rural = build_municipios_map_region(
        mapa_caribe_municipios_geo, colores_rural_mun, mapa_caribe_geo,
        f"Tasa de ruralidad — municipios del Caribe ({anio_sel})", hover_extra=hover_rural_mun,
    )
    col_mapa_rural, _ = st.columns([3, 2])
    with col_mapa_rural:
        st.plotly_chart(fig_mapa_rural, width="stretch")
        st.caption(
            "Color = tasa de ruralidad por municipio (población rural ÷ población total, %) · más oscuro = más "
            "rural · líneas gruesas = límites departamentales."
        )
