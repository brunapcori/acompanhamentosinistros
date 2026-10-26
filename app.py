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

st.title("🚗 Painel Executivo de Sinistros & Gestão de Risco")
st.markdown(
    "Consolidação gerencial de processos em andamento extraídos do Pipefy."
)


# Função para carregar a planilha mais recente do repositório
@st.cache_data
def carregar_dados_repositorio():
  arquivos = [f for f in glob.glob("*.xlsx") if not f.startswith("~$")]
  if not arquivos:
    return None

  # Seleciona sempre a planilha mais recente pela data de modificação
  arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
  df = pd.read_excel(arquivo_mais_recente)

  # Localiza a coluna de fase/status
  col_fase = None
  for col in ["Fase atual", "Status", "Fase", "status"]:
    if col in df.columns:
      col_fase = col
      break

  if col_fase is None:
    st.error("Coluna de status/fase não encontrada na planilha.")
    return None

  df["Fase_Normalizada"] = df[col_fase].astype(str).str.strip().str.lower()

  # Filtro estrito para status em andamento
  fases_alvo = [
      "acompanhamento de sinistro",
      "análise do incidente",
      "analise do incidente",
  ]
  df_filtrado = df[df["Fase_Normalizada"].isin(fases_alvo)].copy()

  return df_filtrado


df = carregar_dados_repositorio()

if df is None or df.empty:
  st.error(
      "⚠️ Nenhuma ocorrência em andamento encontrada ou planilha não localizada"
      " no repositório."
  )
  st.stop()

# ==========================================
# MAPEAMENTO DA COLUNA DE CC / OBRA
# ==========================================
col_cc = None
for col in df.columns:
  col_limpa = str(col).strip().lower()
  if col_limpa in ["cc", "c.c.", "c.c", "centro de custo", "centro de custos"]:
    col_cc = col
    break

# Se não achar exatamente "CC", usa a coluna de obra como alternativa
if not col_cc:
  for col in [
      "Informe a Obra a qual a ocorrencia está relacionada:",
      "Informe a obra ou endereço completo do ocorrido:",
  ]:
    if col in df.columns:
      col_cc = col
      break

# ==========================================
# 1. RESUMO EXECUTIVO (MÉTRICAS)
# ==========================================
st.subheader("1. Visão Geral da Carteira")

total_ocorrencias = len(df)
sinistros_abertos = len(df[df["Fase_Normalizada"] == "acompanhamento de sinistro"])
fase_analise = len(
    df[df["Fase_Normalizada"].str.contains("análise|analise", na=False)]
)

val_terceiro = (
    pd.to_numeric(
        df.get("Valor Indenizável (terceiro)", pd.Series(dtype=float)),
        errors="coerce",
    )
    .fillna(0)
    .sum()
)
val_segurado = (
    pd.to_numeric(
        df.get("Valor Indenizável", pd.Series(dtype=float)), errors="coerce"
    )
    .fillna(0)
    .sum()
)
total_valor = val_terceiro + val_segurado

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ocorrências em Andamento", f"{total_ocorrencias}")
col2.metric(
    "Sinistros Abertos",
    f"{sinistros_abertos}",
    f"{(sinistros_abertos/total_ocorrencias*100):.1f}%",
)
col3.metric(
    "Em Análise Prévia",
    f"{fase_analise}",
    f"{(fase_analise/total_ocorrencias*100):.1f}%",
)
col4.metric(
    "Indenização Estimada",
    f"R$ {total_valor:,.2f}".replace(",", "X")
    .replace(".", ",")
    .replace("X", "."),
)

st.divider()

# ==========================================
# 2. GARGALOS E PENDÊNCIAS
# ==========================================
st.subheader("2. Gargalos e Pendências Operacionais")

col_left, col_right = st.columns([1, 1])

with col_left:
  st.markdown("#### Distribuição por Fase")
  fig_fase = px.pie(
      df,
      names="Fase atual",
      hole=0.4,
      color_discrete_sequence=["#1f77b4", "#ff7f0e"],
  )
  st.plotly_chart(fig_fase, use_container_width=True)

with col_right:
  st.markdown("#### Detalhamento de Pendências")
  col_local = "Informe a obra ou endereço completo do ocorrido:"
  col_causa = "Informe a Causa"
  col_tipo = "Informe o tipo da ocorrencia"

  for idx, row in df.iterrows():
    fase = row.get("Fase atual", "N/A")
    titulo = row.get("Título", "Sem Título")
    comentario = str(row.get("Último comentário", "")).strip()
    cc_valor = row.get(col_cc, "Não informado") if col_cc else "Não informado"
    local = row.get(col_local, "Não informado")
    causa = row.get(col_causa, "Não informada")
    tipo = row.get(col_tipo, "")
    atualizado = row.get("Atualizado em", "-")

    with st.expander(f"📌 {titulo} — [{fase}]"):
      st.markdown(f"**CC / Obra:** {cc_valor}")
      st.markdown(f"**Local/Endereço:** {local}")
      st.markdown(f"**Causa:** {causa} ({tipo})")
      st.markdown(f"**Atualizado em:** {atualizado}")
      if comentario and comentario.lower() != "nan":
        st.info(f"**Anotações e Pendências:**\n\n{comentario}")
      else:
        st.write("*Sem comentários registrados no card.*")

st.divider()

# ==========================================
# 3. SINISTRALIDADE POR CC (OBRA) E CAUSAS
# ==========================================
st.subheader("3. Sinistralidade por Centro de Custo (CC) e Causas")

col_g1, col_g2 = st.columns(2)

with col_g1:
  if col_cc:
    cc_counts = (
        df[col_cc]
        .fillna("Não informado / Operacional")
        .value_counts()
        .reset_index()
    )
    cc_counts.columns = ["Centro de Custo (CC)", "Quantidade"]

    fig_cc = px.bar(
        cc_counts,
        x="Centro de Custo (CC)",
        y="Quantidade",
        title="Ocorrências por Centro de Custo (CC)",
        color="Quantidade",
        text="Quantidade",
    )
    st.plotly_chart(fig_cc, use_container_width=True)
  else:
    st.warning("Coluna 'CC' não encontrada na planilha.")

with col_g2:
  causas_counts = (
      df["Informe o tipo da ocorrencia"].fillna("Outros").value_counts().reset_index()
  )
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
  st.plotly_chart(fig_causas, use_container_width=True)

st.divider()

# ==========================================
# 4. TABELA GERAL DETALHADA
# ==========================================
st.subheader("4. Relação Geral de Processos em Andamento")

colunas_exibir = [
    "Título",
    "Fase atual",
    col_cc if col_cc else "Informe a Obra a qual a ocorrencia está relacionada:",
    "Informe a Causa",
    "Acionado seguro para ",
    "Número do sinistro (segurado)",
    "Número do sinistro (terceiro)",
    "Valor Indenizável (terceiro)",
    "Último comentário",
]
colunas_validas = [c for c in colunas_exibir if c and c in df.columns]

st.dataframe(
    df[colunas_validas].fillna("-"), use_container_width=True, hide_index=True
)
