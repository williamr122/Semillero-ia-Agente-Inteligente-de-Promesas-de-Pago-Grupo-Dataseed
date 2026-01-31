Tema:
Agente IA [Agente Inteligente de Promesas de Pago]

Integrantes
Rosado Rodriguez William Ariel (@williamr122)

1. DESCRIPCIÓN
   Nuestro agente IA permite una negociación, donde el cliente puede proponer montos y fechas de pago de forma natural (ej: "pago el próximo lunes", "pago el próximo mes", "pago el próximo año"), y el sistema se encarga de estructurar bien esa información. El agente interactúa mediante texto y voz, procesa y actualiza automáticamente una base de datos en Excel, evaluando el riesgo crediticio en tiempo real.

2. ANÁLISIS
   Registro de promesas de pago mediante texto o voz
   Cálculo automático de riesgo basado en el porcentaje de abono (Umbral del 40%).
   Conversión de lenguaje natural a fechas reales.
   Requerimientos: El sistema debe ser capaz de "recordar" lo dicho en la conversación y persistir los datos en un Excel.
   El sistema captura audio, lo transcribe y analiza el tono emocional.
   Seguridad: No se exponen llaves API; se gestionan mediante variables de entorno con python-dotenv.

3. DISEÑO
   Tecnologías: Streamlit: Interfaz de usuario.
   Google GenAI: Procesamiento multimodal (Texto/Audio).
   gTTS: Respuesta por voz.
   Pandas: Manejo de base de datos en Excel.
   Pytest: Aseguramiento de calidad (QA).

4. Para ejecutar el proyecto, siga estos pasos:

Ejecución:

4.1 Crear y activar el Entorno Virtual
python -m venv venv
.\venv\Scripts\activate

4.2 Instalar dependencias
pip install -r requirements.txt

4.3 Configuración de Api Key
edita el archivo (.env-ejemplo) a (.env)
dentro de ese archivo se debe agregar la clave: GOOGLE_API_KEY=SU_API_AQUI.

4.4 Ejecutar la aplicación
streamlit run src/main.py

4.5 Ejecutar Pruebas (Opcional)
Para verificar que la lógica de riesgo y la base de datos funcionan correctamente:
python -m pytest tests/test.py

Link del video: youtube, Google Drive.
