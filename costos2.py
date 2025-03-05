from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Usa un backend sin interfaz gráfica
import matplotlib.pyplot as plt
import numpy as np
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
TEMPLATES_FOLDER = "templates"

# Crear carpetas si no existen
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Credenciales de usuario
USUARIO = "nicolas"
PASSWORD = "1234"

# Página de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USUARIO and password == PASSWORD:
            session['user'] = username
            return redirect(url_for('upload_file'))
        else:
            return "Acceso denegado. Usuario o contraseña incorrectos."
    return render_template('login.html')

# Página de carga de archivos CSV
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return "Error: No se encontró ningún archivo.", 400

        file = request.files['file']

        if file.filename == '':
            return "Error: No se seleccionó ningún archivo.", 400

        if file and file.filename.endswith('.csv'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            session['file_path'] = file_path  # Guardar ruta en sesión
            return redirect(url_for('dashboard'))

    return render_template('upload.html')

# Página de análisis de datos
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if 'file_path' not in session:
        return "Error: No hay un archivo cargado.", 400

    file_path = session['file_path']
    
    # Procesamiento del archivo
    df = pd.read_csv(file_path, encoding='latin1')
    df = df.rename(columns={
        "Billed total": "Revenue",
        "Paid total": "Cost",
        "Date": "Date",
        "Account name": "Company"
    })
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")
    df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    
    # Eliminar filas con fechas vacías antes de interpolar
    df = df.dropna(subset=["Date"])
    
    df["Profit"] = df["Revenue"] - df["Cost"]
    df["Profitability (%)"] = (df["Profit"] / df["Revenue"]) * 100
    
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Interpolar solo en columnas numéricas, evitando la fecha
    df.interpolate(method="linear", inplace=True, limit_area="inside")
    
    # Eliminar cualquier fecha mayor a 2024
    df = df[df["Date"].dt.year <= 2024]
    
    df = df.dropna(subset=["Revenue", "Cost", "Company"])
    
    # Generar gráficos y análisis de texto
    weekly_graph = generate_profitability_graph(df, "W")
    monthly_graph = generate_profitability_graph(df, "M")
    annual_graph = generate_profitability_graph(df, "Y")
    
    weekly_text = generate_textual_analysis(df, "W")
    monthly_text = generate_textual_analysis(df, "M")
    annual_text = generate_textual_analysis(df, "Y")

    return render_template('reporte.html', 
                           weekly_graph=weekly_graph,
                           monthly_graph=monthly_graph,
                           annual_graph=annual_graph,
                           weekly_text=weekly_text,
                           monthly_text=monthly_text,
                           annual_text=annual_text)

# Funciones de análisis
def generate_profitability_graph(df, time_period):
    # Implementación de la función aquí...
    return "ruta_del_grafico.png"

def generate_textual_analysis(df, time_period):
    # Implementación de la función aquí...
    return "Análisis textual generado"

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('file_path', None)
    return redirect(url_for('login'))
