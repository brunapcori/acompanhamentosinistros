from datetime import datetime
import glob
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Painel Executivo de Sinistros",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilização CSS personalizada para replicar o modelo dos cartões executivos
st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    
    /* Cartões executivos inferiores */
    .dest-card {
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .dest-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }
    .dest-icon {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }
    .dest-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .dest-subtitle {
        font-size: 0.82rem;
        color: #6b7280;
        margin: 0;
    }
    .item-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.84rem;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
    }
    .item-table th {
        background-color: #f3f4f6;
        color: #374151;
        padding: 8px 10px;
        font-weight: 600;
        text-align: left;
        border-bottom: 1px solid #e5e7eb;
    }
    .item-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #f3f4f6;
        color: #1f2937;
        vertical-align: middle;
    }
    .item-num {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Função para formatar moeda brasileira
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


# Função para formatar data (DD/MM/AAAA)
def formatar_data(val):
  if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
    return "-"
  try:
    dt = pd.to_datetime(val)
    return dt.strftime("%d/%m/%Y")
  except:
    return str(val)


# Função para formatar número do sinistro
def formatar_sinistro(val):
  if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
    return "-"
  try:
    val_float = float(val)
    return str(int(val_float))
  except:
    return str(val).strip()


# Função para carregar a planilha mais recente do repositório
def carregar_dados_repositorio():
  arquivos = [
      f for f in glob.glob("*.xlsx") if not os.path.basename(f).startswith("~$")
  ]
  if not arquivos:
    return None, None, None

  # Seleciona sempre o arquivo mais recente pela data de modificação
  arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
  data_modificacao = datetime.fromtimestamp(
      os.path.getmtime(arquivo_mais_recente)
  ).strftime("%d/%m/%Y às %H:%M")

  df = pd.read_excel(arquivo_mais_recente)

  # Identificar coluna de status/fase
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

  # Filtro estrito: apenas processos em andamento
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

# Cabeçalho Principal
st.title("🚗 Painel Executivo de Sinistros & Gestão de Risco")
if nome_arquivo:
  st.caption(
      f"📁 **Base ativa carregada:** `{nome_arquivo}` | **Última"
      f" atualização:** {info_data}"
  )
else:
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

# ==========================================
# IDENTIFICAÇÃO PRIORITÁRIA DA COLUNA CC
# ==========================================
col_cc = None

# 1. Busca exata por "CC"
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

# 2. Busca por coluna que comece com "CC"
if not col_cc:
  for col in df.columns:
    if str(col).strip().upper().startswith("CC"):
      col_cc = col
      break

# 3. Fallback para Obra relacionada
if not col_cc:
  for col in df.columns:
    if "informe a obra a qual" in str(col).strip().lower():
      col_cc = col
      break

# Mapeamento das colunas de sinistro, valores e datas
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


# Limpeza e Padronização do Centro de Custo / Locação
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
df["Item_Numero"] = [i + 1 for i in range(len(df))]
df["Item_ID"] = [f"#{i + 1}" for i in range(len(df))]
df["Item_Veiculo"] = (
    df["Título"]
    .fillna("Veículo não especificado")
    .astype(str)
    .str.strip()
)

# ==========================================
# 1. RESUMO EXECUTIVO (MÉTRICAS)
# ==========================================
st.subheader("1. Visão Geral da Carteira")

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
    f"{pct_sinistros:.1f}% do total",
)
m3.metric(
    "Em Análise Prévia (Incidente)",
    f"{fase_analise}",
    f"{pct_analise:.1f}% do total",
)
m4.metric("Total Indenizado / Estimado", formatar_moeda(total_indenizado))

st.divider()

# ==========================================
# 2. GARGALOS E PENDÊNCIAS OPERACIONAIS
# ==========================================
st.subheader("2. Gargalos e Pendências Operacionais")

col_left, col_right = st.columns([1, 1])

