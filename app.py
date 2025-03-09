import streamlit as st
import PyPDF2
import difflib
import requests
from fpdf import FPDF
from io import BytesIO
import hashlib
import gspread
import json
from google.oauth2.service_account import Credentials

# =============================
# 🔒 Configuração do Google Sheets
# =============================
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Carregar credenciais do secrets manager
creds_dict = json.loads(st.secrets["gcp_service_account"])
CREDENTIALS = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

# Conectar ao Google Sheets
cliente = gspread.authorize(CREDENTIALS)
SHEET_ID = "1xf00JCVioNn1q5oa_RQyQgXp2Qo1Hs0hUedIb7-xQRw"
sheet = cliente.open_by_key(SHEET_ID).sheet1

# =============================
# 📋 Funções Auxiliares
# =============================

# Registrar dados na planilha
def registrar_dados(nome, email):
    sheet.append_row([nome, email])

# Gerar um código de verificação único
def gerar_codigo_verificacao(texto):
    return hashlib.md5(texto.encode()).hexdigest()[:10].upper()

# Extrair texto de um arquivo PDF
def extrair_texto_pdf(arquivo_pdf):
    leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
    return "".join([pagina.extract_text() or "" for pagina in leitor_pdf.pages]).strip()

# Calcular a similaridade entre dois textos
def calcular_similaridade(texto1, texto2):
    return difflib.SequenceMatcher(None, texto1, texto2).ratio()

# Buscar artigos na API da CrossRef
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

    referencias = [
        {
            "titulo": item.get("title", ["Título não disponível"])[0],
            "resumo": item.get("abstract", ""),
            "link": item.get("URL", "Link não disponível"),
        }
        for item in data.get("message", {}).get("items", [])
    ]

    return referencias

# Gerar relatório PDF
def gerar_relatorio_pdf(referencias_com_similaridade, codigo_verificacao):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, "Relatório de Similaridade de Plágio", ln=True, align='C')
    pdf.ln(10)

    pdf.cell(200, 10, "Top 5 Referências encontradas:", ln=True)
    pdf.ln(5)

    soma_percentual = sum(perc for _, perc, _ in referencias_com_similaridade[:5])
    for i, (ref, perc, link) in enumerate(referencias_com_similaridade[:5], 1):
        pdf.multi_cell(0, 10, f"{i}. {ref} - {perc*100:.2f}%\n{link}")
        pdf.ln(2)

    plágio_medio = (soma_percentual / 5) * 100
    pdf.ln(5)
    pdf.cell(200, 10, f"Plágio médio: {plágio_medio:.2f}%", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, f"Código de Verificação: {codigo_verificacao}", ln=True)

    pdf_file_path = "/tmp/relatorio_plagio.pdf"
    pdf.output(pdf_file_path)

    return pdf_file_path

# =============================
# 💻 Interface do Streamlit
# =============================
if __name__ == "__main__":
    st.title("🔎 Verificador de Plágio - IA NICE - CrossRef")

    # 📋 Formulário para coleta de dados
    with st.form("formulario_usuario"):
        nome = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        submit_button = st.form_submit_button("Enviar")

    if submit_button:
        if nome and email:
            registrar_dados(nome, email)
            st.success("✅ Dados registrados com sucesso! Agora você pode fazer o upload do PDF.")
        else:
            st.error("❌ Por favor, preencha todos os campos.")

    # 📂 Upload do PDF após registro
    arquivo_pdf = st.file_uploader("Faça upload de um arquivo PDF", type=["pdf"])

    if st.button("Processar PDF") and nome and email:
        if arquivo_pdf is not None:
            texto_usuario = extrair_texto_pdf(arquivo_pdf)
            referencias = buscar_referencias_crossref(texto_usuario)

            referencias_com_similaridade = [
                (ref["titulo"], calcular_similaridade(texto_usuario, ref["titulo"] + " " + ref["resumo"]), ref["link"])
                for ref in referencias
            ]

            referencias_com_similaridade.sort(key=lambda x: x[1], reverse=True)

            if referencias_com_similaridade:
                st.subheader("📚 Top 5 Referências encontradas:")
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
                st.warning("⚠️ Nenhuma referência encontrada.")
        else:
            st.error("❌ Por favor, carregue um arquivo PDF.")
