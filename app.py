from flask import Flask, render_template, request, redirect, url_for, session
from flask_babel import Babel, gettext as _
import os
import requests
import json

# -------------------- APP --------------------
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_fallback')

# -------------------- ALMACENAMIENTO DE IP --------------------
ROBOT_IP_FILE = 'robot_ip.json'

def load_robot_ip():
    """Carga la IP del robot desde un archivo JSON"""
    try:
        if os.path.exists(ROBOT_IP_FILE):
            with open(ROBOT_IP_FILE, 'r') as f:
                data = json.load(f)
                return data.get('ip')
    except Exception as e:
        print(f"[ERROR] No se pudo cargar la IP: {e}")
    return None

def save_robot_ip(ip):
    """Guarda la IP del robot en un archivo JSON"""
    try:
        with open(ROBOT_IP_FILE, 'w') as f:
            json.dump({'ip': ip}, f)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la IP: {e}")

# Cargar IP al iniciar la aplicación
app.config["ROBOT_IP"] = load_robot_ip()

# -------------------- IDIOMAS --------------------
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'es']

babel = Babel(app)

def get_locale():
    return session.get('language', 'en')

babel.init_app(app, locale_selector=get_locale)

# -------------------- ROBOT --------------------

@app.route('/robot/get_ip', methods=['GET'])
def get_robot_ip():
    """
    Devuelve la IP actual del robot configurada
    """
    robot_ip = app.config.get("ROBOT_IP")
    return {"ip": robot_ip} if robot_ip else {"ip": ""}

@app.route('/robot/set_ip', methods=['POST'])
def set_robot_ip():
    """
    Guarda la IP del robot enviada desde inicio.html
    """
    ip = request.json.get('ip')

    if not ip:
        return {"error": "IP inválida"}, 400

    app.config["ROBOT_IP"] = ip
    save_robot_ip(ip)  # <-- Guardar en archivo
    print(f"[ROBOT] IP configurada: {ip}")

    return {"status": "ok", "ip": ip}


@app.route('/robot/abrir', methods=['POST'])
def robot_abrir():
    """
    Envía comando HTTP al robot para abrir la puerta
    """
    robot_ip = app.config.get("ROBOT_IP")

    if not robot_ip:
        return {"error": "IP del robot no configurada"}, 400

    try:
        requests.get(f"http://{robot_ip}/relay8", timeout=2)
        return {"status": "ok"}
    except requests.RequestException as e:
        print(f"[ROBOT ERROR] {e}")
        return {"error": "No se pudo conectar al robot"}, 500


# -------------------- IDIOMA --------------------
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['en', 'es']:
        session['language'] = lang
        print(f"[IDIOMA] Cambiado a: {lang}")

    return redirect(request.referrer or url_for('inicio'))

# -------------------- RUTAS --------------------

@app.route('/')
def index():
    """Video / intro"""
    return render_template('index.html')


@app.route('/inicio')
def inicio():
    """Pantalla principal"""
    return render_template('inicio.html')

@app.route('/robot/cerrar', methods=['POST'])
def robot_cerrar():
    robot_ip = app.config.get("ROBOT_IP")

    if not robot_ip:
        return {"error": "IP del robot no configurada"}, 400

    try:
        requests.get(f"http://{robot_ip}/relay8", timeout=2)
        return {"status": "ok"}
    except requests.RequestException as e:
        print(f"[ROBOT ERROR] {e}")
        return {"error": "No se pudo conectar al robot"}, 500


@app.route('/orden/telefono', methods=['GET', 'POST'])
def paso2_telefono():
    """
    Ingreso de código.
    Si es correcto -> abrir puerta por HTTP
    """
    if 'intentos' not in session:
        session['intentos'] = 0

    error_msg = None

    if request.method == 'POST':
        codigo_ingresado = request.form.get('recipient_phone')

        if codigo_ingresado == '1234':
            session.pop('intentos', None)

            # ABRIR PUERTA POR HTTP
            try:
                requests.post(url_for('robot_abrir', _external=True))
            except Exception as e:
                print(f"[ROBOT ERROR] {e}")

            return redirect(url_for('orden_tiempo'))

        else:
            session['intentos'] += 1
            error_msg = _("Incorrect")

            if session['intentos'] >= 3:
                session.pop('intentos', None)
                return redirect(url_for('orden_completada'))

    intentos_restantes = 3 - session['intentos']

    return render_template(
        'crear-orden2.html',
        error_msg=error_msg,
        intentos_restantes=intentos_restantes
    )


@app.route('/orden/tiempo')
def orden_tiempo():
    """Pantalla de espera"""
    return render_template('tiempo.html')


@app.route('/orden/completada')
def orden_completada():
    """Pantalla final"""
    return render_template('fin.html')


# -------------------- RUN --------------------
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5002)