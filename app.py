#python -m streamlit run app_2.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import pytz
import os
import requests
import ephem
from streamlit_js_eval import get_geolocation # Para el GPS del celular

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SkyView Pro v5", layout="wide", page_icon="🔭")
st.markdown("<style>.block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)

# --- TRADUCCIÓN DE CONSTELACIONES ---
CON_ES = {
    'And': 'Andrómeda', 'Ant': 'Máquina Neumática', 'Aps': 'Ave del Paraíso', 'Aqr': 'Acuario', 'Aql': 'Águila',
    'Ara': 'Altar', 'Ari': 'Aries', 'Aur': 'Cochero', 'Boo': 'Boyero', 'Cae': 'Cincel', 'Cam': 'Jirafa',
    'Cnc': 'Cáncer', 'CVn': 'Lebreles', 'CMa': 'Can Mayor', 'CMi': 'Can Menor', 'Cap': 'Capricornio',
    'Car': 'Quilla', 'Cas': 'Casiopea', 'Cen': 'Centauro', 'Cep': 'Cefeo', 'Cet': 'Ballena', 'Cha': 'Camaleón',
    'Cir': 'Compás', 'Col': 'Paloma', 'Com': 'Cabellera de Berenice', 'CrA': 'Corona Austral', 'CrB': 'Corona Boreal',
    'Crv': 'Cuervo', 'Crt': 'Copa', 'Cru': 'Cruz del Sur', 'Cyg': 'Cisne', 'Del': 'Delfín', 'Dor': 'Dorado',
    'Dra': 'Dragón', 'Equ': 'Caballito', 'Eri': 'Erídano', 'For': 'Horno', 'Gem': 'Géminis', 'Gru': 'Grulla',
    'Her': 'Hércules', 'Hor': 'Reloj', 'Hya': 'Hidra', 'Hyi': 'Hidra Macho', 'Ind': 'Indio', 'Lac': 'Lagarto',
    'Leo': 'Leo', 'LMi': 'Leo Menor', 'Lep': 'Liebre', 'Lib': 'Libra', 'Lup': 'Lobo', 'Lyn': 'Lince',
    'Lyr': 'Lira', 'Men': 'Mesa', 'Mic': 'Microscopio', 'Mon': 'Unicornio', 'Mus': 'Mosca', 'Nor': 'Escuadra',
    'Oct': 'Octante', 'Oph': 'Ofiuco', 'Ori': 'Orión', 'Pav': 'Pavo', 'Peg': 'Pegaso', 'Per': 'Perseo',
    'Phe': 'Fénix', 'Pic': 'Caballete del Pintor', 'Psc': 'Piscis', 'PsA': 'Pez Austral', 'Pup': 'Popa',
    'Pyx': 'Brújula', 'Ret': 'Retículo', 'Sge': 'Flecha', 'Sgr': 'Sagitario', 'Sco': 'Escorpio', 'Scl': 'Escultor',
    'Sct': 'Escudo', 'Ser': 'Serpiente', 'Sex': 'Sextante', 'Tau': 'Tauro', 'Tel': 'Telescopio', 'Tri': 'Triángulo',
    'TrA': 'Triángulo Austral', 'Tuc': 'Tucán', 'UMa': 'Osa Mayor', 'UMi': 'Osa Menor', 'Vel': 'Vela',
    'Vir': 'Virgo', 'Vol': 'Pez Volador', 'Vul': 'Zorra'
}

# --- CARGA DE DATOS ---
@st.cache_data
def load_all_data():
    STARS_URL = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"
    STARS_FILE = "hygdata_v41.csv"
    CONST_URL = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/western/constellationship.fab"
    CONST_FILE = "constellationship.fab"

    if not os.path.exists(STARS_FILE):
        r = requests.get(STARS_URL); open(STARS_FILE, 'wb').write(r.content)
    df = pd.read_csv(STARS_FILE, usecols=['id', 'hip', 'proper', 'ra', 'dec', 'mag', 'ci', 'con', 'dist', 'spect'])
    df['proper_clean'] = df['proper'].fillna("HIP" + df['id'].astype(str))
    df['dist_ly'] = df['dist'] * 3.26156 
    df['con_es'] = df['con'].map(CON_ES).fillna(df['con'])
    
    if not os.path.exists(CONST_FILE):
        r = requests.get(CONST_URL); open(CONST_FILE, 'wb').write(r.content)
    const_data = []
    with open(CONST_FILE, 'r') as f:
        for row in f:
            if row.startswith('#') or not row.strip(): continue
            parts = row.split()
            abbr = parts[0]
            pairs = [(int(parts[i]), int(parts[i+1])) for i in range(2, len(parts), 2)]
            const_data.append({'abbr': abbr, 'name_es': CON_ES.get(abbr, abbr), 'pairs': pairs})
    return df, const_data

# --- MATEMÁTICAS ---
def get_alt_az_numpy(ra_hrs, dec_deg, lat, lon, dt_utc):
    lat_rad, lon_rad = np.radians(lat), np.radians(lon)
    J2000 = datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=pytz.utc)
    d_days = (dt_utc - J2000).total_seconds() / 86400.0
    gmst = (280.46061837 + 360.98564736629 * d_days) % 360
    lst_rad = np.radians(gmst + lon)
    ra_rad, dec_rad = np.radians(ra_hrs * 15), np.radians(dec_deg)
    ha_rad = lst_rad - ra_rad
    sin_lat, cos_lat, sin_dec, cos_dec = np.sin(lat_rad), np.cos(lat_rad), np.sin(dec_rad), np.cos(dec_rad)
    sin_alt = sin_dec * sin_lat + cos_dec * cos_lat * np.cos(ha_rad)
    alt_rad = np.arcsin(np.clip(sin_alt, -1, 1))
    cos_az = (sin_dec - sin_alt * sin_lat) / (np.cos(alt_rad) * cos_lat + 1e-9)
    az_rad = np.arccos(np.clip(cos_az, -1, 1))
    az_rad = np.where(np.sin(ha_rad) > 0, 2*np.pi - az_rad, az_rad)
    return np.degrees(alt_rad), np.degrees(az_rad)

