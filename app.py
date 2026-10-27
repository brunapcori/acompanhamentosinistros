from datetime import datetime
import glob
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Gestão de Sinistros | Ellenco",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# IDENTIDADE VISUAL E ESTILIZAÇÃO CORPORATIVA (ELLENCO)
# Cores Oficiais: Azul Ellenco (#154474) e Vermelho Ellenco (#EE3E3F)
# ==============================================================================
st.markdown(
    """
<style>
    /* Tipografia e espaçamentos globais */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 98% !important;
    }

    /* Top Bar Corporativa */
    .ellenco-header {
        background: linear-gradient(135deg, #103358 0%, #154474 60%, #1b5694 100%);
        border-radius: 12px;
        padding: 20px 28px;
        color: #ffffff;
        margin-bottom: 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 4px solid #EE3E3F;
        box-shadow: 0 4px 14px rgba(21, 68, 116, 0.18);
    }
    
    .ellenco-title-box h1 {
        color: #ffffff;
        font-size: 1.65rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .ellenco-title-box p {
        color: #dbeafe;
        font-size: 0.88rem;
        margin: 4px 0 0 0;
        font-weight: 400;
    }

    .ellenco-badge-file {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(4px);
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 0.78rem;
        color: #f1f5f9;
        border: 1px solid rgba(255, 255, 255, 0.22);
        text-align: right;
    }

    /* Cartões de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        border-left: 4px solid #154474;
    }
    
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(21, 68, 116, 0.12);
        border-left: 4px solid #EE3E3F;
        transition: all 0.2s ease-in-out;
    }

    div[data-testid="stMetricLabel"] {
        color: #64748b;
        font-size: 0.82rem !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-size: 1.75rem !important;
        font-weight: 800;
        letter-spacing: -0.5px;
    }

    /* Títulos de Seção */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #154474;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    .section-tag {
        background-color: #EE3E3F;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Cartões Executivos Inferiores */
    .dest-card {
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        height: 100%;
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    
    .dest-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .dest-icon {
        width: 38px;
        height: 38px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 19px;
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
    }
    
    .dest-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #154474;
        margin: 0;
        line-height: 1.2;
    }
    
    .dest-subtitle {
        font-size: 0.78rem;
        color: #64748b;
        margin: 2px 0 0 0;
    }
    
    .item-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
        background-color: #ffffff;
        border-radius: 6px;
        overflow: hidden;
    }
    
    .item-table th {
        background-color: #f8fafc;
        color: #475569;
        padding: 6px 8px;
        font-weight: 600;
        text-align: left;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .item-table td {
        padding: 7px 8px;
        border-bottom: 1px solid #f1f5f9;
        color: #1e293b;
        vertical-align: middle;
    }
    
    .item-num {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.75rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# FUNÇÕES DE FORMATAÇÃO E SUPORTE
# ==============================================================================
def formatar_moeda(valor):
  try:
    val_float = float(valor)
    if pd.isna(val_float) or val_float == 0:
      return "R$ 0,00"
    return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", "."
    )
  except:
    return "R$ 0,00"


def formatar_data(val):
  if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
    return "-"
  try:
    dt = pd.to_datetime(val)
    return dt.strftime("%d/%m/%Y")
  except:
    return str(val)


def formatar_sinistro(val):
  if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
    return "-"
  try:
    val_float = float(val)
    return str(int(val_float))
  except:
    return str(val).strip()


def carregar_dados_repositorio():
  arquivos = [
      f for f in glob.glob("*.xlsx") if not os.path.basename(f).startswith("~$")
  ]
  if not arquivos:
    return None, None, None

  arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
  data_modificacao = datetime.fromtimestamp(
      os.path.getmtime(arquivo_mais_recente)
  ).strftime("%d/%m/%Y às %H:%M")

  df = pd.read_excel(arquivo_mais_recente)

  col_fase = None
  for col in df.columns:
    if str(col).strip().lower() in ["fase atual", "status", "fase"]:
      col_fase = col
      break

  if col_fase is None:
    return (
        None,
        arquivo_mais_recente,
        "Coluna de status/fase não localizada na planilha.",
    )

  df["Fase_Normalizada"] = df[col_fase].astype(str).str.strip().str.lower()

  fases_alvo = [
      "acompanhamento de sinistro",
      "análise do incidente",
      "analise do incidente",
  ]
  df_filtrado = (
      df[df["Fase_Normalizada"].isin(fases_alvo)].copy().reset_index(drop=True)
  )

  return df_filtrado, arquivo_mais_recente, data_modificacao


df, nome_arquivo, info_data = carregar_dados_repositorio()

# ==============================================================================
# CABEÇALHO CORPORATIVO ELLENCO
# ==============================================================================
header_html = f"""
<div class="ellenco-header">
    <div class="ellenco-title-box">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
            <span style="background-color: #EE3E3F; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; letter-spacing: 1px;">ELLENCO</span>
            <span style="font-size: 0.82rem; color: #93c5fd; font-weight: 500;">GESTÃO DE RISCOS & SINISTROS</span>
        </div>
        <h1>Painel Executivo de Sinistros & Frotas</h1>
        <p>Monitoramento integrado de processos em regulação, perícias, alocações de obra e liquidações securitárias.</p>
    </div>
    <div class="ellenco-badge-file">
        <div style="font-weight: 700; color: #ffffff;">BASE ATIVA PIPEFY</div>
        <div style="margin-top: 2px;">📄 <code>{nome_arquivo if nome_arquivo else 'Nenhum arquivo'}</code></div>
        <div style="color: #cbd5e1; font-size: 0.72rem; margin-top: 2px;">Atualizado em: {info_data if info_data else '-'}</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

if not nome_arquivo:
  st.error(
      "⚠️ Nenhuma planilha Excel (.xlsx) encontrada na raiz do repositório."
  )
  st.stop()

if df is None or df.empty:
  st.warning(
      "⚠️ Não foram encontrados registros com status 'Acompanhamento de"
      " Sinistro' ou 'Análise do Incidente' na planilha ativa."
  )
  st.stop()

# ==============================================================================
# IDENTIFICAÇÃO PRIORITÁRIA DA COLUNA CC / OBRA
# ==============================================================================
col_cc = None

for col in df.columns:
  if str(col).strip().upper() in [
      "CC",
      "C.C.",
      "C.C",
      "CENTRO DE CUSTO",
      "CENTRO DE CUSTOS",
  ]:
    col_cc = col
    break

if not col_cc:
  for col in df.columns:
    if str(col).strip().upper().startswith("CC"):
      col_cc = col
      break

if not col_cc:
  for col in df.columns:
    if "informe a obra a qual" in str(col).strip().lower():
      col_cc = col
      break

# Mapeamento securitário
col_sinistro_seg = (
    "Número do sinistro (segurado)"
    if "Número do sinistro (segurado)" in df.columns
    else None
)
col_val_seg = "Valor Indenizável" if "Valor Indenizável" in df.columns else None
col_data_seg = (
    "Data da indenização "
    if "Data da indenização " in df.columns
    else [
        c
        for c in df.columns
        if "data da indenização" in c.lower() and "terceiro" not in c.lower()
    ]
)
col_data_seg = (
    col_data_seg
    if isinstance(col_data_seg, str)
    else (col_data_seg[0] if col_data_seg else None)
)

col_sinistro_ter = (
    "Número do sinistro (terceiro)"
    if "Número do sinistro (terceiro)" in df.columns
    else None
)
col_val_ter = (
    "Valor Indenizável (terceiro)"
    if "Valor Indenizável (terceiro)" in df.columns
    else None
)
col_data_ter = [
    c
    for c in df.columns
    if "data da indenização" in c.lower() and "terceiro" in c.lower()
]
col_data_ter = col_data_ter[0] if col_data_ter else None


def padronizar_cc(val):
  if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
    return "Não informado / Operacional"
  texto = str(val).strip()
  if "afirma" in texto.lower():
    return "Alugado para Afirma"
  if "compasa" in texto.lower():
    return "Alugado para Compasa"
  return texto


df["CC_Padronizado"] = (
    df[col_cc].apply(padronizar_cc)
    if col_cc
    else "Não informado / Operacional"
)
df["Item_ID"] = [f"#{i + 1}" for i in range(len(df))]

# ==============================================================================
# 1. RESUMO EXECUTIVO (MÉTRICAS / KPIS)
# ==============================================================================
st.markdown(
    '<div class="section-header"><span class="section-tag">01</span> VISÃO'
    ' GERAL DA CARTEIRA</div>',
    unsafe_allow_html=True,
)

total_ocorrencias = len(df)
sinistros_abertos = len(df[df["Fase_Normalizada"] == "acompanhamento de sinistro"])
fase_analise = len(
    df[df["Fase_Normalizada"].str.contains("análise|analise", na=False)]
)

val_ter_num = (
    pd.to_numeric(df[col_val_ter], errors="coerce").fillna(0).sum()
    if col_val_ter
    else 0
)
val_seg_num = (
    pd.to_numeric(df[col_val_seg], errors="coerce").fillna(0).sum()
    if col_val_seg
    else 0
)
total_indenizado = val_ter_num + val_seg_num

pct_sinistros = (
    (sinistros_abertos / total_ocorrencias * 100) if total_ocorrencias > 0 else 0
)
pct_analise = (
    (fase_analise / total_ocorrencias * 100) if total_ocorrencias > 0 else 0
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Ocorrências em Andamento", f"{total_ocorrencias}")
m2.metric(
    "Sinistros Abertos (Regulação)",
    f"{sinistros_abertos}",
    f"{pct_sinistros:.1f}% da carteira",
)
m3.metric(
    "Em Análise Prévia (Incidente)",
    f"{fase_analise}",
    f"{pct_analise:.1f}% da carteira",
)
m4.metric("Total Indenizado / Estimado", formatar_moeda(total_indenizado))

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 2. STATUS DO FLUXO E GARGALOS OPERACIONAIS
# ==============================================================================
st.markdown(
    '<div class="section-header"><span class="section-tag">02</span> GARGALOS'
    ' OPERACIONAIS & PIPELINE PIPEFY</div>',
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1.1])

with col_left:
  st.markdown("##### Distribuição de Casos por Fase")
  fig_fase = px.pie(
      df,
      names="Fase atual",
      hole=0.48,
      color="Fase atual",
      color_discrete_map={
          "Acompanhamento de Sinistro": "#154474",
          "Análise do Incidente": "#EE3E3F",
      },
  )
  fig_fase.update_traces(
      textinfo="percent+value",
      textfont=dict(size=13, family="Inter, sans-serif", color="#ffffff"),
      marker=dict(line=dict(color="#ffffff", width=2)),
  )
  fig_fase.update_layout(
      margin=dict(t=20, b=20, l=10, r=10),
      legend=dict(
          orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5
      ),
      paper_bgcolor="rgba(0,0,0,0)",
      plot_bgcolor="rgba(0,0,0,0)",
      height=320,
  )
  st.plotly_chart(fig_fase, use_container_width=True)

with col_right:
  st.markdown("##### Detalhamento de Pendências & Regulação")
  col_local = "Informe a obra ou endereço completo do ocorrido:"
  col_causa = "Informe a Causa"
  col_tipo = "Informe o tipo da ocorrencia"

  for idx, row in df.iterrows():
    fase = row.get("Fase atual", "N/A")
    titulo = row.get("Título", f"Ocorrência #{idx + 1}")
    num_item = row.get("Item_ID", f"#{idx + 1}")
    comentario = str(row.get("Último comentário", "")).strip()

    cc_val = row.get("CC_Padronizado", "Não informado / Operacional")
    local_val = row.get(col_local, "Não informado")
    causa_val = row.get(col_causa, "Não informada")
    tipo_val = row.get(col_tipo, "")
    atualizado_val = row.get("Atualizado em", "-")

    sinistro_seg = (
        formatar_sinistro(row.get(col_sinistro_seg)) if col_sinistro_seg else "-"
    )
    val_seg = formatar_moeda(row.get(col_val_seg)) if col_val_seg else "R$ 0,00"
    data_seg = formatar_data(row.get(col_data_seg)) if col_data_seg else "-"

    sinistro_ter = (
        formatar_sinistro(row.get(col_sinistro_ter)) if col_sinistro_ter else "-"
    )
    val_ter = formatar_moeda(row.get(col_val_ter)) if col_val_ter else "R$ 0,00"
    data_ter = formatar_data(row.get(col_data_ter)) if col_data_ter else "-"

    cor_status = "#154474" if "acompanhamento" in str(fase).lower() else "#EE3E3F"

    with st.expander(f"📌 [{num_item}] {titulo} — ({fase})"):
      st.markdown(f"**🚗 Veículo / Descrição:** `{titulo}`")
      st.markdown(f"**🏢 Centro de Custo / Locação:** `{cc_val}`")
      st.markdown(f"**📍 Local/Endereço:** {local_val}")
      st.markdown(f"**⚠️ Causa / Tipo:** {causa_val} ({tipo_val})")

      st.markdown("---")
      c_seg, c_ter = st.columns(2)
      with c_seg:
        st.markdown(
            f"**Segurado:** Sinistro: `{sinistro_seg}` | Indenizado:"
            f" `{val_seg}` | Data: `{data_seg}`"
        )
      with c_ter:
        st.markdown(
            f"**Terceiro:** Sinistro: `{sinistro_ter}` | Indenizado:"
            f" `{val_ter}` | Data: `{data_ter}`"
        )

      st.markdown("---")
      st.markdown(f"**🕒 Atualizado em:** {atualizado_val}")
      if comentario and comentario.lower() != "nan":
        st.info(f"**Anotações e Pendências:**\n\n{comentario}")
      else:
        st.write("*Sem comentários registrados no card.*")

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 3. SINISTRALIDADE POR DESTINAÇÃO / CC E MOTIVOS (PALETA CORPORATIVA ELLENCO)
# ==============================================================================
st.markdown(
    '<div class="section-header"><span class="section-tag">03</span>'
    ' SINISTRALIDADE POR DESTINAÇÃO (CC) & MOTIVOS</div>',
    unsafe_allow_html=True,
)

col_g1, col_g2 = st.columns([1.1, 0.9])

# Paleta corporativa: Tons derivados do Azul Ellenco (#154474) e Vermelho Ellenco (#EE3E3F)
paleta_ellenco = {
    0: {
        "bar": "#154474",
        "bg": "#f0f5fa",
        "border": "#cbd8e6",
        "icon_bg": "#dbe8f4",
        "badge": "#154474",
        "icon": "🚚",
    },
    1: {
        "bar": "#226aa8",
        "bg": "#f4f8fc",
        "border": "#d2e3f1",
        "icon_bg": "#e3effa",
        "badge": "#226aa8",
        "icon": "🏭",
    },
    2: {
        "bar": "#d97706",
        "bg": "#fffbeb",
        "border": "#fde68a",
        "icon_bg": "#fef3c7",
        "badge": "#b45309",
        "icon": "🛣️",
    },
    3: {
        "bar": "#64748b",
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "icon_bg": "#f1f5f9",
        "badge": "#475569",
        "icon": "⚙️",
    },
    4: {
        "bar": "#EE3E3F",
        "bg": "#fef2f2",
        "border": "#fecaca",
        "icon_bg": "#fee2e2",
        "badge": "#EE3E3F",
        "icon": "📍",
    },
}

df_agrupado = (
    df.groupby("CC_Padronizado", as_index=False)
    .agg(Quantidade=("Título", "count"))
    .sort_values(by="Quantidade", ascending=False)
    .reset_index(drop=True)
)

bar_colors = [
    paleta_ellenco.get(i % len(paleta_ellenco))["bar"]
    for i in range(len(df_agrupado))
]

with col_g1:
  fig_dest = go.Figure()
  fig_dest.add_trace(
      go.Bar(
          x=df_agrupado["CC_Padronizado"],
          y=df_agrupado["Quantidade"],
          text=df_agrupado["Quantidade"],
          textposition="outside",
          textfont=dict(
              size=14,
              family="Inter, sans-serif",
              color="#0f172a",
              weight="bold",
          ),
          marker=dict(
              color=bar_colors, line=dict(color="#ffffff", width=1.5)
          ),
          width=0.42,
      )
  )

  max_val_dest = df_agrupado["Quantidade"].max() if not df_agrupado.empty else 2
  fig_dest.update_layout(
      title=dict(
          text=(
              "<b>Ocorrências por Destinação / CC</b><br><span"
              " style='font-size:12px;color:#64748b;'>Volume de processos por"
              " obra / contrato de locação</span>"
          ),
          x=0.01,
          y=0.96,
      ),
      yaxis=dict(
          title="Quantidade de Ocorrências",
          range=[0, max_val_dest + 0.6],
          gridcolor="#f1f5f9",
          showline=True,
          linecolor="#cbd5e1",
          tickmode="linear",
          tick0=0,
          dtick=0.5,
      ),
      xaxis=dict(title="", showline=True, linecolor="#cbd5e1", tickangle=-12),
      plot_bgcolor="#ffffff",
      paper_bgcolor="#ffffff",
      margin=dict(t=65, b=40, l=50, r=10),
      height=350,
  )
  st.plotly_chart(fig_dest, use_container_width=True)

with col_g2:
  col_tipo_ocorr = "Informe o tipo da ocorrencia"
  col_causa_raiz = "Informe a Causa"

  coluna_motivo = (
      col_tipo_ocorr if col_tipo_ocorr in df.columns else col_causa_raiz
  )
  serie_motivos = df[coluna_motivo].fillna("Outros").astype(str).str.strip()
  serie_motivos = serie_motivos.replace({"nan": "Outros", "": "Outros"})
  motivos_counts = serie_motivos.value_counts().reset_index()
  motivos_counts.columns = ["Motivo / Tipo", "Quantidade"]

  fig_motivos = go.Figure()
  fig_motivos.add_trace(
      go.Bar(
          x=motivos_counts["Motivo / Tipo"],
          y=motivos_counts["Quantidade"],
          text=motivos_counts["Quantidade"],
          textposition="outside",
          textfont=dict(
              size=14,
              family="Inter, sans-serif",
              color="#0f172a",
              weight="bold",
          ),
          marker=dict(
              color=[
                  "#EE3E3F" if i == 0 else "#fca5a5"
                  for i in range(len(motivos_counts))
              ],
              line=dict(color="#ffffff", width=1.5),
          ),
          width=0.42,
      )
  )

  max_val_mot = (
      motivos_counts["Quantidade"].max() if not motivos_counts.empty else 4
  )
  fig_motivos.update_layout(
      title=dict(
          text=(
              "<b>Principais Motivos das Ocorrências</b><br><span"
              " style='font-size:12px;color:#64748b;'>Classificação dos eventos"
              " por tipologia</span>"
          ),
          x=0.01,
          y=0.96,
      ),
      yaxis=dict(
          title="Quantidade",
          range=[0, max_val_mot + 0.8],
          gridcolor="#f1f5f9",
          showline=True,
          linecolor="#cbd5e1",
      ),
      xaxis=dict(title="", showline=True, linecolor="#cbd5e1"),
      plot_bgcolor="#ffffff",
      paper_bgcolor="#ffffff",
      margin=dict(t=65, b=40, l=40, r=10),
      height=350,
  )
  st.plotly_chart(fig_motivos, use_container_width=True)

# 3. Cartões Executivos Inferiores com Detalhamento dos Itens
st.markdown(
    "##### Detalhamento Nominal dos Veículos / Ocorrências por Destinação"
)

num_destinacoes = len(df_agrupado)
if num_destinacoes > 0:
  card_cols = st.columns(num_destinacoes)

  for i, row_cc in df_agrupado.iterrows():
    nome_cc = row_cc["CC_Padronizado"]
    total_cc = row_cc["Quantidade"]
    itens_cc = df[df["CC_Padronizado"] == nome_cc].reset_index(drop=True)
    estilo = paleta_ellenco.get(i % len(paleta_ellenco))

    linhas_html = []
    for n_item, item_row in itens_cc.iterrows():
      titulo_item = item_row.get("Título", "Item não especificado")
      sinistro_val = item_row.get(col_sinistro_seg) or item_row.get(
          col_sinistro_ter
      )
      sinistro_info = ""
      if (
          pd.notna(sinistro_val)
          and str(sinistro_val).strip() != ""
          and str(sinistro_val).lower() != "nan"
      ):
        sinistro_info = (
            " <span style='font-size:0.75rem;color:#EE3E3F;font-weight:600;'>(Sinistro"
            f" {formatar_sinistro(sinistro_val)})</span>"
        )

      linha = (
          "<tr><td style='text-align:center; width:32px;'><span"
          " class='item-num' style='background-color:"
          + estilo["icon_bg"]
          + "; color:"
          + estilo["badge"]
          + ";'>"
          + str(n_item + 1)
          + "</span></td><td style='line-height:1.3;'><b>"
          + str(titulo_item)
          + "</b>"
          + sinistro_info
          + "</td></tr>"
      )
      linhas_html.append(linha)

    tabela_corpo = "".join(linhas_html)

    html_card = (
        "<div class='dest-card' style='background-color:"
        + estilo["bg"]
        + "; border:1.5px solid "
        + estilo["border"]
        + "; border-top: 4px solid "
        + estilo["bar"]
        + ";'>"
        "<div class='dest-header'>"
        "<div class='dest-icon' style='background-color:"
        + estilo["icon_bg"]
        + "; color:"
        + estilo["badge"]
        + ";'>"
        + estilo["icon"]
        + "</div>"
        "<div><h4 class='dest-title'>"
        + str(nome_cc)
        + "</h4>"
        "<p class='dest-subtitle'>Total: <b>"
        + str(total_cc)
        + "</b> ocorrência"
        + ("s" if total_cc > 1 else "")
        + "</p></div>"
        "</div>"
        "<table class='item-table'>"
        "<thead><tr><th style='width:32px; text-align:center;'>Nº</th><th>Item"
        " / Veículo</th></tr></thead>"
        "<tbody>" + tabela_corpo + "</tbody>"
        "</table>"
        "</div>"
    )

    with card_cols[i]:
      st.markdown(html_card, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 4. TABELA EXECUTIVA: VEÍCULOS, SINISTROS E INDENIZAÇÕES
# ==============================================================================
st.markdown(
    '<div class="section-header"><span class="section-tag">04</span> RELATÓRIO'
    ' GERAL DE PROCESSOS, SINISTROS & INDENIZAÇÕES</div>',
    unsafe_allow_html=True,
)

tabela_executiva = pd.DataFrame()
tabela_executiva["Item"] = df["Item_ID"]
tabela_executiva["Veículo / Ocorrência"] = df["Título"].fillna("Não informado")
tabela_executiva["Fase Atual"] = df["Fase atual"].fillna("-")
tabela_executiva["Centro de Custo (CC)"] = df["CC_Padronizado"]

# Sinistro Segurado
tabela_executiva["N° Sinistro (Segurado)"] = (
    df[col_sinistro_seg].apply(formatar_sinistro) if col_sinistro_seg else "-"
)
tabela_executiva["Valor Pago (Segurado)"] = (
    df[col_val_seg].apply(formatar_moeda) if col_val_seg else "R$ 0,00"
)
tabela_executiva["Data Pagamento (Segurado)"] = (
    df[col_data_seg].apply(formatar_data) if col_data_seg else "-"
)

# Sinistro Terceiro
tabela_executiva["N° Sinistro (Terceiro)"] = (
    df[col_sinistro_ter].apply(formatar_sinistro) if col_sinistro_ter else "-"
)
tabela_executiva["Valor Pago (Terceiro)"] = (
    df[col_val_ter].apply(formatar_moeda) if col_val_ter else "R$ 0,00"
)
tabela_executiva["Data Pagamento (Terceiro)"] = (
    df[col_data_ter].apply(formatar_data) if col_data_ter else "-"
)

st.dataframe(
    tabela_executiva, use_container_width=True, hide_index=True
)
