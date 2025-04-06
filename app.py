from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social.db'
db = SQLAlchemy(app)

class Amistad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    amigo_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class LibroVisitas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    autor = db.relationship('Usuario', foreign_keys=[autor_id])
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id])

class MensajePrivado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    emisor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    receptor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<MensajePrivado {self.id} de {self.emisor_id} para {self.receptor_id}>'
    emisor = db.relationship('Usuario', foreign_keys=[emisor_id], backref=db.backref('mensajes_privados_enviados', lazy='dynamic'))
    receptor = db.relationship('Usuario', foreign_keys=[receptor_id], backref=db.backref('mensajes_privados_recibidos', lazy='dynamic'))

class Seguidor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seguidor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    seguido_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    privacidad_perfil = db.Column(db.String(20), default='publico')  # publico, amigos, privado
    mostrar_estado = db.Column(db.Boolean, default=True)
    notificaciones_email = db.Column(db.Boolean, default=True)
    notificaciones_mensajes = db.Column(db.Boolean, default=True)
    notificaciones_amigos = db.Column(db.Boolean, default=True)
    redes_sociales = db.Column(db.JSON, default={})

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    perfil_html = db.Column(db.Text, default='')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    esta_activo = db.Column(db.Boolean, default=True)
    ultima_actividad = db.Column(db.DateTime, default=datetime.utcnow)
    estado_animo = db.Column(db.String(10), default='😊')
    visitas = db.Column(db.Integer, default=0)
    mensajes = db.relationship('Mensaje', backref='autor', lazy=True)
    amigos = db.relationship('Usuario',
        secondary='amistad',
        primaryjoin=(id==Amistad.usuario_id),
        secondaryjoin=(id==Amistad.amigo_id),
        backref=db.backref('amigos_de', lazy='dynamic'),
        lazy='dynamic')
    seguidores = db.relationship('Usuario',
        secondary='seguidor',
        primaryjoin=(id==Seguidor.seguido_id),
        secondaryjoin=(id==Seguidor.seguidor_id),
        backref=db.backref('siguiendo', lazy='dynamic'),
        lazy='dynamic')
    libro_visitas = db.relationship('LibroVisitas',
        foreign_keys='LibroVisitas.destinatario_id',
        backref='perfil',
        lazy='dynamic')
    configuracion = db.relationship('Configuracion', backref='usuario', uselist=False)

class Notificacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, rechazada
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id])
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id])

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Mensaje {self.id} por {self.autor.username}>'

with app.app_context():
    db.create_all()

@app.route('/')
def inicio():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder a esta página')
        return redirect(url_for('login'))
    
    current_user = Usuario.query.get(session['user_id'])
    if not current_user or not current_user.esta_activo:
        session.clear()
        flash('Sesión inválida. Por favor, inicia sesión nuevamente')
        return redirect(url_for('login'))
    
    mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).limit(10).all()
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    notificaciones_pendientes = Notificacion.query.filter_by(
        destinatario_id=session['user_id'],
        estado='pendiente'
    ).count()
    return render_template('home.html', 
                         mensajes=mensajes, 
                         usuarios=usuarios, 
                         current_user=current_user, 
                         notificaciones_pendientes=notificaciones_pendientes)

@app.route('/publicar', methods=['POST'])
def publicar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    contenido = request.form.get('mensaje')
    if contenido:
        mensaje = Mensaje(contenido=contenido, autor_id=session['user_id'])
        db.session.add(mensaje)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if username:
        usuario = Usuario.query.filter_by(username=username).first_or_404()
        if not usuario.id == session['user_id']:
            usuario.visitas += 1
            db.session.commit()
    else:
        usuario = Usuario.query.get(session['user_id'])
    
    mensajes = Mensaje.query.filter_by(autor_id=usuario.id).order_by(Mensaje.fecha.desc()).all()
    es_propio_perfil = usuario.id == session.get('user_id')
    son_amigos = False if es_propio_perfil else usuario in Usuario.query.get(session['user_id']).amigos
    current_user = Usuario.query.get(session['user_id'])
    return render_template('profile.html', usuario=usuario, mensajes=mensajes, es_propio_perfil=es_propio_perfil, son_amigos=son_amigos, current_user=current_user)

