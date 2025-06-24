import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

def check_password() -> None:
    """Checks user password and stops execution if not authenticated."""
    correct_password = os.getenv("APP_PASSWORD", "")
    def password_entered():
        if st.session_state["password"] == correct_password:
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
        st.stop()