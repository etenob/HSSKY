#python -m streamlit run app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
from streamlit_js_eval import get_geolocation
import ephem, pytz, os, requests
from constants import CIUDADES, CON_ES, MESSIER_OBJ, PLANETS
from engine import SkyEngine
from styles import apply_custom_css, get_plotly_layout, get_cardinal_label
from data_manager import DataManager
from sky_plotter import SkyPlotter

# 1. Configuración de página
st.set_page_config(page_title="SkyView Pro v17", layout="wide", page_icon="🔭")
apply_custom_css()

# 2. Carga de datos (Cacheada)
@st.cache_data
def get_catalogs():
    stars = DataManager.load_stars(CON_ES)
    constellations = DataManager.load_constellations(CON_ES)
    return stars, constellations

df_stars, const_data = get_catalogs()
df_exo = DataManager.load_exoplanets() # Nueva carga

# 3. Inicializar Estado
if 'lat' not in st.session_state:
    st.session_state.update({
        'lat': -34.9214,
        'lon': -57.9546,
        'view': 0,               # Dirección hacia donde mira
        'fov': 100,              # Zoom
        'mag': 3.2,              # Brillo límite
        'scale': 1.0,            # Tamaño de puntos
        'show_const': False,      # Antes era 'c'
        'show_grid': False,      # Antes era 'g'
        'mode': 'Panorama',      # Modo de mapa
        'd': datetime.date.today(),
        't': datetime.datetime.now().time(),
        'sel': None,             # Astro seleccionado para trayectoria
        'ciudad_actual': "La Plata, Arg",
        'show_planet':False,
        "dist_max": 500,
        "show_mess": False,
        "show_images": False
    })


# 4. Modal de Configuración 
@st.dialog("Configuración del Planetario", width="large")
def show_settings():
    t1, t2, t3, t4, t5 = st.tabs(["🔍 Buscar", "📍 GPS", "🕒 Tiempo", "🔄 Vista", "🎨 Ajustes"])
    with t1:
        st.session_state.sel = st.selectbox("Elegí un astro:", [""] + sorted(df_stars['proper'].dropna().tolist()))
        if st.button("Limpiar Trayectoria"): st.session_state.sel = None
    with t2:
        if st.button("🛰️ Obtener ubicación GPS"):
            loc = get_geolocation()
            if loc: st.session_state.lat, st.session_state.lon = loc['coords']['latitude'], loc['coords']['longitude']
        st.session_state.lat = st.number_input("Latitud", value=st.session_state.lat, format="%.4f")
        st.session_state.lon = st.number_input("Longitud", value=st.session_state.lon, format="%.4f")
    with t3:
        st.session_state.d = st.date_input("Fecha", st.session_state.d)
        st.session_state.t = st.time_input("Hora", st.session_state.t)
    with t4:
        st.session_state.view = st.slider("Mirar hacia (Solo Panorama)", 0, 360, st.session_state.view, step=15)
        st.session_state.fov = st.slider("Zoom / FOV", 30, 180, st.session_state.fov, step=30 )
    with t5:
        # Definimos las opciones en una lista
        opciones_mapa = ["Panorama", "Cenit (Circular)", "Mapa Galáctico 3D"]

        # Buscamos en qué posición de la lista está lo que tenemos guardado en el state
        indice_actual = opciones_mapa.index(st.session_state.mode)
        
        # Le pasamos ese índice al selectbox
        st.session_state.mode = st.selectbox("Modo de Mapa:", opciones_mapa, index=indice_actual)
        if st.session_state.mode == "Mapa Galáctico 3D":
            st.session_state.dist_max = st.slider("Radio del Cubo (Años Luz)", 5, 50000, st.session_state.dist_max)

            st.session_state.follow_astro = st.checkbox("⚓ Fijar vista en astro seleccionado", 
                                                        value=st.session_state.get('follow_astro', False))
            if st.session_state.follow_astro:
                st.info(f"Orbitando alrededor de: {st.session_state.sel or 'Sol'}")            

        st.session_state.show_const = st.checkbox("Ver Constelaciones", st.session_state.show_const)
        st.session_state.show_mess = st.checkbox("Ver Messiers", st.session_state.show_mess)
        st.session_state.show_planet = st.checkbox("Ver Planetas", st.session_state.show_planet)
        st.session_state.show_images = st.checkbox("🖼️ Ver fotos reales (Nebulosas/Galaxias)", value=st.session_state.show_images)
        st.session_state.show_grid = st.checkbox("Ver Grilla", st.session_state.show_grid)

        st.session_state.mag = st.slider("Brillo Límite", 0.0, 7.0, st.session_state.mag)
        st.session_state.scale = st.slider("Escala Puntos", 1.0, 6.0, st.session_state.scale)
    if st.button("APLICAR Y CERRAR", use_container_width=True): st.rerun()