with col_left:
  st.markdown("#### Distribuição por Fase")
  fig_fase = px.pie(
      df,
      names="Fase atual",
      hole=0.45,
      color_discrete_sequence=["#1f77b4", "#ff7f0e"],
  )
  fig_fase.update_layout(margin=dict(t=20, b=20, l=10, r=10))
  st.plotly_chart(fig_fase, use_container_width=True)

with col_right:
  st.markdown("#### Detalhamento por Processo")
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

    with st.expander(f"📌 [{num_item}] {titulo} — [{fase}]"):
      st.markdown(f"**🚗 Veículo / Descrição:** {titulo}")
      st.markdown(f"**🏢 Centro de Custo / Locação:** `{cc_val}`")
      st.markdown(f"**📍 Local/Endereço:** {local_val}")
      st.markdown(f"**⚠️ Causa / Tipo:** {causa_val} ({tipo_val})")

      st.markdown("---")
      st.markdown("**📋 Dados do Sinistro e Indenizações:**")
      c_seg, c_ter = st.columns(2)
      with c_seg:
        st.markdown(f"- **Sinistro Segurado:** `{sinistro_seg}`")
        st.markdown(f"- **Valor Indenizado:** `{val_seg}`")
        st.markdown(f"- **Data Indenização:** `{data_seg}`")
      with c_ter:
        st.markdown(f"- **Sinistro Terceiro:** `{sinistro_ter}`")
        st.markdown(f"- **Valor Indenizado:** `{val_ter}`")
        st.markdown(f"- **Data Indenização:** `{data_ter}`")

      st.markdown("---")
      st.markdown(f"**🕒 Atualizado em:** {atualizado_val}")
      if comentario and comentario.lower() != "nan":
        st.info(f"**Anotações e Pendências:**\n\n{comentario}")
      else:
        st.write("*Sem comentários registrados no card.*")

st.divider()

# ==========================================
# 3. SINISTRALIDADE POR DESTINAÇÃO / CC (MODELO EXECUTIVO INFOGRÁFICO)
# ==========================================
st.subheader("3. Sinistralidade por Destinação / Centro de Custo (CC)")

# Paleta de cores corporativa alinhada ao modelo da imagem
paleta_cores = {
    0: {
        "bar": "#2b70b8",
        "bg": "#f0f7ff",
        "border": "#bfdbfe",
        "icon_bg": "#dbeafe",
        "badge": "#2563eb",
        "icon": "🚚",
    },
    1: {
        "bar": "#569e87",
        "bg": "#f0fdf4",
        "border": "#bbf7d0",
        "icon_bg": "#dcfce7",
        "badge": "#16a34a",
        "icon": "🏭",
    },
    2: {
        "bar": "#d8b671",
        "bg": "#fffbeb",
        "border": "#fde68a",
        "icon_bg": "#fef3c7",
        "badge": "#d97706",
        "icon": "🛣️",
    },
    3: {
        "bar": "#968bbd",
        "bg": "#faf5ff",
        "border": "#e9d5ff",
        "icon_bg": "#f3e8ff",
        "badge": "#9333ea",
        "icon": "⚙️",
    },
    4: {
        "bar": "#e07a5f",
        "bg": "#fff7ed",
        "border": "#fed7aa",
        "icon_bg": "#ffedd5",
        "badge": "#ea580c",
        "icon": "📍",
    },
}

# Agrupamento por CC / Destinação
df_agrupado = (
    df.groupby("CC_Padronizado", as_index=False)
    .agg(Quantidade=("Título", "count"))
    .sort_values(by="Quantidade", ascending=False)
    .reset_index(drop=True)
)

bar_colors = [
    paleta_cores.get(i % len(paleta_cores))["bar"]
    for i in range(len(df_agrupado))
]

# 1. Gráfico no modelo da imagem (barras limpas com totais no topo e grid suave)
fig_modelo = go.Figure()

