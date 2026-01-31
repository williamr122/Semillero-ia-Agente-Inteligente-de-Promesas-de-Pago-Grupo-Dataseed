import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types
from datetime import datetime, timedelta
from gtts import gTTS
from dotenv import load_dotenv  # <--- NUEVA LIBRERÍA
# --- CARGAR CONFIGURACIÓN ---
load_dotenv()  # Busca el archivo .env y carga las variables

# Obtenemos la API Key del entorno
api_key = os.getenv("GOOGLE_API_KEY")

# Validación para el Jurado
if not api_key:
    st.error("⚠️ Error: No se encontró la 'GOOGLE_API_KEY' en el archivo .env")
    st.stop()

client = genai.Client(api_key=api_key)
EXCEL_FILE = "cartera_clientes.xlsx"
LOG_FILE = "log_conversaciones.txt"

HOY = datetime.now()
FECHA_HOY_STR = HOY.strftime("%A, %d de %B de %Y")

# --- PROMPT CON MEMORIA REFORZADA ---
PROMPT_SISTEMA = f"""
Eres un Asesor de Cobranza con Memoria de Contexto.
HOY ES: {FECHA_HOY_STR}.

INSTRUCCIONES CRUCIALES:
1. REVISA EL HISTORIAL: Antes de preguntar algo, mira los mensajes anteriores. Si el usuario ya dijo el monto por texto y la fecha por audio (o viceversa), ÚNELOS.
2. ACCIÓN INMEDIATA: En cuanto tengas Monto y Fecha (aunque vengan de fuentes distintas), ejecuta 'registrar_promesa'.
3. TRADUCCIÓN TEMPORAL: Convierte términos como "mañana", "lunes" o "fin de mes" a formato DD/MM/YYYY basándote en {HOY.strftime('%d/%m/%Y')}.
4. TONO Y CONSEJO: Tras registrar, resume: "Escuché [fecha] y [monto]. Tono: [Análisis] un resumen muy corto. Registro exitoso." Añade el consejo de riesgo y en que puede mejorar.
"""

def guardar_log(cliente, mensaje, rol):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {rol} - {cliente}: {mensaje}\n")

def texto_a_voz(texto):
    try:
        archivo = "response.mp3"
        tts = gTTS(text=texto, lang='es')
        tts.save(archivo)
        return archivo
    except: return None

def cargar_datos():
    if not os.path.exists(EXCEL_FILE):
        data = {
            'ID': [1, 2], 'Nombre': ['Juan Perez', 'Maria Garcia'],
            'Deuda_Total': [500.0, 1200.0], 'Pagos_Realizados': [0.0, 200.0],
            'Monto_Prometido': [0.0, 0.0], 'Fecha_Promesa': ['', ''],
            'Calificacion_Riesgo': ['Baja', 'Media']
        }
        pd.DataFrame(data).to_excel(EXCEL_FILE, index=False)
    return pd.read_excel(EXCEL_FILE)

def registrar_promesa_api(id_c, monto, fecha):
    df = pd.read_excel(EXCEL_FILE)
    idx = df[df['ID'] == id_c].index
    if not idx.empty:
        deuda_act = df.loc[idx, 'Deuda_Total'].values[0] - df.loc[idx, 'Pagos_Realizados'].values[0]
        riesgo = "Baja" if monto >= (deuda_act * 0.4) else "Alta"
        df.loc[idx, 'Monto_Prometido'] = monto
        df.loc[idx, 'Fecha_Promesa'] = str(fecha)
        df.loc[idx, 'Calificacion_Riesgo'] = riesgo
        df.to_excel(EXCEL_FILE, index=False)
        return riesgo
    return None

# --- INTERFAZ ---
st.set_page_config(page_title="Agente IA", layout="wide")
st.title("🛡️ Agente Inteligente de Promesas de Pago")

df_cartera = cargar_datos()

# Sidebar
st.sidebar.header("Gestión")
dict_clientes = dict(zip(df_cartera['Nombre'], df_cartera['ID']))
n_sel = st.sidebar.selectbox("Seleccionar Cliente:", list(dict_clientes.keys()))
c_id = dict_clientes[n_sel]
c_sel = df_cartera[df_cartera['ID'] == c_id].iloc[0]
saldo = c_sel['Deuda_Total'] - c_sel['Pagos_Realizados']