def get_plot_az(az, center):
    diff = (az - center + 180) % 360 - 180
    return diff

# --- INTERFAZ ---
df_stars, const_lines = load_all_data()

with st.sidebar:
    st.title("🌌 SkyView Pro")
    
    # OPCIÓN GPS
    if st.button("📍 Usar mi GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat = loc['coords']['latitude']
            st.session_state.lon = loc['coords']['longitude']
            st.success("Ubicación actualizada")

    if 'lat' not in st.session_state: st.session_state.lat = -34.9214
    if 'lon' not in st.session_state: st.session_state.lon = -57.9546
    
    lat = st.number_input("Latitud", value=st.session_state.lat, format="%.4f")
    lon = st.number_input("Longitud", value=st.session_state.lon, format="%.4f")
    
    st.divider()
    search_query = st.selectbox("🔍 Buscar Estrella:", [""] + sorted(df_stars['proper'].dropna().tolist()))
    view_center = st.slider("Mirar hacia (Girar)", 0, 360, 0, step=15)
    
    if 'd' not in st.session_state: st.session_state.d = datetime.date.today()
    if 't' not in st.session_state: st.session_state.t = datetime.datetime.now().time()
    d = st.date_input("Fecha", st.session_state.d)
    t = st.time_input("Hora Actual", st.session_state.t)
    st.session_state.d, st.session_state.t = d, t

    st.divider()
    show_const = st.checkbox("Ver Constelaciones", True)
    show_grid = st.checkbox("Mostrar Grilla", False)
    show_planets = st.checkbox("Mostrar Planetas", True)
    mag_limit = st.slider("Brillo Límite", 0.0, 6.5, 4.8)
    star_scale = st.slider("Tamaño Estrellas", 1.0, 5.0, 2.5)
    fov = st.slider("Zoom (Ancho)", 20, 180, 110)

if 'selected_astro' not in st.session_state: st.session_state.selected_astro = None
if search_query: st.session_state.selected_astro = search_query

# --- PROCESAMIENTO ---
local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
dt_now = local_tz.localize(datetime.datetime.combine(d, t)).astimezone(pytz.utc)

# Estrellas
stars_df = df_stars.copy()
stars_df['alt'], stars_df['az'] = get_alt_az_numpy(stars_df['ra'], stars_df['dec'], lat, lon, dt_now)
stars_df['plot_az'] = get_plot_az(stars_df['az'], view_center)
visible_stars = stars_df[(stars_df['alt'] > -1) & (stars_df['mag'] <= mag_limit)].copy()

# Colores (CI Index)
def get_c(ci):
    if pd.isna(ci): return '#ffffff'
    if ci < 0.4: return '#9bb0ff'   # Azul
    if ci < 0.8: return '#f8f7ff'   # Blanco
    return '#ffcc6f'                # Naranja
visible_stars['color'] = visible_stars['ci'].map(get_c)
visible_stars['size'] = (mag_limit - visible_stars['mag']) * 0.5 + star_scale

# Planetas con nombres grandes
obs = ephem.Observer(); obs.lat, obs.lon, obs.date = str(lat), str(lon), dt_now
planet_objs = {'Luna': ephem.Moon(), 'Mercurio': ephem.Mercury(), 'Venus': ephem.Venus(), 'Marte': ephem.Mars(), 'Júpiter': ephem.Jupiter(), 'Saturno': ephem.Saturn()}
planets_data = []
for name, obj in planet_objs.items():
    obj.compute(obs); alt, az = np.degrees(obj.alt), np.degrees(obj.az)
    if alt > -5: planets_data.append({'Nombre': name, 'plot_az': get_plot_az(az, view_center), 'alt': alt, 'mag': obj.mag})
df_planets = pd.DataFrame(planets_data)

# --- CONSTRUIR FIGURA ---
fig = go.Figure()

# 1. Constelaciones (Líneas y Nombres grandes)
if show_const:
    star_map_data = stars_df[stars_df['hip'].notna() & (stars_df['alt'] > -20)].copy()
    star_dict = star_map_data.drop_duplicates(subset='hip').set_index('hip')[['plot_az', 'alt']].to_dict('index')
    lx, ly, cnx, cny, cnt = [], [], [], [], []
    for c in const_lines:
        c_p_x, c_p_y = [], []
        for h1, h2 in c['pairs']:
            if h1 in star_dict and h2 in star_dict:
                s1, s2 = star_dict[h1], star_dict[h2]
                if abs(s1['plot_az'] - s2['plot_az']) < 180:
                    lx.extend([s1['plot_az'], s2['plot_az'], None]); ly.extend([s1['alt'], s2['alt'], None])
                    c_p_x.extend([s1['plot_az'], s2['plot_az']]); c_p_y.extend([s1['alt'], s2['alt']])
        if c_p_x:
            cnx.append(np.mean(c_p_x)); cny.append(np.mean(c_p_y)); cnt.append(c['name_es'])
    fig.add_trace(go.Scattergl(x=lx, y=ly, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=1), hoverinfo='skip'))
    fig.add_trace(go.Scattergl(x=cnx, y=cny, mode='text', text=cnt, textfont=dict(color='rgba(150,180,255,0.5)', size=15), hoverinfo='skip'))

