import streamlit as st


def create_sidebar():
    with st.sidebar:
        bitcoin_svg = open("dashboard/images/bitcoin_logo.svg").read()
        st.image(bitcoin_svg)
        st.write("here is the sidebar")
