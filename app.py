import streamlit as st
import PyPDF2
import difflib
import requests
from fpdf import FPDF
from io import BytesIO

# Função para extrair texto de um arquivo PDF
def extrair_texto_pdf(arquivo_pdf):
    leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
    texto = ""
    for pagina in leitor_pdf.pages:
        texto += pagina.extract_text() or ""
    return texto.strip()

# Função para calcular a similaridade entre dois textos
def calcular_similaridade(texto1, texto2):
    seq_matcher = difflib.SequenceMatcher(None, texto1, texto2)
    return seq_matcher.ratio()

# Função para buscar artigos na API da CrossRef
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

# Função para gerar relatório PDF
def gerar_relatorio_pdf(referencias_com_similaridade):
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

    # Salvar PDF
    pdf_file_path = "/tmp/relatorio_plagio.pdf"
    pdf.output(pdf_file_path)

    return pdf_file_path

# Interface do Streamlit
if __name__ == "__main__":
    st.title("Verificador de Plágio - IA NICE - CrossRef")

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

                # Cálculo do plágio médio
                plágio_medio = (sum(perc for _, perc, _ in referencias_com_similaridade[:5]) / 5) * 100
                st.subheader(f"**Plágio médio: {plágio_medio:.2f}%**")

                # Gerar e exibir link para download do relatório
                pdf_file = gerar_relatorio_pdf(referencias_com_similaridade)
                with open(pdf_file, "rb") as f:
                    st.download_button("📄 Baixar Relatório de Plágio", f, "relatorio_plagio.pdf")
            else:
                st.warning("Nenhuma referência encontrada.")
        else:
            st.error("Por favor, carregue um arquivo PDF.")
