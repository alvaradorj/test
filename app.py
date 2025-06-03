import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Definición de segmentos y regex (igual que en tu script)
tipos_segmento = {"PRÓLOGO", "SS1", "SS2", "REGULARIDAD", "EXCEPCIONALES"}
regex_tramo = re.compile(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d{2}:\s*\d{2}:\s*\d{2}\.\d)')

def extraer_datos_desde_pdf(pdf_bytes):
    datos = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            texto = page.extract_text() or ""
            segmento_actual = ""
            for linea in texto.split("\n"):
                if any(seg in linea.upper() for seg in tipos_segmento):
                    if linea.upper().strip() != "VELOCIDADES MEDIAS EXCEPCIONALES":
                        segmento_actual = next(seg for seg in tipos_segmento if seg in linea.upper())
                match = regex_tramo.search(linea)
                if match:
                    desde, hasta, media, _ = match.groups()
                    label = segmento_actual
                    if page_idx == 1:
                        label = f"{segmento_actual}-EX"
                    datos.append({
                        "Segmento": label,
                        "Desde (km)": float(desde),
                        "Hasta (km)": float(hasta),
                        "Velocidad Media (km/h)": int(media)
                    })
    return datos

st.title("Convertidor PDF → Excel de Tramos")

uploaded_file = st.file_uploader("Sube tu PDF", type="pdf")
if uploaded_file is not None:
    bytes_pdf = uploaded_file.read()
    datos = extraer_datos_desde_pdf(bytes_pdf)
    if not datos:
        st.error("No se encontraron datos válidos o PDF con formato incorrecto.")
    else:
        df = pd.DataFrame(datos, columns=["Segmento", "Desde (km)", "Hasta (km)", "Velocidad Media (km/h)"])
        st.dataframe(df)  # Vista previa
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="Descargar Excel",
            data=towrite,
            file_name="resultado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
