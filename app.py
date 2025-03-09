import streamlit as st
import PyPDF2
import difflib
import requests
from fpdf import FPDF
from io import BytesIO
import hashlib
import pandas as pd  # 🔥 Biblioteca para manipulação do arquivo CSV

# =============================
# 📋 Função para Salvar E-mails no CSV
# =============================
def salvar_email_csv(nome, email):
    dados = {"Nome": [nome], "Email": [email]}
    try:
        df = pd.read_csv("emails_registrados.csv")
        novo_df = pd.DataFrame(dados)
        df = pd.concat([df, novo_df], ignore_index=True)
    except FileNotFoundError:
        df = pd.DataFrame(dados)

    df.to_csv("emails_registrados.csv", index=False)
    st.success("✅ E-mail e nome registrados com sucesso!")

# =============================
# 🔐 Função para Gerar Código de Verificação
# =============================
def gerar_codigo_verificacao(texto):
    return hashlib.md5(texto.encode()).hexdigest()[:10].upper()

# =============================
# 📝 Função para Extrair Texto do PDF
# =============================
def extrair_texto_pdf(arquivo_pdf):
    leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
    texto = ""
    for pagina in leitor_pdf.pages:
        texto += pagina.extract_text() or ""
    return texto.strip()

# =============================
# 📊 Função para Calcular Similaridade
# =============================
def calcular_similaridade(texto1, texto2):
    seq_matcher = difflib.SequenceMatcher(None, texto1, texto2)
    return seq_matcher.ratio()

# =============================
# 🔎 Função para Buscar Artigos na API CrossRef
# =============================
def buscar_referencias_crossref(texto):
    query = "+".join(texto.split()[:10])  
    url = f"https://api.crossref.org/works?query={query}&rows=10"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao acessar a API da CrossRef: {e}")
        return []

    referencias = []
    for item in data.get("message", {}).get("items", []):
        titulo = item.get("title", ["Título não disponível"])[0]
        resumo = item.get("abstract", "")
        link = item.get("URL", "Link não disponível")
        referencias.append({"titulo": titulo, "resumo": resumo, "link": link})

    return referencias

# =============================
# 📄 Função para Gerar Relatório PDF
# =============================
def gerar_relatorio_pdf(referencias_com_similaridade, codigo_verificacao):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Relatório de Similaridade de Plágio", ln=True, align='C')
    pdf.ln(10)

    pdf.cell(200, 10, txt="Top 5 Referências encontradas:", ln=True)
    pdf.ln(5)

    soma_percentual = 0
    for i, (ref, perc, link) in enumerate(referencias_com_similaridade[:5], 1):
        soma_percentual += perc
        pdf.multi_cell(0, 10, f"{i}. {ref} - {perc*100:.2f}%\n{link}")
        pdf.ln(2)

    # Cálculo do plágio médio
    plágio_medio = (soma_percentual / 5) * 100
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Plágio médio: {plágio_medio:.2f}%", ln=True)

    # Código de verificação
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Código de Verificação: {codigo_verificacao}", ln=True)

    # Salvar PDF
    pdf_file_path = "/tmp/relatorio_plagio.pdf"
    pdf.output(pdf_file_path)

    return pdf_file_path

# =============================
# 💻 Interface do Streamlit
# =============================
if __name__ == "__main__":
    st.title("Verificador de Plágio - IA NICE - CrossRef")

    # Formulário para nome e e-mail
    st.subheader("📋 Registro de Usuário")
    nome = st.text_input("Nome completo")
    email = st.text_input("E-mail")

    if st.button("Salvar Dados"):
        if nome and email:
            salvar_email_csv(nome, email)
        else:
            st.warning("⚠️ Por favor, preencha todos os campos.")

    # Upload do PDF após registro
    arquivo_pdf = st.file_uploader("Faça upload de um arquivo PDF", type=["pdf"])

    if st.button("Processar PDF"):
        if arquivo_pdf is not None:
            texto_usuario = extrair_texto_pdf(arquivo_pdf)
            referencias = buscar_referencias_crossref(texto_usuario)

            referencias_com_similaridade = []
            for ref in referencias:
                texto_base = ref["titulo"] + " " + ref["resumo"]
                link = ref["link"]
                similaridade = calcular_similaridade(texto_usuario, texto_base)
                referencias_com_similaridade.append((ref["titulo"], similaridade, link))

            referencias_com_similaridade.sort(key=lambda x: x[1], reverse=True)

            if referencias_com_similaridade:
                st.subheader("Top 5 Referências encontradas:")
                for i, (titulo, perc, link) in enumerate(referencias_com_similaridade[:5], 1):
                    st.markdown(f"**{i}.** [{titulo}]({link}) - **{perc*100:.2f}%**")

                # Gerar código de verificação e salvar no session_state
                codigo_verificacao = gerar_codigo_verificacao(texto_usuario)
                st.session_state['codigo_verificacao'] = codigo_verificacao

                # Gerar e exibir link para download do relatório
                pdf_file = gerar_relatorio_pdf(referencias_com_similaridade, codigo_verificacao)
                with open(pdf_file, "rb") as f:
                    st.download_button("📄 Baixar Relatório de Plágio", f, "relatorio_plagio.pdf")

                # Exibir código de verificação para o usuário
                st.success(f"Código de verificação gerado: **{codigo_verificacao}**")
            else:
                st.warning("Nenhuma referência encontrada.")
        else:
            st.error("Por favor, carregue um arquivo PDF.")

    # Verificação de código
    st.header("Verificar Autenticidade")
    codigo_digitado = st.text_input("Digite o código de verificação:")

    if st.button("Verificar Código"):
        if 'codigo_verificacao' in st.session_state and codigo_digitado == st.session_state['codigo_verificacao']:
            st.success("✅ Documento Autêntico e Original!")
        else:
            st.error("❌ Código inválido ou documento falsificado.")
