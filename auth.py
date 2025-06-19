import streamlit as st

def check_password(correct_password: str = "Q5sU1P5jcg25") -> None:
    """Checks user password and stops execution if not authenticated."""
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