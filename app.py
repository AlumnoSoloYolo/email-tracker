# app.py
import os
import io
import uuid
import time
import random
from datetime import datetime
from flask import Flask, request, send_file, render_template, redirect, url_for, flash
from flask_mail import Mail, Message
from dotenv import load_dotenv
from PIL import Image

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, instance_relative_config=True)

# Configuración
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'clave_secreta_por_defecto'),
    MAIL_SERVER=os.environ.get('MAIL_SERVER'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'True') == 'True',
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD', 'admin'),
    TRACKING_DOMAIN=os.environ.get('TRACKING_DOMAIN')
)

# app.config['TRACKING_DOMAIN'] = 'https://3eab-85-50-107-105.ngrok-free.app'

print(f"TRACKING_DOMAIN configurado como: {os.environ.get('TRACKING_DOMAIN')}")

# Inicializar extensiones
mail = Mail(app)

# Asegurarse de que existen los directorios necesarios
os.makedirs('logs', exist_ok=True)

# Función para crear un pixel transparente
def create_transparent_pixel():
    img = Image.new('RGBA', (1, 1), color=(0, 0, 0, 0))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# Ruta para el tracking pixel
@app.route('/track/<tracking_id>')
def track_email(tracking_id):
    """Registra cuando se abre un correo y devuelve un pixel transparente"""
    # Obtener información del cliente
    ip = request.remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        ip = forwarded_for  # Útil si estás detrás de un proxy o balanceador de carga
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', 'Unknown')
    date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Crear y guardar registro
    log_entry = f"PIXEL | ID: {tracking_id} | Fecha: {date_time} | IP: {ip} | Navegador: {user_agent} | Referer: {referer}\n"
    
    log_file_path = os.path.join('logs', 'email_logs.txt')
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)
    
    # Devolver un pixel transparente
    response = send_file(
        create_transparent_pixel(),
        mimetype='image/png',
        as_attachment=False,
        download_name='pixel.png'
    )

    # Agregar encabezados para evitar caché
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

# Nueva ruta para rastreo de enlaces
@app.route('/link/<tracking_id>')
def track_link(tracking_id):
    """Registra cuando se hace clic en un enlace y redirige al usuario"""
    # Obtener información del cliente
    ip = request.remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        ip = forwarded_for
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', 'Unknown')
    date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Crear y guardar registro
    log_entry = f"ENLACE | ID: {tracking_id} | Fecha: {date_time} | IP: {ip} | Navegador: {user_agent} | Referer: {referer}\n"
    
    log_file_path = os.path.join('logs', 'email_links_logs.txt')
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)
    
    # Obtener la URL de redirección (por defecto Google)
    redirect_url = request.args.get('redirect', 'https://www.google.com')
    
    # Redirigir al usuario
    return redirect(redirect_url)

# Ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Formulario para envío de correos
@app.route('/send', methods=['GET', 'POST'])
def send_email():
    if request.method == 'POST':
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        if not recipient or not subject or not content:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('send_email'))
        
        # Generar ID único para rastreo
        tracking_id = str(uuid.uuid4())
        
        # Parámetros para evitar caché
        cache_params = f"?t={int(time.time())}&r={random.randint(1000, 9999999)}"
        
        # URL completa al pixel de rastreo
        print(f"URL de tracking que se usará: {app.config['TRACKING_DOMAIN']}")
        tracking_url = f"{app.config['TRACKING_DOMAIN']}/track/{tracking_id}{cache_params}"
        print(f"TRACKING_DOMAIN en .env: {os.environ.get('TRACKING_DOMAIN')}")
        print(f"TRACKING_DOMAIN en config: {app.config['TRACKING_DOMAIN']}")
        print(f"URL final del pixel: {tracking_url}")
        
        # URL para el enlace rastreable
        tracking_link = f"{app.config['TRACKING_DOMAIN']}/link/{tracking_id}{cache_params}"
        
        # Añadir pixel de rastreo y enlace rastreable al contenido
        html_content = f"""
        {content}
        
        <img src='{tracking_url}' width='1' height='1' alt='' style='display:none;'>
        
        <div style="margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;">
            <p style="font-size: 12px; color: #666;">
                <a href="{tracking_link}&redirect=https://www.google.com">Ver más información</a> | 
                <a href="{tracking_link}&redirect=https://www.wikipedia.com">Contacto</a>
            </p>
        </div>
        """
        
        try:
            # Crear mensaje
            msg = Message(
                subject=subject,
                sender=app.config['MAIL_USERNAME'],
                recipients=[recipient],
                html=html_content
            )
            
            # Enviar correo
            mail.send(msg)
            
            # Registrar envío
            send_log_entry = f"Email enviado a: {recipient} | ID: {tracking_id} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            send_log_path = os.path.join('logs', 'emails_sent.txt')
            with open(send_log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(send_log_entry)
            
            flash(f'Correo enviado exitosamente con ID de rastreo: {tracking_id}', 'success')
            return redirect(url_for('send_email'))
            
        except Exception as e:
            flash(f'Error al enviar correo: {str(e)}', 'error')
            return redirect(url_for('send_email'))
    
    return render_template('send_form.html')

# Ruta para ver logs
@app.route('/logs')
def view_logs():
    # Leer logs de apertura (pixel)
    email_logs = "No hay registros de apertura disponibles"
    log_path = os.path.join('logs', 'email_logs.txt')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            email_logs = f.read()
    
    # Leer logs de enlaces
    links_logs = "No hay registros de clics en enlaces disponibles"
    links_log_path = os.path.join('logs', 'email_links_logs.txt')
    if os.path.exists(links_log_path):
        with open(links_log_path, 'r', encoding='utf-8') as f:
            links_logs = f.read()
    
    # Leer logs de envío
    sent_logs = "No hay registros de envío disponibles"
    sent_log_path = os.path.join('logs', 'emails_sent.txt')
    if os.path.exists(sent_log_path):
        with open(sent_log_path, 'r', encoding='utf-8') as f:
            sent_logs = f.read()
    
    return render_template('logs_view.html', email_logs=email_logs, links_logs=links_logs, sent_logs=sent_logs)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)