import sys
import os
import shutil
import subprocess
import platform

# --- Path setup: must happen before any src/ imports ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from config import assert_folder_structure, get_ollama_model
from llm_provider import list_models, select_model, get_active_model
from cache import get_accounts, get_products
from utils import fetch_songs

DEFAULT_MODEL = "llama3.2:3b"


def is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def is_ollama_running() -> bool:
    try:
        list_models()
        return True
    except Exception:
        return False


def install_and_setup_ollama():
    """Installs Ollama, starts the service, and pulls the default model."""
    system = platform.system()

    yield "Verificando instalacion de Ollama..."
    if not is_ollama_installed():
        yield "Instalando Ollama..."
        if system == "Darwin":
            result = subprocess.run(
                ["brew", "install", "ollama"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Error instalando Ollama:\n{result.stderr}")
        elif system == "Linux":
            result = subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Error instalando Ollama:\n{result.stderr}")
        else:
            raise RuntimeError(
                "Instalacion automatica no soportada en Windows. "
                "Descarga Ollama desde https://ollama.com/download"
            )
        yield "Ollama instalado correctamente."
    else:
        yield "Ollama ya esta instalado."

    yield "Iniciando servicio de Ollama..."
    if system == "Darwin":
        subprocess.run(["brew", "services", "start", "ollama"],
                       capture_output=True, text=True, timeout=30)
    else:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    # Wait for server to be ready
    import time
    for i in range(15):
        if is_ollama_running():
            break
        time.sleep(2)
        yield f"Esperando que Ollama inicie... ({i + 1}/15)"
    else:
        raise RuntimeError("Ollama no respondio despues de 30 segundos.")

    yield "Servicio de Ollama activo."

    yield f"Descargando modelo {DEFAULT_MODEL} (esto puede tomar unos minutos)..."
    result = subprocess.run(
        ["ollama", "pull", DEFAULT_MODEL],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error descargando modelo:\n{result.stderr}")

    yield f"Modelo {DEFAULT_MODEL} listo."

# --- Page config ---
st.set_page_config(
    page_title="MoneyPrinter V2",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card h3 { margin: 0; font-size: 2rem; }
    .metric-card p { margin: 0; opacity: 0.85; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- Initialize folder structure ---
assert_folder_structure()

# --- Session state defaults ---
if "model_ready" not in st.session_state:
    st.session_state.model_ready = False
if "generated_video_path" not in st.session_state:
    st.session_state.generated_video_path = None

# --- Sidebar ---
with st.sidebar:
    st.markdown("# 💰 MoneyPrinter V2")
    st.markdown("---")

    # Ollama model selector
    st.markdown("### 🤖 Modelo LLM")
    configured = get_ollama_model()
    ollama_available = is_ollama_installed() and is_ollama_running()

    models = []
    if ollama_available:
        try:
            models = list_models()
        except Exception:
            models = []

    if models:
        default_idx = 0
        if configured and configured in models:
            default_idx = models.index(configured)
        elif get_active_model() and get_active_model() in models:
            default_idx = models.index(get_active_model())

        chosen = st.selectbox("Modelo Ollama", models, index=default_idx, label_visibility="collapsed")
        if chosen:
            select_model(chosen)
            st.session_state.model_ready = True
            st.caption(f"✅ Usando: **{chosen}**")
    else:
        if not is_ollama_installed():
            st.error("Ollama no esta instalado.")
        elif not ollama_available:
            st.warning("Ollama esta instalado pero el servicio no responde.")
        else:
            st.warning("No hay modelos descargados.")

        if st.button("⚡ Instalar y configurar automaticamente", type="primary", use_container_width=True):
            try:
                with st.status("Configurando Ollama...", expanded=True) as status:
                    for step_msg in install_and_setup_ollama():
                        st.write(step_msg)
                    status.update(label="Ollama listo!", state="complete")

                select_model(DEFAULT_MODEL)
                st.session_state.model_ready = True
                st.success(f"Modelo {DEFAULT_MODEL} configurado.")
                st.rerun()
            except RuntimeError as e:
                st.error(str(e))
            except subprocess.TimeoutExpired:
                st.error("La operacion tomo demasiado tiempo. Intenta manualmente.")

        st.caption(f"Instalara Ollama + modelo `{DEFAULT_MODEL}`")

    st.markdown("---")

    # Stats
    yt_accounts = get_accounts("youtube")
    tw_accounts = get_accounts("twitter")
    products = get_products()

    total_videos = sum(len(acc.get("videos", [])) for acc in yt_accounts)
    total_posts = sum(len(acc.get("posts", [])) for acc in tw_accounts)

    st.markdown("### 📊 Estadisticas")
    col1, col2 = st.columns(2)
    col1.metric("Videos", total_videos)
    col2.metric("Posts", total_posts)
    col1.metric("Cuentas YT", len(yt_accounts))
    col2.metric("Cuentas TW", len(tw_accounts))

# --- Main landing page ---
st.markdown("# 💰 MoneyPrinter V2")
st.markdown("**Automatiza tu presencia online con IA**")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <h3>🎬</h3>
        <p>YouTube Shorts</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Genera y sube videos cortos automaticamente")

with col2:
    st.markdown("""
    <div class="metric-card">
        <h3>🐦</h3>
        <p>Twitter Bot</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Publica tweets generados por IA")

with col3:
    st.markdown("""
    <div class="metric-card">
        <h3>🛒</h3>
        <p>Affiliate Marketing</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Genera pitches para productos de Amazon")

with col4:
    st.markdown("""
    <div class="metric-card">
        <h3>📧</h3>
        <p>Outreach</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Encuentra negocios y envia correos")

st.markdown("---")
st.info("👈 Usa la barra lateral para navegar entre las secciones y seleccionar tu modelo de IA.")

# --- Fetch songs on first run ---
if "songs_fetched" not in st.session_state:
    with st.spinner("Descargando canciones de fondo..."):
        try:
            fetch_songs()
        except Exception:
            pass
    st.session_state.songs_fetched = True
