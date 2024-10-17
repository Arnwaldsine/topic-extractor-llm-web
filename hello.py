import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import os
import json
# AWS S3 y Glue configuraciones
S3_BUCKET = 'aws-glue-assets-339713014948-us-east-1'
S3_REGION = 'us-east-1'
GLUE_JOB_NAME = 'topic-extraction-llm'

access_key = os.environ.get('ACCESS_KEY')
secret_access_key = os.environ.get('ACCESS_KEY_SECRET')

# Inicializar clientes AWS
s3_client = boto3.client('s3', region_name=S3_REGION,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_access_key)
glue_client = boto3.client('glue', region_name=S3_REGION,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_access_key)
sm_client = boto3.client('secretsmanager', region_name=S3_REGION,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_access_key)
def get_credentials():
    try:
        # Fetch OpenAI secret
        openai_response = sm_client.get_secret_value(SecretId="openai_key_secret")
        openai_secret = openai_response['SecretString']
        
        # Fetch DB secret and parse the JSON string
        db_secret_response = sm_client.get_secret_value(SecretId="llm-db-secret")
        db_secret = json.loads(db_secret_response['SecretString'])  # Parsing the JSON string into a dictionary
        
    except Exception as e:
        st.error(f"Error al obtener las credenciales de AWS: {e}")
        return None, None

    return openai_secret, db_secret
# Función para subir archivo a S3
def upload_to_s3(uploaded_file):
    file_name = uploaded_file.name
    file_path_in_s3 = f"files/{file_name}"

    try:
        s3_client.upload_fileobj(uploaded_file, S3_BUCKET, file_path_in_s3)
        st.success(f"El archivo fue subido exitosamente a S3: s3://{S3_BUCKET}/{file_path_in_s3}")
        return f"s3://{S3_BUCKET}/{file_path_in_s3}"
    except NoCredentialsError:
        st.error("No se encontraron credenciales de AWS.")
        return None
    except Exception as e:
        st.error(f"Error al subir el archivo a S3: {e}")
        return None

# Función para disparar el job de Glue
def trigger_glue_job(s3_file_path, run_name):

    openai_secret, db_secret = get_credentials()

    try:
        response = glue_client.start_job_run(
            JobName=GLUE_JOB_NAME,
            Arguments={
                '--DB_TOPICS_DBNAME': db_secret['engine'],
                '--DB_TOPICS_HOST' : db_secret['host'],
                '--DB_TOPICS_PASSWORD' : db_secret['password'],
                '--DB_TOPICS_PORT'  : db_secret['port'],
                '--DB_TOPICS_USER' : db_secret['username'],
                '--OPENAI_API_KEY ': db_secret['API_KEY'], 
                '--conversation_text_file': s3_file_path,
                '--execution_id': run_name  # Argumento adicional con el nombre de la corrida
            }
        )
        st.success("¡El job de Glue ha comenzado exitosamente!")
        st.json(response)
    except Exception as e:
        st.error(f"Error al iniciar el job de Glue: {e}")

# Navegación entre páginas
def main():
    st.sidebar.title("Navegación")
    page = st.sidebar.radio("Ir a", ["Bienvenida", "Subir archivo para análisis"])

    if page == "Bienvenida":
        show_welcome_page()
    elif page == "Subir archivo para análisis":
        show_upload_page()

# Página de presentación pomposa
def show_welcome_page():
    st.markdown("""
    <style>
        p {
            color: #555;        
        }
        .big-font {
            font-size:60px !important;
            color: #4CAF50;
            font-weight: bold;
        }
        .medium-font {
            font-size:40px !important;
            color: #009688;
        }
        .intro-paragraph {
            font-size: 24px;
            color: whitesmoke;
            font-weight: 400;
        }
        .benefit-list {
            font-size: 20px;
            color: whitesmoke;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-font">Mejore la experiencia del cliente con análisis conversacional</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="intro-paragraph">
    Bienvenido a nuestra plataforma innovadora, donde podrá transformar su negocio mediante la obtención de conocimientos profundos 
    a partir de las conversaciones con sus clientes. Aproveche el verdadero potencial de sus datos y lleve la experiencia del cliente al siguiente nivel.
    </div>
    <br>
    """, unsafe_allow_html=True)

    st.markdown('<p class="medium-font">¿Por qué análisis conversacional?</p>', unsafe_allow_html=True)

    st.markdown("""
    <ul class="benefit-list">
        <li><strong>Análisis de Sentimientos:</strong> Descubra cómo se sienten los clientes acerca de sus productos o servicios.</li>
        <li><strong>Identificación de Temáticas Clave:</strong> Encuentre patrones recurrentes y temas importantes en las conversaciones.</li>
        <li><strong>Mejora en la Atención al Cliente:</strong> Detecte problemas de manera proactiva y resuélvalos antes de que se agraven.</li>
    </ul>
    <br>
    <div class="intro-paragraph">
    ¿Listo para analizar? Suba sus archivos de texto conversacional ahora y permita que nuestras herramientas de análisis avanzado hagan el resto por usted.
    </div>
    """, unsafe_allow_html=True)

# Página de subida de archivo
def show_upload_page():
    st.title("Suba su archivo de texto conversacional para análisis")

    # Input para el nombre de identificar el lote
    run_name = st.text_input("Ingrese el nombre para identificar el lote")

    uploaded_file = st.file_uploader("Elija un archivo de texto", type="txt")
    
    if uploaded_file is not None and run_name:
        s3_file_path = upload_to_s3(uploaded_file)
        
        if s3_file_path:
            st.write("Iniciando job de Glue para el análisis...")
            trigger_glue_job(s3_file_path, run_name)
    elif not run_name:
        st.warning("Por favor, ingrese un nombre para identificar el lote.")

if __name__ == '__main__':
    main()