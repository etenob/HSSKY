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
from streamlit_js_eval import get_geolocation # PARA EL GPS

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SkyView Pro", layout="wide")

# --- AUTO-DETECCIÓN DE UBICACIÓN (GPS) ---
loc = get_geolocation()
if loc:
    default_lat = loc['coords']['latitude']
    default_lon = loc['coords']['longitude']
    ubicacion_msg = "📍 Ubicación detectada por GPS"
else:
    default_lat = -34.9214 # La Plata
    default_lon = -57.9546
    ubicacion_msg = "📍 Usando ubicación por defecto (La Plata)"

# --- TRADUCCIÓN DE CONSTELACIONES ---
CON_ES = {'And': 'Andrómeda', 'Ant': 'Máquina Neumática', 'Aps': 'Ave del Paraíso', 'Aqr': 'Acuario', 'Aql': 'Águila', 'Ara': 'Altar', 'Ari': 'Aries', 'Aur': 'Cochero', 'Boo': 'Boyero', 'Cae': 'Cincel', 'Cam': 'Jirafa', 'Cnc': 'Cáncer', 'CVn': 'Lebreles', 'CMa': 'Can Mayor', 'CMi': 'Can Menor', 'Cap': 'Capricornio', 'Car': 'Quilla', 'Cas': 'Casiopea', 'Cen': 'Centauro', 'Cep': 'Cefeo', 'Cet': 'Ballena', 'Cha': 'Camaleón', 'Cir': 'Compás', 'Col': 'Paloma', 'Com': 'Cabellera de Berenice', 'CrA': 'Corona Austral', 'CrB': 'Corona Boreal', 'Crv': 'Cuervo', 'Crt': 'Copa', 'Cru': 'Cruz del Sur', 'Cyg': 'Cisne', 'Del': 'Delfín', 'Dor': 'Dorado', 'Dra': 'Dragón', 'Equ': 'Caballito', 'Eri': 'Erídano', 'For': 'Horno', 'Gem': 'Géminis', 'Gru': 'Grulla', 'Her': 'Hércules', 'Hor': 'Reloj', 'Hya': 'Hidra', 'Hyi': 'Hidra Macho', 'Ind': 'Indio', 'Lac': 'Lagarto', 'Leo': 'Leo', 'LMi': 'Leo Menor', 'Lep': 'Liebre', 'Lib': 'Libra', 'Lup': 'Lobo', 'Lyn': 'Lince', 'Lyr': 'Lira', 'Men': 'Mesa', 'Mic': 'Microscopio', 'Mon': 'Unicornio', 'Mus': 'Mosca', 'Nor': 'Escuadra', 'Oct': 'Octante', 'Oph': 'Ofiuco', 'Ori': 'Orión', 'Pav': 'Pavo', 'Peg': 'Pegaso', 'Per': 'Perseo', 'Phe': 'Fénix', 'Pic': 'Caballete del Pintor', 'Psc': 'Piscis', 'PsA': 'Pez Austral', 'Pup': 'Popa', 'Pyx': 'Brújula', 'Ret': 'Retículo', 'Sge': 'Flecha', 'Sgr': 'Sagitario', 'Sco': 'Escorpio', 'Scl': 'Escultor', 'Sct': 'Escudo', 'Ser': 'Serpiente', 'Sex': 'Sextante', 'Tau': 'Tauro', 'Tel': 'Telescopio', 'Tri': 'Triángulo', 'TrA': 'Triángulo Austral', 'Tuc': 'Tucán', 'UMa': 'Osa Mayor', 'UMi': 'Osa Menor', 'Vel': 'Vela', 'Vir': 'Virgo', 'Vol': 'Pez Volador', 'Vul': 'Zorra'}

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

def get_alt_az(ra, dec, lat, lon, dt_utc):
    lat_r, lon_r = np.radians(lat), np.radians(lon)
    d = (dt_utc - datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=pytz.utc)).total_seconds() / 86400.0
    lst = np.radians((280.46061837 + 360.98564736629 * d) % 360 + lon)
    ra_r, dec_r = np.radians(ra * 15), np.radians(dec)
    ha = lst - ra_r
    alt = np.arcsin(np.sin(dec_r)*np.sin(lat_r) + np.cos(dec_r)*np.cos(lat_r)*np.cos(ha))
    az = np.arccos((np.sin(dec_r) - np.sin(alt)*np.sin(lat_r)) / (np.cos(alt)*np.cos(lat_r) + 1e-9))
    az = np.where(np.sin(ha) > 0, 2*np.pi - az, az)
    return np.degrees(alt), np.degrees(az)

# --- UI ---
df_stars, const_lines = load_all_data()