# 2. Estrellas con Tooltip detallado
h_text = ("<b>" + visible_stars['proper_clean'] + "</b><br>" +
          "Const: " + visible_stars['con_es'] + "<br>" +
          "Dist: " + visible_stars['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
          "Tipo: " + visible_stars['spect'].fillna('-') + "<br>" +
          "Mag: " + visible_stars['mag'].map('{:.2f}'.format))

fig.add_trace(go.Scattergl(x=visible_stars['plot_az'], y=visible_stars['alt'], mode='markers', text=h_text, 
                           customdata=visible_stars['proper_clean'], hoverinfo='text',
                           marker=dict(size=visible_stars['size'], color=visible_stars['color'], opacity=0.9, line=dict(width=0))))

# 3. Planetas (Letra Grande)
if show_planets and not df_planets.empty:
    fig.add_trace(go.Scatter(x=df_planets['plot_az'], y=df_planets['alt'], mode='markers+text', text="<b>"+df_planets['Nombre']+"</b>", 
                             customdata=df_planets['Nombre'], textposition="top center",
                             marker=dict(size=14, color='#ffd166', line=dict(width=1, color='white')), textfont=dict(color='white', size=16)))

# 4. Trayectoria Suave (Cada 5 min)
if st.session_state.selected_astro:
    sel = st.session_state.selected_astro
    px, py, pt, ptxt = [], [], [], []
    for m in range(0, 24*60, 5):
        dt_c = local_tz.localize(datetime.datetime.combine(d, datetime.time(0,0)) + datetime.timedelta(minutes=m)).astimezone(pytz.utc)
        if sel in planet_objs:
            p_o = planet_objs[sel]; obs.date = dt_c; p_o.compute(obs)
            p_alt, p_az = np.degrees(p_o.alt), np.degrees(p_o.az)
        else:
            found = df_stars[df_stars['proper_clean'] == sel]
            if not found.empty:
                row = found.iloc[0]; p_alt, p_az = get_alt_az_numpy(row['ra'], row['dec'], lat, lon, dt_c)
            else: p_alt = -1
        if p_alt > 0:
            cur_az = get_plot_az(p_az, view_center)
            if px and abs(cur_az - px[-1]) > 100: px.append(None); py.append(None)
            px.append(cur_az); py.append(p_alt)
            if m % 120 == 0: ptxt.append(f"{m//60}h"); pt.append((cur_az, p_alt))
    if px:
        fig.add_trace(go.Scatter(x=px, y=py, mode='lines', line=dict(color='yellow', width=2, dash='dot'), hoverinfo='skip'))
        if pt:
            lx, ly = zip(*pt)
            fig.add_trace(go.Scatter(x=lx, y=ly, mode='text', text=ptxt, textposition="top center", textfont=dict(color='yellow', size=13), hoverinfo='skip'))

# --- LAYOUT DINÁMICO ---
def get_cardinal(a):
    mapping = {0:'NORTE', 45:'NE', 90:'ESTE', 135:'SE', 180:'SUR', 225:'SO', 270:'OESTE', 315:'NO'}
    return mapping.get(a % 360, f"{a%360}°")

tick_vals = [-135, -90, -45, 0, 45, 90, 135]
tick_text = [get_cardinal(view_center + v) for v in tick_vals]

fig.update_layout(
    plot_bgcolor='#050510', paper_bgcolor='#0e1117',
    xaxis=dict(title=dict(text=f"ORIENTACIÓN: {get_cardinal(view_center)}", font=dict(size=22, color='gray')),
               range=[-fov, fov], tickvals=tick_vals, ticktext=tick_text, 
               tickfont=dict(size=16, color='#ff9900'), showgrid=show_grid, gridcolor='#1c2a4d', zeroline=False),
    yaxis=dict(title=dict(text="ALTURA", font=dict(size=22, color='gray')), range=[0, 90], 
               tickfont=dict(size=14, color='gray'), showgrid=show_grid, gridcolor='#1c2a4d', zeroline=False),
    height=800, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, hovermode='closest'
)
fig.add_shape(type="rect", x0=-200, y0=-5, x1=200, y1=0, fillcolor="#101810", line_width=0)

chart_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
if chart_event and "selection" in chart_event and chart_event["selection"]["points"]:
    st.session_state.selected_astro = chart_event["selection"]["points"][0]["customdata"]
    st.rerun()

st.success(f"Estrellas visibles: {len(visible_stars)} | Seleccionado: {st.session_state.selected_astro or 'Ninguno'}")