@app.route('/amigos')
def amigos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['user_id'])
    return render_template('amigos.html', amigos=usuario.amigos)

@app.route('/agregar_amigo/<int:amigo_id>', methods=['POST'])
def agregar_amigo(amigo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    amigo = Usuario.query.get(amigo_id)
    
    if amigo and amigo not in usuario.amigos:
        notificacion = Notificacion(
            tipo='solicitud_amistad',
            remitente_id=usuario.id,
            destinatario_id=amigo_id
        )
        db.session.add(notificacion)
        db.session.commit()
        flash('Solicitud de amistad enviada')
    return redirect(url_for('profile', username=amigo.username))

@app.route('/notificaciones')
def notificaciones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    notificaciones = Notificacion.query.filter_by(
        destinatario_id=session['user_id'],
        estado='pendiente'
    ).order_by(Notificacion.fecha.desc()).all()
    
    return render_template('notificaciones.html', notificaciones=notificaciones)

@app.route('/url/<red_social>/<username>')
def redirigir_red_social(red_social, username):
    redes = {
        'facebook': f'https://facebook.com/{username}',
        'twitter': f'https://twitter.com/{username}',
        'instagram': f'https://instagram.com/{username}',
        'youtube': f'https://youtube.com/{username}'
    }
    if red_social in redes:
        return redirect(redes[red_social])
    return redirect(url_for('home'))

@app.route('/responder_solicitud/<int:notif_id>/<accion>', methods=['POST'])
def responder_solicitud(notif_id, accion):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    notificacion = Notificacion.query.get_or_404(notif_id)
    if notificacion.destinatario_id != session['user_id']:
        flash('No tienes permiso para realizar esta acción')
        return redirect(url_for('notificaciones'))
    
    if accion == 'aceptar':
        usuario = Usuario.query.get(session['user_id'])
        remitente = Usuario.query.get(notificacion.remitente_id)
        usuario.amigos.append(remitente)
        notificacion.estado = 'aceptada'
        flash('¡Solicitud de amistad aceptada!')
    elif accion == 'rechazar':
        notificacion.estado = 'rechazada'
        flash('Solicitud de amistad rechazada')
    
    db.session.commit()
    return redirect(url_for('notificaciones'))

@app.route('/eliminar_amigo/<int:amigo_id>', methods=['POST'])
def eliminar_amigo(amigo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    amigo = Usuario.query.get(amigo_id)
    
    if amigo and amigo in usuario.amigos:
        usuario.amigos.remove(amigo)
        db.session.commit()
        flash('Amigo eliminado')
    return redirect(url_for('amigos'))

@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    usuario.perfil_html = request.form.get('perfil_html', '')
    db.session.commit()
    flash('¡Perfil actualizado!')
    return redirect(url_for('profile'))

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    usuario.estado_animo = request.form.get('estado_animo', '😊')
    db.session.commit()
    flash('¡Estado de ánimo actualizado!')
    return redirect(url_for('profile'))

@app.route('/firmar_libro/<int:usuario_id>', methods=['POST'])
def firmar_libro(usuario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if usuario_id == session['user_id']:
        flash('No puedes firmar tu propio libro de visitas')
        return redirect(url_for('profile'))
    
    mensaje = request.form.get('mensaje')
    if mensaje:
        firma = LibroVisitas(
            mensaje=mensaje,
            autor_id=session['user_id'],
            destinatario_id=usuario_id
        )
        db.session.add(firma)
        db.session.commit()
        flash('¡Gracias por firmar!')
    
    return redirect(url_for('profile', username=Usuario.query.get(usuario_id).username))

@app.route('/mensajes')
def mensajes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    mensajes_recibidos = usuario.mensajes_privados_recibidos.order_by(MensajePrivado.fecha.desc()).all()
    mensajes_enviados = usuario.mensajes_privados_enviados.order_by(MensajePrivado.fecha.desc()).all()
    
    return render_template('mensajes.html', mensajes_recibidos=mensajes_recibidos, mensajes_enviados=mensajes_enviados)

@app.route('/enviar_mensaje/<int:receptor_id>', methods=['POST'])
def enviar_mensaje(receptor_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    receptor = Usuario.query.get(receptor_id)
    
    if not receptor in usuario.amigos:
        flash('Solo puedes enviar mensajes a tus amigos')
        return redirect(url_for('profile', username=receptor.username))
    
    contenido = request.form.get('mensaje')
    if contenido:
        mensaje = MensajePrivado(
            contenido=contenido,
            emisor_id=session['user_id'],
            receptor_id=receptor_id
        )
        db.session.add(mensaje)
        db.session.commit()
        flash('Mensaje enviado')
    
    return redirect(url_for('mensajes'))

@app.route('/marcar_leido/<int:mensaje_id>', methods=['POST'])
def marcar_leido(mensaje_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    mensaje = MensajePrivado.query.get(mensaje_id)
    if mensaje and mensaje.receptor_id == session['user_id']:
        mensaje.leido = True
        db.session.commit()
    
    return redirect(url_for('mensajes'))

@app.route('/seguir/<int:usuario_id>', methods=['POST'])
def seguir(usuario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    a_seguir = Usuario.query.get(usuario_id)
    
    if a_seguir and a_seguir not in usuario.siguiendo:
        usuario.siguiendo.append(a_seguir)
        notificacion = Notificacion(
            tipo='nuevo_seguidor',
            remitente_id=usuario.id,
            destinatario_id=usuario_id
        )
        db.session.add(notificacion)
        db.session.commit()
        flash('Ahora estás siguiendo a este usuario')
    
    return redirect(url_for('profile', username=a_seguir.username))

@app.route('/dejar_seguir/<int:usuario_id>', methods=['POST'])
def dejar_seguir(usuario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    dejar = Usuario.query.get(usuario_id)
    
    if dejar and dejar in usuario.siguiendo:
        usuario.siguiendo.remove(dejar)
        db.session.commit()
        flash('Has dejado de seguir a este usuario')
    
    return redirect(url_for('profile', username=dejar.username))

@app.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    if not usuario.configuracion:
        config = Configuracion(usuario_id=usuario.id)
        db.session.add(config)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Configuración general
            usuario.configuracion.privacidad_perfil = request.form.get('privacidad_perfil', 'publico')
            usuario.configuracion.mostrar_estado = request.form.get('mostrar_estado', 'false').lower() == 'true'
            usuario.configuracion.notificaciones_email = request.form.get('notificaciones_email', 'false').lower() == 'true'
            usuario.configuracion.notificaciones_mensajes = request.form.get('notificaciones_mensajes', 'false').lower() == 'true'
            usuario.configuracion.notificaciones_amigos = request.form.get('notificaciones_amigos', 'false').lower() == 'true'
            

            
            # Redes sociales
            redes_sociales = {}
            for red in ['facebook', 'twitter', 'instagram', 'youtube']:
                if request.form.get(red):
                    redes_sociales[red] = request.form.get(red)
            usuario.configuracion.redes_sociales = redes_sociales
            
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Configuración actualizada correctamente'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return render_template('configuracion.html', usuario=usuario)

@app.route('/logout')
def logout():
    if 'user_id' in session:
        usuario = Usuario.query.get(session['user_id'])
        if usuario:
            usuario.esta_activo = False
            db.session.commit()
    session.clear()
    flash('¡Hasta pronto!')
    return redirect(url_for('inicio'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username, password=password).first()
        
        if usuario:
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            usuario.esta_activo = True
            usuario.ultima_actividad = datetime.utcnow()
            db.session.commit()
            flash('¡Bienvenido de vuelta!')
            return redirect(url_for('inicio'))
        else:
            flash('Usuario o contraseña incorrectos')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe')
            return redirect(url_for('registro'))
        
        nuevo_usuario = Usuario(username=username, password=password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('¡Registro exitoso!')
        return redirect(url_for('inicio'))
    
    return render_template('registro.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)