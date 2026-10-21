import os
import re
import html
import base64
import hashlib
import fitz
import streamlit as st
from dotenv import load_dotenv
from google import genai

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="Bobolo | Asistente Industrial",
    page_icon="🐤",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

COLORES_DEFAULT = {
    "Fondo principal": "#FFF2E8",
    "Barra lateral": "#B94F5B",
    "Tarjetas": "#FFFBF7",
    "Botones": "#EBA09A",
    "Títulos": "#613632",
    "Texto secundario": "#765650",
    "Avisos": "#FFE2D2",
}

COLORES_OSCUROS = {
    "Fondo principal": "#191719",
    "Barra lateral": "#713741",
    "Tarjetas": "#272327",
    "Botones": "#62404A",
    "Títulos": "#F3DCD8",
    "Texto secundario": "#D0BFC0",
    "Avisos": "#3C2D34",
}

if "colores" not in st.session_state:
    st.session_state.colores = COLORES_DEFAULT.copy()

if "modo_visual" not in st.session_state:
    st.session_state.modo_visual = "Claro"

for clave, valor in {
    "nombre_documento": "",
    "paginas_documento": [],
    "documento_bytes": None,
    "documento_id": None,
    "mensajes": [],
    "navigation": "Inicio",
    "estado_documento": "Sin documento",
    "pregunta_inicio": "",
    "respuesta_inicio": None,
    "paginas_citadas": [],
}.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor


# =====================================================
# FUNCIONES AUXILIARES PARA IMÁGENES
# =====================================================

