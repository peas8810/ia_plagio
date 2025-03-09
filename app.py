import PyPDF2
import difflib
import requests
from fpdf import FPDF
from io import BytesIO
import base64
import ipywidgets as widgets
from IPython.display import display, HTML
import os

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
    query = "+".join(texto.split()[:10])  # Usar as primeiras palavras como query
    url = f"https://api.crossref.org/works?query={query}&rows=10"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API da CrossRef: {e}")
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
    if not referencias_com_similaridade:
        display(HTML("<p>Não foram encontradas referências para gerar o relatório.</p>"))
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Relatório de Similaridade de Plágio", ln=True, align='C')
    pdf.ln(10)

    pdf.cell(200, 10, txt="Artigo com maior percentual de similaridade:", ln=True)
    pdf.set_text_color(0, 0, 255)
    pdf.multi_cell(0, 10, referencias_com_similaridade[0][2])
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    pdf.cell(200, 10, txt="Top 5 referências com maior percentual de plágio:", ln=True)
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

    # Salvar o relatório PDF na pasta local
    pdf_file_path = 'relatorio_plagio.pdf'
    pdf.output(pdf_file_path)

    # Gerar link de download
    with open(pdf_file_path, "rb") as file:
        pdf_data = file.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

    display(HTML(f'<a href="data:application/pdf;base64,{pdf_base64}" download="relatorio_plagio.pdf">Clique aqui para baixar o relatório</a>'))

# Função para processar o arquivo PDF carregado
def processar_pdf(uploaded_file):
    if uploaded_file:
        for nome_arquivo, arquivo_info in uploaded_file.items():
            texto_usuario = extrair_texto_pdf(BytesIO(arquivo_info['content']))

        referencias = buscar_referencias_crossref(texto_usuario)

        referencias_com_similaridade = []
        for ref in referencias:
            texto_base = ref["titulo"] + " " + ref["resumo"]
            link = ref["link"]
            similaridade = calcular_similaridade(texto_usuario, texto_base)
            referencias_com_similaridade.append((ref["titulo"], similaridade, link))

        referencias_com_similaridade.sort(key=lambda x: x[1], reverse=True)

        resultado_texto = "Referências com maior percentual de plágio:\n\n"
        for i, (ref, perc, link) in enumerate(referencias_com_similaridade[:5], 1):
            resultado_texto += f"{i}. {ref} - {perc*100:.2f}% - {link}\n"

        resultado_label.value = resultado_texto

        gerar_relatorio_pdf(referencias_com_similaridade)

# Interface do usuário
botao_carregar = widgets.FileUpload(accept='.pdf', multiple=False)
resultado_label = widgets.Label(value="Aguardando upload do arquivo...")

botao_processar = widgets.Button(description="Processar PDF")
botao_processar.on_click(lambda b: processar_pdf(botao_carregar.value))

display(botao_carregar, botao_processar, resultado_label)
