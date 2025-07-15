import streamlit as st
import pandas as pd
import os
from openai import OpenAI
import io
import contextlib
import io as io_sys

# 🔐 Chave da OpenAI vinda de Streamlit Cloud
api_key = st.secrets["OPENAI_API_KEY"]

# Testa se openpyxl está instalado (caso queira usar .xlsx futuramente)
try:
    import openpyxl
except ImportError:
    st.error("❌ A biblioteca 'openpyxl' é necessária para ler arquivos .xlsx. Adicione 'openpyxl' no requirements.txt.")
    st.stop()

# Validação da chave
if not api_key:
    st.error("❌ Chave da API OpenAI não encontrada nos segredos.")
    st.stop()

api_key = api_key.strip().replace('\n', '').replace('\r', '')

if len(api_key) > 200 or len(api_key) < 50:
    st.error(f"⚠️ Chave com tamanho suspeito: {len(api_key)} caracteres")
    st.stop()

# Cliente OpenAI
client = OpenAI(api_key=api_key)

# Teste de conexão com a API
try:
    test_response = client.models.list()
    st.sidebar.success("✅ API OpenAI funcionando")
except Exception as e:
    st.sidebar.error(f"❌ Erro na API: {str(e)}")

# Interface Streamlit
st.set_page_config(page_title="Análise de Dados com IA", layout="centered")
st.title("📊 Análise de Dados em Linguagem Natural")
st.write("Este app usa o arquivo fixo `dados_mercurio.csv`. Pergunte algo como: **Quantas vendas com ovos?**")

# Carregamento da base de dados fixa
try:
    df = pd.read_csv("supermercado_vendas.csv")
    st.success("✅ Base de dados carregada com sucesso!")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"Erro ao carregar a base de dados: {e}")
    st.stop()

# Entrada do usuário
prompt = st.text_input("💬 Escreva sua pergunta:",
                       placeholder="Ex: Quantas vendas com 'ovos'?")

# Análise com IA
if st.button("🔎 Analisar com IA") and df is not None and prompt:
    with st.spinner("🔧 Consultando a IA..."):
        saida_print = ""  # Inicializa para evitar NameError
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

            # Remove markdown se vier com ```
            if codigo.startswith("```"):
                codigo = codigo.replace("```python", "").replace("```", "").strip()

            # Garante compatibilidade de tipos
            usa_str = ".str" in codigo
            df_exec = df.copy()
            if usa_str:
                df_exec = df_exec.astype(str)

            # Ambiente de execução
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
