import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from uuid import uuid4
from cache import get_accounts, add_account, remove_account, get_youtube_cache_path
from config import get_verbose
from utils import rem_temp_files

st.set_page_config(page_title="YouTube - MoneyPrinter V2", page_icon="🎬", layout="wide")

st.markdown("# 🎬 YouTube Shorts Automater")
st.markdown("---")


def get_videos_for_account(account_id: str) -> list:
    """Read videos from cache without instantiating YouTube class."""
    cache_path = get_youtube_cache_path()
    if not os.path.exists(cache_path):
        return []
    with open(cache_path, "r") as f:
        data = json.load(f)
    for acc in data.get("accounts", []):
        if acc["id"] == account_id:
            return acc.get("videos", [])
    return []


# --- Tabs ---
tab_accounts, tab_generate, tab_history = st.tabs(["👥 Cuentas", "🎥 Generar Video", "📋 Historial"])

# ============================
# TAB: Cuentas
# ============================
with tab_accounts:
    accounts = get_accounts("youtube")

    if accounts:
        st.markdown("### Cuentas registradas")
        for idx, acc in enumerate(accounts):
            with st.container():
                cols = st.columns([1, 2, 2, 2, 1])
                cols[0].markdown(f"**#{idx + 1}**")
                cols[1].markdown(f"🏷️ {acc['nickname']}")
                cols[2].markdown(f"📁 {acc['niche']}")
                cols[3].markdown(f"🌐 {acc.get('language', 'N/A')}")
                if cols[4].button("🗑️", key=f"del_yt_{acc['id']}", help="Eliminar cuenta"):
                    remove_account("youtube", acc["id"])
                    st.success(f"Cuenta '{acc['nickname']}' eliminada.")
                    st.rerun()
                st.markdown("---")
    else:
        st.info("No hay cuentas configuradas. Crea una abajo.")

    # Add account form
    with st.expander("➕ Vincular cuenta de YouTube", expanded=len(accounts) == 0):
        st.info(
            "**Como funciona:** La app usa un perfil de Firefox donde ya estas logueado en YouTube. "
            "No necesitas crear una cuenta nueva — vinculas tu cuenta existente.\n\n"
            "**Pasos:**\n"
            "1. Abre Firefox y logueate en [YouTube Studio](https://studio.youtube.com)\n"
            "2. Copia la ruta de tu perfil de Firefox (ver abajo)\n"
            "3. Llena el formulario"
        )

        system = os.uname().sysname
        if system == "Darwin":
            default_profile_hint = "~/Library/Application Support/Firefox/Profiles/xxxxxxxx.default-release"
        elif system == "Linux":
            default_profile_hint = "~/.mozilla/firefox/xxxxxxxx.default-release"
        else:
            default_profile_hint = r"C:\Users\TU_USUARIO\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxxxxx.default-release"

        st.code(default_profile_hint, language=None)
        st.caption("Reemplaza con tu perfil real. Puedes verlo en Firefox escribiendo `about:profiles` en la barra de direcciones.")

        with st.form("add_yt_account"):
            nickname = st.text_input("Nombre para identificar esta cuenta", placeholder="ej: Mi canal de cocina")
            fp_profile = st.text_input("Ruta al perfil de Firefox")
            niche = st.text_input("Nicho del canal", placeholder="ej: cocina, tecnologia, fitness")
            language = st.text_input("Idioma del contenido", value="Spanish")

            if st.form_submit_button("Crear cuenta", type="primary"):
                if not nickname or not fp_profile or not niche:
                    st.error("Todos los campos son requeridos.")
                elif not os.path.isdir(fp_profile):
                    st.error(f"La ruta del perfil no existe: {fp_profile}")
                else:
                    add_account("youtube", {
                        "id": str(uuid4()),
                        "nickname": nickname,
                        "firefox_profile": fp_profile,
                        "niche": niche,
                        "language": language,
                        "videos": [],
                    })
                    st.success(f"Cuenta '{nickname}' creada exitosamente!")
                    st.rerun()

