import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from config import (
    get_google_maps_scraper_niche,
    get_scraper_timeout,
    get_email_credentials,
    get_outreach_message_subject,
)
from cache import get_results_cache_path

st.set_page_config(page_title="Outreach - MoneyPrinter V2", page_icon="📧", layout="wide")

st.markdown("# 📧 Local Business Outreach")
st.markdown("---")

# --- Tabs ---
tab_config, tab_run, tab_results = st.tabs(["⚙️ Configuracion", "🚀 Ejecutar", "📊 Resultados"])

# ============================
# TAB: Configuracion
# ============================
with tab_config:
    st.markdown("### Estado actual")

    col1, col2 = st.columns(2)

    with col1:
        niche = get_google_maps_scraper_niche()
        timeout = get_scraper_timeout()
        subject = get_outreach_message_subject()

        st.markdown(f"**Nicho del scraper:** {niche or '❌ No configurado'}")
        st.markdown(f"**Timeout del scraper:** {timeout}s")
        st.markdown(f"**Asunto del email:** {subject}")

    with col2:
        email_creds = get_email_credentials()
        has_email = bool(email_creds.get("username"))

        st.markdown(f"**Servidor SMTP:** {email_creds.get('smtp_server', 'N/A')}")
        st.markdown(f"**Puerto SMTP:** {email_creds.get('smtp_port', 'N/A')}")
        st.markdown(f"**Email configurado:** {'✅' if has_email else '❌ No configurado'}")

    if not niche:
        st.warning("Configura el nicho del scraper en la pagina de Ajustes antes de ejecutar.")
    if not has_email:
        st.warning("Configura las credenciales de email en la pagina de Ajustes para enviar correos.")

    st.info("📝 Para cambiar estos valores, ve a la pagina **Ajustes**.")

# ============================
# TAB: Ejecutar
# ============================
with tab_run:
    st.markdown("### Ejecutar Outreach")
    st.markdown("""
    Este proceso:
    1. Descarga y compila el scraper de Google Maps (requiere Go instalado)
    2. Busca negocios locales segun el nicho configurado
    3. Extrae emails de los resultados
    4. Envia correos de outreach
    """)

    niche = get_google_maps_scraper_niche()
    if not niche:
        st.error("Configura un nicho en Ajustes antes de ejecutar.")
    else:
        st.markdown(f"**Nicho:** {niche}")
        st.markdown(f"**Timeout:** {get_scraper_timeout()}s")

        if st.button("🚀 Iniciar Outreach", type="primary"):
            try:
                with st.status("Ejecutando outreach...", expanded=True) as status:
                    st.write("🔧 Inicializando...")
                    from classes.Outreach import Outreach

                    outreach = Outreach()

                    st.write("🔍 Verificando instalacion de Go...")
                    if not outreach.is_go_installed():
                        st.error("Go no esta instalado. Instalalo desde https://golang.org/")
                        st.stop()

                    st.write("📥 Descargando scraper...")
                    st.write("🔨 Compilando...")
                    st.write("🔍 Ejecutando scraper (esto puede tomar varios minutos)...")

                    outreach.start()

                    status.update(label="Outreach completado!", state="complete")
                    st.success("Proceso de outreach completado.")
                    st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

# ============================
# TAB: Resultados
# ============================
with tab_results:
    st.markdown("### Resultados del Scraping")

    results_path = get_results_cache_path()

    if os.path.exists(results_path):
        try:
            import pandas as pd
            df = pd.read_csv(results_path)
            st.markdown(f"**{len(df)} negocios encontrados**")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Descargar CSV",
                csv,
                "outreach_results.csv",
                "text/csv",
                type="secondary",
            )
        except Exception as e:
            st.error(f"Error al leer resultados: {e}")
    else:
        st.info("No hay resultados disponibles. Ejecuta el scraper primero.")
