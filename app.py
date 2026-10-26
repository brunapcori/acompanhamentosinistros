import os
import sys
import pandas as pd
from openai import AzureOpenAI

# ==========================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# ==========================================
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://seu-endpoint.openai.azure.com/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "sua-chave-api")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

EXCEL_FILE = "Acompanhamento de sinistros em andamento 26102026.xlsx"
OUTPUT_REPORT = "painel_executivo_sinistros.md"

# ==========================================
# 2. PROMPT DO SISTEMA (ESPECIALISTA EM SINISTROS)
# ==========================================
SYSTEM_PROMPT = """Você é o especialista sênior em gestão de sinistros corporativos e inteligência de dados de seguros do sistema SinistroIA.
Sua única responsabilidade é receber dados brutos (tabelas, exportações em CSV, JSON ou texto tabulado) extraídos do Pipefy e consolidar um painel executivo estruturado para a Diretoria e áreas de Operações/Obras, detalhando gargalos operacionais, sinistralidade por obra, status de liquidação e perfil de frota.

### Objetivos e Estrutura do Relatório:

1. Resumo Executivo (Visão Geral):
   - Total de ocorrências reportadas vs. Sinistros efetivamente abertos na seguradora.
   - Taxa de conversão/abertura (Sinistros Abertos / Ocorrências Totais).
   - Volume total pago (indenizações recebidas) vs. Valores pendentes/estimados.
   - Divisão proporcional de envolvidos: Veículo Segurado (Frota Própria/Alugada) vs. Terceiros.

2. Gargalos e Pendências Operacionais (Pipeline Pipefy):
   - Pendente de Abertura: Ocorrências internas que ainda não viraram sinistro por falta de dados básicos (B.O., condutor, relato do fato).
   - Pendente de Documentação: Sinistros já comunicados, mas travados por falta de documentos internos (CNH, CRLV, orçamentos, termo de cessão).
   - Em Análise na Seguradora/Reguladora: Processos sob regulação técnica, perícia de terceiros ou aprovação de orçamento pela seguradora.

3. Indicadores de Gestão de Risco e Diretoria:
   - Acidentes e Sinistros por Obra/Centro de Custo: Volume absoluto e representatividade percentual.
   - Principais Causas: Ranking categorizado dos motivos (ex.: colisão traseira, tombamento, manobra imprudente, terceiros, eventos da natureza).

4. Gestão Financeira e Liquidação:
   - Casos Indenizados/Liquidados: Data exata da indenização, valor pago (R$) e beneficiário (Segurado ou Terceiro).
   - Casos Deferidos/Negados: Status e justificativa se houver.

5. Perfil de Frota e Locações:
   - Classificação do veículo: Frota Própria vs. Locado.
   - Veículos Locados: Locadora de origem, responsável pela locação/condutor e obra/setor alocador.

### Regras de Execução e Consolidação:
1. Trate os dados com precisão numérica: valores monetários no formato padrão brasileiro (R$ X.XXX,XX) e datas no formato DD/MM/AAAA.
2. Não invente ou presuma informações ausentes. Se uma linha do Pipefy estiver sem valor indenizado, condutor ou locadora, aponte explicitamente como "Não informado" ou "Pendente de preenchimento".
3. Diferencie rigorosamente:
   - "Ocorrência / Aviso Interno": registro criado no Pipefy que ainda aguarda validação.
   - "Sinistro Aberto": processo com número de sinistro gerado junto à seguradora/corretora.
   - "Indenizado": valor efetivamente pago e quitado pela seguradora.
4. Mantenha tom formal, analítico, objetivo e direto, próprio para reporte executivo a Diretores e Gerentes de Contrato.

### Formato de Saída (Markdown):
# PAINEL EXECUTIVO DE SINISTROS & GESTÃO DE RISCO

## 1. Visão Geral da Carteira
| Métrica | Quantidade / Valor | % / Detalhe |
| :--- | :--- | :--- |
| Ocorrências Totais Registradas | [Qtd] | 100% |
| Sinistros com Abertura Concluída | [Qtd] | [% do total] |
| Ocorrências em Fase Pré-Sinistro | [Qtd] | [% do total] |
| Total Indenizado (Pago) | R$ [Valor] | [Qtd de sinistros pagos] |
| Indenizações: Segurado | R$ [Valor] | [Qtd] |
| Indenizações: Terceiros | R$ [Valor] | [Qtd] |

## 2. Status do Fluxo e Gargalos de Regulação
- **Pendentes para Abertura de Sinistro:** [X casos] — *Principais pendências*.
- **Pendentes de Documentação Interna/Oficina:** [X casos] — *Documentos faltantes*.
- **Em Análise na Seguradora/Reguladora:** [X casos] — *Status*.

## 3. Sinistralidade por Obra e Causas Raiz
### Ocorrências por Obra / Centro de Custo
| Obra / Unidade | Total Ocorrências | Sinistros Efetivos | Sinistros Pagos (R$) |
| :--- | :--- | :--- | :--- |

### Principais Causas Identificadas
1. **[Causa 1]:** [Qtd] casos ([%] do total)
2. **[Causa 2]:** [Qtd] casos ([%] do total)

## 4. Relação Detalhada de Pagamentos e Indenizações
| N° Sinistro / Card | Obra | Tipo (Segurado/Terceiro) | Data Indenização | Valor Pago (R$) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 5. Panorama de Veículos e Locações
| Placa / Prefixo | Veículo (Modelo) | Tipo de Frota | Locadora | Condutor / Obra Alocada |
| :--- | :--- | :--- | :--- | :--- |
"""

