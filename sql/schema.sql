CREATE TABLE IF NOT EXISTS noticias (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  fecha TIMESTAMP NOT NULL,
  fuente VARCHAR(255),
  autor VARCHAR(255),
  url TEXT NOT NULL,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  contenido TEXT,
  palabra_clave VARCHAR(100) NOT NULL,
  sentimiento_label ENUM('positive','neutral','negative') NOT NULL,
  sentimiento_score DECIMAL(5,4) NOT NULL,
  idioma VARCHAR(10),
  PRIMARY KEY (id),
  UNIQUE KEY uk_noticias_url (url),
  KEY idx_noticias_fecha (fecha),
  KEY idx_noticias_sentimiento (sentimiento_label),
  KEY idx_noticias_keyword (palabra_clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