def obtener_imagen_base64(nombre_archivo):
    """Busca una imagen local y la retorna en formato base64 para HTML."""
    for ext in [".jpg", ".jpeg", ".png"]:
        ruta = nombre_archivo + ext
        if os.path.exists(ruta):
            with open(ruta, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
                return f"data:image/{ext.replace('.', '')};base64,{encoded}"
    return None


# =====================================================
# ESTILOS
# =====================================================

def aplicar_estilos():
    # El modo oscuro utiliza una paleta propia.
    # El modo claro conserva los colores personalizables.
    if st.session_state.get("modo_visual", "Claro") == "Oscuro":
        c = COLORES_OSCUROS
        oscuro = True
    else:
        c = st.session_state.colores
        oscuro = False

    color_borde = "#45373E" if oscuro else "rgba(120, 65, 60, 0.18)"
    sombra = (
        "0 4px 14px rgba(0, 0, 0, 0.16)"
        if oscuro
        else "0 4px 14px rgba(90, 48, 42, 0.045)"
    )
    color_boton_texto = "#FFFFFF" if oscuro else "#452923"
    color_borde_hover = c["Barra lateral"]

    st.markdown(
        f"""
        <style>
        :root {{
            --fondo: {c["Fondo principal"]};
            --lateral: {c["Barra lateral"]};
            --tarjeta: {c["Tarjetas"]};
            --boton: {c["Botones"]};
            --titulo: {c["Títulos"]};
            --secundario: {c["Texto secundario"]};
            --aviso: {c["Avisos"]};
            color-scheme: {"dark" if oscuro else "light"};
        }}

        /* FONDO Y TEXTO GENERAL */

        .stApp,
        [data-testid="stAppViewContainer"] {{
            background: var(--fondo) !important;
            color: var(--titulo) !important;
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        [data-testid="stMain"] {{
            background: var(--fondo) !important;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: var(--titulo) !important;
        }}

        p, label, [data-testid="stCaptionContainer"] {{
            color: var(--secundario);
        }}

        [data-testid="stMarkdownContainer"] {{
            color: var(--titulo);
        }}

        /* BARRA LATERAL */

        [data-testid="stSidebar"] {{
            background: var(--lateral) !important;
        }}

        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {{
            color: #FFFFFF;
        }}

        [data-testid="stSidebar"] [data-baseweb="radio"] label {{
            background: transparent;
            border-radius: 8px;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background: var(--tarjeta) !important;
            border-color: {color_borde} !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] * {{
            color: var(--titulo) !important;
        }}

        /* TARJETAS */

        .bobolo-card {{
            box-sizing: border-box;
            background: var(--tarjeta);
            border: 1px solid {color_borde};
            border-radius: 20px;
            padding: 22px;
            margin-bottom: 18px;
            box-shadow: {sombra};
            overflow-wrap: anywhere;
        }}

        .bobolo-header {{
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }}

        .bobolo-name {{
            color: var(--lateral) !important;
            font-size: 29px;
            font-weight: 800;
            margin: 0;
        }}

        .bobolo-subtitle {{
            color: var(--secundario) !important;
            font-size: 14px;
            margin-top: 4px;
        }}

        .bobolo-status {{
            display: inline-block;
            background: var(--aviso);
            color: var(--titulo) !important;
            padding: 8px 13px;
            border-radius: 22px;
            font-size: 12px;
            font-weight: 800;
        }}

        .bobolo-alert {{
            background: var(--aviso);
            color: var(--titulo) !important;
            padding: 13px 16px;
            border-radius: 13px;
            margin: 12px 0 18px;
            font-size: 14px;
            overflow-wrap: anywhere;
        }}

        .bobolo-alert *,
        .bobolo-status * {{
            color: var(--titulo) !important;
        }}

        .bobolo-mini-title {{
            color: var(--titulo) !important;
            font-weight: 800;
            font-size: 17px;
            margin-bottom: 7px;
        }}

        .bobolo-footnote {{
            color: var(--secundario) !important;
            font-size: 12px;
            line-height: 1.6;
        }}

        /* IMÁGENES: SE CONSERVAN LOS TAMAÑOS ACTUALES */

        .bobolo-mascota-img {{
            display: block;
            margin: 0 auto;
            max-width: 100px;
            width: 100%;
            height: auto;
            object-fit: contain;
            border-radius: 16px;
        }}

        .bobolo-avatar-img {{
            width: 50px;
            height: 50px;
            object-fit: contain;
            border-radius: 50%;
        }}

        .bobolo-sidebar-img {{
            width: 160px;
            height: 160px;
            max-width: 100%;
            object-fit: contain;
            border-radius: 50%;
            margin-bottom: 8px;
        }}

        /* BOTONES */

        .stButton > button,
        .stFormSubmitButton > button {{
            background: var(--boton) !important;
            color: {color_boton_texto} !important;
            border: 1px solid {color_borde};
            border-radius: 12px;
            min-height: 42px;
            height: auto;
            font-weight: 700;
            white-space: normal;
            overflow-wrap: anywhere;
        }}

        .stButton > button *,
        .stFormSubmitButton > button * {{
            color: {color_boton_texto} !important;
        }}

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{
            background: {color_borde_hover} !important;
            color: #FFFFFF !important;
            border-color: {color_borde_hover} !important;
        }}

        .stButton > button:hover *,
        .stFormSubmitButton > button:hover * {{
            color: #FFFFFF !important;
        }}

        /* CAMPOS DE TEXTO Y SELECTORES */

        input,
        textarea,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {{
            background: var(--tarjeta) !important;
            color: var(--titulo) !important;
            border-color: {color_borde} !important;
        }}

        [data-baseweb="select"] > div {{
            background: var(--tarjeta) !important;
            border-color: {color_borde} !important;
        }}

        [data-baseweb="select"] * {{
            color: var(--titulo) !important;
        }}

        [data-testid="stFileUploader"] {{
            background: var(--tarjeta) !important;
            color: var(--titulo) !important;
            border-radius: 13px;
            padding: 8px;
        }}

        [data-testid="stFileUploader"] * {{
            color: var(--titulo);
        }}

        [data-testid="stChatInput"] {{
            border-radius: 13px;
        }}

        [data-testid="stChatInput"] textarea {{
            background: var(--tarjeta) !important;
            color: var(--titulo) !important;
        }}

        [data-testid="stExpander"] {{
            background: var(--tarjeta);
            border-color: {color_borde} !important;
            border-radius: 13px;
        }}

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p {{
            color: var(--titulo) !important;
        }}

        /* MENSAJES DEL CHAT */

        [data-testid="stChatMessage"] {{
            background: var(--tarjeta);
            border-radius: 14px;
        }}

        /* DISTRIBUCIÓN */

        [data-testid="stMainBlockContainer"] {{
            padding-bottom: 4rem;
            max-width: 1500px;
        }}

        hr {{
            border-color: {color_borde} !important;
        }}

        /* MENÚ DESPLEGABLE */

        [data-baseweb="popover"],
        [data-baseweb="menu"] {{
            background: var(--tarjeta) !important;
        }}

        [role="option"] {{
            background: var(--tarjeta) !important;
            color: var(--titulo) !important;
        }}

        [role="option"]:hover {{
            background: var(--aviso) !important;
        }}

        /* DISEÑO ADAPTABLE PARA PANTALLAS PEQUEÑAS */

        @media (max-width: 700px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-left: 0.8rem;
                padding-right: 0.8rem;
                padding-top: 1rem;
            }}

            .bobolo-card {{
                padding: 15px;
                border-radius: 15px;
                margin-bottom: 13px;
            }}

            .bobolo-header {{
                gap: 10px;
            }}

            .bobolo-name {{
                font-size: 25px;
            }}

            .bobolo-subtitle {{
                font-size: 13px;
            }}

            .bobolo-mascota-img {{
                max-width: 85px;
            }}

            .bobolo-avatar-img {{
                width: 42px;
                height: 42px;
            }}

            .bobolo-sidebar-img {{
                width: 110px;
                height: 110px;
            }}

            .stButton > button,
            .stFormSubmitButton > button {{
                width: 100%;
                min-height: 44px;
                font-size: 14px;
            }}

            h1 {{
                font-size: 1.8rem !important;
            }}

            h2 {{
                font-size: 1.5rem !important;
            }}

            h3 {{
                font-size: 1.25rem !important;
            }}
        }}

        @media (max-width: 400px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-left: 0.55rem;
                padding-right: 0.55rem;
            }}

            .bobolo-card {{
                padding: 12px;
            }}

            .bobolo-name {{
                font-size: 23px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# ESTADO DEL DOCUMENTO
# =====================================================

def actualizar_estado():
    if st.session_state.estado_documento == "Procesando":
        return

    if st.session_state.paginas_documento:
        st.session_state.estado_documento = "Cargado"
    else:
        st.session_state.estado_documento = "Sin documento"


def mostrar_estado():
    estado = st.session_state.estado_documento

    iconos = {
        "Sin documento": "⚪",
        "Procesando": "🟠",
        "Cargado": "🟢",
    }

    st.markdown(
        f"""
        <span class="bobolo-status">
            {iconos.get(estado, "⚪")} {html.escape(estado)}
        </span>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# LECTURA DE PDF
# =====================================================

def extraer_paginas(pdf_bytes):
    paginas = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for numero, pagina in enumerate(pdf, start=1):
            paginas.append({
                "numero": numero,
                "texto": pagina.get_text("text").strip(),
            })

    return paginas


def cargar_documento(archivo):
    if archivo is None:
        return

    pdf_bytes = archivo.getvalue()
    identificador = hashlib.sha256(pdf_bytes).hexdigest()

    if identificador == st.session_state.documento_id:
        return

    st.session_state.estado_documento = "Procesando"

    try:
        with st.spinner("Procesando el documento..."):
            paginas = extraer_paginas(pdf_bytes)

        if not paginas or not any(p["texto"] for p in paginas):
            st.session_state.estado_documento = "Sin documento"
            st.error(
                "El PDF no contiene texto extraíble. "
                "Si es un documento escaneado, necesitará OCR."
            )
            return

        st.session_state.documento_bytes = pdf_bytes
        st.session_state.nombre_documento = archivo.name
        st.session_state.paginas_documento = paginas
        st.session_state.documento_id = identificador
        st.session_state.mensajes = []
        st.session_state.respuesta_inicio = None
        st.session_state.estado_documento = "Cargado"

        st.success(
            f"Documento cargado: {archivo.name} "
            f"({len(paginas)} páginas)"
        )

    except Exception as error:
        print(f"Error al leer PDF: {error}")
        st.session_state.estado_documento = "Sin documento"
        st.error("No se pudo procesar el PDF. Prueba con otro archivo.")


def quitar_documento():
    st.session_state.nombre_documento = ""
    st.session_state.paginas_documento = []
    st.session_state.documento_bytes = None
    st.session_state.documento_id = None
    st.session_state.mensajes = []
    st.session_state.respuesta_inicio = None
    st.session_state.paginas_citadas = []
    st.session_state.estado_documento = "Sin documento"


# =====================================================
# SELECCIÓN DE PÁGINAS RELEVANTES
# =====================================================

def buscar_paginas_relevantes(pregunta, paginas, limite=8):
    palabras = set(
        re.findall(r"\w+", pregunta.lower(), flags=re.UNICODE)
    )
    palabras = {p for p in palabras if len(p) > 2}

    if not palabras:
        return []

    puntuadas = []

    for pagina in paginas:
        texto = pagina["texto"].lower()

        if not texto.strip():
            continue

        puntuacion = sum(
            len(re.findall(r"\b" + re.escape(palabra) + r"\b", texto))
            for palabra in palabras
        )

        if puntuacion:
            puntuadas.append((puntuacion, pagina))

    puntuadas.sort(key=lambda x: x[0], reverse=True)

    return [pagina for _, pagina in puntuadas[:limite]]


# =====================================================
# CONSULTAS Y CITAS
# =====================================================

def consultar_bobolo(pregunta):
    if not st.session_state.paginas_documento:
        return (
            "Primero debes cargar un documento PDF "
            "en la sección Documentos."
        ), []

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return (
            "No se encuentra configurada la conexión del asistente. "
            "Comprueba el archivo .env sin compartir tu clave."
        ), []

    relevantes = buscar_paginas_relevantes(
        pregunta,
        st.session_state.paginas_documento,
    )

    if not relevantes:
        return (
            "No encontré páginas con texto relacionado con esa pregunta. "
            "Prueba con otros términos o revisa el documento."
        ), []

    contexto = "\n\n".join(
        f"===== PÁGINA {p['numero']} =====\n{p['texto']}"
        for p in relevantes
    )

    numeros_paginas = [p["numero"] for p in relevantes]

    instruccion = f"""
Eres Bobolo, un asistente de consulta de documentación industrial.

REGLAS:
- Responde en español, de forma clara y técnica.
- Usa exclusivamente el contexto del documento proporcionado.
- No inventes especificaciones, procedimientos, normas ni valores.
- Si la información no está en el contexto, dilo con claridad.
- Cuando uses un dato, indica la página que lo respalda con el formato
  [Página N].
- Solo puedes citar números de página que aparezcan en los encabezados
  del contexto proporcionado.
- No confundas una inferencia con una instrucción explícita.
- Si la pregunta trata sobre seguridad y el documento no contiene
  suficiente información, advierte esa limitación.
- No presentes una respuesta como confirmada si no está respaldada
  por el texto.

PÁGINAS DISPONIBLES:
{numeros_paginas}

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}
"""

    try:
        cliente = genai.Client(api_key=api_key)

        respuesta = cliente.models.generate_content(
            model="gemini-3.8-flash",
            contents=instruccion,
        )

        texto = getattr(respuesta, "text", None)

        if not texto:
            return "No se obtuvo una respuesta. Intenta nuevamente.", []

        return texto, numeros_paginas

    except Exception as error:
        print("\n========== ERROR DE BOBOLO ==========")
        print("Tipo de error:", type(error).__name__)
        print("Detalle:", str(error))
        print("=====================================\n")

        return (
            f"Error de consulta: {type(error).__name__}. "
            "Revisa la terminal de Python para ver el detalle."
        ), []


def mostrar_citas(paginas):
    if not paginas:
        return

    citas = ", ".join(f"[Página {n}]" for n in sorted(paginas))

    st.markdown(
        f"""
        <div class="bobolo-alert">
            <strong>📚 Páginas de referencia</strong><br>
            {html.escape(citas)}
            <div class="bobolo-footnote">
                Son las páginas del PDF seleccionadas como contexto
                para esta respuesta; comprueba el contenido original
                antes de aplicar instrucciones técnicas.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def procesar_pregunta(pregunta, destino):
    pregunta = pregunta.strip()

    if not pregunta:
        return

    if not st.session_state.paginas_documento:
        st.warning("Carga un PDF antes de hacer una consulta.")
        return

    st.session_state.estado_documento = "Procesando"

    with st.spinner("Consultando la documentación..."):
        respuesta, paginas = consultar_bobolo(pregunta)

    st.session_state.estado_documento = "Cargado"

    if destino == "inicio":
        st.session_state.respuesta_inicio = {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "paginas": paginas,
        }
    else:
        st.session_state.mensajes.append({
            "role": "user",
            "content": pregunta,
        })
        st.session_state.mensajes.append({
            "role": "assistant",
            "content": respuesta,
            "paginas": paginas,
        })


# =====================================================
# CABECERA
# =====================================================

def mostrar_cabecera():
    b64_cara = obtener_imagen_base64("pato_cara")
    if b64_cara:
        avatar_html = f'<img src="{b64_cara}" class="bobolo-avatar-img" alt="Bobolo">'
    else:
        avatar_html = '<div style="font-size:25px;">🐤</div>'

    st.markdown(
        f"""
        <div class="bobolo-card">
          <div class="bobolo-header">
            <div>{avatar_html}</div>
            <div>
              <p class="bobolo-name">Bobolo</p>
              <div class="bobolo-subtitle">
                Tu asistente para el mundo industrial
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mostrar_estado()


# =====================================================
# CARGA REUTILIZABLE
# =====================================================

def zona_carga(clave):
    st.markdown(
        """
        <div class="bobolo-card">
          <div class="bobolo-mini-title">
            📄 Documento de trabajo
          </div>
          Arrastra un PDF a la zona de carga o selecciónalo desde tu equipo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    archivo = st.file_uploader(
        "Seleccionar documento PDF",
        type=["pdf"],
        key=clave,
        help="Puedes arrastrar el PDF directamente a esta zona.",
    )

    if archivo is not None:
        cargar_documento(archivo)


# =====================================================
# VISTA PREVIA DEL DOCUMENTO
# =====================================================

def mostrar_vista_previa():
    if not st.session_state.documento_bytes:
        return

    with st.expander("👀 Vista previa del PDF", expanded=False):
        paginas = st.session_state.paginas_documento

        numero = st.selectbox(
            "Página que deseas consultar",
            options=list(range(1, len(paginas) + 1)),
            key="pagina_previa",
        )

        pagina = paginas[numero - 1]

        st.caption(f"Página {numero} de {len(paginas)}")

        if pagina["texto"]:
            st.text_area(
                "Texto extraído de esta página",
                value=pagina["texto"],
                height=260,
                disabled=True,
                key=f"texto_previo_{numero}_{st.session_state.documento_id[:8]}",
            )
        else:
            st.info(
                "No se extrajo texto de esta página. "
                "Podría contener imágenes o un escaneo."
            )

        st.download_button(
            "Descargar PDF original",
            data=st.session_state.documento_bytes,
            file_name=st.session_state.nombre_documento,
            mime="application/pdf",
            key="descargar_pdf",
        )


# =====================================================
# INICIO
# =====================================================

def mostrar_inicio():
    mostrar_cabecera()

    izquierda, derecha = st.columns(
        [1.25, 0.85],
        gap="large",
    )

    with izquierda:
        st.markdown(
            """
            <div class="bobolo-card">
              <p style="font-weight:800;">¡Hola!</p>
              <h1 style="font-size:40px;line-height:1.1;margin:0;">
                Soy Bobolo
              </h1>
              <p style="font-size:16px;margin-top:16px;">
                Consulta manuales, procedimientos y documentación técnica
                desde un solo lugar.
              </p>
              <div class="bobolo-alert">
                ⚙️ Mis respuestas se basan en el documento que cargues.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        zona_carga("pdf_inicio")

    with derecha:
        b64_pato = obtener_imagen_base64("pato")
        if b64_pato:
            img_html = f'<img src="{b64_pato}" class="bobolo-mascota-img" alt="Bobolo">'
        else:
            img_html = '<div style="text-align:center;font-size:90px;">🐤</div>'

        st.markdown(
            f"""
            <div class="bobolo-card" style="text-align: center;">
              {img_html}
              <p style="text-align:center;font-size:18px;font-weight:800;margin-top:12px;">
                ¡Listo para ayudarte!
              </p>
              <p style="text-align:center;">
                Carga un PDF y empieza a consultar su contenido.
              </p>
              <p style="text-align:center;font-size:22px;">
                ⚙️ 📐 📄
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.paginas_documento:
        st.markdown("### Consulta rápida")

        st.caption(
            "Puedes escribir una pregunta o elegir una de las sugerencias."
        )

        sugerencias = [
            "Resume el contenido del documento.",
            "¿Qué medidas de seguridad se mencionan?",
            "¿Qué procedimiento describe?",
            "¿Qué especificaciones técnicas aparecen?",
        ]

        columnas = st.columns(2)

        for i, sugerencia in enumerate(sugerencias):
            with columnas[i % 2]:
                if st.button(
                    sugerencia,
                    key=f"sugerencia_inicio_{i}",
                    use_container_width=True,
                ):
                    procesar_pregunta(sugerencia, "inicio")

        with st.form("form_consulta_rapida", clear_on_submit=True):
            pregunta = st.text_input(
                "Tu pregunta",
                placeholder="Ej.: ¿Qué indica el manual sobre el mantenimiento?",
            )

            enviar = st.form_submit_button(
                "Consultar a Bobolo",
                use_container_width=True,
            )

        if enviar and pregunta.strip():
            procesar_pregunta(pregunta, "inicio")

        if st.session_state.respuesta_inicio:
            resultado = st.session_state.respuesta_inicio

            st.markdown("### Respuesta")
            st.markdown(f"**Pregunta:** {resultado['pregunta']}")
            st.markdown(resultado["respuesta"])
            mostrar_citas(resultado["paginas"])

            if st.button(
                "Continuar en el chat",
                key="continuar_chat",
            ):
                st.session_state.navigation = "Chat"
                st.rerun()

        mostrar_vista_previa()

        if st.button("Quitar documento", key="inicio_quitar"):
            quitar_documento()
            st.rerun()

    else:
        st.info(
            "El chat y las consultas rápidas estarán disponibles "
            "cuando cargues un documento PDF."
        )

    st.markdown("---")
    st.caption(
        "Prototipo demostrativo para consultas sobre documentación técnica."
    )


# =====================================================
# DOCUMENTOS
# =====================================================

def mostrar_documentos():
    mostrar_cabecera()
    st.title("Documentos")

    st.write(
        "Carga la documentación que servirá como fuente para las respuestas."
    )

    zona_carga("pdf_documentos")

    if st.session_state.nombre_documento:
        st.markdown(
            f"""
            <div class="bobolo-card">
              <div class="bobolo-mini-title">📄 Documento activo</div>
              {html.escape(st.session_state.nombre_documento)}<br>
              <p class="bobolo-small">
                {len(st.session_state.paginas_documento)} páginas detectadas
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mostrar_vista_previa()

        if st.button("Quitar documento", key="documentos_quitar"):
            quitar_documento()
            st.rerun()
    else:
        st.info("Todavía no has cargado un documento.")


# =====================================================
# CHAT
# =====================================================

def mostrar_chat():
    mostrar_cabecera()
    st.title("Chat con Bobolo")

    if not st.session_state.paginas_documento:
        st.warning(
            "Primero debes cargar un PDF para habilitar las consultas."
        )

        if st.button("Ir a Documentos", key="chat_ir_documentos"):
            st.session_state.navigation = "Documentos"
            st.rerun()

        return

    st.markdown(
        f"""
        <div class="bobolo-alert">
            📄 Documento activo:
            <strong>{html.escape(st.session_state.nombre_documento)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Preguntas sugeridas")

    sugerencias = [
        "Resume el documento.",
        "¿Qué medidas de seguridad indica?",
        "¿Qué pasos tiene el procedimiento?",
        "¿Qué especificaciones técnicas aparecen?",
    ]

    columnas = st.columns(2)

    for i, sugerencia in enumerate(sugerencias):
        with columnas[i % 2]:
            if st.button(
                sugerencia,
                key=f"sugerencia_chat_{i}",
                use_container_width=True,
            ):
                procesar_pregunta(sugerencia, "chat")
                st.rerun()

    for i, mensaje in enumerate(st.session_state.mensajes):
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

            if mensaje["role"] == "assistant":
                mostrar_citas(mensaje.get("paginas", []))

    pregunta = st.chat_input(
        "Escribe tu consulta sobre el documento..."
    )

    if pregunta:
        procesar_pregunta(pregunta, "chat")
        st.rerun()


# =====================================================
# CONFIGURACIÓN VISUAL
# =====================================================

def mostrar_configuracion():
    mostrar_cabecera()
    st.title("Personalización")

    st.write("Modifica los colores de los elementos de la interfaz.")

    for nombre in COLORES_DEFAULT:
        clave = f"color_{nombre}"

        if clave not in st.session_state:
            st.session_state[clave] = st.session_state.colores[nombre]

        st.session_state.colores[nombre] = st.color_picker(
            nombre,
            key=clave,
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Aplicar cambios"):
            st.rerun()

    with col2:
        if st.button("Restaurar colores originales"):
            st.session_state.colores = COLORES_DEFAULT.copy()

            for nombre, color in COLORES_DEFAULT.items():
                st.session_state[f"color_{nombre}"] = color

            st.rerun()


# =====================================================
# BARRA LATERAL
# =====================================================

aplicar_estilos()

with st.sidebar:
    # Selector de apariencia independiente del menú de Streamlit.
    st.selectbox(
        "🎨 Apariencia de Bobolo",
        ["Claro", "Oscuro"],
        key="modo_visual",
    )

    st.markdown("---")

    b64_sidebar_cara = obtener_imagen_base64("pato_cara")
    if b64_sidebar_cara:
        sidebar_img_html = f'<img src="{b64_sidebar_cara}" class="bobolo-sidebar-img" alt="Bobolo">'
    else:
        sidebar_img_html = '<div style="font-size:54px;">🐤</div>'

    st.markdown(
        f"""
        <div style="text-align:center;padding:15px 4px 20px;">
          {sidebar_img_html}
          <div style="font-size:28px;font-weight:800;color:#FFFFFF;">
            Bobolo
          </div>
          <div style="font-size:13px;color:#FFFFFF;">
            Asistente industrial
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    pagina = st.radio(
        "MENÚ PRINCIPAL",
        ["Inicio", "Documentos", "Chat", "Configuración"],
        key="navigation",
    )

    st.markdown("---")

    if st.session_state.nombre_documento:
        st.markdown("**Documento activo**")
        st.caption(st.session_state.nombre_documento)
    else:
        st.caption("No hay documentos cargados.")

    st.markdown("---")

    st.caption("Prototipo demostrativo")


# =====================================================
# NAVEGACIÓN
# =====================================================

if pagina == "Inicio":
    mostrar_inicio()

elif pagina == "Documentos":
    mostrar_documentos()

elif pagina == "Chat":
    mostrar_chat()

elif pagina == "Configuración":
    mostrar_configuracion()