fig_modelo.add_trace(
    go.Bar(
        x=df_agrupado["CC_Padronizado"],
        y=df_agrupado["Quantidade"],
        text=df_agrupado["Quantidade"],
        textposition="outside",
        textfont=dict(size=16, family="Arial, sans-serif", color="#111827"),
        marker=dict(
            color=bar_colors, line=dict(color="rgba(0,0,0,0.1)", width=1)
        ),
        width=0.45,
    )
)

max_val = df_agrupado["Quantidade"].max() if not df_agrupado.empty else 2
fig_modelo.update_layout(
    title=dict(
        text=(
            "<b>Ocorrências por Destinação / Centro de Custo"
            " (CC)</b><br><span"
            " style='font-size:13px;color:#6b7280;font-weight:normal;'>Detalhamento"
            " por Itens / Veículos</span>"
        ),
        x=0.01,
        y=0.96,
    ),
    yaxis=dict(
        title="Quantidade<br>de Ocorrências",
        range=[0, max_val + 0.6],
        gridcolor="#e5e7eb",
        showline=True,
        linecolor="#9ca3af",
        tickmode="linear",
        tick0=0,
        dtick=0.5,
    ),
    xaxis=dict(title="", showline=True, linecolor="#9ca3af"),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    margin=dict(t=70, b=40, l=60, r=20),
    height=370,
)

st.plotly_chart(fig_modelo, use_container_width=True)

# 2. Cartões Executivos Inferiores (Detalhamento por Item/Veículo)
num_destinacoes = len(df_agrupado)
if num_destinacoes > 0:
  card_cols = st.columns(num_destinacoes)

  for i, row_cc in df_agrupado.iterrows():
    nome_cc = row_cc["CC_Padronizado"]
    total_cc = row_cc["Quantidade"]
    itens_cc = df[df["CC_Padronizado"] == nome_cc].reset_index(drop=True)

    estilo = paleta_cores.get(i % len(paleta_cores))

    linhas_tabela = ""
    for n_item, item_row in itens_cc.iterrows():
      titulo_item = item_row.get("Título", "Item não especificado")
      sinistro_val = item_row.get(col_sinistro_seg) or item_row.get(
          col_sinistro_ter
      )
      sinistro_info = (
          f" <span style='font-size:0.75rem;color:#6b7280;'>(Sinistro"
          f" {formatar_sinistro(sinistro_val)})</span>"
          if pd.notna(sinistro_val)
          else ""
      )

      linhas_tabela += f"""
            <tr>
                <td style="text-align: center; width: 40px;">
                    <span class="item-num" style="background-color: {estilo['icon_bg']}; color: {estilo['badge']};">
                        {n_item + 1}
                    </span>
                </td>
                <td style="line-height: 1.3;">
                    <b>{titulo_item}</b>{sinistro_info}
                </td>
            </tr>
            """

    html_card = f"""
        <div class="dest-card" style="background-color: {estilo['bg']}; border: 1.5px solid {estilo['border']};">
            <div class="dest-header">
                <div class="dest-icon" style="background-color: {estilo['icon_bg']};">
                    {estilo['icon']}
                </div>
                <div>
                    <h4 class="dest-title">{nome_cc}</h4>
                    <p class="dest-subtitle">Total: {total_cc} ocorrência{'s' if total_cc > 1 else ''}</p>
                </div>
            </div>
            <table class="item-table">
                <thead>
                    <tr>
                        <th style="width: 40px; text-align: center;">Nº</th>
                        <th>Item / Veículo</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_tabela}
                </tbody>
            </table>
        </div>
        """

    with card_cols[i]:
      st.markdown(html_card, unsafe_allow_html=True)

st.divider()

# ==========================================
# 4. TABELA EXECUTIVA: VEÍCULOS, SINISTROS E INDENIZAÇÕES
# ==========================================
st.subheader("4. Relação Geral: Veículos, Sinistros e Valores Indenizados")

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