# ============================
# TAB: Generar Video
# ============================
with tab_generate:
    accounts = get_accounts("youtube")

    if not accounts:
        st.warning("Primero agrega una cuenta en la pestana 'Cuentas'.")
    elif not st.session_state.get("model_ready"):
        st.warning("Selecciona un modelo Ollama en la barra lateral primero.")
    else:
        account_names = [f"{acc['nickname']} ({acc['niche']})" for acc in accounts]
        selected_idx = st.selectbox("Seleccionar cuenta", range(len(accounts)),
                                     format_func=lambda i: account_names[i])
        selected = accounts[selected_idx]

        st.markdown(f"**Cuenta:** {selected['nickname']} | **Nicho:** {selected['niche']} | **Idioma:** {selected.get('language', 'N/A')}")

        col1, col2 = st.columns(2)
        generate_only = col1.button("🎬 Generar Video", type="primary", use_container_width=True)
        generate_and_upload = col2.button("🚀 Generar y Subir", use_container_width=True)

        if generate_only or generate_and_upload:
            try:
                rem_temp_files()

                with st.status("Generando video...", expanded=True) as status:
                    st.write("🔧 Inicializando...")
                    from classes.YouTube import YouTube
                    from classes.Tts import TTS

                    yt = YouTube(
                        selected["id"],
                        selected["nickname"],
                        selected["firefox_profile"],
                        selected["niche"],
                        selected.get("language", "English"),
                    )

                    try:
                        st.write("💡 Generando tema...")
                        topic = yt.generate_topic()
                        st.write(f"**Tema:** {topic}")

                        st.write("📝 Generando guion...")
                        script = yt.generate_script()
                        st.write(f"**Guion:** {script[:200]}...")

                        st.write("🏷️ Generando metadata...")
                        metadata = yt.generate_metadata()
                        st.write(f"**Titulo:** {metadata['title']}")

                        st.write("🖼️ Generando prompts de imagenes...")
                        prompts = yt.generate_prompts()
                        st.write(f"Se generaron **{len(prompts)}** prompts")

                        for i, prompt in enumerate(prompts):
                            st.write(f"🎨 Generando imagen {i + 1}/{len(prompts)}...")
                            yt.generate_image(prompt)

                        st.write("🔊 Generando audio TTS...")
                        tts = TTS()
                        yt.generate_script_to_speech(tts)

                        st.write("🎞️ Combinando video final...")
                        path = yt.combine()

                        status.update(label="Video generado exitosamente!", state="complete")

                        st.session_state.generated_video_path = path
                        st.session_state.yt_instance = yt

                        st.video(path)
                        st.success(f"Video guardado en: {path}")

                        if generate_and_upload:
                            with st.spinner("Subiendo a YouTube..."):
                                result = yt.upload_video()
                                if result:
                                    st.success(f"Video subido: {yt.uploaded_video_url}")
                                    st.balloons()
                                else:
                                    st.error("Error al subir el video.")
                    finally:
                        try:
                            yt.browser.quit()
                        except Exception:
                            pass

            except Exception as e:
                st.error(f"Error: {e}")

# ============================
# TAB: Historial
# ============================
with tab_history:
    accounts = get_accounts("youtube")

    if not accounts:
        st.info("No hay cuentas configuradas.")
    else:
        account_names = [f"{acc['nickname']} ({acc['niche']})" for acc in accounts]
        selected_idx = st.selectbox("Cuenta", range(len(accounts)),
                                     format_func=lambda i: account_names[i],
                                     key="history_account")
        selected = accounts[selected_idx]

        videos = get_videos_for_account(selected["id"])

        if videos:
            st.markdown(f"### {len(videos)} videos encontrados")
            for idx, video in enumerate(videos):
                with st.container():
                    cols = st.columns([1, 3, 2, 2])
                    cols[0].markdown(f"**#{idx + 1}**")
                    cols[1].markdown(f"📹 {video.get('title', 'Sin titulo')[:60]}")
                    cols[2].markdown(f"📅 {video.get('date', 'N/A')}")
                    url = video.get("url", "")
                    if url:
                        cols[3].markdown(f"[🔗 Ver video]({url})")
                st.markdown("---")
        else:
            st.info("No hay videos para esta cuenta.")
