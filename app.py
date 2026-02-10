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
from streamlit_js_eval import get_geolocation

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SkyView Pro v7", layout="wide", page_icon="🔭")
st.markdown("<style>.block-container {padding: 1rem;} [data-testid='stHeader'] {display: none;}</style>", unsafe_allow_html=True)

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

# --- 1. CARGA DE DATOS ---
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
            const_data.append({'abbr': parts[0], 'name_es': CON_ES.get(parts[0], parts[0]), 'pairs': [(int(parts[i]), int(parts[i+1])) for i in range(2, len(parts), 2)]})
    return df, const_data

# --- 2. MATEMÁTICAS ---
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

# --- 3. SESSION STATE (INICIALIZACIÓN) ---
if 'lat' not in st.session_state: st.session_state.lat = -34.9214
if 'lon' not in st.session_state: st.session_state.lon = -57.9546
if 'view_center' not in st.session_state: st.session_state.view_center = 0
if 'fov' not in st.session_state: st.session_state.fov = 90
if 'mag_limit' not in st.session_state: st.session_state.mag_limit = 4.8
if 'star_scale' not in st.session_state: st.session_state.star_scale = 2.5
if 'show_const' not in st.session_state: st.session_state.show_const = True
if 'show_grid' not in st.session_state: st.session_state.show_grid = False
if 'd' not in st.session_state: st.session_state.d = datetime.date.today()
if 't' not in st.session_state: st.session_state.t = datetime.datetime.now().time()
if 'selected_astro' not in st.session_state: st.session_state.selected_astro = None

df_stars, const_lines_data = load_all_data()

# --- 4. MODAL DE CONFIGURACIÓN ---
@st.dialog("🔭 Configuración del Telescopio", width="large")
def show_settings():
    t1, t2, t3, t4, t5 = st.tabs(["🔍 Buscar", "📍 Ubicación", "🕒 Tiempo", "🔄 Vista", "🎨 Ajustes"])
    
    with t1:
        search = st.selectbox("Buscar Astro:", [""] + sorted(df_stars['proper'].dropna().tolist()))
        if search: st.session_state.selected_astro = search
        if st.button("Limpiar Trayectoria"): st.session_state.selected_astro = None
        
    with t2:
        if st.button("🛰️ Usar GPS"):
            loc = get_geolocation()
            if loc: 
                st.session_state.lat, st.session_state.lon = loc['coords']['latitude'], loc['coords']['longitude']
                st.rerun()
        st.session_state.lat = st.number_input("Latitud", value=st.session_state.lat, format="%.4f")
        st.session_state.lon = st.number_input("Longitud", value=st.session_state.lon, format="%.4f")

    with t3:
        st.session_state.d = st.date_input("Fecha", st.session_state.d)
        st.session_state.t = st.time_input("Hora", st.session_state.t)

    with t4:
        st.session_state.view_center = st.slider("Orientación (0°=N, 180°=S)", 0, 360, st.session_state.view_center, step=15)
        st.session_state.fov = st.slider("Campo de Visión (Zoom)", 20, 160, st.session_state.fov)

    with t5:
        st.session_state.show_const = st.checkbox("Ver Constelaciones", st.session_state.show_const)
        st.session_state.show_grid = st.checkbox("Mostrar Grilla", st.session_state.show_grid)
        st.session_state.mag_limit = st.slider("Brillo Mínimo", 0.0, 7.0, st.session_state.mag_limit)
        st.session_state.star_scale = st.slider("Tamaño de Puntos", 1.0, 6.0, st.session_state.star_scale)

    if st.button("Aplicar cambios", use_container_width=True): st.rerun()

# --- 5. CÁLCULOS PRINCIPALES ---
local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
dt_utc = local_tz.localize(datetime.datetime.combine(st.session_state.d, st.session_state.t)).astimezone(pytz.utc)

