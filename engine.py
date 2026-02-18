import numpy as np
import datetime
import pandas as pd
import ephem
import pytz
from constants import SPECTRAL_ANCHORS


class SkyEngine:
    @staticmethod
    def get_dt_utc(date, time, timezone_str):
        """Convierte fecha y hora local a UTC"""
        local_tz = pytz.timezone(timezone_str)
        local_dt = local_tz.localize(datetime.datetime.combine(date, time))
        return local_dt.astimezone(pytz.utc)

    @staticmethod
    def get_alt_az(ra_hrs, dec_deg, lat, lon, dt_utc):
        """Matemática de posición astronómica"""
        lat_r, lon_r = np.radians(lat), np.radians(lon)
        d = (dt_utc - datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)).total_seconds() / 86400.0
        lst = np.radians((280.46061837 + 360.98564736629 * d) % 360 + lon)
        ra_r, dec_r = np.radians(ra_hrs * 15), np.radians(dec_deg)
        ha = lst - ra_r
        alt = np.arcsin(np.clip(np.sin(dec_r)*np.sin(lat_r) + np.cos(dec_r)*np.cos(lat_r)*np.cos(ha), -1, 1))
        cos_az = np.clip((np.sin(dec_r) - np.sin(alt)*np.sin(lat_r)) / (np.cos(alt)*np.cos(lat_r) + 1e-9), -1, 1)
        az = np.arccos(cos_az)
        az = np.where(np.sin(ha) > 0, 2*np.pi - az, az)
        return np.degrees(alt), np.degrees(az)

    @staticmethod
    def transform(az_deg, alt_deg, config):
        """Transforma coordenadas según el modo (Panorama/Cenit)"""
        if config['mode'] == "Panorama":
            px = (az_deg - config['view'] + 180) % 360 - 180
            return px, alt_deg
        else:
            r = 90 - alt_deg
            theta = np.radians(az_deg)
            return r * np.sin(theta), r * np.cos(theta)


    @staticmethod
    def get_spectral_color(spect):
        """Calcula el color RGB exacto evitando errores de índice"""
        if pd.isna(spect) or len(str(spect)) < 1: 
            return '#ffffff'
        
        s = str(spect).upper()
        

        order = ['O', 'B', 'A', 'F', 'G', 'K', 'M', 'Z']
        
        # Buscamos la letra
        let = 'A'
        for c in s:
            if c in SPECTRAL_ANCHORS:
                let = c
                break
        
        # Buscamos el número (0-9)
        num = 0
        for c in s:
            if c.isdigit():
                num = int(c)
                break
        
        idx = order.index(let)
        
        # --- CORRECCIÓN DEL ERROR ---
        # Si es la última letra ('Z'), no intentamos buscar la siguiente
        if idx >= len(order) - 1:
            rgb = SPECTRAL_ANCHORS[let]
        else:
            curr_rgb = SPECTRAL_ANCHORS[let]
            next_rgb = SPECTRAL_ANCHORS[order[idx + 1]]
            
            # Factor de mezcla suave
            f = num / 10.0
            r = int(curr_rgb[0] + (next_rgb[0] - curr_rgb[0]) * f)
            g = int(curr_rgb[1] + (next_rgb[1] - curr_rgb[1]) * f)
            b = int(curr_rgb[2] + (next_rgb[2] - curr_rgb[2]) * f)
            rgb = (r, g, b)
        # -----------------------------

        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        

    @classmethod
    def process_stars(cls, df, config, dt_utc):
        """Punto 5A refactorizado: Filtra y procesa el catálogo de estrellas"""
        """
        df_stars = df.copy()
        df_stars['alt'], df_stars['az'] = cls.get_alt_az(df_stars['ra'], df_stars['dec'], config['lat'], config['lon'], dt_utc)
        df_stars['px'], df_stars['py'] = cls.transform(df_stars['az'], df_stars['alt'], config)
        """
        
        visible = df[(df['alt'] > -1) & (df['mag'] <= config['mag'])].copy()
        visible['color'] = visible['spect'].map(cls.get_spectral_color)
        visible['size'] = (config['mag'] - visible['mag']) * 0.3 + config['scale']
        print(visible)
        return visible

    @classmethod
    def process_planets(cls, config, dt_utc, con_es_dict):
        """Punto 5B refactorizado: Calcula planetas y genera sus tooltips"""
        obs = ephem.Observer()
        obs.lat, obs.lon, obs.date = str(config['lat']), str(config['lon']), dt_utc
        
        p_objs = {'Sol':ephem.Sun(), 'Luna':ephem.Moon(), 'Mercurio':ephem.Mercury(), 'Venus':ephem.Venus(), 
                  'Marte':ephem.Mars(), 'Júpiter':ephem.Jupiter(), 'Saturno':ephem.Saturn(), 
                  'Urano':ephem.Uranus(), 'Neptuno':ephem.Neptune()}
        
        planets_list = []
        for name, obj in p_objs.items():
            obj.compute(obs)
            alt, az = np.degrees(obj.alt), np.degrees(obj.az)
            
            if alt > -5 and obj.mag <= config['mag']:
                px, py = cls.transform(az, alt, config)
                if name == 'Sol':
                    con_ast = ephem.constellation(obj)[1]
                    h_info = f"<b>{name}</b><br>Const: {con_es_dict.get(con_ast, con_ast)}<br>Dist: 8.3 min luz<br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#FFCC33', 24  # Dorado grande
                elif name == 'Luna':
                    h_info = f"<b>{name}</b><br>Ilum: {obj.phase:.1f}%<br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#FFFFFF', 22  # Blanca grande
                elif name == 'Mercurio':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#adb5bd', 14  # Gris pequeño
                elif name == 'Venus':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#ffd166', 18  # Amarillento brillante
                elif name == 'Marte':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#ef476f', 16  # Rojizo
                elif name == 'Júpiter':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#a5d6f1', 20  # Crema/Azul claro grande
                elif name == 'Saturno':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#e9c46a', 18  # Ocre/Anillos
                elif name == 'Urano':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#81dfd0', 14  # Cian pálido
                elif name == 'Neptuno':
                    h_info = f"<b>{name}</b><br>Mag: {obj.mag:.1f}"
                    col_ast, size_ast = '#4361ee', 14  # Azul profundo
                    
                planets_list.append({
                    'Nombre': name, 'px': px, 'py': py, 
                    'hover': h_info, 'color': col_ast, 'size': size_ast,
                    'alt': alt, 'az_real': az
                })
        
        return pd.DataFrame(planets_list)

    @classmethod
    def get_grid_line(cls, lat, lon, dt_utc, config, type='ecliptic'):
        """Genera puntos para la Eclíptica o el Ecuador Celeste"""
        ra_points = np.linspace(0, 24, 100)
        if type == 'ecliptic':
            # La eclíptica está inclinada 23.44° respecto al ecuador
            dec_points = 23.44 * np.sin(np.radians(ra_points * 15))
        else: # equatorial
            dec_points = np.zeros(100)
            
        alt, az = cls.get_alt_az(ra_points, dec_points, lat, lon, dt_utc)
        
        # Transformar según el modo
        px, py = [], []
        for a, z in zip(alt, az):
            if a > -5: # Solo mostrar si está cerca del horizonte
                x, y = cls.transform(z, a, config)
                if px and abs(x - px[-1]) > 100 and config['mode'] == "Panorama":
                    px.append(None); py.append(None)
                px.append(x); py.append(y)
        return px, py


    @staticmethod
    def get_galactic_3d(ra_hrs, dec_deg, dist_ly):
        """Coordenadas cartesianas reales en Años Luz"""
        ra_rad = np.radians(ra_hrs * 15)
        dec_rad = np.radians(dec_deg)
        x = dist_ly * np.cos(dec_rad) * np.cos(ra_rad)
        y = dist_ly * np.cos(dec_rad) * np.sin(ra_rad)
        z = dist_ly * np.sin(dec_rad)
        return x, y, z

    @classmethod
    def get_translated_universe(cls, df_stars, target_name):
        """Mueve todo el universo para que la estrella elegida sea el centro (0,0,0)"""
        df = df_stars.copy()
        # 1. Calcular coordenadas absolutas
        df['x_abs'], df['y_abs'], df['z_abs'] = cls.get_galactic_3d(df['ra'], df['dec'], df['dist_ly'])
        
        # 2. Encontrar el centro (Sol por defecto)
        cx, cy, cz = 0, 0, 0
        if target_name:
            target = df[df['proper_clean'] == target_name]
            if not target.empty:
                cx, cy, cz = target.iloc[0]['x_abs'], target.iloc[0]['y_abs'], target.iloc[0]['z_abs']
        
        # 3. Traslación: Restamos el centro a todos
        df['x'] = df['x_abs'] - cx
        df['y'] = df['y_abs'] - cy
        df['z'] = df['z_abs'] - cz
        
        # Posición del Sol relativa al nuevo centro
        sol_rel = (-cx, -cy, -cz)
        
        return df, sol_rel

    @staticmethod
    def get_galactic_coords(ra_hrs, dec_deg, dist_ly):
        """Convierte coordenadas celestes a cartesianas ALINEADAS con la Vía Láctea"""
        # 1. Convertir RA/Dec a Radianes
        ra = np.radians(ra_hrs * 15)
        dec = np.radians(dec_deg)
        
        # 2. Coordenadas del Polo Norte Galáctico (J2000)
        ra_ngp = np.radians(192.85948)
        dec_ngp = np.radians(27.12825)
        l_cpb = np.radians(122.93192)
        
        # 3. Trigonometría para pasar a Latitud (b) y Longitud (l) galáctica
        sin_b = np.sin(dec_ngp) * np.sin(dec) + np.cos(dec_ngp) * np.cos(dec) * np.cos(ra - ra_ngp)
        b = np.arcsin(np.clip(sin_b, -1, 1)) # b es la latitud respecto al disco
        
        y_l = np.cos(dec) * np.sin(ra - ra_ngp)
        x_l = np.cos(dec_ngp) * np.sin(dec) - np.sin(dec_ngp) * np.cos(dec) * np.cos(ra - ra_ngp)
        l = l_cpb - np.arctan2(y_l, x_l)
        
        # 4. Convertir a X, Y, Z cartesianos (donde Z=0 es el plano de la galaxia)
        x = dist_ly * np.cos(b) * np.cos(l)
        y = dist_ly * np.cos(b) * np.sin(l)
        z = dist_ly * np.sin(b)
        
        return x, y, z    
    
    