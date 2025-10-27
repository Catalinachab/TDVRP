import streamlit as st
import zipfile
import os
import tempfile
import json
import pandas as pd

st.title("Cargador de instancias y soluciones óptimas. Las instancias son jsons con el formato C100_50 siendo " \
"C si es combinado, R si es random o RC si es ambas, seguido del numero de instancia, y seguido del numero de clientes que tiene esa instancia")

# Subida de archivos
instancias_zip = st.file_uploader("Subí el ZIP de instancias (.zip)", type="zip")
soluciones_file = st.file_uploader("Subí el archivo de soluciones (.json)", type="json")

if instancias_zip and soluciones_file:
    # Crear carpeta temporal
    tmp_dir = tempfile.mkdtemp()
    inst_dir = os.path.join(tmp_dir, "instancias")
    os.makedirs(inst_dir, exist_ok=True)

    # Extraer ZIP de instancias
    with zipfile.ZipFile(instancias_zip, "r") as zip_ref:
        zip_ref.extractall(inst_dir)
    st.success("✅ Archivos de instancias descomprimidos correctamente")

    # Cargar soluciones
    soluciones = json.load(soluciones_file)