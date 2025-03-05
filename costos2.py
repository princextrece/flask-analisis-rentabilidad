from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Usa un backend sin interfaz gráfica
import matplotlib.pyplot as plt
import numpy as np
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'  # Necesario para manejar sesiones
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
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Profit"] = df["Revenue"] - df["Cost"]
    df["Profitability (%)"] = pd.to_numeric((df["Profit"] / df["Revenue"]) * 100, errors="coerce")
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.interpolate(method="linear", inplace=True)
    
    # Filtrar fechas para evitar datos de 2025
    df = df[df["Date"].notna()]  # Asegura que no haya valores NaN
    df = df[df["Date"].dt.year <= 2024]  # Mantiene solo fechas hasta 2024
# Revisión final para eliminar cualquier fila errónea con fechas de 2025
    df = df[~(df["Date"].dt.year == 2025)]  
    df = df.dropna(subset=["Revenue", "Cost", "Date", "Company"])


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

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('file_path', None)
    return redirect(url_for('login'))

# Funciones de análisis
def get_top_companies(df, time_period):
    if time_period == "Y":
        df["Period"] = df["Date"].dt.to_period("Y")
    elif time_period == "M":
        df["Period"] = df["Date"].dt.to_period("M")
    elif time_period == "W":
        df["Period"] = df["Date"].dt.to_period("W")
    
    top_revenue_companies = df.groupby(["Period", "Company"], as_index=False)["Revenue"].sum()
    top_revenue_companies = top_revenue_companies.groupby("Period", group_keys=False).apply(lambda x: x.nlargest(10, "Revenue")).reset_index(drop=True)
    
    grouped_profitability = df.groupby(["Period", "Company"], as_index=False)["Profitability (%)"].mean()
    top_companies_per_period = pd.merge(top_revenue_companies, grouped_profitability, on=["Period", "Company"], how="left")
    
    return top_companies_per_period if not top_companies_per_period.empty else None

def generate_profitability_graph(df, time_period):
    top_companies_per_period = get_top_companies(df, time_period)
    if top_companies_per_period is None:
        return None
    
    plt.figure(figsize=(14, 6))
    top_companies = top_companies_per_period["Company"].unique()[:10]
    
    for company in top_companies:
        subset = top_companies_per_period[top_companies_per_period["Company"] == company]
        plt.plot(subset["Period"].astype(str), subset["Profitability (%)"], marker='o', linestyle='-', label=company)
        for i, txt in enumerate(subset["Profitability (%)"]):
            plt.annotate(f"{txt:.2f}%", (subset["Period"].astype(str).iloc[i], txt), textcoords="offset points", xytext=(0,5), ha='center')
    
    plt.xlabel("Fecha")
    plt.ylabel("Rentabilidad (%)")
    plt.title(f"Top 10 Empresas con Más Ingresos y su Rentabilidad por {time_period}")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize='small', ncol=1, frameon=True)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True)
    graph_filename = f"static/{time_period.lower()}_profitability.png"
    plt.savefig(graph_filename, dpi=300, bbox_inches='tight')
    plt.close()
    return f"/{graph_filename}"

def generate_textual_analysis(df, time_period):
    top_companies_per_period = get_top_companies(df, time_period)
    if top_companies_per_period is None:
        return "No hay datos suficientes para el análisis."

    color_classes = ["color1", "color2", "color3", "color4", "color5", 
                     "color6", "color7", "color8", "color9", "color10"]

    company_colors = {}
    text_analysis = "<strong>Análisis de Rentabilidad:</strong><br>"

    for i, company in enumerate(top_companies_per_period["Company"].unique()[:10]):
        color_class = color_classes[i % len(color_classes)]
        company_colors[company] = color_class  # Asignar color a la empresa

        text_analysis += f"<br><strong class='{color_class}'>{company}</strong><br>"
        company_data = top_companies_per_period[top_companies_per_period["Company"] == company].sort_values("Period", ascending=True)

        prev_value = None
        for index, row in company_data.iterrows():
            # Determinar el color según la rentabilidad
            if row['Profitability (%)'] < 0:
                profit_color = "red-text"
            elif 0 <= row['Profitability (%)'] <= 8:
                profit_color = "yellow-text"
            else:
                profit_color = "green-text"

            if prev_value is not None:
                diff = row['Profitability (%)'] - prev_value
                diff_color = "green-text" if diff > 0 else "red-text"
                final_color = "green-text" if row['Profitability (%)'] > 0 else "red-text"
                text_analysis += f"El {row['Period']} la rentabilidad <span>{'aumentó' if diff > 0 else 'disminuyó'} en</span> <span class='{diff_color}'>{abs(diff):.2f}%</span>, alcanzando <span class='{profit_color}'>{row['Profitability (%)']:.2f}%</span><br>"
            else:
                # Aplicar el color a la primera línea debajo del nombre de la empresa
                text_analysis += f"El {row['Period']} la rentabilidad fue de <span class='{profit_color}'>{row['Profitability (%)']:.2f}%</span><br>"
            
            prev_value = row['Profitability (%)']

    return text_analysis



if __name__ == '__main__':
    app.run(debug=True)