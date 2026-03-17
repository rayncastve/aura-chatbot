import streamlit as st
import google.generativeai as genai
import requests

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="AURA - Caraballeda", page_icon="🛰️", layout="centered")

# --- 2. CONFIGURACIÓN DE GEMINI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Error al configurar la API Key. Verifica tus secretos. Detalles: {e}")
    st.stop()

# --- 3. HERRAMIENTAS (CONEXIÓN A ARCGIS) ---
def consultar_clima_caraballeda():
    """Consulta la lluvia acumulada actual y la fecha de los sensores en Caraballeda."""
    url = "https://services8.arcgis.com/2jmdYNQsteiDSgjD/arcgis/rest/services/weather_data_gdb_v2/FeatureServer/0/query?where=Ciudad=%27Caraballeda%27&outFields=*&orderByFields=OBJECTID+DESC&resultRecordCount=1&f=json"
    try:
        respuesta = requests.get(url)
        return respuesta.json()
    except Exception as e:
        return {"error": str(e)}

def consultar_alerta_huracanes():
    """Consulta si hay alertas de huracanes activas en la región costera."""
    url = "https://services8.arcgis.com/2jmdYNQsteiDSgjD/arcgis/rest/services/VenShapes_gdb/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=False&f=json"
    try:
        respuesta = requests.get(url)
        return respuesta.json()
    except Exception as e:
        return {"error": str(e)}

# --- 4. SYSTEM MESSAGE (INSTRUCCIONES DE AURA) ---
INSTRUCCIONES_AURA = """
Eres AURA (Asistente de Gestión de Riesgos Atmosféricos) para Caraballeda, estado La Guaira. Eres una profesional venezolana experta en protección civil.

<OBJETIVO_PRINCIPAL>
Informar el riesgo cruzando datos locales (lluvia) y regionales (huracanes) usando tus herramientas. SIEMPRE redirige al Monitor Oficial.

<CONOCIMIENTO_LOCAL_CARABALLEDA>
- Zonas más vulnerables (Riesgo Muy Alto): Zona de protección del Río San Julián, laderas y cauces de quebradas. Ámbitos: Palmar Este y Oeste, Los Corales, Caribe, Corapal, San Julián y Tarigua.
- Protocolos: Si llueve fuerte por más de 4h cerca de colinas, alejarse. Vigilar si el caudal del río baja bruscamente mientras llueve (posible represamiento).
- Cierra con: "Para ver el protocolo completo, revisa nuestra Guía Oficial: https://storymaps.arcgis.com/stories/b649f5d8425443198bbad65eb39528f5#ref-n-0VE7BJ"

<REGLAS_DE_DATOS>
1. FECHA: Viene en Unix Timestamp (milisegundos). Conviértelo a hora de Venezuela (UTC-4) "DD de Mes de YYYY, HH:MM AM/PM".
2. HURACANES: Si "huracan" != 0, RIESGO MÁXIMO (Ciclón).
3. LLUVIA: Si huracán es 0, evalúa: <90mm (🟢 VERDE), 90-150mm (🟡 AMARILLO), 150-210mm (🟠 NARANJA), >210mm (🔴 ROJO).

<FORMATO_OBLIGATORIO_REPORTE>
🛰️ **Sistema AURA — Monitoreo**
*[Fecha convertida]*

🌀 **Influencia Ciclónica:** [Dato]
🌧️ **Lluvia Acumulada:** [Dato] mm

🚦 **ESTADO GENERAL:** [Color y Nivel]

📢 **Recomendación:** [Consejo breve adaptado al perfil]

🖥️ **Monitor en vivo:** https://lsigma.maps.arcgis.com/apps/dashboards/c37a4bbf182a49c2b135672004bdf1e4
💡 **Guías Oficiales:** https://storymaps.arcgis.com/stories/b649f5d8425443198bbad65eb39528f5#ref-n-0VE7BJ
"""

# --- 5. INICIALIZAR EL MODELO ---
modelo = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=INSTRUCCIONES_AURA,
    tools=[consultar_clima_caraballeda, consultar_alerta_huracanes]
)

# --- 6. INTERFAZ DE USUARIO (STREAMLIT) ---
st.title("🛰️ AURA - Monitor de Riesgos")
st.markdown("Hola, soy AURA. Estoy aquí para informarte sobre el clima y los riesgos atmosféricos en Caraballeda. ¿En qué te puedo ayudar hoy?")

# Inicializar memoria del chat
if "chat" not in st.session_state:
    st.session_state.chat = modelo.start_chat(enable_automatic_function_calling=True)

# Mostrar historial de mensajes de forma limpia
for mensaje in st.session_state.chat.history:
    rol = "assistant" if mensaje.role == "model" else "user"
    try:
        if hasattr(mensaje, 'parts') and len(mensaje.parts) > 0:
            part = mensaje.parts[0]
            if not part.function_call and not part.function_response:
                with st.chat_message(rol):
                    st.markdown(part.text)
    except Exception:
        pass

# Caja de texto para el usuario
if prompt := st.chat_input("Ej: ¿Cuál es el reporte del clima actual?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("AURA está consultando los sensores de ArcGIS..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
            except Exception as e:
                error_msg = str(e)
                if "ResourceExhausted" in error_msg or "429" in error_msg:
                    st.warning("⏳ ¡Guau! Has hecho muchas consultas seguidas y el servidor gratuito está tomando un respiro. Por favor, espera 1 minuto y vuelve a intentarlo.")
                else:
                    st.error(f"⚠️ Error técnico: {error_msg}")
