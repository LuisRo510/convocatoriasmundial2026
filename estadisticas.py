import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import calendar
from datetime import date


def _parsear_valor(val_str):
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


def _edad_completa(fecha_str):
    try:
        d, m, y = str(fecha_str).strip().split('/')
        nac = date(int(y), int(m), int(d))
        hoy = date.today()
        años  = hoy.year  - nac.year
        meses = hoy.month - nac.month
        dias  = hoy.day   - nac.day
        if dias < 0:
            meses -= 1
            mes_ant = hoy.month - 1 if hoy.month > 1 else 12
            año_ant = hoy.year  if hoy.month > 1 else hoy.year - 1
            dias += calendar.monthrange(año_ant, mes_ant)[1]
        if meses < 0:
            años  -= 1
            meses += 12
        return f"{años}a {meses}m {dias}d"
    except Exception:
        return "—"


def _fmt_eu(n, decimals=1):
    """1234.5 → '1.234,5'"""
    return f"{n:,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _preparar_datos(df):
    df_j = df[df['nombre_completo'].notna()].copy()
    rows = []
    for sel, grp in df_j.groupby('seleccion'):
        edades = grp['edad'].dropna() if 'edad' in grp.columns else pd.Series(dtype=float)
        if edades.empty:
            continue
        edad_media = round(edades.mean(), 1)

        if 'valor' not in grp.columns:
            continue
        valores = grp['valor'].apply(_parsear_valor).dropna()
        if valores.empty:
            continue

        rows.append({
            'seleccion':  sel,
            'edad_media': edad_media,
            'valor_total': round(valores.sum(), 1),
        })
    return pd.DataFrame(rows)


def _titulo_ranking(texto):
    st.markdown(
        f"<div style='font-size:13px;font-weight:700;letter-spacing:1px;"
        f"color:#9ca3af;margin-bottom:8px;'>{texto}</div>",
        unsafe_allow_html=True,
    )


def _ranking_clubes(df_j):
    _titulo_ranking("TOP 20 CLUBES")
    if 'club' not in df_j.columns:
        st.caption("Sin datos de club.")
        return
    counts = (
        df_j['club'].dropna()
        .value_counts()
        .head(20)
        .reset_index()
    )
    counts.columns = ['Club', 'Jugadores']
    counts.insert(0, '#', range(1, len(counts) + 1))
    st.dataframe(counts, hide_index=True, use_container_width=True)


def _sub_por_fecha(df_j, n, mas_reciente_primero):
    """Devuelve los n jugadores ordenados exactamente por fecha de nacimiento."""
    sub = df_j[df_j['fecha_nacimiento'].notna()].copy()
    sub['_fecha'] = pd.to_datetime(sub['fecha_nacimiento'], dayfirst=True, errors='coerce')
    sub = sub[sub['_fecha'].notna()]
    sub = sub.nlargest(n, '_fecha') if mas_reciente_primero else sub.nsmallest(n, '_fecha')
    return sub[['nombre_completo', 'seleccion', 'fecha_nacimiento']].copy()


def _ranking_jovenes(df_j):
    _titulo_ranking("20 MÁS JÓVENES")
    if 'fecha_nacimiento' not in df_j.columns:
        st.caption("Sin datos de edad.")
        return
    sub = _sub_por_fecha(df_j, 20, mas_reciente_primero=True)
    sub['Edad'] = sub['fecha_nacimiento'].apply(_edad_completa)
    sub = sub.drop(columns='fecha_nacimiento')
    sub.columns = ['Jugador', 'Selección', 'Edad']
    sub.insert(0, '#', range(1, len(sub) + 1))
    st.dataframe(sub, hide_index=True, use_container_width=True)


def _ranking_veteranos(df_j):
    _titulo_ranking("20 MÁS VETERANOS")
    if 'fecha_nacimiento' not in df_j.columns:
        st.caption("Sin datos de edad.")
        return
    sub = _sub_por_fecha(df_j, 20, mas_reciente_primero=False)
    sub['Edad'] = sub['fecha_nacimiento'].apply(_edad_completa)
    sub = sub.drop(columns='fecha_nacimiento')
    sub.columns = ['Jugador', 'Selección', 'Edad']
    sub.insert(0, '#', range(1, len(sub) + 1))
    st.dataframe(sub, hide_index=True, use_container_width=True)


def mostrar(df):
    df_plot = _preparar_datos(df)

    if df_plot.empty:
        st.info("No hay datos suficientes para mostrar el gráfico.")
        return

    # ── Gráfico de dispersión ────────────────────────────────────────────────
    edad_fmt  = df_plot['edad_media'].apply(lambda x: f"{_fmt_eu(x)} años")
    valor_fmt = df_plot['valor_total'].apply(lambda x: f"{_fmt_eu(x)} mill.")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot['edad_media'],
        y=df_plot['valor_total'],
        mode='markers+text',
        text=df_plot['seleccion'],
        textposition='top center',
        textfont=dict(size=12, color='#1a1a2e'),
        marker=dict(size=13, color='#2e6da4', line=dict(width=1, color='white')),
        customdata=list(zip(df_plot['seleccion'], edad_fmt, valor_fmt)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Edad media: %{customdata[1]}<br>"
            "Valor de plantilla: %{customdata[2]}"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        xaxis=dict(
            range=[24, 30], dtick=1,
            title='Edad media de la plantilla (años)',
            gridcolor='#e5e7eb', zeroline=False,
        ),
        yaxis=dict(
            range=[0, 1600],
            title='Valor total de la plantilla (mill. €)',
            gridcolor='#e5e7eb', zeroline=False,
        ),
        height=540,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=40, t=30, b=60),
        showlegend=False,
        hoverlabel=dict(bgcolor='white', font_size=13),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Rankings en tres columnas ─────────────────────────────────────────────
    st.divider()
    df_j = df[df['nombre_completo'].notna()].copy()

    col_clubes, col_jovenes, col_vets = st.columns(3, gap="large")
    with col_clubes:
        _ranking_clubes(df_j)
    with col_jovenes:
        _ranking_jovenes(df_j)
    with col_vets:
        _ranking_veteranos(df_j)
