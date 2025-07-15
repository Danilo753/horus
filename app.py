import streamlit as st
import pandas as pd
import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
import logging
import contextlib
import io as io_sys

load_dotenv()
st.set_page_config(page_title="Horus - IA para Análise de Dados", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>body {background-color: #0e1117; color: white;} .stTextInput>div>div>input {color:white;}</style>""", unsafe_allow_html=True)

# Logo
logo_path = Path("naga_logo.png")
if logo_path.exists():
    st.image(str(logo_path), width=80)
else:
    st.warning("⚠️ Logo não encontrada. Verifique se 'naga_logo.png' está na mesma pasta do app.")

st.title("📊 Horus - Análise de Dados com IA")
st.write("Faça perguntas como: *Qual a média de vendas de arroz?* ou *Quantas vezes o cliente João comprou?*")

# Chave da API
api_key = st.secrets["OPENAI_API_KEY"]

try:
    import openpyxl
except ImportError:
    st.error("❌ A biblioteca 'openpyxl' é necessária para ler arquivos .xlsx. Adicione 'openpyxl' no requirements.txt.")
    st.stop()

if not api_key:
    st.error("❌ Chave da API OpenAI não encontrada nos segredos.")
    st.stop()

api_key = api_key.strip().replace('\n', '').replace('\r', '')
if len(api_key) > 200 or len(api_key) < 50:
    st.error(f"⚠️ Chave com tamanho suspeito: {len(api_key)} caracteres")
    st.stop()

client = OpenAI(api_key=api_key)

try:
    test_response = client.models.list()
    st.sidebar.success("✅ API OpenAI funcionando")
except Exception as e:
    st.sidebar.error(f"❌ Erro na API: {str(e)}")

# Carregamento da base de dados
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

# Sugestões fixas
st.markdown("📌 Exemplos de perguntas úteis:")
st.markdown("""
- Quantas vendas de **arroz**?
- Qual o cliente com mais compras?
- Qual o total vendido em **fevereiro**?
- Média de preço por produto?
""")

# Análise
if st.button("🔎 Analisar com IA") and df is not None and prompt:
    with st.spinner("🔧 Consultando a IA..."):
        saida_print = ""
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

            with st.expander("👨‍💻 Ver código gerado"):
                st.code(codigo, language='python')

        except Exception as e:
            logging.error(f"Erro ao executar a IA: {e}")
            st.error("⚠️ A análise não pôde ser realizada com os dados fornecidos.")

            with st.expander("❓ Dicas para fazer boas perguntas", expanded=False):
                st.markdown("""
- Use termos que existam na tabela (como *produto*, *cliente*, *quantidade*, *venda*, etc.)
- Seja direto: ex: **Qual a média de vendas de arroz?**
- Evite perguntas muito amplas como: *Analise tudo*, *Gere insights completos*, etc.
- Tente incluir **nomes reais de colunas ou valores** existentes na base.
- Exemplos úteis:
    - **Quantas vendas tiveram 'leite'?**
    - **Qual o total vendido pelo cliente João?**
    - **Quantas compras foram feitas em março?**
""")
            st.info("💡 Reformule sua pergunta com mais clareza e tente novamente.")
