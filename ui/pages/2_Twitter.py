import sys
import os
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from uuid import uuid4
from cache import get_accounts, add_account, remove_account, get_twitter_cache_path
from config import get_twitter_language
from llm_provider import generate_text

st.set_page_config(page_title="Twitter - MoneyPrinter V2", page_icon="🐦", layout="wide")

st.markdown("# 🐦 Twitter Bot")
st.markdown("---")


def get_posts_for_account(account_id: str) -> list:
    """Read posts from cache without instantiating Twitter class."""
    cache_path = get_twitter_cache_path()
    if not os.path.exists(cache_path):
        return []
    with open(cache_path, "r") as f:
        data = json.load(f)
    for acc in data.get("accounts", []):
        if acc["id"] == account_id:
            return acc.get("posts", [])
    return []


def generate_tweet_text(topic: str) -> str:
    """Generate a tweet using LLM without instantiating Twitter."""
    completion = generate_text(
        f"Generate a Twitter post about: {topic} in {get_twitter_language()}. "
        "The Limit is 2 sentences. Choose a specific sub-topic of the provided topic."
    )
    completion = re.sub(r"\*", "", completion).replace('"', "")
    if len(completion) >= 260:
        return completion[:257].rsplit(" ", 1)[0] + "..."
    return completion


# --- Tabs ---
tab_accounts, tab_post, tab_history = st.tabs(["👥 Cuentas", "✍️ Publicar", "📋 Historial"])

# ============================
# TAB: Cuentas
# ============================
with tab_accounts:
    accounts = get_accounts("twitter")

    if accounts:
        st.markdown("### Cuentas registradas")
        for idx, acc in enumerate(accounts):
            with st.container():
                cols = st.columns([1, 2, 2, 1])
                cols[0].markdown(f"**#{idx + 1}**")
                cols[1].markdown(f"🏷️ {acc['nickname']}")
                cols[2].markdown(f"📌 {acc['topic']}")
                if cols[3].button("🗑️", key=f"del_tw_{acc['id']}", help="Eliminar cuenta"):
                    remove_account("twitter", acc["id"])
                    st.success(f"Cuenta '{acc['nickname']}' eliminada.")
                    st.rerun()
                st.markdown("---")
    else:
        st.info("No hay cuentas configuradas. Crea una abajo.")

    with st.expander("➕ Agregar nueva cuenta", expanded=len(accounts) == 0):
        with st.form("add_tw_account"):
            nickname = st.text_input("Nombre de la cuenta")
            fp_profile = st.text_input("Ruta al perfil de Firefox", help="Debe estar logueado en X/Twitter")
            topic = st.text_input("Tema", placeholder="ej: criptomonedas, fitness, programacion")

            if st.form_submit_button("Crear cuenta", type="primary"):
                if not nickname or not fp_profile or not topic:
                    st.error("Todos los campos son requeridos.")
                elif not os.path.isdir(fp_profile):
                    st.error(f"La ruta del perfil no existe: {fp_profile}")
                else:
                    add_account("twitter", {
                        "id": str(uuid4()),
                        "nickname": nickname,
                        "firefox_profile": fp_profile,
                        "topic": topic,
                        "posts": [],
                    })
                    st.success(f"Cuenta '{nickname}' creada exitosamente!")
                    st.rerun()

# ============================
# TAB: Publicar
# ============================
with tab_post:
    accounts = get_accounts("twitter")

    if not accounts:
        st.warning("Primero agrega una cuenta en la pestana 'Cuentas'.")
    elif not st.session_state.get("model_ready"):
        st.warning("Selecciona un modelo Ollama en la barra lateral primero.")
    else:
        account_names = [f"{acc['nickname']} ({acc['topic']})" for acc in accounts]
        selected_idx = st.selectbox("Seleccionar cuenta", range(len(accounts)),
                                     format_func=lambda i: account_names[i],
                                     key="tw_post_account")
        selected = accounts[selected_idx]

        st.markdown(f"**Cuenta:** {selected['nickname']} | **Tema:** {selected['topic']}")

        mode = st.radio("Modo", ["🤖 Auto-generar", "✏️ Texto manual"], horizontal=True)

        if "tweet_draft" not in st.session_state:
            st.session_state.tweet_draft = ""

        if mode == "🤖 Auto-generar":
            if st.button("Generar tweet", type="secondary"):
                with st.spinner("Generando..."):
                    st.session_state.tweet_draft = generate_tweet_text(selected["topic"])

        tweet_text = st.text_area(
            "Contenido del tweet",
            value=st.session_state.tweet_draft,
            max_chars=280,
            height=120,
            key="tweet_text_area",
        )

        char_count = len(tweet_text)
        if char_count > 0:
            color = "green" if char_count <= 280 else "red"
            st.markdown(f":{color}[{char_count}/280 caracteres]")

        if st.button("🚀 Publicar en Twitter", type="primary", disabled=not tweet_text.strip()):
            try:
                with st.status("Publicando tweet...", expanded=True) as status:
                    st.write("🔧 Iniciando navegador...")
                    from classes.Twitter import Twitter

                    twitter = Twitter(
                        selected["id"],
                        selected["nickname"],
                        selected["firefox_profile"],
                        selected["topic"],
                    )

                    try:
                        st.write("📤 Enviando tweet...")
                        twitter.post(text=tweet_text)
                        status.update(label="Tweet publicado!", state="complete")
                        st.success("Tweet publicado exitosamente!")
                        st.session_state.tweet_draft = ""
                        st.balloons()
                    finally:
                        try:
                            twitter.browser.quit()
                        except Exception:
                            pass
            except Exception as e:
                st.error(f"Error al publicar: {e}")

# ============================
# TAB: Historial
# ============================
with tab_history:
    accounts = get_accounts("twitter")

    if not accounts:
        st.info("No hay cuentas configuradas.")
    else:
        account_names = [f"{acc['nickname']} ({acc['topic']})" for acc in accounts]
        selected_idx = st.selectbox("Cuenta", range(len(accounts)),
                                     format_func=lambda i: account_names[i],
                                     key="tw_history_account")
        selected = accounts[selected_idx]

        posts = get_posts_for_account(selected["id"])

        if posts:
            st.markdown(f"### {len(posts)} tweets publicados")
            for idx, post in enumerate(reversed(posts)):
                with st.container():
                    cols = st.columns([1, 4, 2])
                    cols[0].markdown(f"**#{len(posts) - idx}**")
                    cols[1].markdown(f"💬 {post.get('content', '')[:120]}")
                    cols[2].markdown(f"📅 {post.get('date', 'N/A')}")
                st.markdown("---")
        else:
            st.info("No hay tweets para esta cuenta.")
