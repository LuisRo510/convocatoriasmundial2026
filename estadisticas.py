import streamlit as st
import plotly.graph_objects as go
import pandas as pd


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


def mostrar(df):
    df_plot = _preparar_datos(df)

    if df_plot.empty:
        st.info("No hay datos suficientes para mostrar el gráfico.")
        return

    # Textos formateados para el hover
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
            range=[24, 29], dtick=1,
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
