-- Esquema de la base de datos (generado desde modelos.py, dialecto SQLite)

CREATE TABLE emparejamiento (
	id_emparejamiento INTEGER NOT NULL, 
	fecha_ejecucion DATETIME NOT NULL, 
	n_emparejados INTEGER NOT NULL, 
	n_sin_coincidencia INTEGER NOT NULL, 
	codigos_excluidos TEXT, 
	estado VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_emparejamiento)
);

CREATE TABLE empresa (
	id_empresa INTEGER NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id_empresa), 
	UNIQUE (nombre)
);

CREATE TABLE usuario_admin (
	id_usuario INTEGER NOT NULL, 
	usuario VARCHAR(40) NOT NULL, 
	hash_contrasena VARCHAR(255) NOT NULL, 
	intentos_fallidos INTEGER NOT NULL, 
	bloqueado_hasta DATETIME, 
	PRIMARY KEY (id_usuario), 
	UNIQUE (usuario)
);

CREATE TABLE analisis (
	id_analisis INTEGER NOT NULL, 
	id_emparejamiento INTEGER NOT NULL, 
	fecha_ejecucion DATETIME NOT NULL, 
	n_muestra INTEGER NOT NULL, 
	estado VARCHAR(30) NOT NULL, 
	advertencias TEXT, 
	PRIMARY KEY (id_analisis), 
	FOREIGN KEY(id_emparejamiento) REFERENCES emparejamiento (id_emparejamiento)
);

CREATE TABLE equipo_desarrollo (
	id_equipo INTEGER NOT NULL, 
	id_empresa INTEGER NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	metodologia_trabajo VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_equipo), 
	CONSTRAINT uq_equipo_empresa UNIQUE (id_empresa, nombre), 
	FOREIGN KEY(id_empresa) REFERENCES empresa (id_empresa)
);

CREATE TABLE sesion (
	id_sesion INTEGER NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	fecha_inicio DATETIME NOT NULL, 
	ultima_actividad DATETIME NOT NULL, 
	fecha_cierre DATETIME, 
	motivo_cierre VARCHAR(20), 
	PRIMARY KEY (id_sesion), 
	FOREIGN KEY(id_usuario) REFERENCES usuario_admin (id_usuario)
);

CREATE TABLE estadistico_descriptivo (
	id_estadistico INTEGER NOT NULL, 
	id_analisis INTEGER NOT NULL, 
	agrupacion VARCHAR(20) NOT NULL, 
	categoria VARCHAR(40) NOT NULL, 
	variable VARCHAR(30) NOT NULL, 
	frecuencia INTEGER NOT NULL, 
	media FLOAT, 
	desviacion FLOAT, 
	PRIMARY KEY (id_estadistico), 
	FOREIGN KEY(id_analisis) REFERENCES analisis (id_analisis)
);

CREATE TABLE participante (
	codigo_anonimo VARCHAR(12) NOT NULL, 
	id_equipo INTEGER NOT NULL, 
	rol_profesional VARCHAR(30) NOT NULL, 
	anios_experiencia INTEGER NOT NULL, 
	estado_formulario VARCHAR(20) NOT NULL, 
	fecha_consentimiento DATETIME NOT NULL, 
	fecha_fin_bfi44 DATETIME, 
	fecha_fin_escala DATETIME, 
	PRIMARY KEY (codigo_anonimo), 
	FOREIGN KEY(id_equipo) REFERENCES equipo_desarrollo (id_equipo)
);

CREATE TABLE reporte_metricas (
	id_reporte INTEGER NOT NULL, 
	id_equipo INTEGER NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	periodo_inicio DATE NOT NULL, 
	periodo_fin DATE NOT NULL, 
	nombre_archivo VARCHAR(120) NOT NULL, 
	formato VARCHAR(10) NOT NULL, 
	fecha_carga DATETIME NOT NULL, 
	registros_procesados INTEGER NOT NULL, 
	PRIMARY KEY (id_reporte), 
	FOREIGN KEY(id_equipo) REFERENCES equipo_desarrollo (id_equipo), 
	FOREIGN KEY(id_usuario) REFERENCES usuario_admin (id_usuario)
);

