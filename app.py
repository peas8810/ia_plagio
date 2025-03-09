import streamlit as st

if __name__ == "__main__":
    st.title("Verificador de Plágio - IA NICE")

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