# Mostrar el botón antes que el mapa (el CSS se encarga de hacerlo flotar)
if st.button("⚙️"):
    show_settings()

# 5. Cálculos Astronómicos
local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
dt_utc = local_tz.localize(datetime.datetime.combine(st.session_state.d, st.session_state.t)).astimezone(pytz.utc)

# A. Procesar Estrellas
stars_df = df_stars.copy()
stars_df['alt'], stars_df['az'] = SkyEngine.get_alt_az(
    stars_df['ra'], stars_df['dec'], st.session_state.lat, st.session_state.lon, dt_utc
)

# Aplicar Proyección (Panorama o Cenit)
stars_df['px'], stars_df['py'] = SkyEngine.transform(
    stars_df['az'], stars_df['alt'], st.session_state
)

# A. Procesar Estrellas (Llamada al motor)
visible = SkyEngine.process_stars(stars_df, st.session_state, dt_utc)

# B. Procesar Planetas (Llamada al motor)
df_planets = SkyEngine.process_planets(st.session_state, dt_utc, CON_ES)


# app.py (Sección de CÁLCULOS y RENDER)

# 1. Preparar capas especiales
if st.session_state.mode == "Mapa Galáctico 3D":
    chart_fig = SkyPlotter.draw_galactic_cube(stars_df, const_data, df_exo, st.session_state, SkyEngine)

   
    # 2. Mostrar y capturar clic (rerun automático al seleccionar)
    event = st.plotly_chart(chart_fig, use_container_width=True, on_select="rerun", config={'displayModeBar': False})
    
    """
    # 3. Lógica de Viaje (Warp)
    print('çlick 0')
    if event and "selection" in event and event["selection"]["points"]:
        print('çlick')
        # El mapa ahora nos devuelve el ID numérico
        selected_id = event["selection"]["points"][0].get("customdata")
        
        if selected_id:
            # Buscamos el nombre correspondiente a ese ID en nuestro catálogo
            match = df_stars[df_stars['id'] == selected_id]
            if not match.empty:
                star_name = match.iloc[0]['proper_clean']
                st.session_state.sel = star_name # Guardamos para el arco amarillo
                st.rerun()  
    else:
        print('çlick1')
    """
else:
    fig = SkyPlotter.create_base_fig(st.session_state)
    
    if st.session_state.show_grid:
        # Dibujamos la Eclíptica (Línea amarilla del Sol) como referencia extra
        ex, ey = SkyEngine.get_grid_line(st.session_state.lat, st.session_state.lon, dt_utc, st.session_state, 'ecliptic')
        fig.add_trace(go.Scatter(x=ex, y=ey, mode='lines', 
                                line=dict(color='rgba(255, 255, 0, 0.2)', dash='dot'),
                                name="Eclíptica", hoverinfo='skip'))
    
        # Dibujar Ecuador Celeste (Línea Azul)
        #if st.session_state.equ:
        ux, uy = SkyEngine.get_grid_line(st.session_state.lat,st.session_state.lon, dt_utc, st.session_state, 'equatorial')
        fig.add_trace(go.Scatter(x=ux, y=uy, mode='lines', line=dict(color='rgba(100,100,255,0.2)')))

    # Dibujar todo lo demás
    SkyPlotter.draw_constellations(fig, stars_df, const_data, st.session_state)
    SkyPlotter.draw_messier(fig, st.session_state.lat, st.session_state.lon, dt_utc, st.session_state, SkyEngine)
    SkyPlotter.draw_exoplanets(fig, visible, df_exo, st.session_state)
    SkyPlotter.draw_stars(fig, visible)
    SkyPlotter.draw_planets(fig, df_planets, st.session_state)
    SkyPlotter.draw_trajectory(fig, st.session_state, SkyEngine, stars_df, df_planets, local_tz)
    SkyPlotter.draw_deep_sky_images(fig, st.session_state.lat, st.session_state.lon, dt_utc, st.session_state, SkyEngine)
    chart_fig = fig


    # 7. Renderizado Final
    #st.markdown('<div class="floating-btn">', unsafe_allow_html=True)
    #if st.button("⚙️"): show_settings()
    #st.markdown('</div>', unsafe_allow_html=True)


    chart = st.plotly_chart(chart_fig, use_container_width=True, on_select="rerun", config={'displayModeBar': False})
    if chart and "selection" in chart and chart["selection"]["points"]:
        st.session_state.sel = chart["selection"]["points"][0]["customdata"]; st.rerun()

# app.py
