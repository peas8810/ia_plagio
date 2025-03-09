import streamlit as st
import requests
import PyPDF2
import difflib
from fpdf import FPDF
from io import BytesIO
import hashlib

# 🔗 URL da API gerada no Google Sheets
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbw-FHvvPe5vv98AYQBmKAlt68TVH0S_vdaHA5GfVNgECdfR1F0xlYyzbsdo6Wo0Nas/exec"

# =============================
# 📋 Função para Salvar E-mails no Google Sheets
# =============================
def salvar_email_google_sheets(nome, email):
    dados = {
        "nome": nome,
        "email": email
    }
    try:
        response = requests.post(URL_GOOGLE_SHEETS, json=dados)
        if response.text.strip() == "Sucesso":
            st.success("✅ E-mail e nome registrados com sucesso!")
        else:
            st.error(f"❌ Erro ao salvar dados no Google Sheets: {response.text}")
    except Exception as e:
        st.error(f"❌ Erro na conexão com o Google Sheets: {e}")

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
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, "Relatório de Similaridade de Plágio", ln=True, align='C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 10, body)
        self.ln()

def gerar_relatorio_pdf(referencias_com_similaridade, codigo_verificacao):
    pdf = PDF()
    pdf.add_page()

    pdf.chapter_title("Top 5 Referências encontradas:")

    soma_percentual = 0
    for i, (ref, perc, link) in enumerate(referencias_com_similaridade[:5], 1):
        soma_percentual += perc
        pdf.chapter_body(f"{i}. {ref} - {perc*100:.2f}%\n{link}")

    plágio_medio = (soma_percentual / 5) * 100
    pdf.chapter_body(f"Plágio médio: {plágio_medio:.2f}%")

    pdf.chapter_body(f"Código de Verificação: {codigo_verificacao}")

    pdf_file_path = "/tmp/relatorio_plagio.pdf"
    pdf.output(pdf_file_path, 'F')

    return pdf_file_path

# =============================
# 💻 Interface do Streamlit
# =============================
if __name__ == "__main__":
    st.title("Verificador de Plágio - IA NICE - CrossRef")

    st.subheader("📋 Registro de Usuário")
    nome = st.text_input("Nome completo")
    email = st.text_input("E-mail")

    if st.button("Salvar Dados"):
        if nome and email:
            salvar_email_google_sheets(nome, email)
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
