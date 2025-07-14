import streamlit as st
import pandas as pd
import os
from openai import OpenAI
import io
import contextlib
import io as io_sys

# 🔐 Chave da OpenAI vinda de Streamlit Cloud
api_key = st.secrets["OPENAI_API_KEY"]

# Testa se openpyxl está instalado (para arquivos .xlsx)
try:
    import openpyxl
except ImportError:
    st.error("❌ A biblioteca 'openpyxl' é necessária para ler arquivos .xlsx. Adicione 'openpyxl' no requirements.txt.")
    st.stop()

# Valida a chave
if not api_key:
    st.error("❌ Chave da API OpenAI não encontrada nos segredos.")
    st.stop()

api_key = api_key.strip().replace('\n', '').replace('\r', '')

if len(api_key) > 200 or len(api_key) < 50:
    st.error(f"⚠️ Chave com tamanho suspeito: {len(api_key)} caracteres")
    st.stop()

# Cliente OpenAI
client = OpenAI(api_key=api_key)

# Teste simples da API
try:
    test_response = client.models.list()
    st.sidebar.success("✅ API OpenAI funcionando")
except Exception as e:
    st.sidebar.error(f"❌ Erro na API: {str(e)}")

# Configuração inicial
st.set_page_config(page_title="Análise de Dados com IA", layout="centered")
st.title("📊 Análise de Dados em Linguagem Natural")
st.write("Envie **um ou mais arquivos** (.csv, .xlsx, .json...) e pergunte algo como: **Quantas vendas com ovos?**")

try:
    df = pd.read_csv("dados_mercurio.csv")  # ou pd.read_excel("dados_vendas.xlsx")
    st.success("✅ Base de dados carregada com sucesso!")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"Erro ao carregar a base de dados: {e}")
    st.stop()

# Função para corrigir CSVs com IA
def limpar_csv_com_ia(conteudo_csv: str) -> str:
    prompt = (
        "Corrija o seguinte CSV desalinhado ou com erro e retorne apenas o CSV corrigido separado por ponto e vírgula:\n\n"
        f"{conteudo_csv}"
    )
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
    except Exception as e:
        st.error(f"Erro na API durante limpeza CSV: {e}")
        return conteudo_csv
    return resposta.choices[0].message.content.strip()

# Carregador de arquivos
def carregar_arquivo(uploaded_file, ext):
    try:
        if ext == ".csv":
            try:
                return pd.read_csv(uploaded_file, sep=None, engine="python")
            except Exception:
                st.warning(f"⚠️ Erro no arquivo {uploaded_file.name}. Tentando corrigir com IA...")
                conteudo = uploaded_file.read().decode("utf-8")
                corrigido = limpar_csv_com_ia(conteudo)
                return pd.read_csv(io.StringIO(corrigido), sep=";")
        elif ext == ".txt":
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        elif ext == ".tsv":
            return pd.read_csv(uploaded_file, delimiter="\t")
        elif ext == ".xlsx":
            return pd.read_excel(uploaded_file)
        elif ext == ".json":
            return pd.read_json(uploaded_file)
        else:
            st.error("❌ Formato não suportado.")
            return None
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# Processa os arquivos
dfs = []
if uploaded_files:
    for file in uploaded_files:
        ext = os.path.splitext(file.name)[-1].lower()
        df_temp = carregar_arquivo(file, ext)
        if df_temp is not None:
            dfs.append(df_temp)

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        st.success(f"✅ {len(dfs)} arquivo(s) carregado(s) e unificado(s) com sucesso!")
        st.dataframe(df.head())

# Entrada do usuário
prompt = st.text_input("💬 Escreva sua pergunta:",
                       placeholder="Ex: Quantas vendas com 'ovos'?")

# Análise com IA
if st.button("🔎 Analisar com IA") and df is not None and prompt:
    with st.spinner("🔧 Consultando a IA..."):
        try:
            amostra_csv = df.head(20).to_csv(index=False)
            prompt_analise = (
                f"Você é um assistente Python. Gere apenas código Python (sem explicações nem markdown) "
                f"que responda à solicitação abaixo, usando o DataFrame `df` com os dados:\n\n"
                f"{amostra_csv}\n\n"
                f"Solicitação: {prompt}"
            )

            resposta = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_analise}],
                temperature=0.3,
                max_tokens=1000
            )

            codigo = resposta.choices[0].message.content.strip()

            if codigo.startswith("```"):
                codigo = codigo.replace("```python", "").replace("```", "").strip()

            usa_str = ".str" in codigo
            df_exec = df.copy()
            if usa_str:
                df_exec = df_exec.astype(str)

            exec_env = {"df": df_exec, "pd": pd}
            buffer = io_sys.StringIO()

            with contextlib.redirect_stdout(buffer):
                exec("resultado = " + codigo if "=" not in codigo else codigo, exec_env)

            resultado_exec = exec_env.get("resultado", None)
            saida_print = buffer.getvalue().strip()

            st.success("✅ Resultado da análise:")
            if resultado_exec is not None:
                st.write(resultado_exec)
            elif saida_print:
                st.text(saida_print)
            else:
                st.info("⚠️ A análise foi executada, mas não houve retorno visível.")

        except Exception as e:
            st.error(f"❌ Erro ao executar o código da IA:\n\n{e}")
