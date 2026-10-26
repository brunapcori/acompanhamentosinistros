import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Painel Executivo de Sinistros",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Painel Executivo de Sinistros & Gestão de Risco")
st.markdown("Consolidação gerencial de processos em andamento extraídos do Pipefy.")

# Função para carregar os dados
@st.cache_data
def carregar_dados(uploaded_file=None):
    caminho_padrao = "Acompanhamento de sinistros em andamento 26102026.xlsx"
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif os.path.exists(caminho_padrao):
        df = pd.read_excel(caminho_padrao)
    else:
        return None
        
    # Localizar coluna de fase
    col_fase = None
    for col in ["Fase atual", "Status", "Fase", "status"]:
        if col in df.columns:
            col_fase = col
            break
            
    if col_fase is None:
        st.error("Coluna de status/fase não encontrada na planilha.")
        return None
        
    df["Fase_Normalizada"] = df[col_fase].astype(str).str.strip().str.lower()
    
    # Filtrar estritamente os status em andamento solicitados
    fases_alvo = ["acompanhamento de sinistro", "análise do incidente", "analise do incidente"]
    df_filtrado = df[df["Fase_Normalizada"].isin(fases_alvo)].copy()
    
    return df_filtrado

# Barra lateral
with st.sidebar:
    st.header("⚙️ Base de Dados")
    uploaded_file = st.file_uploader("Carregar nova planilha (.xlsx)", type=["xlsx", "xls"])
    st.info("Filtro ativo: apenas **Acompanhamento de Sinistro** e **Análise do Incidente**.")

df = carregar_dados(uploaded_file)

if df is None or df.empty:
    st.warning("⚠️ Nenhuma ocorrência em andamento encontrada ou o arquivo Excel não foi localizado. Por favor, anexe a planilha pelo menu lateral à esquerda.")
    st.stop()

# ==========================================
# 1. RESUMO EXECUTIVO (MÉTRICAS)
# ==========================================
st.subheader("1. Visão Geral da Carteira")

total_ocorrencias = len(df)
sinistros_abertos = len(df[df["Fase_Normalizada"] == "acompanhamento de sinistro"])
fase_analise = len(df[df["Fase_Normalizada"].str.contains("análise|analise", na=False)])

val_terceiro = pd.to_numeric(df.get("Valor Indenizável (terceiro)", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
val_segurado = pd.to_numeric(df.get("Valor Indenizável", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
total_valor = val_terceiro + val_segurado

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ocorrências em Andamento", f"{total_ocorrencias}")
col2.metric("Sinistros Abertos", f"{sinistros_abertos}", f"{(sinistros_abertos/total_ocorrencias*100):.1f}%")
col3.metric("Em Análise Prévia", f"{fase_analise}", f"{(fase_analise/total_ocorrencias*100):.1f}%")
col4.metric("Indenização Estimada", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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
        color_discrete_sequence=["#1f77b4", "#ff7f0e"]
    )
    st.plotly_chart(fig_fase, use_container_width=True)

with col_right:
    st.markdown("#### Detalhamento de Pendências")
    for idx, row in df.iterrows():
        fase = row.get("Fase atual", "N/A")
        titulo = row.get("Título", "Sem Título")
        comentario = str(row.get("Último comentário", "")).strip()
        
        with st.expander(f"📌 {titulo} — [{fase}]"):
            st.markdown(f"**Local/Endereço:** {row.get('Informe a obra ou endereço completo do ocorrido:', 'Não informado')}")
            st.markdown(f"**Causa:** {row.get('Informe a Causa', 'Não informada')} ({row.get('Informe o tipo da ocorrencia', '')})")
            st.markdown(f"**Atualizado em:** {row.get('Atualizado em', '-')}")
            if comentario and comentario.lower() != "nan":
                st.info(f"**Anotações e Pendências:**\n\n{comentario}")
            else:
                st.write("*Sem comentários registrados no card.*")

st.divider()

# ==========================================
# 3. SINISTRALIDADE POR OBRA E CAUSAS
# ==========================================
st.subheader("3. Sinistralidade por Obra e Causas")

col_g1, col_g2 = st.columns(2)

with col_g1:
    col_obra = "Informe a Obra a qual a ocorrencia está relacionada:"
    obra_counts = df[col_obra].fillna("Não informado / Operacional").value_counts().reset_index()
    obra_counts.columns = ["Obra / Locação", "Quantidade"]
    
    fig_obra = px.bar(
        obra_counts, 
        x="Obra / Locação", 
        y="Quantidade", 
        title="Ocorrências por Obra / Alocação",
        color="Quantidade",
        text="Quantidade"
    )
    st.plotly_chart(fig_obra, use_container_width=True)

with col_g2:
    causas_counts = df["Informe o tipo da ocorrencia"].fillna("Outros").value_counts().reset_index()
    causas_counts.columns = ["Tipo da Ocorrência", "Quantidade"]
    
    fig_causas = px.bar(
        causas_counts, 
        x="Tipo da Ocorrência", 
        y="Quantidade", 
        title="Principais Causas Identificadas",
        color="Quantidade",
        text="Quantidade",
        color_continuous_scale="Reds"
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
    "Informe a Obra a qual a ocorrencia está relacionada:", 
    "Informe a Causa",
    "Acionado seguro para ",
    "Número do sinistro (segurado)", 
    "Número do sinistro (terceiro)",
    "Valor Indenizável (terceiro)",
    "Último comentário"
]
colunas_validas = [c for c in colunas_exibir if c in df.columns]

st.dataframe(
    df[colunas_validas].fillna("-"),
    use_container_width=True,
    hide_index=True
)
