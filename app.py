import pdfplumber
import pandas as pd
import re
import io
from pathlib import Path

# Intentar detectar Streamlit
try:
    import streamlit as st
    EN_STREAMLIT = True
except ImportError:
    EN_STREAMLIT = False

# Detectar entorno Colab
try:
    from google.colab import files
    EN_COLAB = True
except ImportError:
    EN_COLAB = False

# Segmentos conocidos
tipos_segmento = {"PRÓLOGO", "SS1", "SS2", "REGULARIDAD", "EXCEPCIONALES"}

# Expresión regular para detectar líneas con datos
regex_tramo = re.compile(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d{2}:\s*\d{2}:\s*\d{2}\.\d*)')

def extraer_datos_desde_pdf(pdf_source):
    datos = []
    fuente = io.BytesIO(pdf_source) if EN_COLAB or EN_STREAMLIT else pdf_source
    try:
        pdf = pdfplumber.open(fuente)
    except Exception:
        return []
    with pdf:
        for page_idx, page in enumerate(pdf.pages):
            width, height = page.width, page.height
            mid_x = width / 2
            solap = 5
            izq = page.crop((0, 0, mid_x + solap, height))
            der = page.crop((mid_x - solap, 0, width, height))
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

# Función para formatear dos decimales en DataFrame
def formatear_decimal(df):
    df["Desde (km)"] = df["Desde (km)"].map(lambda x: f"{x:.2f}")
    df["Hasta (km)"] = df["Hasta (km)"].map(lambda x: f"{x:.2f}")
    return df

# Lógica principal para Streamlit
if EN_STREAMLIT:
    st.title("Convertidor PDF → Excel de Tramos")
    st.markdown("Carga un PDF y descarga un Excel con formato de 2 decimales.")
    uploaded = st.file_uploader("Sube tu archivo PDF", type="pdf")
    if uploaded is not None:
        pdf_bytes = uploaded.read()
        datos = extraer_datos_desde_pdf(pdf_bytes)
        if not datos:
            st.error("No se encontraron datos válidos o formato incorrecto.")
        else:
            df = pd.DataFrame(datos, columns=["Segmento", "Desde (km)", "Hasta (km)", "Velocidad Media (km/h)"])
            df = formatear_decimal(df)
            st.dataframe(df)
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            st.download_button(
                label="⬇️ Descargar Excel",
                data=buffer,
                file_name="resultado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
# Lógica principal para Colab
elif EN_COLAB:
    print("📤 Sube tu PDF:")
    archivos = files.upload()
    if archivos:
        clave = next(iter(archivos))
        datos = extraer_datos_desde_pdf(archivos[clave])
        if not datos:
            print("⚠️ No se encontraron datos válidos o formato incorrecto.")
        else:
            df = pd.DataFrame(datos, columns=["Segmento", "Desde (km)", "Hasta (km)", "Velocidad Media (km/h)"])
            df = formatear_decimal(df)
            archivo_salida = "resultado.xlsx"
            with pd.ExcelWriter(archivo_salida, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
                ws = writer.book.active
                for col_letter in ("B", "C"):
                    for cell in ws[col_letter][1:]:
                        cell.number_format = '0.00'
            files.download(archivo_salida)
# Lógica para consola o GitHub script
else:
    print("📥 Ingresa la ruta completa al archivo PDF (sin comillas):")
    ruta_pdf = input("Ruta PDF: ").strip().strip('"')
    if not Path(ruta_pdf).exists():
        print(f"❌ Archivo no encontrado: {ruta_pdf}")
    else:
        datos = extraer_datos_desde_pdf(ruta_pdf)
        if not datos:
            print("⚠️ No se encontraron datos válidos o formato incorrecto.")
        else:
            df = pd.DataFrame(datos, columns=["Segmento", "Desde (km)", "Hasta (km)", "Velocidad Media (km/h)"])
            df = formatear_decimal(df)
            print("📤 Ingresa la ruta de salida para guardar el Excel (ej: C:/ruta/salida.xlsx):")
            ruta_excel = input("Ruta Excel: ").strip().strip('"')
            if ruta_excel:
                try:
                    with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False)
                        ws = writer.book.active
                        for col_letter in ("B", "C"):
                            for cell in ws[col_letter][1:]:
                                cell.number_format = '0.00'
                    print(f"✅ Excel generado: {ruta_excel}")
                except Exception as e:
                    print(f"❌ Error al guardar el Excel: {e}")
