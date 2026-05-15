import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date
import estadisticas  # type: ignore

st.set_page_config(page_title="Convocatorias Mundial 2026", layout="wide")
st.markdown("""
<style>
    [data-testid="stSidebar"]    { display: none; }
    [data-testid="stDecoration"] { display: none; }
    .block-container { padding-top: 4rem !important; }
    .stMarkdown h1 a, .stMarkdown h2 a { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ── Orden de posiciones ───────────────────────────────────────────────────────

_ORDEN_POS   = ['Portero', 'Defensa', 'Centrocampista', 'Delantero']
_PLURAL_POS  = {
    'Portero':        'Porteros',
    'Defensa':        'Defensas',
    'Centrocampista': 'Centrocampistas',
    'Delantero':      'Delanteros',
}


# ── Carga y preparación de datos ─────────────────────────────────────────────

def _calcular_edad(fecha_str):
    try:
        d, m, y = str(fecha_str).strip().split('/')
        nac  = date(int(y), int(m), int(d))
        hoy  = date.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _cargar():
    df = pd.read_csv('convocatoria_con_iso.csv', sep=';', encoding='utf-8-sig')
    df.columns = df.columns.str.replace('﻿', '', regex=False).str.strip()
    df = df.rename(columns={df.columns[0]: 'seleccion'})

    if 'dorsal' in df.columns:
        df['dorsal'] = pd.to_numeric(df['dorsal'], errors='coerce').fillna(0).astype(int)

    if 'fecha_nacimiento' in df.columns:
        df['edad'] = df['fecha_nacimiento'].apply(_calcular_edad)

    return df


# ── Datos del mapa choropleth ─────────────────────────────────────────────────

def _build_mapa_data(df):
    rows = []
    for iso3, grp in df.groupby('iso3'):
        sels = grp['seleccion'].unique()
        hover = 'Inglaterra / Escocia' if iso3 == 'GBR' else sels[0]
        rows.append({'iso3': iso3, 'pais': hover})
    return pd.DataFrame(rows)


def _build_mapa(mapa_df):
    mapa_df = mapa_df.copy()
    mapa_df['val'] = 1

    fig = px.choropleth(
        mapa_df,
        locations='iso3',
        color='val',
        hover_name='pais',
        projection='natural earth',
        color_continuous_scale=[[0, '#2e6da4'], [1, '#2e6da4']],
    )
    fig.update_traces(
        marker_line_color='white',
        marker_line_width=0.5,
        hovertemplate='<b>%{hovertext}</b><extra></extra>',
    )
    fig.update_layout(
        coloraxis_showscale=False,
        geo=dict(
            showframe=False,
            showcoastlines=True, coastlinecolor='#c8bfb0',
            showland=True,       landcolor='#e8e3da',
            showocean=True,      oceancolor='#d6eaf8',
            showlakes=False,     bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=480,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# ── Valor de mercado ──────────────────────────────────────────────────────────

def _parsear_valor(val_str):
    """Convierte '3,00 mill. €' o '400 mil €' a float en millones."""
    if pd.isna(val_str) or not str(val_str).strip():
        return None
    s = str(val_str).strip()
    try:
        if 'mill.' in s:
            return float(s.split('mill.')[0].strip().replace(',', '.'))
        if 'mil' in s:
            return float(s.split('mil')[0].strip().replace(',', '.')) / 1000
    except (ValueError, IndexError):
        return None
    return None


def _fmt_millones(total):
    num = f"{total:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{num} mill."


# ── Estadísticas de plantilla ─────────────────────────────────────────────────

def _stats_plantilla(df_con_nombres):
    """Devuelve (edad_media, club_top, valor_total_str)."""
    edad_media = None
    if 'edad' in df_con_nombres.columns:
        edades = df_con_nombres['edad'].dropna()
        if not edades.empty:
            edad_media = round(edades.mean(), 1)

    club_top = "—"
    if 'club' in df_con_nombres.columns:
        clubs = df_con_nombres['club'].dropna()
        if not clubs.empty:
            counts    = clubs.value_counts()
            max_count = counts.iloc[0]
            if max_count <= 1:
                club_top = "Ninguno aporta más de 1"
            else:
                top = counts[counts == max_count].index.tolist()
                club_top = " / ".join(top) + f" ({max_count})"

    valor_total = None
    if 'valor' in df_con_nombres.columns:
        valores = df_con_nombres['valor'].apply(_parsear_valor).dropna()
        if not valores.empty:
            valor_total = _fmt_millones(valores.sum())

    return edad_media, club_top, valor_total


# ── Aviso de dorsales ─────────────────────────────────────────────────────────

@st.dialog("Dorsales no definitivos")
def _aviso_dorsales():
    st.write("Los dorsales mostrados pueden no ser definitivos.")
    if st.button("Entendido", use_container_width=True, type="primary"):
        st.rerun()


def _trigger_aviso(nombre):
    if st.session_state.get('_aviso_sel') != nombre:
        st.session_state['_aviso_sel'] = nombre
        _aviso_dorsales()


# ── Visualización de plantilla ────────────────────────────────────────────────

def _mostrar_plantilla(df_sel, nombre):
    st.subheader(f"Convocatoria | {nombre}", anchor=False)

    # ¿Hay datos de jugadores?
    tiene_nombres = df_sel['nombre_completo'].notna().any() if 'nombre_completo' in df_sel.columns else False

    # Barra de info: grupo + estadísticas (solo si hay nombres)
    grupo_txt  = ""
    if 'grupo' in df_sel.columns:
        grupos = df_sel['grupo'].dropna().unique()
        if len(grupos):
            grupo_txt = f"GRUPO {grupos[0]}"

    if tiene_nombres:
        df_nombres = df_sel[df_sel['nombre_completo'].notna()]
        edad_media, club_top, valor_total = _stats_plantilla(df_nombres)
    else:
        edad_media, club_top, valor_total = None, None, None

    # Renderizar barra de info en una sola línea HTML
    partes = []
    if grupo_txt:
        partes.append(
            f"<span style='background:#2e6da4;color:white;font-weight:700;"
            f"font-size:12px;padding:3px 10px;border-radius:4px;'>{grupo_txt}</span>"
        )
    if edad_media is not None:
        partes.append(
            f"<span style='font-size:13px;color:#6b7280;'>Edad media: "
            f"<b style='color:#1a1a2e;'>{edad_media:.1f}</b></span>"
        )
    if club_top:
        partes.append(
            f"<span style='font-size:13px;color:#6b7280;'>Club predominante: "
            f"<b style='color:#1a1a2e;'>{club_top}</b></span>"
        )
    if valor_total:
        partes.append(
            f"<span style='font-size:13px;color:#6b7280;'>Valor de plantilla: "
            f"<b style='color:#1a1a2e;'>{valor_total}</b></span>"
        )
    if partes:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:20px;margin-bottom:16px;'>"
            + "".join(partes)
            + "</div>",
            unsafe_allow_html=True,
        )

    if not tiene_nombres:
        st.info(f"Convocatoria de {nombre} no disponible.")
        return

    df_sel = df_sel[df_sel['nombre_completo'].notna()].copy()
    df_sel = df_sel.sort_values('dorsal')

    pos_presentes = [p for p in _ORDEN_POS if p in df_sel['posicion'].values]
    cols = st.columns(len(pos_presentes) if pos_presentes else 1)

    for i, pos in enumerate(pos_presentes):
        jugadores = df_sel[df_sel['posicion'] == pos]
        with cols[i]:
            st.markdown(
                f"<div style='font-size:15px;font-weight:700;letter-spacing:1px;"
                f"color:#9ca3af;margin-bottom:10px;'>{_PLURAL_POS.get(pos, pos).upper()}</div>",
                unsafe_allow_html=True,
            )
            for _, j in jugadores.iterrows():
                dorsal_str = f"<span style=font-size:16px;'>{int(j['dorsal'])}.</span> " if j.get('dorsal', 0) > 0 else ""
                nombre_j   = str(j['nombre_completo']).strip()

                detalles = []
                if 'edad' in j and pd.notna(j['edad']):
                    detalles.append(f"{int(j['edad'])} años")
                if 'club' in j and pd.notna(j.get('club')) and str(j['club']).strip():
                    detalles.append(str(j['club']).strip())
                if 'valor' in j and pd.notna(j.get('valor')) and str(j['valor']).strip():
                    detalles.append(str(j['valor']).strip())
                detalle_str = ' · '.join(detalles)

                st.markdown(
                    f"<div style='margin-bottom:12px;line-height:1.4;'>"
                    f"{dorsal_str}<span style='font-weight:600;color:#1a1a2e;font-size:14px;'>{nombre_j}</span><br>"
                    f"<span style='font-size:12px;color:#6b7280;'>{detalle_str}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ── Entrada pública ───────────────────────────────────────────────────────────

def _tab_convocatorias(df):
    mapa_df = _build_mapa_data(df)

    # Cuando el mapa registra un clic nuevo, resetear el dropdown para que el
    # mapa tenga prioridad (si no, el dropdown persiste en session_state y
    # sobreescribe la selección del mapa).
    _map_raw  = st.session_state.get('mapa_mundial') or {}
    _map_pts  = _map_raw.get('selection', {}).get('points', [])
    _curr_iso = _map_pts[0].get('location', '') if _map_pts else None
    _prev_iso = st.session_state.get('_sel_prev_iso')
    if _curr_iso is not None and _curr_iso != _prev_iso:
        st.session_state['equipo_sel'] = '— Selecciona —'
        st.session_state['grupo_sel']  = '— Todos —'
    st.session_state['_sel_prev_iso'] = _curr_iso

    # ── Layout: mapa (izq) + selectores (der) ────────────────────────────────
    col_mapa, col_sel = st.columns([3, 1])

    with col_mapa:
        event = st.plotly_chart(
            _build_mapa(mapa_df),
            on_select='rerun',
            selection_mode='points',
            use_container_width=True,
            key='mapa_mundial',
        )

    with col_sel:
        st.markdown(
            "<div style='font-size:13px;font-weight:700;color:#6b7280;"
            "letter-spacing:0.5px;margin-bottom:8px;'>BUSCAR SELECCIÓN</div>",
            unsafe_allow_html=True,
        )

        grupos_raw   = sorted(df['grupo'].dropna().unique())
        grupo_opts   = ['— Todos —'] + [f"Grupo {g}" for g in grupos_raw]
        grupo_sel    = st.selectbox("Grupo", grupo_opts, key='grupo_sel',
                                    label_visibility='collapsed')

        if grupo_sel == '— Todos —':
            equipos_disp = sorted(df['seleccion'].unique())
        else:
            letra        = grupo_sel.replace('Grupo ', '').strip()
            equipos_disp = sorted(df[df['grupo'] == letra]['seleccion'].unique())

        equipo_sel = st.selectbox(
            "Selección", ['— Selecciona —'] + equipos_disp,
            key='equipo_sel', label_visibility='collapsed',
        )

    st.divider()

    if equipo_sel != '— Selecciona —':
        df_vista = df[df['seleccion'] == equipo_sel]
        _trigger_aviso(equipo_sel)
        _mostrar_plantilla(df_vista, equipo_sel)
        return

    if not (event and event.get('selection', {}).get('points')):
        st.info("Haz clic en un país del mapa o usa el selector de la derecha.")
        return

    iso3        = event['selection']['points'][0].get('location', '')
    nombre_mapa = event['selection']['points'][0].get('hovertext', iso3)

    if iso3 == 'GBR':
        sels_gbr = sorted(df[df['iso3'] == 'GBR']['seleccion'].unique())
        elegida  = st.radio(
            "Selecciona la selección:",
            sels_gbr,
            horizontal=True,
            key='gbr_selector',
        )
        _trigger_aviso(elegida)
        _mostrar_plantilla(df[(df['iso3'] == 'GBR') & (df['seleccion'] == elegida)], elegida)
        return

    df_sel = df[df['iso3'] == iso3]
    if df_sel.empty:
        st.info(f"**{nombre_mapa}** no aparece en la convocatoria.")
        return

    nombre_sel = df_sel['seleccion'].iloc[0]
    _trigger_aviso(nombre_sel)
    _mostrar_plantilla(df_sel, nombre_sel)


def mostrar():
    st.title("Convocatorias para la Copa Mundial de la FIFA 2026", anchor=False)

    df = _cargar()

    tab_conv, tab_stats = st.tabs(["🗺️  Convocatorias", "📊  Estadísticas"])

    with tab_conv:
        _tab_convocatorias(df)

    with tab_stats:
        estadisticas.mostrar(df)

    st.markdown(
        "<div style='position:fixed;bottom:12px;right:50px;"
        "font-size:11px;color:#9ca3af;pointer-events:none;'>"
        "Fuente de los datos: Transfermarkt.com</div>",
        unsafe_allow_html=True,
    )


mostrar()
