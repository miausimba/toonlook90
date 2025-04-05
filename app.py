from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social.db'
db = SQLAlchemy(app)

class Amistad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    amigo_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    perfil_html = db.Column(db.Text, default='')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    esta_activo = db.Column(db.Boolean, default=True)
    ultima_actividad = db.Column(db.DateTime, default=datetime.utcnow)
    mensajes = db.relationship('Mensaje', backref='autor', lazy=True)
    amigos = db.relationship('Usuario',
        secondary='amistad',
        primaryjoin=(id==Amistad.usuario_id),
        secondaryjoin=(id==Amistad.amigo_id),
        backref=db.backref('amigos_de', lazy='dynamic'),
        lazy='dynamic')

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
        return redirect(url_for('login'))
    mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).limit(10).all()
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    current_user = Usuario.query.get(session['user_id'])
    notificaciones_pendientes = Notificacion.query.filter_by(
        destinatario_id=session['user_id'],
        estado='pendiente'
    ).count()
    return render_template('home.html', mensajes=mensajes, usuarios=usuarios, 
                         current_user=current_user, notificaciones_pendientes=notificaciones_pendientes)

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
    else:
        usuario = Usuario.query.get(session['user_id'])
    
    mensajes = Mensaje.query.filter_by(autor_id=usuario.id).order_by(Mensaje.fecha.desc()).all()
    es_propio_perfil = usuario.id == session.get('user_id')
    son_amigos = False if es_propio_perfil else usuario in Usuario.query.get(session['user_id']).amigos
    
    return render_template('profile.html', usuario=usuario, mensajes=mensajes, es_propio_perfil=es_propio_perfil, son_amigos=son_amigos)

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