# sky_plotter.py
from constants import MESSIER_OBJ, PLANETS, MESSIER_IMAGES
import plotly.graph_objects as go
import numpy as np
import datetime
from styles import get_plotly_layout
import streamlit as st
import pandas as pd
import ephem

class SkyPlotter:
    @staticmethod
    def create_base_fig(config):
        """Crea la figura con el layout base"""
        fig = go.Figure()
        fig.update_layout(get_plotly_layout(config))
        # Suelo para modo Panorama
        if config['mode'] == "Panorama":
            fig.add_shape(type="rect", x0=-200, y0=-10, x1=200, y1=0, 
                          fillcolor="#0a150a", line_width=0, layer="below")
        return fig


    @staticmethod
    def draw_constellations(fig, stars_df, const_data, config):
        """Dibuja líneas y nombres de constelaciones"""
        if not config['show_const']: return
        
        # Mapa de coordenadas para las líneas
        star_map = stars_df[stars_df['hip'].notna() & (stars_df['alt'] > -20)].drop_duplicates('hip').set_index('hip')[['px', 'py', 'alt']].to_dict('index')
        lx, ly, cnx, cny, cnt = [], [], [], [], []
        
        for c in const_data:
            c_pxs, c_pys = [], []
            for h1, h2 in c['pairs']:
                if h1 in star_map and h2 in star_map:
                    s1, s2 = star_map[h1], star_map[h2]
                    # Evitar líneas cruzando el borde en Panorama
                    if config['mode'] == "Cenit (Circular)" or abs(s1['px'] - s2['px']) < 120:
                        lx.extend([s1['px'], s2['px'], None]); ly.extend([s1['py'], s2['py'], None])
                        c_pxs.extend([s1['px'], s2['px']]); c_pys.extend([s1['py'], s2['py']])
            
            if c_pxs and np.mean(c_pys) > (5 if config['mode'] == "Panorama" else -85):
                cnx.append(np.mean(c_pxs)); cny.append(np.mean(c_pys)); cnt.append(c['name_es'])
        
        fig.add_trace(go.Scattergl(x=lx, y=ly, mode='lines', line=dict(color='rgba(100,200,255,0.15)', width=1), hoverinfo='skip'))
        fig.add_trace(go.Scattergl(x=cnx, y=cny, mode='text', text=cnt, textfont=dict(color='rgba(150,180,255,0.4)', size=15), hoverinfo='skip'))


    @staticmethod
    def draw_stars(fig, visible_stars):
        """Dibuja estrellas con optimización de memoria para evitar el error de JSON"""
        
        # Ordenamos por brillo para priorizar nombres de las más importantes
        df_sorted = visible_stars.sort_values('mag')
        
        # LÍMITE DE SEGURIDAD: 
        # Solo ponemos nombres/tooltips a las primeras 8,000 para que el JSON no pese 5MB
        # El resto se dibujan igual pero no 'hablan' al pasar el mouse.
        n_info = 8000
        
        # Estrellas con información
        df_info = df_sorted.head(n_info).copy()
        print(df_info.columns.tolist())
        h_text = ("<b>" + df_info['proper_clean'] + "("+ df_info['rank_brillo'].astype(str) + ")</b><br>" +
                  "Const: " + df_info['con_es'] + "<br>" +
                  "Dist: " + df_info['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
                  "Tipo: " + df_info['spect'].fillna('?') + "<br>" +
                  "Mag: " + df_info['mag'].map('{:.2f}'.format))

        fig.add_trace(go.Scattergl(
            x=df_info['px'], y=df_info['py'], mode='markers',
            text=h_text, hoverinfo='text',            
            customdata=df_info['id'],
            marker=dict(size=df_info['size'], color=df_info['color'], opacity=0.9,  
                line=dict(
                width=0.5, 
                color='rgba(255, 255, 255, 0.2)' # Un borde casi invisible que simula un pequeño brillo
                ))
        ))
        
        # Estrellas de fondo (sin información, para que no pese el JSON)
        if len(df_sorted) > n_info:
            df_bg = df_sorted.tail(len(df_sorted) - n_info).copy()
            fig.add_trace(go.Scattergl(
                x=df_bg['px'], y=df_bg['py'], mode='markers',
                hoverinfo='none', # Esto ahorra muchísimo tamaño en el JSON
                marker=dict(size=df_bg['size'], color=df_bg['color'], opacity=0.6, line=dict(width=0))
            ))


    @staticmethod
    def draw_stars_OLD(fig, visible_stars):
        """Dibuja los puntos de las estrellas con tooltip rico"""
        h_text = ("<b>" + visible_stars['proper_clean'] + "</b><br>" +
                  "Const: " + visible_stars['con_es'] + "<br>" +
                  "Dist: " + visible_stars['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
                  "Tipo: " + visible_stars['spect'].fillna('?') + "<br>" +
                  "Mag: " + visible_stars['mag'].map('{:.2f}'.format))
        
        fig.add_trace(go.Scattergl(
            x=visible_stars['px'], y=visible_stars['py'], mode='markers', text=h_text, customdata=visible_stars['proper_clean'],
            hoverinfo='text', marker=dict(size=visible_stars['size'], color=visible_stars['color'], opacity=0.85,  
                line=dict(
                width=0.5, 
                color='rgba(255, 255, 255, 0.2)' # Un borde casi invisible que simula un pequeño brillo
                ))
        ))


    @staticmethod
    def draw_planets(fig, df_planets, config):
        """Dibuja los planetas y el Sol"""
        if not config['show_planet']: return
        if df_planets.empty: return
        fig.add_trace(go.Scatter(
            x=df_planets['px'], 
            y=df_planets['py'], 
            mode='markers+text', 
            text=df_planets['Nombre'], # El nombre que flota
            customdata=df_planets['Nombre'],
            textposition="top center",
            hovertext=df_planets['hover'], # <--- LA INFO RICA AL PASAR EL MOUSE
            hoverinfo='text',
            marker=dict(
                size=df_planets['size'], 
                color=df_planets['color'], 
                line=dict(width=2, color='white')
        ),
        textfont=dict(color='white', size=18)
    ))        


    @staticmethod
    def draw_trajectory(fig, config, engine, df_stars_all, planet_objs, local_tz):
    #def draw_trajectory_OLS(fig, config, engine, df_stars_all, local_tz):
        """Dibuja el arco amarillo (CORREGIDO)"""
        sel = config.get('sel')
        if not sel: return
        
        px, py, pt, ptxt = [], [], [], []
        
        # 1. IDENTIFICAR QUÉ ASTRO ES (Planeta o Estrella por ID/Nombre)
        is_planet = sel in planet_objs
        star_row = None
        
        if not is_planet:
            # Buscamos en el catálogo. Probamos por ID primero, luego por nombre
            found = df_stars_all[df_stars_all['id'] == sel]
            if found.empty:
                found = df_stars_all[df_stars_all['proper_clean'] == sel]
            
            if not found.empty:
                star_row = found.iloc[0]
            else:
                return # Si no se encuentra, salimos sin error

        # 2. CALCULAR ARCO (Cada 10 min)
        for m in range(0, 24*60, 10):
            dt_c = local_tz.localize(datetime.datetime.combine(config['d'], datetime.time(0,0)) + datetime.timedelta(minutes=m)).astimezone(datetime.timezone.utc)
            
            if is_planet:
                p_o = planet_objs[sel]
                obs = ephem.Observer()
                obs.lat, obs.lon, obs.date = str(config['lat']), str(config['lon']), dt_c
                p_o.compute(obs)
                p_alt, p_az = np.degrees(p_o.alt), np.degrees(p_o.az)
            else:
                p_alt, p_az = engine.get_alt_az(star_row['ra'], star_row['dec'], config['lat'], config['lon'], dt_c)
            
            if p_alt > 0:
                cx, cy = engine.transform(p_az, p_alt, config)
                if px and abs(cx - px[-1]) > 100 and config['mode'] == "Panorama":
                    px.append(None); py.append(None) # Romper línea en el borde
                px.append(cx); py.append(cy)
                if m % 120 == 0: 
                    pt.append((cx, cy)); ptxt.append(f"{m//60}h")

        # 3. DIBUJAR
        if px:
            fig.add_trace(go.Scatter(x=px, y=py, mode='lines', line=dict(color='#ffff00', width=2, dash='dot'), hoverinfo='skip'))
            if pt:
                lx, ly = zip(*pt)
                fig.add_trace(go.Scatter(x=lx, y=ly, mode='text', text=ptxt, textfont=dict(color='#ffff00', size=14), hoverinfo='skip'))

                
    @staticmethod
    def draw_messier(fig, lat, lon, dt_utc, config, engine):
        
        if not config['show_mess']: return
        """Dibuja objetos de cielo profundo (Galaxias, Nebulosas)"""
        #if not config.get('show_messier', True): return
        
        m_x, m_y, m_text = [], [], []
        for code, data in MESSIER_OBJ.items():
            alt, az = engine.get_alt_az(data[0], data[1], lat, lon, dt_utc)
            if alt > 0:
                x, y = engine.transform(az, alt, config)
                m_x.append(x); m_y.append(y)
                m_text.append(f"<b>{code}</b><br>{data[2]}")
        
        fig.add_trace(go.Scattergl(
            x=m_x, y=m_y, mode='markers+text', text=[c.split('<')[0] for c in m_text],
            hovertext=m_text, hoverinfo='text', textposition="bottom center",
            marker=dict(symbol='diamond', size=10, color='#00ffff'),
            textfont=dict(color='#00ffff', size=12), name='Messier'
        ))


    @staticmethod
    def draw_exoplanets(fig, stars_df, exo_df, config):
        """Dibuja un marcador especial sobre estrellas con planetas"""
        #if not config.get('show_exo', False) or exo_df.empty: return

        # 4. CAPA DE EXOPLANETAS: Resaltar estrellas que tienen planetas
        #if config.get('show_exo') and not exo_df.empty:
            
        df_exo_vis = stars_df.merge(exo_df, on='hip', how='inner')
        
        # Si no encontró nada por ID, intentamos por NOMBRE (como Proxima Centauri)
        if df_exo_vis.empty:
            df_exo_vis = stars_df.merge(exo_df, on='hostname_match', how='inner')
        
        if df_exo_vis.empty: return

        h_text = ("<b>" + df_exo_vis['proper_clean'] + "</b><br>" +
                "🪐 Planetas: " + df_exo_vis['sy_pnum'].astype(str) + "<br>" +
                "Nombres: " + df_exo_vis['pl_name'] + "<br>" +
                "Const: " + df_exo_vis['con_es'] + "<br>" +
                "Dist: " + df_exo_vis['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
                "Tipo: " + df_exo_vis['spect'].fillna('?') + "<br>" +
                "Mag: " + df_exo_vis['mag'].map('{:.2f}'.format))

        """
        fig.add_trace(go.Scattergl(
            x=df_exo_vis['px'], y=df_exo_vis['py'], mode='markers',
            text=h_text, hoverinfo='text',
            marker=dict(
                symbol='circle-open',
                size=df_exo_vis['size'] + 10, # Un poco más grande que la estrella
                line=dict(width=2, color="#00ff00"),
                 color='#00ff00' 
            ),
            name="Exoplanetas"
        ))      
        """
        


    def draw_galactic_cube(df_stars, const_data, exo_df, config, engine):
        # 1. Procesar el universo centrado en la selección
        show_g = config.get('show_grid', False)
        target = config.get('sel')
        dist_max = config.get('dist_max', 50)
        df_trans, sol_rel = engine.get_translated_universe(df_stars, target)
        
        # 2. Filtrar por radio de visión y brillo
        mask = (df_trans['x']**2 + df_trans['y']**2 + df_trans['z']**2)**0.5 <= dist_max
        df_plot = df_trans[mask & (df_trans['mag'] <= config['mag'])].copy()
        #df_plot = df_plot[df_plot['con'] == 'Ori'] #SOLO ORION PRUEBA

        fig = go.Figure()

        # 3. Dibujar Constelaciones en 3D (Líneas reales en el espacio)
        if config['show_const']:
            star_map = df_trans.drop_duplicates('hip').set_index('hip')[['x', 'y', 'z']]
            d_3d = star_map.to_dict('index')
            lx, ly, lz = [], [], []
            for c in const_data:
                for h1, h2 in c['pairs']:
                    if h1 in d_3d and h2 in d_3d:
                        s1, s2 = d_3d[h1], d_3d[h2]
                        lx.extend([s1['x'], s2['x'], None])
                        ly.extend([s1['y'], s2['y'], None])
                        lz.extend([s1['z'], s2['z'], None])
            fig.add_trace(go.Scatter3d(x=lx, y=ly, z=lz, mode='lines', 
                                       line=dict(color='rgba(100,200,255,0.1)', width=2), hoverinfo='skip'))

        # 4. Dibujar Estrellas
        """Dibuja los puntos de las estrellas con tooltip rico"""
        h_text = ("<b>" + df_plot['proper_clean'] + "</b><br>" +
                  "Const: " + df_plot['con_es'] + "<br>" +
                  "Dist: " + df_plot['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
                  "Tipo: " + df_plot['spect'].fillna('?') + "<br>" +
                  "Mag: " + df_plot['mag'].map('{:.2f}'.format))

        fig.add_trace(go.Scatter3d(
            x=df_plot['x'], y=df_plot['y'], z=df_plot['z'], mode='markers',
            text=df_plot['proper_clean'], 
            hovertext=h_text,
            hoverinfo='text+name',
            customdata=df_plot['proper_clean'],
            marker=dict(size=config['scale']*1.5, color=df_plot['spect'].map(engine.get_spectral_color), opacity=0.9)
        ))

        df_plot['hip'] = pd.to_numeric(df_plot['hip'], errors='coerce')
        # Creamos una columna limpia para el nombre para cruce por texto como backup
        df_plot['hostname_match'] = df_plot['proper'].str.strip().str.upper()        


        # 4. CAPA DE EXOPLANETAS: Resaltar estrellas que tienen planetas
        #if config.get('show_exo') and not exo_df.empty:
            
        df_stars_hit = df_plot.dropna(subset=['hip'])
        exo_df_hit = exo_df.dropna(subset=['hip'])
        
        df_exo_vis = df_stars_hit.merge(exo_df_hit, on='hip', how='inner')
        
        # Si no encontró nada por ID, intentamos por NOMBRE (como Proxima Centauri)
        if df_exo_vis.empty:
            df_exo_vis = df_plot.merge(exo_df, on='hostname_match', how='inner')

        if not df_exo_vis.empty:
            h_text = ("<b>" + df_exo_vis['proper_clean'] + "</b><br>" +
                    "🪐 Planetas: " + df_exo_vis['sy_pnum'].astype(str) + "<br>" +
                    "Nombres: " + df_exo_vis['pl_name'] + "<br>" +
                    "Const: " + df_exo_vis['con_es'] + "<br>" +
                    "Dist: " + df_exo_vis['dist_ly'].map('{:.1f} ly'.format) + "<br>" +
                    "Tipo: " + df_exo_vis['spect'].fillna('?') + "<br>" +
                    "Mag: " + df_exo_vis['mag'].map('{:.2f}'.format))
                    

            fig.add_trace(go.Scatter3d(
                x=df_exo_vis['x'], y=df_exo_vis['y'], z=df_exo_vis['z'],
                mode='markers',
                text=h_text,
                hoverinfo='text',
                marker=dict(symbol='circle-open', size=config['scale']+10, 
                            line=dict(width=3, color='#00ff00'))
            ))

        # 5. Dibujar el Sol (si está cerca)
        if (sol_rel[0]**2 + sol_rel[1]**2 + sol_rel[2]**2)**0.5 <= dist_max:
            fig.add_trace(go.Scatter3d(x=[sol_rel[0]], y=[sol_rel[1]], z=[sol_rel[2]], 
                                       mode='markers+text', text=["EL SOL"], 
                                       marker=dict(size=8, color='yellow', line=dict(width=2, color='white'))))


        # Si show_g es False, desactivamos todo lo visual del cubo
        axis_config = dict(
            showgrid=show_g, 
            showbackground=show_g, 
            showticklabels=show_g, 
            title="" if not show_g else None, # Quitamos nombres de ejes si no hay grilla
            zeroline=show_g,
            backgroundcolor="#070715" if show_g else "rgba(0,0,0,0)",
            gridcolor="#1c2a4d",
            range=[-dist_max, dist_max],
            showspikes=False
        )

        # --- LAYOUT DE ÓRBITA ---
        fig.update_layout(
            scene=dict(
                bgcolor='#050510',
                aspectmode='cube',
                xaxis=axis_config,#dict(title="ly", gridcolor='#1c2a4d', range=[-dist_max, dist_max]),
                yaxis=axis_config,#dict(title="ly", gridcolor='#1c2a4d', range=[-dist_max, dist_max]),
                zaxis=axis_config,#dict(title="ly", gridcolor='#1c2a4d', range=[-dist_max, dist_max]),
                camera=dict(eye=dict(x=1.2, y=1.2, z=1.2)) # Vista desde la esquina del cubo
            ),
            paper_bgcolor='#050510', margin=dict(l=0,r=0,t=0,b=0), height=900,
            dragmode='orbit' # <--- FORZAMOS EL MODO ÓRBITA
            ,hoverlabel=dict(font_size=18)
        )
        return fig
      
    @staticmethod
    def draw_deep_sky_images(fig, lat, lon, dt_utc, config, engine):
        """Dibuja fotos reales de nebulosas y galaxias en el mapa"""
        if not config.get('show_images', True): return
        
        for code, data in MESSIER_IMAGES.items():
            ra, dec, url, size = data
            alt, az = engine.get_alt_az(ra, dec, lat, lon, dt_utc)
            
            # Solo si está sobre el horizonte
            if alt > 0:
                px, py = engine.transform(az, alt, config)
                
                # Agregamos la imagen como un "layout image"
                # sizing='contain' para que no se deforme
                fig.add_layout_image(
                    dict(
                        source=url,
                        xref="x", yref="y",
                        x=px, y=py,
                        sizex=size, sizey=size, # Tamaño en grados
                        xanchor="center", yanchor="middle",
                        opacity=0.7, # Para que se vea inmersivo
                        layer="below" # Detrás de las estrellas
                    )
                )