with st.sidebar:
    st.subheader(ubicacion_msg)
    lat = st.number_input("Latitud", value=default_lat, format="%.4f")
    lon = st.number_input("Longitud", value=default_lon, format="%.4f")
    view_center = st.slider("Girar vista (Mirar a)", 0, 360, 0, step=15)
    d = st.date_input("Fecha", datetime.date.today())
    t = st.time_input("Hora", datetime.datetime.now().time())
    st.divider()
    search_query = st.selectbox("🔭 Ir a Astro:", [""] + sorted(df_stars['proper'].dropna().tolist()))
    mag_limit = st.slider("Estrellas (Brillo)", 0.0, 6.5, 4.5)
    star_scale = st.slider("Grosor puntos", 1.0, 5.0, 2.5)

# --- LÓGICA ---
local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
dt_utc = local_tz.localize(datetime.datetime.combine(d, t)).astimezone(pytz.utc)

stars_df = df_stars.copy()
stars_df['alt'], stars_df['az'] = get_alt_az(stars_df['ra'], stars_df['dec'], lat, lon, dt_utc)
stars_df['plot_az'] = (stars_df['az'] - view_center + 180) % 360 - 180
visible = stars_df[(stars_df['alt'] > 0) & (stars_df['mag'] <= mag_limit)].copy()
visible['color'] = visible['ci'].map(lambda ci: '#9bb0ff' if ci < 0.4 else ('#ffcc6f' if ci > 1.0 else '#ffffff'))
visible['size'] = (mag_limit - visible['mag']) * 0.5 + star_scale

if 'sel' not in st.session_state: st.session_state.sel = None
if search_query: st.session_state.sel = search_query

# --- DIBUJO ---
fig = go.Figure()

# Líneas y Nombres Const.
star_dict = stars_df[stars_df['hip'].notna() & (stars_df['alt'] > -20)].drop_duplicates('hip').set_index('hip')[['plot_az', 'alt']].to_dict('index')
lx, ly, cnx, cny, cnt = [], [], [], [], []
for c in const_lines:
    c_p_x, c_p_y = [], []
    for h1, h2 in c['pairs']:
        if h1 in star_dict and h2 in star_dict:
            s1, s2 = star_dict[h1], star_dict[h2]
            if abs(s1['plot_az'] - s2['plot_az']) < 100:
                lx.extend([s1['plot_az'], s2['plot_az'], None]); ly.extend([s1['alt'], s2['alt'], None])
                c_p_x.extend([s1['plot_az'], s2['plot_az']]); c_p_y.extend([s1['alt'], s2['alt']])
    if c_p_x: cnx.append(np.mean(c_p_x)); cny.append(np.mean(c_p_y)); cnt.append(c['name_es'])

fig.add_trace(go.Scattergl(x=lx, y=ly, mode='lines', line=dict(color='rgba(100,200,255,0.15)', width=1), hoverinfo='skip'))
fig.add_trace(go.Scattergl(x=cnx, y=cny, mode='text', text=cnt, textfont=dict(color='rgba(150,180,255,0.4)', size=14), hoverinfo='skip'))

# Estrellas
fig.add_trace(go.Scattergl(x=visible['plot_az'], y=visible['alt'], mode='markers', 
                           text="<b>"+visible['proper_clean']+"</b><br>"+visible['con_es'], customdata=visible['proper_clean'],
                           hoverinfo='text', marker=dict(size=visible['size'], color=visible['color'], opacity=0.9)))

# Trayectoria
if st.session_state.sel:
    px, py, pt = [], [], []
    for m in range(0, 24*60, 10):
        dt_c = local_tz.localize(datetime.datetime.combine(d, datetime.time(0,0)) + datetime.timedelta(minutes=m)).astimezone(pytz.utc)
        row = df_stars[df_stars['proper_clean'] == st.session_state.sel].iloc[0]
        p_alt, p_az = get_alt_az(row['ra'], row['dec'], lat, lon, dt_c)
        if p_alt > 0:
            cur_az = (p_az - view_center + 180) % 360 - 180
            if px and abs(cur_az - px[-1]) > 100: px.append(None); py.append(None)
            px.append(cur_az); py.append(p_alt)
            if m % 120 == 0: pt.append((cur_az, p_alt, f"{m//60}h"))
    if px:
        fig.add_trace(go.Scatter(x=px, y=py, mode='lines', line=dict(color='yellow', width=2, dash='dot')))
        for tx, ty, txt in pt: fig.add_trace(go.Scatter(x=[tx], y=[ty], mode='text', text=[txt], textfont=dict(color='yellow')))

# Layout
fig.update_layout(plot_bgcolor='#050510', paper_bgcolor='#0e1117', height=700, showlegend=False, margin=dict(l=0,r=0,t=0,b=0),
                  xaxis=dict(range=[-90, 90], tickvals=[-90, -45, 0, 45, 90], gridcolor='#1c2a4d',
                             ticktext=['OESTE', 'NO', 'NORTE', 'NE', 'ESTE'], tickfont=dict(color='#ff9900')),
                  yaxis=dict(range=[0, 90], gridcolor='#1c2a4d', tickfont=dict(color='gray')))

ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
if ev and ev.get("selection") and ev["selection"]["points"]:
    st.session_state.sel = ev["selection"]["points"][0]["customdata"]; st.rerun()