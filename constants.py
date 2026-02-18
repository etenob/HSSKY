# constants.py
import datetime
import ephem

# Diccionario de Ciudades (Nombre: [Lat, Lon, Timezone])
CIUDADES = {
    "La Plata, Arg": [-34.9214, -57.9546, "America/Argentina/Buenos_Aires"],
    "Buenos Aires, Arg": [-34.6037, -58.3816, "America/Argentina/Buenos_Aires"],
    "Córdoba, Arg": [-31.4135, -64.1811, "America/Argentina/Buenos_Aires"],
    "Madrid, España": [40.4168, -3.7038, "Europe/Madrid"],
    "Santiago, Chile": [-33.4489, -70.6693, "America/Santiago"]
}

# --- TRADUCCIÓN DE CONSTELACIONES ---
CON_ES = {
    'And': 'Andrómeda', 'Ant': 'Antlia', 'Aps': 'Apus', 'Aqr': 'Acuario', 'Aql': 'Águila',
    'Ara': 'Altar', 'Ari': 'Aries', 'Aur': 'Auriga', 'Boo': 'Boyero', 'Cae': 'Cincel',
    'Cnc': 'Cáncer', 'CVn': 'Lebreles', 'CMa': 'Can Mayor', 'CMi': 'Can Menor', 'Cap': 'Capricornio',
    'Car': 'Quilla', 'Cas': 'Casiopea', 'Cen': 'Centauro', 'Cep': 'Cefeo', 'Cet': 'Cetus', 'Cha': 'Camaleón',
    'Cir': 'Circinus', 'Col': 'Paloma', 'Com': 'Coma Berenices', 'CrA': 'Corona Austral', 'CrB': 'Corona Boreal',
    'Crv': 'Cuervo', 'Crt': 'Copa', 'Cru': 'Cruz del Sur', 'Cyg': 'Cisne', 'Del': 'Delfín', 'Dor': 'Dorado',
    'Dra': 'Dragón', 'Equ': 'Equuleus', 'Eri': 'Erídano', 'For': 'Fornax', 'Gem': 'Géminis', 'Gru': 'Grulla',
    'Her': 'Hércules', 'Hor': 'Reloj', 'Hya': 'Hidra', 'Hyi': 'Hidra Macho', 'Ind': 'Indio', 'Lac': 'Lacerta',
    'Leo': 'Leo', 'LMi': 'Leo Menor', 'Lep': 'Lepus', 'Lib': 'Libra', 'Lup': 'Lobo', 'Lyn': 'Lynx',
    'Lyr': 'Lira', 'Men': 'Mesa', 'Mic': 'Microscopio', 'Mon': 'Monoceros', 'Mus': 'Mosca', 'Nor': 'Norma',
    'Oct': 'Octante', 'Oph': 'Ofiuco', 'Ori': 'Orión', 'Pav': 'Pavo', 'Peg': 'Pegaso', 'Per': 'Perseo',
    'Phe': 'Fénix', 'Pic': 'Pictor', 'Psc': 'Piscis', 'PsA': 'Pez Austral', 'Pup': 'Popa',
    'Pyx': 'Pyxis', 'Ret': 'Retículo', 'Sge': 'Sagitta', 'Sgr': 'Sagitario', 'Sco': 'Escorpio', 'Scl': 'Escultor',
    'Sct': 'Scutum', 'Ser': 'Serpiente', 'Sex': 'Sextante', 'Tau': 'Tauro', 'Tel': 'Telescopio', 'Tri': 'Triángulo',
    'TrA': 'Triángulo Austral', 'Tuc': 'Tucán', 'UMa': 'Osa Mayor', 'UMi': 'Osa Menor', 'Vel': 'Vela',
    'Vir': 'Virgo', 'Vol': 'Volans', 'Vul': 'Vulpecula'
}

# constants.py

# constants.py

# Diccionario de imágenes Messier (ID: [RA, Dec, URL, Tamaño_en_grados])
MESSIER_IMAGES = {
    'M42': [5.588, -5.39, "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg/600px-Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg", 3],
    'M31': [0.712, 41.26, "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/M31_09-01-2011_%28C9.25%29.jpg/600px-M31_09-01-2011_%28C9.25%29.jpg", 5],
    'M45': [3.783, 24.11, "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Pleiades_large.jpg/600px-Pleiades_large.jpg", 4],
    'M104': [12.66, -11.62, "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/M104_ngc4594_sombrero_galaxy_hi-res.jpg/600px-M104_ngc4594_sombrero_galaxy_hi-res.jpg", 2],
    'M51': [13.49, 47.19, "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Messier51_sRGB.jpg/600px-Messier51_sRGB.jpg", 2]
}

# --- DICCIONARIO OBJETOS MESSIER (Cielo Profundo) ---
MESSIER_OBJ = {
    'M31': [0.7123, 41.269, 'Galaxia de Andrómeda'],
    'M42': [5.5881, -5.391, 'Nebulosa de Orión'],
    'M45': [3.7836, 24.11, 'Cúmulo de las Pléyades'],
    'M44': [8.6667, 19.67, 'Cúmulo del Pesebre'],
    'M13': [16.695, 36.46, 'Gran Cúmulo de Hércules'],
    'M8': [18.06, -24.38, 'Nebulosa de la Laguna'],
    'M20': [18.04, -23.03, 'Nebulosa Trífida'],
    'M51': [13.498, 47.19, 'Galaxia Remolino'],
    'M104': [12.66, -11.62, 'Galaxia del Sombrero'],
    'M7': [17.89, -34.82, 'Cúmulo de Ptolomeo (Escorpio)'],
    'M6': [17.67, -32.22, 'Cúmulo de la Mariposa']
}

# Estilos de color para la escala espectral (O, B, A, F, G, K, M)
SPECTRAL_ANCHORS = {
    'O': (155, 176, 255), 'B': (170, 191, 255), 'A': (248, 247, 255), 
    'F': (255, 244, 234), 'G': (255, 242, 161), 'K': (255, 204, 111), 
    'M': (255, 90, 90),   'Z': (255, 50, 50) 
}

PLANETS = {'Sol':ephem.Sun(), 'Luna':ephem.Moon(), 'Mercurio':ephem.Mercury(), 'Venus':ephem.Venus(), 
                  'Marte':ephem.Mars(), 'Júpiter':ephem.Jupiter(), 'Saturno':ephem.Saturn(), 
                  'Urano':ephem.Uranus(), 'Neptuno':ephem.Neptune()}
