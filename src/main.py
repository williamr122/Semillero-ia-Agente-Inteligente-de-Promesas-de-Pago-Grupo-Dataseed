import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types
from datetime import datetime, timedelta
from gtts import gTTS
from dotenv import load_dotenv  

load_dotenv()  

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("Error: No se encontró la 'GOOGLE_API_KEY' en el archivo .env")
    st.stop()

client = genai.Client(api_key=api_key)
EXCEL_FILE = "cartera_clientes.xlsx"
LOG_FILE = "log_conversaciones.txt"

HOY = datetime.now()
FECHA_HOY_STR = HOY.strftime("%A, %d de %B de %Y")

# --- CONFIGURACIÓN DEL SISTEMA ---
PROMPT_SISTEMA = f"""
Eres un Asesor de Cobranza Experto en Negociación y Conciliación.
HOY ES: {FECHA_HOY_STR}.

INSTRUCCIONES CRUCIALES (Mantener funcionamiento actual):
1. REVISA EL HISTORIAL: Mira mensajes anteriores. Si el monto está en texto y la fecha en audio, ÚNELOS.
2. ACCIÓN INMEDIATA: Al tener Monto y Fecha, ejecuta 'registrar_promesa' sin dudar.
3. TRADUCCIÓN TEMPORAL: Convierte "mañana", "lunes" o "fin de mes" a DD/MM/YYYY según {HOY.strftime('%d/%m/%Y')}.

NUEVAS REGLAS DE NEGOCIACIÓN (Aplicar en el punto 4):
4. TONO Y CONSEJO PERSONALIZADO: Tras registrar, resume: "Escuché [fecha] y [monto]. Tono: [Análisis] corto. Registro exitoso." Y añade el consejo según estos criterios:
   - SI EL PAGO ES EN < 15 DÍAS: Felicita efusivamente al cliente por su excelente disposición y compromiso temprano.
   - SI EL PAGO ES EN < 30 DÍAS: Agradece la intención y confirma que ayuda a mantener su cuenta al día.
   - SI EL PAGO ES EN > 30 DÍAS O AÑO PRÓXIMO: Advierte seriamente que el plazo es demasiado largo. Indica que un monto bajo en una fecha tan lejana afecta su score crediticio, genera intereses adicionales y no detiene procesos de coactiva.
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

st.set_page_config(page_title="Agente IA", layout="wide")
st.title("🛡️ Agente Inteligente de Promesas de Pago")

df_cartera = cargar_datos()

st.sidebar.header("Gestión")
dict_clientes = dict(zip(df_cartera['Nombre'], df_cartera['ID']))
n_sel = st.sidebar.selectbox("Seleccionar Cliente:", list(dict_clientes.keys()))
c_id = dict_clientes[n_sel]
c_sel = df_cartera[df_cartera['ID'] == c_id].iloc[0]
saldo = c_sel['Deuda_Total'] - c_sel['Pagos_Realizados']

with st.sidebar.expander("➕ Nuevo Cliente"):
    with st.form("n_c"):
        name = st.text_input("Nombre")
        debt = st.number_input("Deuda", min_value=0.0)
        if st.form_submit_button("Guardar"):
            new_id = int(df_cartera['ID'].max() + 1)
            row = {'ID': new_id, 'Nombre': name, 'Deuda_Total': debt, 'Pagos_Realizados': 0.0, 'Monto_Prometido': 0.0, 'Fecha_Promesa': '', 'Calificacion_Riesgo': 'Baja'}
            pd.concat([df_cartera, pd.DataFrame([row])], ignore_index=True).to_excel(EXCEL_FILE, index=False)
            st.rerun()

col1, col2, col3 = st.columns(3)
col1.metric("Cliente", c_sel['Nombre'])
col2.metric("Saldo Real", f"${saldo}")
status_emoji = "🟢" if c_sel['Calificacion_Riesgo'] == "Baja" else "🔴"
col3.metric("Riesgo", f"{status_emoji} {c_sel['Calificacion_Riesgo']}")

st.dataframe(df_cartera[['ID', 'Nombre', 'Deuda_Total', 'Monto_Prometido', 'Fecha_Promesa', 'Calificacion_Riesgo']], width='stretch', hide_index=True)

st.sidebar.divider()
audio_input = st.sidebar.audio_input("Grabar Propuesta")

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
            contents=[f"Transcribe y analiza en pocas palabaras el tono. Hoy es {FECHA_HOY_STR}:", types.Part.from_bytes(data=audio_input.read(), mime_type="audio/wav")]
        )
        user_input = f"AUDIO_TRANSCRIPCIÓN: {res_audio.text}"
        st.session_state.last_processed_audio = audio_id

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    guardar_log(c_sel['Nombre'], user_input, "CLIENTE")
    
    with st.spinner("🤖 El Agente está procesando su solicitud..."):
        try:
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

            for part in response.candidates[0].content.parts:
                text_res = ""
                if part.function_call:
                    f = part.function_call.args
                    riesgo = registrar_promesa_api(c_id, f['monto'], f['fecha'])
                    
                    text_res = f"Registro exitoso: ${f['monto']} para el {f['fecha']}. Riesgo: {riesgo}. "
                    
                    res_consejo = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"El cliente agendó para el {f['fecha']} un monto de {f['monto']}. Según tus reglas de negociación, genera un consejo breve sobre su riesgo."
                    )
                    text_res += res_consejo.text

                if text_res:
                    audio_p = texto_a_voz(text_res)
                    st.session_state.messages.append({"role": "assistant", "content": text_res, "audio": audio_p})
                    guardar_log(c_sel['Nombre'], text_res, "AGENTE")
                    st.rerun() 

        except Exception as e:
            st.error(f"Hubo un inconveniente: {e}")