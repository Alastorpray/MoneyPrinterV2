import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from config import ROOT_DIR
from llm_provider import list_models, select_model, get_active_model

st.set_page_config(page_title="Ajustes - MoneyPrinter V2", page_icon="⚙️", layout="wide")

st.markdown("# ⚙️ Ajustes")
st.markdown("---")

CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


config = load_config()

# --- Tabs ---
tab_model, tab_general, tab_image, tab_tts, tab_outreach, tab_email = st.tabs([
    "🤖 Modelo", "⚡ General", "🖼️ Imagenes", "🔊 TTS & STT", "📧 Outreach", "✉️ Email"
])

# ============================
# TAB: Modelo Ollama
# ============================
with tab_model:
    st.markdown("### Seleccion de Modelo Ollama")

    try:
        models = list_models()
    except Exception:
        models = []

    if models:
        current = config.get("ollama_model", "") or get_active_model() or ""
        default_idx = models.index(current) if current in models else 0

        chosen = st.selectbox("Modelo", models, index=default_idx)

        col1, col2 = st.columns([3, 1])
        base_url = col1.text_input("URL base de Ollama", value=config.get("ollama_base_url", "http://127.0.0.1:11434"))

        if st.button("Guardar modelo", type="primary"):
            config["ollama_model"] = chosen
            config["ollama_base_url"] = base_url
            save_config(config)
            select_model(chosen)
            st.session_state.model_ready = True
            st.success(f"Modelo guardado: {chosen}")
    else:
        st.warning("No se pudo conectar a Ollama. Verifica que este corriendo.")
        st.code("ollama serve", language="bash")

# ============================
# TAB: General
# ============================
with tab_general:
    st.markdown("### Configuracion General")

    col1, col2 = st.columns(2)

    with col1:
        verbose = st.toggle("Modo verbose", value=config.get("verbose", True))
        headless = st.toggle("Navegador headless", value=config.get("headless", False),
                              help="Ejecutar Selenium sin ventana visible")
        is_for_kids = st.toggle("Contenido para ninos", value=config.get("is_for_kids", False))

    with col2:
        threads = st.number_input("Hilos de procesamiento", value=config.get("threads", 2),
                                   min_value=1, max_value=16)
        script_length = st.number_input("Longitud del guion (oraciones)", value=config.get("script_sentence_length", 4),
                                         min_value=1, max_value=20)

    firefox_profile = st.text_input("Perfil de Firefox (por defecto)", value=config.get("firefox_profile", ""))
    imagemagick = st.text_input("Ruta de ImageMagick", value=config.get("imagemagick_path", ""))
    font = st.text_input("Fuente", value=config.get("font", "bold_font.ttf"))
    zip_url = st.text_input("URL del ZIP de canciones", value=config.get("zip_url", ""))

    if st.button("Guardar configuracion general", type="primary"):
        config["verbose"] = verbose
        config["headless"] = headless
        config["is_for_kids"] = is_for_kids
        config["threads"] = threads
        config["script_sentence_length"] = script_length
        config["firefox_profile"] = firefox_profile
        config["imagemagick_path"] = imagemagick
        config["font"] = font
        config["zip_url"] = zip_url
        save_config(config)
        st.success("Configuracion general guardada.")

# ============================
# TAB: Imagenes
# ============================
with tab_image:
    st.markdown("### Generacion de Imagenes (Nano Banana 2 / Gemini)")

    nb_base_url = st.text_input("API Base URL",
                                 value=config.get("nanobanana2_api_base_url",
                                                   "https://generativelanguage.googleapis.com/v1beta"))
    nb_api_key = st.text_input("API Key", value=config.get("nanobanana2_api_key", ""), type="password")
    nb_model = st.text_input("Modelo", value=config.get("nanobanana2_model", "gemini-3.1-flash-image-preview"))
    nb_aspect = st.selectbox("Aspect Ratio", ["9:16", "16:9", "1:1", "4:3", "3:4"],
                              index=["9:16", "16:9", "1:1", "4:3", "3:4"].index(
                                  config.get("nanobanana2_aspect_ratio", "9:16")))

    if st.button("Guardar configuracion de imagenes", type="primary"):
        config["nanobanana2_api_base_url"] = nb_base_url
        config["nanobanana2_api_key"] = nb_api_key
        config["nanobanana2_model"] = nb_model
        config["nanobanana2_aspect_ratio"] = nb_aspect
        save_config(config)
        st.success("Configuracion de imagenes guardada.")