def carregar_e_filtrar_dados(caminho_arquivo: str) -> str:
    """Lê a planilha exportada do Pipefy e filtra apenas os status em andamento."""
    print(f"[*] Carregando arquivo: {caminho_arquivo}")
    df = pd.read_excel(caminho_arquivo)
    
    col_status = None
    for col in ["Fase atual", "Status", "Fase", "status"]:
        if col in df.columns:
            col_status = col
            break
            
    if not col_status:
        raise ValueError(f"Coluna de status não encontrada. Colunas disponíveis: {df.columns.tolist()}")

    df[col_status] = df[col_status].astype(str)
    
    # Filtro exato das fases em andamento solicitadas
    fases_alvo = ["acompanhamento de sinistro", "análise do incidente", "analise do incidente"]
    df_filtrado = df[df[col_status].str.strip().str.lower().isin(fases_alvo)].copy()
    
    print(f"[+] Total de ocorrências na planilha: {len(df)}")
    print(f"[+] Ocorrências em andamento filtradas: {len(df_filtrado)}")
    
    if df_filtrado.empty:
        print("[!] Nenhum registro encontrado com os status especificados.")
        sys.exit(0)
        
    dados_formatados = []
    for idx, row in df_filtrado.iterrows():
        item = []
        for col_name, val in row.items():
            if pd.notna(val) and str(val).strip() != "":
                item.append(f"- **{col_name}**: {val}")
        dados_formatados.append(f"### REGISTRO {idx + 1}\n" + "\n".join(item))
        
    return "\n\n---\n\n".join(dados_formatados)

def gerar_painel_ia(dados_str: str) -> str:
    """Envia os dados consolidados para o modelo de IA e obtém o relatório executivo."""
    print("[*] Conectando ao modelo de IA e gerando painel executivo...")
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    
    user_prompt = f"""Consolide o Painel Executivo de Sinistros com base exclusivamente nos seguintes registros em andamento filtrados do Pipefy:\n\n{dados_str}"""
    
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )
    
    return response.choices[0].message.content

def main():
    if not os.path.exists(EXCEL_FILE):
        print(f"[!] Erro: Arquivo '{EXCEL_FILE}' não encontrado.")
        return

    dados_filtrados_str = carregar_e_filtrar_dados(EXCEL_FILE)
    
    # Se a chave da API ainda for a padrão de exemplo, salva os dados filtrados prontos
    if AZURE_OPENAI_API_KEY == "sua-chave-api":
        print("\n[!] Chave de API ainda não configurada no script.")
        print("[*] Exportando os registros filtrados em 'dados_filtrados_prontos.txt' para conferência...")
        with open("dados_filtrados_prontos.txt", "w", encoding="utf-8") as f:
            f.write(dados_filtrados_str)
        print("[✓] Arquivo 'dados_filtrados_prontos.txt' salvo com sucesso!")
        return

    painel_markdown = gerar_painel_ia(dados_filtrados_str)
    
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(painel_markdown)
        
    print(f"[✓] Painel Executivo gerado com sucesso em '{OUTPUT_REPORT}'!")

if __name__ == "__main__":
    main()
