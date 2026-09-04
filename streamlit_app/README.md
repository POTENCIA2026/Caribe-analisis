# Tablero Caribe — versión Streamlit

Versión web del panel departamental/municipal del Caribe colombiano (la
misma lógica de `EDA.ipynb`, reescrita como app Streamlit para poder
publicarla como sitio web real, sin depender de un kernel de Jupyter).

## Estructura

- `data.py` — carga y prepara todos los datos (equivalente a la celda
  `# DATA` del notebook). Lee los `.geojson` como diccionarios planos con
  `json.load` en vez de `geopandas`, para no depender de GDAL en el deploy.
- `charts.py` — funciones puras que arman cada gráfico de Plotly (mapa,
  línea, dona, radar, pirámide). No mutan nada; cada llamada devuelve una
  figura nueva, porque así funciona Streamlit (reejecuta el script completo
  en cada interacción, a diferencia del notebook con `FigureWidget`).
- `app.py` — la app en sí: estado (`st.session_state`), layout, y el cableado
  de clicks en el mapa / tarjetas / dona / selector de comparación.

## Correr localmente

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

Los datos se leen de `../DATA` (la misma carpeta `DATA/` del repo), así que
hay que correrlo desde dentro de `streamlit_app/` o mantener la estructura
de carpetas del repo intacta.

## Desplegar gratis (Streamlit Community Cloud)

1. Sube este repo a GitHub (ya lo tienes ahí).
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de
   GitHub.
3. "New app" → selecciona el repo `infopotencia/Caribe-analisis`, la rama, y
   como *main file path* pon `streamlit_app/app.py`.
4. Deploy. Streamlit instala `streamlit_app/requirements.txt`
   automáticamente. No hace falta `packages.txt` porque no usamos geopandas.

Te da una URL pública (`https://<algo>.streamlit.app`) gratis, sin servidor
que mantener.

## Qué falta portar del notebook (no incluido en esta primera versión)

- El detalle de "sub-actividades" / drill-down más fino que el de PIB.
- Ajustes finos de estética que solo existen en el notebook (tooltips
  extendidos, animaciones de Plotly específicas).

Todo lo demás (mapa departamental y municipal con drill-down, tarjetas de
Población/PIB/Competitividad, dona de PIB con click por sector, radar de
competitividad con comparación, y la pirámide poblacional con overlay
departamento/municipio) ya está portado y funcionando.
