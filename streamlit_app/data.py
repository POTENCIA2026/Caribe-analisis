"""Carga y preparación de datos para el dashboard del Caribe colombiano.

Es el equivalente de la celda `# DATA` del notebook, pero sin geopandas --
los .geojson se leen como diccionarios planos (json.load) y se filtran con
comprensiones de listas. Esto evita depender de GDAL en el deploy (geopandas
necesita paquetes de sistema que Streamlit Community Cloud no trae por
defecto), sin perder nada de la lógica original.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "DATA"

CARIBE = ["LA GUAJIRA", "MAGDALENA", "CESAR", "ATLÁNTICO", "BOLÍVAR", "CÓRDOBA", "SUCRE"]

# Mismo mapeo que en la celdota, para acortar los nombres de sector en la dona de PIB.
NOMBRES_CORTOS_SECTOR = {
    "Agricultura, ganadería, caza, silvicultura y pesca": "Agricultura, ganadería, caza, silvicultura y pesca",
    "Explotación de minas y canteras": "Explotación de minas y canteras",
    "Industrias manufactureras": "Industrias manufactureras",
    "Suministro de electricidad, gas, vapor y aire acondicionado; distribución de agua; evacuación y tratamiento de aguas residuales, gestión de desechos y actividades de saneamiento ambiental": "Electricidad, gas, agua y saneamiento",
    "Construcción": "Construcción",
    "Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas; transporte y almacenamiento; alojamiento y servicios de comida": "Comercio, transporte, alojamiento y comida",
    "Información y comunicaciones": "Información y comunicaciones",
    "Actividades financieras y de seguros": "Actividades financieras y de seguros",
    "Actividades inmobiliarias": "Actividades inmobiliarias",
    "Actividades profesionales, científicas y técnicas; actividades de servicios administrativos y de apoyo": "Act. profesionales, científicas y de apoyo",
    "Administración pública y defensa; planes de seguridad social de afiliación obligatoria; educación; actividades de atención de la salud humana y de servicios sociales": "Adm. pública, educación y salud",
    "Actividades artísticas, de entretenimiento y recreación y otras actividades de servicios; actividades de los hogares individuales en calidad de empleadores; actividades no diferenciadas de los hogares individuales como productores de bienes y servicios para uso propio": "Artísticas, entretenimiento y otros servicios",
    "Impuestos": "Impuestos",
}

NOMBRES_ACTIVIDADES_MUNICIPIO = {
    "actividades_primarias": "Actividades primarias",
    "actividades_secundarias": "Actividades secundarias",
    "actividades_terciarias": "Actividades terciarias",
}

ORDEN_GRUPOS_EDAD = [f"{i}-{i + 4}" for i in range(0, 100, 5)] + ["100+"]

# Ciudad capital de cada departamento -- la GEIH (mercado laboral) solo trae
# dato para estas 7 ciudades, no para el resto de municipios ni para el
# departamento agregado (igual que pasa con el ICC de Competitividad).
CAPITALES = {
    "ATLÁNTICO": "BARRANQUILLA",
    "BOLÍVAR": "CARTAGENA DE INDIAS",
    "CESAR": "VALLEDUPAR",
    "CÓRDOBA": "MONTERÍA",
    "LA GUAJIRA": "RIOHACHA",
    "MAGDALENA": "SANTA MARTA",
    "SUCRE": "SINCELEJO",
}

NOMBRES_RAMA_CORTOS = {
    "Agricultura, ganadería, caza, silvicultura y pesca": "Agricultura, ganadería, caza, silvicultura y pesca",
    "Explotación de minas y canteras": "Explotación de minas y canteras",
    "Industrias manufactureras": "Industrias manufactureras",
    "Suministro de electricidad gas, agua y gestión de desechos": "Electricidad, gas, agua y saneamiento",
    "Construcción": "Construcción",
    "Comercio y reparación de vehículos": "Comercio y reparación de vehículos",
    "Alojamiento y servicios de comida": "Alojamiento y servicios de comida",
    "Transporte y almacenamiento": "Transporte y almacenamiento",
    "Información y comunicaciones": "Información y comunicaciones",
    "Actividades financieras y de seguros": "Actividades financieras y de seguros",
    "Actividades inmobiliarias": "Actividades inmobiliarias",
    "Actividades profesionales, científicas, técnicas y servicios administrativos": "Act. profesionales, científicas y de apoyo",
    "Administración pública y defensa, educación y atención de la salud humana": "Adm. pública, educación y salud",
    "Actividades artísticas, entretenimiento, recreación y otras actividades de servicios": "Artísticas, entretenimiento y otros servicios",
}

# Rama GEIH (empleo, por ciudad) -> Sector PIB (cuentas nacionales, por
# departamento) -- las dos clasificaciones no son idénticas: la GEIH separa
# "Comercio", "Alojamiento y comida" y "Transporte" en tres ramas, mientras
# que el PIB los junta en un solo sector. Para esas tres, el PIB por
# trabajador que se calcule va a estar inflado (el numerador incluye las
# otras dos actividades que esa rama sola no cubre) -- se advierte en el
# caption de la app, no aquí.
RAMA_A_SECTOR_PIB = {
    "Agricultura, ganadería, caza, silvicultura y pesca": "Agricultura, ganadería, caza, silvicultura y pesca",
    "Explotación de minas y canteras": "Explotación de minas y canteras",
    "Industrias manufactureras": "Industrias manufactureras",
    "Suministro de electricidad gas, agua y gestión de desechos": (
        "Suministro de electricidad, gas, vapor y aire acondicionado; distribución de agua; "
        "evacuación y tratamiento de aguas residuales, gestión de desechos y actividades de "
        "saneamiento ambiental"
    ),
    "Construcción": "Construcción",
    "Comercio y reparación de vehículos": (
        "Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas; "
        "transporte y almacenamiento; alojamiento y servicios de comida"
    ),
    "Alojamiento y servicios de comida": (
        "Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas; "
        "transporte y almacenamiento; alojamiento y servicios de comida"
    ),
    "Transporte y almacenamiento": (
        "Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas; "
        "transporte y almacenamiento; alojamiento y servicios de comida"
    ),
    "Información y comunicaciones": "Información y comunicaciones",
    "Actividades financieras y de seguros": "Actividades financieras y de seguros",
    "Actividades inmobiliarias": "Actividades inmobiliarias",
    "Actividades profesionales, científicas, técnicas y servicios administrativos": (
        "Actividades profesionales, científicas y técnicas; actividades de servicios "
        "administrativos y de apoyo"
    ),
    "Administración pública y defensa, educación y atención de la salud humana": (
        "Administración pública y defensa; planes de seguridad social de afiliación obligatoria; "
        "educación; actividades de atención de la salud humana y de servicios sociales"
    ),
    "Actividades artísticas, entretenimiento, recreación y otras actividades de servicios": (
        "Actividades artísticas, de entretenimiento y recreación y otras actividades de servicios; "
        "actividades de los hogares individuales en calidad de empleadores; actividades no "
        "diferenciadas de los hogares individuales como productores de bienes y servicios para uso propio"
    ),
}

# Las 3 ramas que comparten un sector de PIB combinado -- para avisar en el
# caption solo cuando de verdad aplica.
RAMAS_SECTOR_COMBINADO = {"Comercio y reparación de vehículos", "Alojamiento y servicios de comida", "Transporte y almacenamiento"}


# El geojson trae "TURBANA" sin tilde -- no matchea con "TURBANÁ" (Bolívar)
# como está escrito en el resto de las tablas, y ese municipio queda afuera
# de cualquier mapa que filtre por nombre exacto.
_CORRECCIONES_NOMBRE_ENTIDAD = {"TURBANA": "TURBANÁ"}


@st.cache_data
def _load_geojson(filename: str) -> dict:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        geo = json.load(f)
    # Normalizamos "nombre entidad" (con espacio, como viene del archivo) a
    # "nombre_entidad" para que coincida con la convención de las tablas.
    for feature in geo["features"]:
        props = feature["properties"]
        if "nombre entidad" in props:
            props["nombre_entidad"] = props.pop("nombre entidad")
        props["nombre_entidad"] = _CORRECCIONES_NOMBRE_ENTIDAD.get(props["nombre_entidad"], props["nombre_entidad"])
    return geo


def filtrar_geojson(geo: dict, mantener) -> dict:
    """mantener: función(properties) -> bool"""
    return {
        "type": "FeatureCollection",
        "features": [f for f in geo["features"] if mantener(f["properties"])],
    }


def geojson_municipios_de(mapa_mun_geo: dict, mun: pd.DataFrame, nombre_departamento: str) -> dict:
    """Municipios de un departamento, geometría filtrada por (nombre, últimos 3
    dígitos del código DANE) -- hay nombres de municipio repetidos entre
    departamentos del Caribe (ej. VILLANUEVA existe en Bolívar y en La Guajira)
    y el geojson solo trae el sufijo de 3 dígitos, así que filtrar solo por
    nombre trae ambos."""
    filas = mun[mun["nombre_departamento"] == nombre_departamento][["nombre_entidad", "codigo_dane"]].drop_duplicates()
    codigos_cortos = filas["codigo_dane"].astype(str).str.zfill(5).str[-3:]
    pares_validos = set(zip(filas["nombre_entidad"], codigos_cortos))
    return filtrar_geojson(
        mapa_mun_geo,
        lambda p: (p["nombre_entidad"], p["codigo_dane"]) in pares_validos,
    )


def geojson_municipios_caribe(mapa_mun_geo: dict, mun: pd.DataFrame) -> dict:
    """Los 193 municipios de los 7 departamentos del Caribe de una sola vez
    (para los mapas de profundización de Población urbana/rural, que
    muestran toda la región en un solo mapa) -- le agrega a cada feature una
    propiedad 'clave' (nombre + últimos 3 dígitos del código DANE) porque,
    a diferencia del mapa de un solo departamento, acá SÍ hay nombres
    repetidos entre departamentos (ej. VILLANUEVA en Bolívar y en La
    Guajira) y el nombre solo ya no alcanza para identificar cada uno."""
    filas = mun[["nombre_entidad", "codigo_dane"]].drop_duplicates()
    codigos_cortos = filas["codigo_dane"].astype(str).str.zfill(5).str[-3:]
    pares_validos = set(zip(filas["nombre_entidad"], codigos_cortos))
    geo = filtrar_geojson(
        mapa_mun_geo,
        lambda p: (p["nombre_entidad"], p["codigo_dane"]) in pares_validos,
    )
    for feature in geo["features"]:
        props = feature["properties"]
        props["clave"] = f"{props['nombre_entidad']}|{props['codigo_dane']}"
    return geo


@st.cache_data
def load_all() -> dict:
    mun_full = pd.read_csv(DATA_DIR / "indicadores_municipales.csv")
    dep_full = pd.read_csv(DATA_DIR / "indicadores_departamentales.csv").dropna(subset=["nombre_entidad"])

    mun = mun_full[mun_full["nombre_departamento"].isin(CARIBE)].copy()
    dep = dep_full[dep_full["nombre_entidad"].isin(CARIBE)].copy()
    mun = mun[mun["anio"] != 2025]
    dep = dep[dep["anio"] != 2025]
    dep_nacional = dep_full[dep_full["anio"] != 2025].copy()  # las 33, para el PIB total del país
    mun_nacional = mun_full[mun_full["anio"] != 2025].copy()  # todos los municipios del país

    idc = pd.read_csv(DATA_DIR / "idc_departamental.csv", sep=";")
    dep = dep.merge(idc, on=["nombre_entidad", "anio"], how="left")
    idc_pilares = pd.read_csv(DATA_DIR / "idc_pilares_departamental.csv", sep=";")

    icc = pd.read_csv(DATA_DIR / "icc_municipal.csv", sep=";")
    mun = mun.merge(icc, on=["nombre_entidad", "anio"], how="left")
    icc_pilares = pd.read_csv(DATA_DIR / "icc_pilares_municipal.csv", sep=";")

    pib_sector = pd.read_csv(DATA_DIR / "pib_sector_departamental.csv", sep="|")
    pib_sector["Departamento"] = pib_sector["Departamento"].str.upper()
    pib_sector_caribe = pib_sector[pib_sector["Departamento"].isin(CARIBE)].copy()

    piramide_dep = pd.read_csv(DATA_DIR / "piramide_departamental.csv", sep=";")
    piramide_mun = pd.read_csv(DATA_DIR / "piramide_municipal.csv", sep=";")

    # GEIH (mercado laboral) -- solo cubre las 7 ciudades capitales, no todo
    # el departamento ni los demás municipios (igual que el ICC).
    geih_tasas = pd.read_csv(DATA_DIR / "geih_mercado_laboral_ciudades.csv", sep=";")
    geih_ocupados_rama = pd.read_csv(DATA_DIR / "geih_ocupados_rama_ciudades.csv", sep=";")

    # Composición política de las asambleas departamentales -- las 33, para
    # las 3 últimas elecciones (2016-2019, 2020-2023, 2024-2027). Fuente:
    # Wikipedia (es), "Asamblea Departamental (Colombia)" -- dato
    # colaborativo, contrastar con registraduria.gov.co si se necesita
    # exactitud certificada.
    composicion_asamblea = pd.read_csv(DATA_DIR / "composicion_asamblea_departamental.csv", sep=";")

    # Composición política de los concejos municipales -- por ahora solo las
    # 7 capitales (San Andrés no se pudo verificar), periodo 2024-2027,
    # situación actual (incorpora renuncias/reemplazos detectados en prensa a
    # la fecha de corte, no la posesión inicial de enero de 2024). Se irán
    # sumando más municipios a medida que se registren. Fuente: directorios
    # oficiales de cada Concejo y prensa regional -- dato colaborativo, sin
    # una base centralizada única; contrastar antes de un uso oficial.
    composicion_concejo = pd.read_csv(DATA_DIR / "composicion_concejo_municipal.csv", sep=";")

    # Gobernador vigente de cada departamento (periodo 2024-2027) -- dato
    # colaborativo, contrastar con la gobernación respectiva si se necesita
    # exactitud certificada. La foto y el resumen de cada uno se traen en
    # vivo desde la API de Wikipedia (ver _resumen_wikipedia en app.py), acá
    # solo se guarda el nombre para buscarlo.
    gobernadores_departamentales = pd.read_csv(DATA_DIR / "gobernadores_departamentales.csv", sep=";")

    for df in (mun, dep):
        df[["poblacion_total", "poblacion_rural", "poblacion_urbana"]] = df[
            ["poblacion_total", "poblacion_rural", "poblacion_urbana"]
        ].astype(int)

    mun = mun.assign(
        log_poblacion=np.log10(mun["poblacion_total"]),
        densidad_pob=mun["poblacion_total"] / mun["area_km2"],
        # Tasa de urbanidad/ruralidad = qué % de la población del municipio
        # vive en cabecera vs. resto -- no densidad (no usa el área para
        # nada), son complementarias entre sí (suman 100%).
        tasa_urbanidad=mun["poblacion_urbana"] / mun["poblacion_total"] * 100,
        tasa_ruralidad=mun["poblacion_rural"] / mun["poblacion_total"] * 100,
    )
    mun["log_densidad"] = np.log10(mun["densidad_pob"])

    # Área departamental = suma del área de sus municipios (no viene un dato
    # de área a nivel departamental aparte) -- con eso, densidad poblacional
    # departamental para el mapa, igual que ya se hace a nivel municipal.
    area_dep = (
        mun.groupby(["nombre_departamento", "anio"], as_index=False)["area_km2"].sum()
        .rename(columns={"nombre_departamento": "nombre_entidad"})
    )
    dep = dep.merge(area_dep, on=["nombre_entidad", "anio"], how="left")
    dep["densidad_pob"] = dep["poblacion_total"] / dep["area_km2"]
    dep["log_densidad"] = np.log10(dep["densidad_pob"])

    mapa_dep_geo = _load_geojson("departamento.geojson")
    mapa_mun_geo = _load_geojson("municipio.geojson")

    pilares_disponibles = [c for c in idc_pilares.columns if c not in ("nombre_entidad", "anio")]
    departamentos_pais = sorted(idc_pilares["nombre_entidad"].unique().tolist())
    ciudades_icc = sorted(icc_pilares["nombre_entidad"].unique().tolist())
    anios_disponibles = sorted(dep["anio"].dropna().unique().astype(int).tolist())

    return {
        "mun": mun,
        "mun_nacional": mun_nacional,
        "dep": dep,
        "dep_nacional": dep_nacional,
        "idc_pilares": idc_pilares,
        "icc_pilares": icc_pilares,
        "pib_sector_caribe": pib_sector_caribe,
        "piramide_dep": piramide_dep,
        "piramide_mun": piramide_mun,
        "geih_tasas": geih_tasas,
        "geih_ocupados_rama": geih_ocupados_rama,
        "composicion_asamblea": composicion_asamblea,
        "composicion_concejo": composicion_concejo,
        "gobernadores_departamentales": gobernadores_departamentales,
        "mapa_dep_geo": mapa_dep_geo,
        "mapa_mun_geo": mapa_mun_geo,
        "pilares_disponibles": pilares_disponibles,
        "departamentos_pais": departamentos_pais,
        "ciudades_icc": ciudades_icc,
        "anios_disponibles": anios_disponibles,
        "capitales": CAPITALES,
        "caribe": CARIBE,
    }
