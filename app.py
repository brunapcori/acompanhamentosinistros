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

# Estilização CSS para visual executivo
st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)


# Leitura direta da planilha mais recente do repositório (sem cache bloqueante)
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
    col_norm = str(col).strip().lower()
    if col_norm in ["fase atual", "status", "fase"]:
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

# Cabeçalho Principal e Indicador da Planilha Ativa
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
# IDENTIFICAÇÃO DINÂMICA DA COLUNA CC / OBRA
# ==========================================
col_cc = None
for col in df.columns:
  c_limpo = str(col).strip().lower()
  if c_limpo in ["cc", "c.c.", "c.c", "centro de custo", "centro de custos"]:
    col_cc = col
    break

if not col_cc:
  for col in df.columns:
    c_limpo = str(col).strip().lower()
    if "informe a obra a qual" in c_limpo or "obra relacionada" in c_limpo:
      col_cc = col
      break

if not col_cc:
  for col in df.columns:
    c_limpo = str(col).strip().lower()
    if "obra ou endereço" in c_limpo or "obra" in c_limpo:
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
m4.metric(
    "Indenização Estimada",
    f"R$ {total_valor:,.2f}".replace(",", "X")
    .replace(".", ",")
    .replace("X", "."),
)

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
  st.markdown("#### Detalhamento de Pendências Registradas")
  col_local = "Informe a obra ou endereço completo do ocorrido:"
  col_causa = "Informe a Causa"
  col_tipo = "Informe o tipo da ocorrencia"

  for idx, row in df.iterrows():
    fase = row.get("Fase atual", "N/A")
    titulo = row.get("Título", f"Ocorrência #{idx + 1}")
    comentario = str(row.get("Último comentário", "")).strip()

    cc_val = row.get(col_cc, "Não informado") if col_cc else "Não informado"
    if (
        pd.isna(cc_val)
        or str(cc_val).strip() == ""
        or str(cc_val).lower() == "nan"
    ):
      cc_val = "Não informado / Operacional"

    local_val = row.get(col_local, "Não informado")
    causa_val = row.get(col_causa, "Não informada")
    tipo_val = row.get(col_tipo, "")
    atualizado_val = row.get("Atualizado em", "-")

    with st.expander(f"📌 {titulo} — [{fase}]"):
      st.markdown(f"**CC / Obra:** {cc_val}")
      st.markdown(f"**Local/Endereço:** {local_val}")
      st.markdown(f"**Causa / Tipo:** {causa_val} ({tipo_val})")
      st.markdown(f"**Atualizado em:** {atualizado_val}")
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
    serie_cc = (
        df[col_cc]
        .fillna("Não informado / Operacional")
        .astype(str)
        .str.strip()
    )
    serie_cc = serie_cc.replace(
        {"nan": "Não informado / Operacional", "": "Não informado / Operacional"}
    )
    cc_counts = serie_cc.value_counts().reset_index()
    cc_counts.columns = ["Centro de Custo (CC)", "Quantidade"]

    fig_cc = px.bar(
        cc_counts,
        x="Centro de Custo (CC)",
        y="Quantidade",
        title="Ocorrências por Centro de Custo (CC) / Obra",
        color="Quantidade",
        text="Quantidade",
        color_continuous_scale="Blues",
    )
    fig_cc.update_layout(
        xaxis_tickangle=-25, margin=dict(t=40, b=60, l=10, r=10)
    )
    st.plotly_chart(fig_cc, use_container_width=True)
  else:
    st.warning("Coluna 'CC' ou de Obra não localizada para gerar o gráfico.")

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
# 4. TABELA GERAL DETALHADA
# ==========================================
st.subheader("4. Relação Geral de Processos em Andamento")

colunas_desejadas = [
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
colunas_validas = [c for c in colunas_desejadas if c and c in df.columns]

st.dataframe(
    df[colunas_validas].fillna("-"), use_container_width=True, hide_index=True
)