# Estrellas
stars_df = df_stars.copy()
stars_df['alt'], stars_df['az'] = get_alt_az_numpy(stars_df['ra'], stars_df['dec'], st.session_state.lat, st.session_state.lon, dt_utc)
stars_df['plot_az'] = get_plot_az(stars_df['az'], st.session_state.view_center)
visible = stars_df[(stars_df['alt'] > -1) & (stars_df['mag'] <= st.session_state.mag_limit)].copy()

# Colores y Tamaños
def get_c(ci):
    if pd.isna(ci): return '#ffffff'
    if ci < 0.4: return '#9bb0ff'
    if ci < 0.8: return '#f8f7ff'
    return '#ffcc6f'
visible['color'] = visible['ci'].map(get_c)
visible['size'] = (st.session_state.mag_limit - visible['mag']) * 0.5 + st.session_state.star_scale

# Planetas
obs = ephem.Observer(); obs.lat, obs.lon, obs.date = str(st.session_state.lat), str(st.session_state.lon), dt_utc
planet_objs = {'Luna': ephem.Moon(), 'Mercurio': ephem.Mercury(), 'Venus': ephem.Venus(), 'Marte': ephem.Mars(), 'Júpiter': ephem.Jupiter(), 'Saturno': ephem.Saturn()}
planets_data = []
for name, obj in planet_objs.items():
    obj.compute(obs); alt, az = np.degrees(obj.alt), np.degrees(obj.az)
    if alt > -5: planets_data.append({'Nombre': name, 'plot_az': get_plot_az(az, st.session_state.view_center), 'alt': alt})
df_planets = pd.DataFrame(planets_data)

# --- 6. GRÁFICO PLOTLY ---
fig = go.Figure()

# A. Constelaciones
if st.session_state.show_const:
    star_map = stars_df[stars_df['hip'].notna() & (stars_df['alt'] > -20)].drop_duplicates('hip').set_index('hip')[['plot_az', 'alt']].to_dict('index')
    lx, ly, cnx, cny, cnt = [], [], [], [], []
    for c in const_lines_data:
        c_px, c_py = [], []
        for h1, h2 in c['pairs']:
            if h1 in star_map and h2 in star_map:
                s1, s2 = star_map[h1], star_map[h2]
                if abs(s1['plot_az'] - s2['plot_az']) < 120:
                    lx.extend([s1['plot_az'], s2['plot_az'], None]); ly.extend([s1['alt'], s2['alt'], None])
                    c_px.extend([s1['plot_az'], s2['plot_az']]); c_py.extend([s1['alt'], s2['alt']])
        if c_px and np.mean(c_py) > 0:
            cnx.append(np.mean(c_px)); cny.append(np.mean(c_py)); cnt.append(c['name_es'])
    fig.add_trace(go.Scattergl(x=lx, y=ly, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=1), hoverinfo='skip'))
    fig.add_trace(go.Scattergl(x=cnx, y=cny, mode='text', text=cnt, textfont=dict(color='rgba(150,180,255,0.4)', size=15), hoverinfo='skip'))

# B. Estrellas
h_text = ("<b>" + visible['proper_clean'] + "</b><br>Const: " + visible['con_es'] + 
          "<br>Dist: " + visible['dist_ly'].map('{:.1f} ly'.format) + "<br>Mag: " + visible['mag'].map('{:.2f}'.format))
fig.add_trace(go.Scattergl(x=visible['plot_az'], y=visible['alt'], mode='markers', text=h_text, customdata=visible['proper_clean'], hoverinfo='text',
                           marker=dict(size=visible['size'], color=visible['color'], opacity=0.9, line=dict(width=0))))

# C. Planetas
if not df_planets.empty:
    fig.add_trace(go.Scatter(x=df_planets['plot_az'], y=df_planets['alt'], mode='markers+text', text="<b>"+df_planets['Nombre']+"</b>", 
                             customdata=df_planets['Nombre'], textposition="top center",
                             marker=dict(size=15, color='#ffd166', line=dict(width=1, color='white')), textfont=dict(color='white', size=16)))