CREATE TABLE resultado_correlacion (
	id_resultado INTEGER NOT NULL, 
	id_analisis INTEGER NOT NULL, 
	dimension VARCHAR(20) NOT NULL, 
	variable_rendimiento VARCHAR(30) NOT NULL, 
	prueba VARCHAR(20) NOT NULL, 
	coeficiente FLOAT NOT NULL, 
	p_valor FLOAT NOT NULL, 
	n INTEGER NOT NULL, 
	PRIMARY KEY (id_resultado), 
	FOREIGN KEY(id_analisis) REFERENCES analisis (id_analisis)
);

CREATE TABLE resultado_subgrupo (
	id_resultado INTEGER NOT NULL, 
	id_analisis INTEGER NOT NULL, 
	variable_agrupacion VARCHAR(20) NOT NULL, 
	variable_comparada VARCHAR(30) NOT NULL, 
	prueba VARCHAR(20) NOT NULL, 
	estadistico FLOAT NOT NULL, 
	p_valor FLOAT NOT NULL, 
	grupos_incluidos INTEGER NOT NULL, 
	grupos_excluidos VARCHAR(200), 
	PRIMARY KEY (id_resultado), 
	FOREIGN KEY(id_analisis) REFERENCES analisis (id_analisis)
);

CREATE TABLE metrica_rendimiento (
	id_metrica INTEGER NOT NULL, 
	id_reporte INTEGER NOT NULL, 
	codigo_anonimo VARCHAR(12) NOT NULL, 
	issues_completados INTEGER NOT NULL, 
	story_points FLOAT NOT NULL, 
	bugs_resueltos INTEGER NOT NULL, 
	tiempo_ciclo_dias FLOAT NOT NULL, 
	PRIMARY KEY (id_metrica), 
	CONSTRAINT uq_metrica_reporte_codigo UNIQUE (id_reporte, codigo_anonimo), 
	FOREIGN KEY(id_reporte) REFERENCES reporte_metricas (id_reporte)
);

CREATE TABLE puntaje_participante (
	codigo_anonimo VARCHAR(12) NOT NULL, 
	apertura FLOAT NOT NULL, 
	responsabilidad FLOAT NOT NULL, 
	extraversion FLOAT NOT NULL, 
	amabilidad FLOAT NOT NULL, 
	neuroticismo FLOAT NOT NULL, 
	rendimiento_autopercibido FLOAT NOT NULL, 
	PRIMARY KEY (codigo_anonimo), 
	FOREIGN KEY(codigo_anonimo) REFERENCES participante (codigo_anonimo)
);

CREATE TABLE respuesta_bfi44 (
	id_respuesta INTEGER NOT NULL, 
	codigo_anonimo VARCHAR(12) NOT NULL, 
	numero_item INTEGER NOT NULL, 
	valor_likert INTEGER NOT NULL, 
	PRIMARY KEY (id_respuesta), 
	CONSTRAINT uq_bfi_participante_item UNIQUE (codigo_anonimo, numero_item), 
	FOREIGN KEY(codigo_anonimo) REFERENCES participante (codigo_anonimo)
);

CREATE TABLE respuesta_escala (
	id_respuesta INTEGER NOT NULL, 
	codigo_anonimo VARCHAR(12) NOT NULL, 
	numero_item INTEGER NOT NULL, 
	valor_likert INTEGER NOT NULL, 
	PRIMARY KEY (id_respuesta), 
	CONSTRAINT uq_escala_participante_item UNIQUE (codigo_anonimo, numero_item), 
	FOREIGN KEY(codigo_anonimo) REFERENCES participante (codigo_anonimo)
);

CREATE TABLE registro_emparejado (
	id_emparejamiento INTEGER NOT NULL, 
	codigo_anonimo VARCHAR(12) NOT NULL, 
	id_metrica INTEGER NOT NULL, 
	PRIMARY KEY (id_emparejamiento, codigo_anonimo), 
	FOREIGN KEY(id_emparejamiento) REFERENCES emparejamiento (id_emparejamiento), 
	FOREIGN KEY(codigo_anonimo) REFERENCES participante (codigo_anonimo), 
	FOREIGN KEY(id_metrica) REFERENCES metrica_rendimiento (id_metrica)
);
