import streamlit as st
import PyPDF2
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
import difflib
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
    pdf.cell(