# D. Trayectoria
if st.session_state.selected_astro:
    sel = st.session_state.selected_astro
    px, py, pt, ptxt = [], [], [], []
    for m in range(0, 24*60, 5):
        dt_c = local_tz.localize(datetime.datetime.combine(st.session_state.d, datetime.time(0,0)) + datetime.timedelta(minutes=m)).astimezone(pytz.utc)
        if sel in planet_objs:
            p_o = planet_objs[sel]; obs.date = dt_c; p_o.compute(obs); p_alt, p_az = np.degrees(p_o.alt), np.degrees(p_o.az)
        else:
            found = df_stars[df_stars['proper_clean'] == sel]
            if not found.empty:
                row = found.iloc[0]; p_alt, p_az = get_alt_az_numpy(row['ra'], row['dec'], st.session_state.lat, st.session_state.lon, dt_c)
            else: p_alt = -1
        if p_alt > 0:
            cur_az = get_plot_az(p_az, st.session_state.view_center)
            if px and abs(cur_az - px[-1]) > 100: px.append(None); py.append(None)
            px.append(cur_az); py.append(p_alt)
            if m % 120 == 0: ptxt.append(f"{m//60}h"); pt.append((cur_az, p_alt))
    if px:
        fig.add_trace(go.Scatter(x=px, y=py, mode='lines', line=dict(color='yellow', width=2, dash='dot'), hoverinfo='skip'))
        if pt:
            lx, ly = zip(*pt)
            fig.add_trace(go.Scatter(x=lx, y=ly, mode='text', text=ptxt, textposition="top center", textfont=dict(color='yellow', size=14), hoverinfo='skip'))

# --- LAYOUT ACOTADO (CORREGIDO) ---
def get_card(a):
    mapping = {0:'NORTE', 45:'NE', 90:'ESTE', 135:'SE', 180:'SUR', 225:'SO', 270:'OESTE', 315:'NO'}
    return mapping.get(a % 360, f"{a%360}°")

tick_vals = [-135, -90, -45, 0, 45, 90, 135]
tick_text = [get_card(st.session_state.view_center + v) for v in tick_vals]

fig.update_layout(
    plot_bgcolor='#050510', paper_bgcolor='#0e1117',
    xaxis=dict(
        title=dict(text=f"VISTA AL {get_card(st.session_state.view_center)}", font=dict(size=22, color='gray')),
        range=[-st.session_state.fov, st.session_state.fov], 
        tickvals=tick_vals, ticktext=tick_text, 
        tickfont=dict(size=16, color='#ff9900'), 
        showgrid=st.session_state.show_grid, gridcolor='#1c2a4d', 
        zeroline=False, fixedrange=False # Permite arrastrar de lado a lado
    ),
    yaxis=dict(
        title=dict(text="ALTURA", font=dict(size=22, color='gray')), 
        range=[0, 90], 
        tickfont=dict(size=14, color='gray'), 
        showgrid=st.session_state.show_grid, gridcolor='#1c2a4d', 
        zeroline=False, fixedrange=True # BLOQUEA ZOOM ARRIBA/ABAJO
    ),
    height=850, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, hovermode='closest'
)
fig.add_shape(type="rect", x0=-200, y0=-5, x1=200, y1=0, fillcolor="#101810", line_width=0)

# --- UI Y RENDER ---
c_map, c_set = st.columns([0.94, 0.06])
with c_set:
    if st.button("⚙️", help="Configuración"): show_settings()

ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", config={'displayModeBar': False, 'scrollZoom': True})

if ev and "selection" in ev and ev["selection"]["points"]:
    st.session_state.selected_astro = ev["selection"]["points"][0]["customdata"]
    st.rerun()

st.write(f"📍 {st.session_state.lat:.2f}, {st.session_state.lon:.2f} | {get_card(st.session_state.view_center)} | ✨ {len(visible)} estrellas")