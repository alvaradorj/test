import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Segmentos conocidos
tipos_segmento = {"PRÓLOGO", "SS1", "SS2", "REGULARIDAD", "EXCEPCIONALES"}
regex_tramo = re.compile(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d{2}:\s*\d{2}:\s*\d{2}\.?\d*)')

def extraer_datos_desde_pdf(pdf_bytes):
    datos = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            w, h = page.width, page.height
            mid_x = w / 2
            solap = 5
            izq = page.crop((0, 0, mid_x + solap, h))
            der = page.crop((mid_x - solap, 0, w, h))
            segmento = ""
            for col in (izq, der):
                texto = col.extract_text() or ""
                for linea in texto.split("\n"):
                    may = linea.upper()
                    for seg in tipos_segmento:
                        if seg in may:
                            segmento = seg
                            break
                    match = regex_tramo.search(linea)
                    if match and segmento:
                        desde, hasta, media, _ = match.groups()
                        label = segmento
                        if segmento.upper() == "EXCEPCIONALES" or page_idx == 1:
                            label = f"{segmento}-EX"
                        datos.append({
                            "Segmento": label,
                            "Desde (km)": float(desde.replace(",", ".")),
                            "Hasta (km)": float(hasta.replace(",", ".")),
                            "Velocidad Media (km/h)": int(media)
                        })
    return datos

st.title("Convertidor PDF → Excel de Tramos")
st.markdown("Carga un PDF y obtén un Excel con columnas formateadas a 2 decimales.")

uploaded = st.file_uploader("Sube tu archivo PDF", type="pdf")
if uploaded is not None:
    pdf_bytes = uploaded.read()
    datos = extraer_datos_desde_pdf(pdf_bytes)
    if not datos:
        st.error("No se encontraron datos válidos en el PDF (o el formato es incorrecto).")
    else:
        df = pd.DataFrame(datos, columns=["Segmento", "Desde (km)", "Hasta (km)", "Velocidad Media (km/h)"])
        # Forzar dos decimales en Desde y Hasta:
        df["Desde (km)"] = df["Desde (km)"].map(lambda x: f"{x:.2f}")
        df["Hasta (km)"] = df["Hasta (km)"].map(lambda x: f"{x:.2f}")

        st.dataframe(df)  # Vista previa
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=buffer,
            file_name="resultado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
