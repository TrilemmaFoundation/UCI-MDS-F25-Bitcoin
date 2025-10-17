import streamlit as st


with st.sidebar:
    col1, col2, col3 = st.columns(3)

    with col2:
        st.image("images/bitcoin_logo.svg")

pg = st.navigation(["Dashboard.py", "About.py"])
pg.run()