# ============================
# TAB: TTS & STT
# ============================
with tab_tts:
    st.markdown("### Text-to-Speech")

    tts_voice = st.text_input("Voz TTS", value=config.get("tts_voice", "Jasper"))

    st.markdown("### Speech-to-Text (Subtitulos)")

    stt_provider = st.selectbox("Proveedor STT",
                                 ["local_whisper", "third_party_assemblyai"],
                                 index=["local_whisper", "third_party_assemblyai"].index(
                                     config.get("stt_provider", "local_whisper")))

    if stt_provider == "local_whisper":
        whisper_model = st.selectbox("Modelo Whisper",
                                      ["tiny", "base", "small", "medium", "large"],
                                      index=["tiny", "base", "small", "medium", "large"].index(
                                          config.get("whisper_model", "base")))
        whisper_device = st.selectbox("Dispositivo", ["auto", "cpu", "cuda"],
                                       index=["auto", "cpu", "cuda"].index(
                                           config.get("whisper_device", "auto")))
        whisper_compute = st.selectbox("Tipo de computo", ["int8", "float16", "float32"],
                                        index=["int8", "float16", "float32"].index(
                                            config.get("whisper_compute_type", "int8")))
    else:
        whisper_model = config.get("whisper_model", "base")
        whisper_device = config.get("whisper_device", "auto")
        whisper_compute = config.get("whisper_compute_type", "int8")

    assemblyai_key = st.text_input("AssemblyAI API Key",
                                    value=config.get("assembly_ai_api_key", ""),
                                    type="password",
                                    disabled=stt_provider != "third_party_assemblyai")

    if st.button("Guardar configuracion TTS/STT", type="primary"):
        config["tts_voice"] = tts_voice
        config["stt_provider"] = stt_provider
        config["whisper_model"] = whisper_model
        config["whisper_device"] = whisper_device
        config["whisper_compute_type"] = whisper_compute
        config["assembly_ai_api_key"] = assemblyai_key
        save_config(config)
        st.success("Configuracion TTS/STT guardada.")

# ============================
# TAB: Outreach
# ============================
with tab_outreach:
    st.markdown("### Configuracion de Outreach")

    scraper_niche = st.text_input("Nicho del scraper", value=config.get("google_maps_scraper_niche", ""),
                                   placeholder="ej: restaurants in New York")
    scraper_timeout = st.number_input("Timeout del scraper (segundos)",
                                       value=config.get("scraper_timeout", 300),
                                       min_value=30, max_value=1800)
    scraper_url = st.text_input("URL del scraper", value=config.get("google_maps_scraper", ""))
    outreach_subject = st.text_input("Asunto del email", value=config.get("outreach_message_subject", ""))
    outreach_body_file = st.text_input("Archivo del cuerpo del email",
                                        value=config.get("outreach_message_body_file", "outreach_message.html"))

    if st.button("Guardar configuracion de outreach", type="primary"):
        config["google_maps_scraper_niche"] = scraper_niche
        config["scraper_timeout"] = scraper_timeout
        config["google_maps_scraper"] = scraper_url
        config["outreach_message_subject"] = outreach_subject
        config["outreach_message_body_file"] = outreach_body_file
        save_config(config)
        st.success("Configuracion de outreach guardada.")

# ============================
# TAB: Email
# ============================
with tab_email:
    st.markdown("### Credenciales de Email (SMTP)")

    email_config = config.get("email", {})

    smtp_server = st.text_input("Servidor SMTP", value=email_config.get("smtp_server", "smtp.gmail.com"))
    smtp_port = st.number_input("Puerto SMTP", value=email_config.get("smtp_port", 587),
                                 min_value=1, max_value=65535)
    email_user = st.text_input("Usuario (email)", value=email_config.get("username", ""))
    email_pass = st.text_input("Contrasena", value=email_config.get("password", ""), type="password",
                                help="Para Gmail, usa una contrasena de aplicacion")

    if st.button("Guardar credenciales de email", type="primary"):
        config["email"] = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": email_user,
            "password": email_pass,
        }
        save_config(config)
        st.success("Credenciales de email guardadas.")

st.markdown("---")
st.markdown("### 📄 Config raw")
with st.expander("Ver config.json completo"):
    st.json(load_config())
