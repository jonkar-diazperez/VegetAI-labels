SELECT * FROM registros_clima;

SELECT * FROM clima_actual_parcela;

SELECT * FROM clima_hist_parcela;

DELETE FROM clima_hist_parcela;

ALTER TABLE suelo_parcela DROP CONSTRAINT suelo_parcela_parcela_id_key;

SELECT * FROM suelo_parcela;

DELETE FROM suelo_parcela;

DELETE FROM logs_procesos;

DELETE FROM registros_clima;

SELECT * FROM agro_chat_history;

DELETE FROM agro_chat_history;

SELECT * FROM logs_procesos;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'registros_clima';

ALTER TABLE clima_hist_parcela
ALTER COLUMN fecha TYPE DATE;

-- Crear la tabla para el historial de AgroTech
CREATE TABLE IF NOT EXISTS agro_chat_history (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,       -- Aquí se guardará el correo del usuario
    message JSONB NOT NULL,         -- Aquí se guarda el mensaje (formato JSON)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Crear un índice para optimizar la velocidad
-- Esto hace que buscar el historial por correo sea instantáneo
CREATE INDEX idx_agro_chat_session_id ON agro_chat_history (session_id);




-- -------------------------------------------------
-- 1. LIMPIEZA DE TABLAS PREVIAS
-- -------------------------------------------------
DROP TABLE IF EXISTS logs_procesos CASCADE;
DROP TABLE IF EXISTS clima_hist_parcela CASCADE;
DROP TABLE IF EXISTS suelo_parcela CASCADE;

-- -------------------------------------------------
-- 2. Tabla clima_hist_parcela
-- -------------------------------------------------
CREATE TABLE IF NOT EXISTS clima_hist_parcela (
    id SERIAL PRIMARY KEY,
    parcela_id INT NOT NULL,
    fecha DATE NOT NULL,    -- Fecha exacta del dato del JSON
    tipo VARCHAR(10) NOT NULL,     -- 'diario' o 'mensual'
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    temperatura DOUBLE PRECISION,
    humedad_relativa DOUBLE PRECISION,
    humedad_suelo DOUBLE PRECISION,
    precipitacion DOUBLE PRECISION,
    viento_velocidad DOUBLE PRECISION,
    viento_direccion DOUBLE PRECISION,
    evapotranspiracion DOUBLE PRECISION
);

-- -------------------------------------------------
-- 3. Tabla logs_procesos
-- -------------------------------------------------
CREATE TABLE IF NOT EXISTS logs_procesos (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ NOT NULL,
    proceso TEXT,
    endpoint TEXT,
    estado TEXT,
    mensaje TEXT
);

-- -------------------------------------------------
-- 4. Tabla suelo_parcela (para endpoint /tierra)
-- -------------------------------------------------
CREATE TABLE IF NOT EXISTS suelo_parcela (
    id SERIAL PRIMARY KEY,
    parcela_id INT NOT NULL,
    fecha_consulta TIMESTAMPTZ NOT NULL,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    datos_suelo JSONB
);

CREATE TABLE IF NOT EXISTS clima_actual_parcela (
    id SERIAL PRIMARY KEY,
    parcela_id INTEGER, -- Relación lógica con suelo_parcela
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    temperatura DOUBLE PRECISION,
    humedad_relativa DOUBLE PRECISION,
    humedad_suelo DOUBLE PRECISION,
    precipitacion DOUBLE PRECISION,
    viento_velocidad DOUBLE PRECISION,
    viento_direccion DOUBLE PRECISION,
    evapotranspiracion DOUBLE PRECISION
);

-- Índice esencial para que tus JOINs con suelo_parcela sean ultra rápidos
CREATE INDEX idx_clima_actual_parcela_id ON clima_actual_parcela(parcela_id);

SELECT 
    c.id AS medicion_id,
    c.parcela_id,
    c.fecha AS fecha_clima,
    c.temperatura,
    c.humedad_suelo AS humedad_clima,
    s.fecha_consulta AS fecha_analisis_suelo,
    -- Extraemos datos específicos del JSON de suelo (ajusta las llaves según tu JSON)
    s.datos_suelo->>'textura' AS textura_suelo,
    s.datos_suelo->>'ph' AS ph_suelo
FROM clima_actual_parcela c
LEFT JOIN suelo_parcela s ON c.parcela_id = s.parcela_id
WHERE c.parcela_id = 101
ORDER BY c.fecha DESC
LIMIT 1;

SELECT 
    h.fecha,
    h.temperatura,
    h.precipitacion,
    s.datos_suelo
FROM clima_hist_parcela h
INNER JOIN suelo_parcela s ON h.parcela_id = s.parcela_id
WHERE h.parcela_id = 101
ORDER BY h.fecha DESC;
