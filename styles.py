# styles.py
import streamlit as st

def apply_custom_css():
    """Limpia los márgenes y fija el botón de configuración sin romper el menú"""
    st.markdown("""
        <style>
            /* 1. ELIMINAR CABECERAS Y MÁRGENES */
            header[data-testid="stHeader"], [data-testid="stToolbar"] {
                display: none !important;
            }

            [data-testid="stMainBlockContainer"] {
                padding: 2rem !important;
                max-width: 100% !important;
            }

            /* 2. DISEÑO DEL BOTÓN FLOTANTE (Solo el engranaje) */
            /* Usamos un selector que busca el primer contenedor de botones fuera de la modal */
            section[data-testid="stMain"] .stButton:first-of-type {
                position: fixed !important;
                top: 20px !important;
                left: 20px !important;
                z-index: 1000000 !important;
            }

            section[data-testid="stMain"] .stButton:first-of-type button {
                border-radius: 50% !important;
                width: 50px !important;
                height: 50px !important;
                background-color: rgba(255, 153, 0, 0.5) !important;
                color: white !important;
                border: 1px solid rgba(255, 255, 255, 0.3) !important;
                font-size: 24px !important;
                backdrop-filter: blur(8px) !important;
                box-shadow: 0px 4px 15px rgba(0,0,0,0.5) !important;
            }

            /* 3. REGLAS DE RESCATE: Asegurar que los botones del menú se vean BIEN */
            /* Forzamos que CUALQUIER botón dentro de una modal o pestaña sea normal */
            div[data-testid="stDialog"] button, 
            div[data-testid="stTab"] button,
            button[data-testid="baseButton-secondary"] {
                border-radius: 4px !important;
                width: auto !important;
                height: auto !important;
                background-color: transparent !important;
                display: inline-flex !important;
                position: static !important;
            }
            
            /* Específico para los botones de las pestañas que se ven mal en tu foto */
            div[data-testid="stHorizontalBlock"] button {
                border-radius: 4px !important;
                width: auto !important;
                height: auto !important;
            }

            /* 4. FONDO INTEGRADO */
            [data-testid="stAppViewContainer"] {
                background-color: #050510 !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ... (mantener get_plotly_layout igual)

def apply_custom_css_():
    """Aplica el estilo inmersivo de pantalla fija"""
    st.markdown("""
        <style>
            body, .stApp, [data-testid="stAppViewContainer"] {
                background-color: #050510 !important;
                overflow: hidden !important;
            }
            .main .block-container { padding: 0 !important; max-width: 100% !important; }
            [data-testid="stHeader"] {display: none;}
            
            /* Botón de configuración circular y naranja */
            .floating-btn {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
            }
            .floating-btn button {
                border-radius: 50% !important;
                width: 55px !important;
                height: 55px !important;
                background-color: rgba(255, 153, 0, 0.4) !important;
                color: white !important;
                border: 1px solid rgba(255,255,255,0.3) !important;
                font-size: 24px !important;
            }
            /* Estilo para los botones DENTRO del modal (que sean normales) */
            div[role="dialog"] button {
                border-radius: 5px !important;
                width: auto !important;
                height: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

def get_cardinal_label(angle):
    """Retorna el nombre del punto cardinal para un ángulo"""
    mapping = {0:'NORTE', 45:'NE', 90:'ESTE', 135:'SE', 180:'SUR', 225:'SO', 270:'OESTE', 315:'NO'}
    return mapping.get(angle % 360, f"{angle % 360}°")

def get_plotly_layout(config):
    """Genera el diccionario de layout para Plotly basado en el modo"""
    layout = dict(
        plot_bgcolor='#050510', paper_bgcolor='#050510',
        height=950, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False, hovermode='closest', 
        hoverlabel=dict(
            font_size=20, 
            font_family="Arial",
            namelength=-1  # <--- ESTO EVITA QUE EL TEXTO SE CORTE CON "..."
        ),
        dragmode='zoom' # Habilitamos el modo recuadro por defecto
    )
    
    if config['mode'] == "Panorama":
        tick_v = [-135, -90, -45, 0, 45, 90, 135]
        layout['xaxis'] = dict(
            range=[-config['fov'], config['fov']],
            tickvals=tick_v,
            ticktext=[get_cardinal_label(config['view'] + v) for v in tick_v],
            tickfont=dict(size=18, color='#ff9900'),
            showgrid=config['show_grid'], gridcolor='#1c2a4d', zeroline=False, fixedrange=False
        )
        layout['yaxis'] = dict(
            range=[0, 90], 
            tickfont=dict(size=14, color='gray'),
            showgrid=config['show_grid'], gridcolor='#1c2a4d', zeroline=False, fixedrange=False
        )
    else:
        # Modo Cenital
        layout['xaxis'] = dict(range=[-100, 100], visible=False, fixedrange=False)
        layout['yaxis'] = dict(range=[-100, 100], visible=False, fixedrange=False)
        
    return layout
