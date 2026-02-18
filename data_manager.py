# data_manager.py
import pandas as pd
import os
import requests
import streamlit as st
import numpy as np
import re 

class DataManager:
    STARS_URL = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"
    STARS_FILE = "stars.csv"
    CONST_URL = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/western/constellationship.fab"
    CONST_FILE = "constellationship.fab"
    EXO_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+pl_name,hostname,hip_name,sy_pnum+from+ps+where+default_flag=1&format=csv"
    EXO_FILE = "exoplanets.csv"

    @staticmethod
    def load_stars(con_es_dict):
        """Descarga y limpia el catálogo HYG v41"""
        if not os.path.exists(DataManager.STARS_FILE):
            r = requests.get(DataManager.STARS_URL)
            open(DataManager.STARS_FILE, 'wb').write(r.content)
        
        # Cargar columnas necesarias
        df = pd.read_csv(DataManager.STARS_FILE, usecols=['id', 'hip', 'proper', 'ra', 'dec', 'mag', 'ci', 'con', 'dist', 'spect'])


        df['mag'] = pd.to_numeric(df['mag'], errors='coerce')
        
        # 2. Quitamos el Sol (ID 0) y cualquier fila que no tenga magnitud válida
        df = df[(df['id'] != 0) & (df['mag'].notna())].copy()
        
        # 3. Creamos el ranking real
        # 'min' asegura que si dos estrellas brillan igual, compartan puesto (ej: 1, 2, 2, 4)
        df['rank_brillo'] = df['mag'].rank(method='min', ascending=True).astype(int)

        df = df[df['id'] != 0] # Sin Sol
        


        # Limpieza profunda de todas las columnas de texto
        df['proper_clean'] = df['proper'].fillna("HIP" + df['id'].astype(str)).apply(DataManager.deep_clean)
        df['spect'] = df['spect'].fillna('?').apply(DataManager.deep_clean)
        df['con_es'] = df['con'].map(con_es_dict).fillna(df['con']).apply(DataManager.deep_clean)

        
        df['dist_ly'] = df['dist'] * 3.26156
        df['hip'] = pd.to_numeric(df['hip'], errors='coerce')
        # Columna de cruce para exoplanetas (Texto limpio)
        df['hostname_match'] = df['proper'].str.strip().str.upper().apply(DataManager.deep_clean)

        return df


    @staticmethod
    def load_exoplanets():
        """Descarga y limpia la base de datos de exoplanetas de la NASA"""
        
        if not os.path.exists(DataManager.EXO_FILE):
            try:
                r = requests.get(DataManager.EXO_URL)
                open(DataManager.EXO_FILE, 'wb').write(r.content)
            except: 
                
                return pd.DataFrame()

        try:
            # Cargamos el archivo ignorando comentarios
            df = pd.read_csv(DataManager.EXO_FILE, comment='#')
            # Extraer el número del campo 'hip_name' (ej: "HIP 123" -> 123)
            if 'hip_name' in df.columns:
                df['hip'] = df['hip_name'].astype(str).str.extract(r'(\d+)').astype(float)
            
            df['hostname'] = df['hostname'].apply(DataManager.deep_clean)
            df['pl_name'] = df['pl_name'].apply(DataManager.deep_clean)

            # Limpiar nombre de estrella para cruce por texto como backup
            df['hostname_match'] = df['hostname'].str.strip().str.upper()
            

            # Consolidamos: cuántos planetas por estrella
            # Importante: reset_index() hace que 'hip' vuelva a ser una columna normal
            exo_summary = df.groupby('hostname_match').agg({
                'hip': 'first',
                'sy_pnum': 'first',
                'pl_name': lambda x: ", ".join(x.astype(str))
            }).reset_index()

            # Forzar que HIP sea numérico
            exo_summary['hip'] = pd.to_numeric(exo_summary['hip'], errors='coerce')            
            
            return exo_summary
        except Exception as e:
            st.error(f"Error procesando exoplanetas: {e}")
            return pd.DataFrame()
        


    @staticmethod
    def load_constellations(con_es_dict):
        """Descarga y parsea las líneas de Stellarium"""
        if not os.path.exists(DataManager.CONST_FILE):
            r = requests.get(DataManager.CONST_URL)
            open(DataManager.CONST_FILE, 'wb').write(r.content)
            
        const_data = []
        with open(DataManager.CONST_FILE, 'r') as f:
            for row in f:
                if not row.startswith('#') and row.strip():
                    parts = row.split()
                    const_data.append({
                        'abbr': parts[0], 
                        'name_es': con_es_dict.get(parts[0], parts[0]), 
                        'pairs': [(int(parts[i]), int(parts[i+1])) for i in range(2, len(parts), 2)]
                    })
        return const_data
    
    def deep_clean(text):
        """Elimina absolutamente cualquier caracter que pueda romper un JSON"""
        if pd.isna(text): return ""
        t = str(text)
        # 1. Quitar barras, comillas y carácteres de escape
        t = t.replace('\\', '/').replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', ' ')
        # 2. Dejar solo caracteres imprimibles (quita caracteres de control invisibles)
        t = "".join(c for c in t if c.isprintable())
        # 3. Solo permitir letras, números y puntuación mínima
        t = re.sub(r'[^a-zA-Z0-9\s\.\,\-\(\)\/\:]', '', t)
        return t.strip()