# Formulario Nuevo Cliente
with st.sidebar.expander("➕ Nuevo Cliente"):
    with st.form("n_c"):
        name = st.text_input("Nombre")
        debt = st.number_input("Deuda", min_value=0.0)
        if st.form_submit_button("Guardar"):
            new_id = int(df_cartera['ID'].max() + 1)
            row = {'ID': new_id, 'Nombre': name, 'Deuda_Total': debt, 'Pagos_Realizados': 0.0, 'Monto_Prometido': 0.0, 'Fecha_Promesa': '', 'Calificacion_Riesgo': 'Baja'}
            pd.concat([df_cartera, pd.DataFrame([row])], ignore_index=True).to_excel(EXCEL_FILE, index=False)
            st.rerun()

# Dashboard
col1, col2, col3 = st.columns(3)
col1.metric("Cliente", c_sel['Nombre'])
col2.metric("Saldo Real", f"${saldo}")
status_emoji = "🟢" if c_sel['Calificacion_Riesgo'] == "Baja" else "🔴"
col3.metric("Riesgo", f"{status_emoji} {c_sel['Calificacion_Riesgo']}")

st.dataframe(df_cartera[['ID', 'Nombre', 'Deuda_Total', 'Monto_Prometido', 'Fecha_Promesa', 'Calificacion_Riesgo']], width='stretch', hide_index=True)

st.sidebar.divider()
audio_input = st.sidebar.audio_input("Grabar Propuesta")

# --- LÓGICA DE CHAT ---
if "messages" not in st.session_state or st.session_state.get("last_id") != c_id:
    st.session_state.messages = []
    st.session_state.last_id = c_id
    st.session_state.messages.append({"role": "assistant", "content": f"Hola {c_sel['Nombre']}, su saldo es ${saldo}. ¿Cómo desea pagar?"})

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if "audio" in m: st.audio(m["audio"])

user_input = None
if p := st.chat_input("Escriba su mensaje..."):
    user_input = p
elif audio_input:
    audio_id = f"{audio_input.name}_{audio_input.size}"
    if st.session_state.get("last_processed_audio") != audio_id:
        with st.spinner("🔍 Analizando audio y tono emocional..."):
            res_audio = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[f"Transcribe y analiza el tono brevemente, un resumen muy corto. Hoy es {FECHA_HOY_STR}:", types.Part.from_bytes(data=audio_input.read(), mime_type="audio/wav")]
        )
        user_input = f"AUDIO_TRANSCRIPCIÓN: {res_audio.text}"
        st.session_state.last_processed_audio = audio_id

if user_input:
    # 1. Guardamos el mensaje del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": user_input})
    guardar_log(c_sel['Nombre'], user_input, "CLIENTE")
    
    # 2. Mostramos el spinner MIENTRAS consultamos a Gemini
    with st.spinner("🤖 El Agente está procesando su solicitud..."):
        try:
            # Preparamos el contexto para que no olvide lo dicho antes
            historial_contexto = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{PROMPT_SISTEMA}\nCLIENTE: {c_sel['Nombre']}\nSALDO: {saldo}\nHISTORIAL:\n{historial_contexto}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=[
                        types.FunctionDeclaration(
                            name="registrar_promesa",
                            description="Registra monto y fecha",
                            parameters={
                                "type": "OBJECT",
                                "properties": {"monto": {"type": "NUMBER"}, "fecha": {"type": "STRING"}},
                                "required": ["monto", "fecha"]
                            }
                        )
                    ])]
                )
            )

            # 3. Procesamos la respuesta (el spinner desaparece al salir del bloque 'with')
            for part in response.candidates[0].content.parts:
                text_res = ""
                if part.function_call:
                    f = part.function_call.args
                    riesgo = registrar_promesa_api(c_id, f['monto'], f['fecha'])
                    text_res = f"He registrado su promesa de ${f['monto']} para el {f['fecha']}. Riesgo: {riesgo}. ¡Gracias por su compromiso!"
                elif part.text:
                    text_res = part.text

                if text_res:
                    audio_p = texto_a_voz(text_res)
                    st.session_state.messages.append({"role": "assistant", "content": text_res, "audio": audio_p})
                    guardar_log(c_sel['Nombre'], text_res, "AGENTE")
                    st.rerun() # Refresca para mostrar la respuesta y quitar el spinner

        except Exception as e:
            st.error(f"Hubo un inconveniente: {e}")