import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyBiGoE_10d6yOzzOehJruXNmK_KAvYOBM4"
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
EXCEL_FILE = "cartera_clientes.xlsx"

# --- PROMPTS ---
PROMPT_SISTEMA = """
Eres un Agente Inteligente de Cobranzas.
Tu objetivo es identificar el MONTO y la FECHA de compromiso de pago.
Consulta siempre el saldo del cliente antes de negociar.
Si el monto ofrecido es bajo, advierte sobre el riesgo crediticio.
"""

# --- FUNCIONES DE BASE DE DATOS ---
def cargar_datos():
    if not os.path.exists(EXCEL_FILE):
        data = {
            'ID': [1, 2],
            'Nombre': ['Juan Perez', 'Maria Garcia'],
            'Deuda_Total': [500.0, 1200.0],
            'Pagos_Realizados': [0.0, 200.0],
            'Monto_Prometido': [0.0, 0.0],
            'Fecha_Promesa': ['', ''],
            'Calificacion_Riesgo': ['Baja', 'Media']
        }
        df = pd.DataFrame(data)
        df.to_excel(EXCEL_FILE, index=False)
    return pd.read_excel(EXCEL_FILE)

def registrar_promesa_api(id_c, monto, fecha):
    df = pd.read_excel(EXCEL_FILE)
    idx = df[df['ID'] == id_c].index
    if not idx.empty:
        deuda = df.loc[idx, 'Deuda_Total'].values[0] - df.loc[idx, 'Pagos_Realizados'].values[0]
        # Análisis de Riesgo: Si paga menos del 40% de la deuda pendiente
        riesgo = "Baja" if monto >= (deuda * 0.4) else "Alta"
        
        df.loc[idx, 'Monto_Prometido'] = monto
        df.loc[idx, 'Fecha_Promesa'] = str(fecha)
        df.loc[idx, 'Calificacion_Riesgo'] = riesgo
        df.to_excel(EXCEL_FILE, index=False)
        return riesgo
    return None

# --- INTERFAZ ---
st.title("Agente Inteligente de Promesas de Pago")

# Cargar datos al inicio de cada renderizado
df_cartera = cargar_datos()

st.subheader("📊 Tabla de Cartera de Clientes")
st.dataframe(df_cartera, use_container_width=True, hide_index=True)

# SIDEBAR
st.sidebar.header("Menú de Gestión")

# SOLUCIÓN: Agregar nuevo cliente y refrescar
with st.sidebar.expander("➕ Agregar Nuevo Cliente"):
    with st.form("form_nuevo"):
        n_nombre = st.text_input("Nombre completo")
        n_deuda = st.number_input("Deuda inicial", min_value=0.0)
        if st.form_submit_button("Registrar Cliente"):
            if n_nombre:
                nuevo_id = int(df_cartera['ID'].max() + 1)
                nuevo_registro = {
                    'ID': nuevo_id, 'Nombre': n_nombre, 'Deuda_Total': n_deuda,
                    'Pagos_Realizados': 0.0, 'Monto_Prometido': 0.0, 
                    'Fecha_Promesa': '', 'Calificacion_Riesgo': 'Baja'
                }
                # Concatenar y guardar inmediatamente
                df_nuevo = pd.concat([df_cartera, pd.DataFrame([nuevo_registro])], ignore_index=True)
                df_nuevo.to_excel(EXCEL_FILE, index=False)
                st.success(f"Cliente {n_nombre} agregado correctamente.")
                st.rerun() # Esto fuerza a la app a leer el Excel otra vez

st.sidebar.divider()
cliente_id = st.sidebar.selectbox("Seleccionar Cliente para Chat:", df_cartera['ID'])
c_sel = df_cartera[df_cartera['ID'] == cliente_id].iloc[0]

# --- LÓGICA DE CHAT POR CLIENTE ---
if "last_client_id" not in st.session_state or st.session_state.last_client_id != cliente_id:
    st.session_state.messages = []
    st.session_state.last_client_id = cliente_id
    saldo = c_sel['Deuda_Total'] - c_sel['Pagos_Realizados']
    st.session_state.messages.append({"role": "assistant", "content": f"Hola {c_sel['Nombre']}, su saldo es de ${saldo}. ¿Cómo desea proceder?"})

for m in st.session_state.messages:
    st.chat_message(m["role"]).write(m["content"])

if prompt := st.chat_input("Escriba su compromiso de pago..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{PROMPT_SISTEMA}\nContexto: {st.session_state.messages[-3:]}\nUsuario: {prompt}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name="registrar_promesa",
                        description="Registra monto y fecha de pago en el sistema",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "monto": {"type": "NUMBER"},
                                "fecha": {"type": "STRING"}
                            },
                            "required": ["monto", "fecha"]
                        }
                    )
                ])]
            )
        )

        for part in res.candidates[0].content.parts:
            if part.function_call:
                # Ejecutar y actualizar visualmente
                args = part.function_call.args
                r_final = registrar_promesa_api(cliente_id, args['monto'], args['fecha'])
                st.session_state.messages.append({"role": "assistant", "content": f" Promesa de ${args['monto']} para el {args['fecha']} registrada. Nivel de Riesgo: {r_final}."})
                st.rerun()
            elif part.text:
                st.session_state.messages.append({"role": "assistant", "content": part.text})
                st.rerun()

    except Exception as e:
        st.error(f"Error de conexión: {e}")