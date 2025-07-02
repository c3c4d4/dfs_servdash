import streamlit as st

st.set_page_config(
    page_title="Chamados de Serviços",
    page_icon="🛠️",
)

st.write("# Bem-vindo ao Dashboard de Chamados de Serviços! 🛠️")

st.sidebar.success("Selecione uma página acima.")

st.markdown(
    """
    Este é um dashboard interativo para análise de chamados de serviços.
    
    **👈 Selecione uma página no menu lateral** para visualizar diferentes análises e relatórios.
    
    ### Sobre
    - Projeto do time de Serviços - Dover Fueling Solutions
    - Contato: [Cauã Almeida (BI)](mailto:c-calmeida@doverfs.com), [Fernanda Barbieri (Gerente)](mailto:fernanda.barbieri@doverfs.com)
    """
) 