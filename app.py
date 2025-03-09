import streamlit as st

if __name__ == "__main__":
    st.title("Verificador de Plágio - API CrossRef")

    arquivo_pdf = st.file_uploader("Faça upload de um arquivo PDF", type=["pdf"])

    if st.button("Processar PDF"):
        if arquivo_pdf is not None:
            texto_usuario = extrair_texto_pdf(arquivo_pdf)
            referencias = buscar_referencias_crossref(texto_usuario)

            if referencias:
                st.subheader("Top 5 Referências encontradas:")
                for i, (titulo, link) in enumerate(referencias[:5], 1):
                    st.markdown(f"**{i}.** [{titulo}]({link})")
            else:
                st.warning("Nenhuma referência encontrada.")
        else:
            st.error("Por favor, carregue um arquivo PDF.")
