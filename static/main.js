document.addEventListener('DOMContentLoaded', function() {
    // Función para aplicar el tema
    function aplicarTema(tema) {
        if (!tema) return;
        document.body.setAttribute('data-theme', tema);
        localStorage.setItem('tema', tema);
    }

    // Obtener el tema del usuario actual
    const temaUsuario = document.body.getAttribute('data-theme');
    aplicarTema(temaUsuario);

    // Manejar cambios en el selector de tema
    const selectorTema = document.querySelector('select[name="tema"]');
    if (selectorTema) {
        selectorTema.addEventListener('change', function() {
            aplicarTema(this.value);
        });
    }

    // Manejar la previsualización y validación de imágenes
    function manejarArchivosImagen(input, previewElement, maxSize = 5 * 1024 * 1024) {
        if (!input || !previewElement) return;

        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Validar tamaño del archivo
            if (file.size > maxSize) {
                alert('El archivo es demasiado grande. El tamaño máximo es 5MB.');
                input.value = '';
                return;
            }

            // Validar tipo de archivo
            if (!file.type.startsWith('image/')) {
                alert('Por favor, selecciona un archivo de imagen válido.');
                input.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                previewElement.src = e.target.result;
                previewElement.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    // Configuración inicial

    // Manejar configuraciones de privacidad
    const privacidadSelect = document.querySelector('select[name="privacidad_perfil"]');
    if (privacidadSelect) {
        privacidadSelect.addEventListener('change', function() {
            const valor = this.value;
            document.querySelectorAll('.configuracion-privacidad').forEach(elem => {
                elem.style.display = valor === 'privado' ? 'none' : 'block';
            });
        });
    }

    // Manejar estado de ánimo
    const estadoSelect = document.querySelector('select[name="estado_animo"]');
    const estadoPreview = document.getElementById('estado-preview');
    if (estadoSelect && estadoPreview) {
        estadoSelect.addEventListener('change', function() {
            estadoPreview.textContent = this.value;
        });
    }

    // Manejar redes sociales
    const redesSocialesForm = document.getElementById('redes-sociales-form');
    if (redesSocialesForm) {
        const inputs = redesSocialesForm.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                const redSocial = this.getAttribute('name');
                const preview = document.querySelector(`.${redSocial}-preview`);
                if (preview) {
                    preview.style.display = this.value ? 'inline-block' : 'none';
                    preview.href = `https://${redSocial}.com/${this.value}`;
                }
            });
        });
    }

    // Manejar el autoajuste de los textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        // Ajustar altura inicial
        textarea.dispatchEvent(new Event('input'));
    });

    // Función para mostrar mensajes de estado
    function mostrarMensaje(mensaje, tipo = 'info') {
        const contenedor = document.createElement('div');
        contenedor.className = `mensaje-estado mensaje-${tipo}`;
        contenedor.textContent = mensaje;
        document.body.appendChild(contenedor);

        setTimeout(() => {
            contenedor.remove();
        }, 3000);
    }

    // Manejar formulario de configuración
    const formConfig = document.querySelector('form');
    if (formConfig) {
        formConfig.addEventListener('submit', async function(e) {
            e.preventDefault();
            const todosLosCampos = this.querySelectorAll('input, select, textarea');
            let camposValidos = true;

            todosLosCampos.forEach(campo => {
                if (campo.required && !campo.value) {
                    camposValidos = false;
                    campo.classList.add('campo-error');
                } else {
                    campo.classList.remove('campo-error');
                }
            });

            if (!camposValidos) {
                mostrarMensaje('Por favor, completa todos los campos requeridos', 'error');
                return;
            }

            mostrarMensaje('Guardando configuración...', 'info');
            
            try {
                const formData = new FormData(this);
                // Asegurarnos de que los checkboxes no marcados también se envíen
                const checkboxes = ['mostrar_estado', 'notificaciones_email', 'notificaciones_mensajes', 'notificaciones_amigos'];
                checkboxes.forEach(checkbox => {
                    if (!formData.has(checkbox)) {
                        formData.append(checkbox, 'false');
                    }
                });

                const response = await fetch('/configuracion', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    mostrarMensaje('Configuración guardada exitosamente', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    mostrarMensaje('Error al guardar la configuración', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error al guardar la configuración', 'error');
            }
        });
    }
    }
});
