from datetime import datetime
import glob
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Painel Executivo de Sinistros",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilização CSS para melhor leitura
st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    .badge-info {
        background-color: #1f2937;
        color: #f3f4f6;
        padding: 4px 8px;
        border-radius: 4px;
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
  df_filtrado = df[df["Fase_Normalizada"].isin(fases_alvo)].copy()

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
    comentario = str(row.get("Último comentário", "")).strip()

    # CC
    cc_val = str(row.get(col_cc, "")).strip() if col_cc else ""
    if not cc_val or cc_val.lower() == "nan":
      cc_val = "Não informado / Operacional"

    local_val = row.get(col_local, "Não informado")
    causa_val = row.get(col_causa, "Não informada")
    tipo_val = row.get(col_tipo, "")
    atualizado_val = row.get("Atualizado em", "-")

    # Dados de Sinistro e Indenização
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

    with st.expander(f"📌 {titulo} — [{fase}]"):
      st.markdown(f"**🚗 Veículo / Descrição:** {titulo}")
      st.markdown(f"**🏢 Centro de Custo (CC):** `{cc_val}`")
      st.markdown(f"**📍 Local/Endereço:** {local_val}")
      st.markdown(f"**⚠️ Causa / Tipo:** {causa_val} ({tipo_val})")

      # Bloco de Informações de Sinistro e Indenização
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
# 3. SINISTRALIDADE POR CC E CAUSAS
# ==========================================
st.subheader("3. Sinistralidade por Centro de Custo (CC) e Causas")

col_g1, col_g2 = st.columns(2)

with col_g1:
  if col_cc:
    serie_cc = df[col_cc].astype(str).str.strip()
    serie_cc = serie_cc.replace(
        {"nan": "Não informado / Operacional", "": "Não informado / Operacional"}
    )
    cc_counts = serie_cc.value_counts().reset_index()
    cc_counts.columns = ["Centro de Custo (CC)", "Quantidade"]

    fig_cc = px.bar(
        cc_counts,
        x="Centro de Custo (CC)",
        y="Quantidade",
        title="Ocorrências por Centro de Custo (CC)",
        color="Quantidade",
        text="Quantidade",
        color_continuous_scale="Blues",
    )
    fig_cc.update_layout(
        xaxis_tickangle=-30, margin=dict(t=40, b=80, l=10, r=10)
    )
    st.plotly_chart(fig_cc, use_container_width=True)
  else:
    st.warning("⚠️ Coluna 'CC' não foi encontrada na planilha.")

with col_g2:
  col_tipo_ocorr = "Informe o tipo da ocorrencia"
  if col_tipo_ocorr in df.columns:
    serie_causas = (
        df[col_tipo_ocorr].fillna("Outros").astype(str).str.strip()
    )
    serie_causas = serie_causas.replace({"nan": "Outros", "": "Outros"})
    causas_counts = serie_causas.value_counts().reset_index()
    causas_counts.columns = ["Tipo da Ocorrência", "Quantidade"]

    fig_causas = px.bar(
        causas_counts,
        x="Tipo da Ocorrência",
        y="Quantidade",
        title="Principais Causas Identificadas",
        color="Quantidade",
        text="Quantidade",
        color_continuous_scale="Reds",
    )
    fig_causas.update_layout(
        xaxis_tickangle=-25, margin=dict(t=40, b=60, l=10, r=10)
    )
    st.plotly_chart(fig_causas, use_container_width=True)

st.divider()

# ==========================================
# 4. TABELA EXECUTIVA: VEÍCULOS, SINISTROS E INDENIZAÇÕES
# ==========================================
st.subheader("4. Relação Geral: Veículos, Sinistros e Valores Indenizados")

tabela_executiva = pd.DataFrame()
tabela_executiva["Veículo / Ocorrência"] = df["Título"].fillna("Não informado")
tabela_executiva["Fase Atual"] = df["Fase atual"].fillna("-")
tabela_executiva["Centro de Custo (CC)"] = (
    df[col_cc].fillna("Não informado") if col_cc else "Não informado"
)

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
