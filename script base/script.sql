-- =============================================================================
-- PROYECTO FINAL: SISTEMA INTEGRAL E-MARKET EXPRESS
-- CURSO: BASES DE DATOS (Cód. 603401) - UNIVERSIDAD DE LOS LLANOS
-- SCRIPT SQL CONSOLIDADO (DDL, DML, TRIGGERS, PROCEDIMIENTOS, VISTAS Y ROLES)
-- =============================================================================

DROP DATABASE IF EXISTS parcial;
CREATE DATABASE parcial CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE parcial;

-- =============================================================================
-- 1. DDL: CREACIÓN DE TABLAS, RESTRICCIONES E ÍNDICES
-- =============================================================================

-- 1.1 Tabla: usuario
CREATE TABLE usuario (
    id_usuario INT(11) NOT NULL,
    cedula INT(11) NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    correo VARCHAR(50) NOT NULL UNIQUE,
    telefono INT(11) NOT NULL,
    PRIMARY KEY (id_usuario),
    INDEX idx_usuario_correo (correo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.2 Tabla: estado (Catálogo de estados de envío/pedido)
CREATE TABLE estado (
    id_estado INT(11) NOT NULL AUTO_INCREMENT,
    estado VARCHAR(50) NOT NULL UNIQUE,
    PRIMARY KEY (id_estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.3 Tabla: categoria
CREATE TABLE categoria (
    id_categoria INT(11) NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (id_categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.4 Tabla: proveedor
CREATE TABLE proveedor (
    nit VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    contacto VARCHAR(50) NOT NULL,
    ciudad VARCHAR(50) NOT NULL,
    PRIMARY KEY (nit)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.5 Tabla: bodega
CREATE TABLE bodega (
    id_bodega INT(11) NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    ubicacion VARCHAR(150) NOT NULL,
    PRIMARY KEY (id_bodega)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.6 Tabla: productos (Catálogo de artículos)
CREATE TABLE productos (
    codigo INT(11) NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    cantidad_disponible INT(11) NOT NULL DEFAULT 0,
    id_categoria INT(11) NULL,
    nit_proveedor VARCHAR(20) NULL,
    PRIMARY KEY (codigo),
    CONSTRAINT chk_producto_precio CHECK (precio_unitario >= 0),
    CONSTRAINT chk_producto_stock CHECK (cantidad_disponible >= 0),
    CONSTRAINT fk_productos_categoria FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_productos_proveedor FOREIGN KEY (nit_proveedor) REFERENCES proveedor(nit) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.7 Tabla: inventario_bodega (Relación productos - bodegas)
CREATE TABLE inventario_bodega (
    id_articulo INT(11) NOT NULL,
    id_bodega INT(11) NOT NULL,
    stock_actual INT(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_articulo, id_bodega),
    CONSTRAINT chk_stock_valido CHECK (stock_actual >= 0),
    CONSTRAINT fk_inventario_articulo FOREIGN KEY (id_articulo) REFERENCES productos(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_inventario_bodega FOREIGN KEY (id_bodega) REFERENCES bodega(id_bodega) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.8 Tabla: pedido (Cabecera de transacción)
CREATE TABLE pedido (
    id_pedido INT(11) NOT NULL AUTO_INCREMENT,
    fecha_transaccion DATE NOT NULL,
    usuario_pedido INT(11) NOT NULL,
    total INT(11) NOT NULL,
    estado_pedido VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_pedido),
    INDEX idx_pedido_fecha (fecha_transaccion),
    CONSTRAINT fk_pedido_usuario FOREIGN KEY (usuario_pedido) REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_pedido_estado_texto FOREIGN KEY (estado_pedido) REFERENCES estado(estado) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.9 Tabla: transaccion (Detalle del pedido)
CREATE TABLE transaccion (
    id_transaccion INT(11) NOT NULL,
    cantidad_vendida INT(11) NOT NULL,
    precio_unitario_real DECIMAL(10,2) NOT NULL,
    pedido_transaccion INT(11) NOT NULL,
    producto_transaccion INT(11) NOT NULL,
    PRIMARY KEY (id_transaccion),
    CONSTRAINT chk_cantidad_positiva CHECK (cantidad_vendida > 0),
    CONSTRAINT fk_transaccion_pedido FOREIGN KEY (pedido_transaccion) REFERENCES pedido(id_pedido) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_transaccion_producto FOREIGN KEY (producto_transaccion) REFERENCES productos(codigo) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.10 Tabla: factura_pago (Pasarela de pagos)
CREATE TABLE factura_pago (
    id_factura INT(11) NOT NULL AUTO_INCREMENT,
    id_pedido INT(11) NOT NULL UNIQUE,
    metodo_pago ENUM('Tarjeta','PSE','Efectivo') NOT NULL,
    fecha_pago DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    valor_pagado DECIMAL(10,2) NOT NULL,
    estado_pago VARCHAR(30) NOT NULL DEFAULT 'Aprobado',
    PRIMARY KEY (id_factura),
    CONSTRAINT chk_valor_positivo CHECK (valor_pagado > 0),
    CONSTRAINT chk_estado_pago CHECK (estado_pago IN ('Pendiente','Aprobado','Rechazado','Reembolsado')),
    CONSTRAINT fk_factura_pedido FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.11 Tabla: auditoria_precio_articulo (Auditoría para disparadores)
CREATE TABLE auditoria_precio_articulo (
    id_auditoria INT(11) NOT NULL AUTO_INCREMENT,
    codigo_articulo INT(11) NOT NULL,
    precio_anterior DECIMAL(10,2) NOT NULL,
    precio_nuevo DECIMAL(10,2) NOT NULL,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP(),
    usuario_bd VARCHAR(50) DEFAULT CURRENT_USER(),
    PRIMARY KEY (id_auditoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =============================================================================
-- 2. DML: POBLAMIENTO INICIAL DE DATOS DE PRUEBA
-- =============================================================================

-- Estados
INSERT INTO estado (id_estado, estado) VALUES 
(1, 'pendiente'),
(2, 'enviado'),
(3, 'entregado');

-- Categorías
INSERT INTO categoria (id_categoria, nombre, descripcion) VALUES 
(1, 'Ropa y Calzado', 'Prendas de vestir y calzado formal e informal'),
(2, 'Accesorios', 'Bolsos, cinturones, gafas y bisutería'),
(3, 'Cuidado Personal', 'Productos naturales, aromáticos y cosméticos');

-- Proveedores
INSERT INTO proveedor (nit, nombre, contacto, ciudad) VALUES 
('900123456-1', 'Textiles del Llano S.A.S', '3105551234', 'Villavicencio'),
('900987654-2', 'Distribuidora Moda Colombia', '3208889900', 'Bogotá'),
('800456789-3', 'Cosméticos & Salud Natural', '3157774411', 'Medellín');

-- Usuarios
INSERT INTO usuario (id_usuario, cedula, nombre, apellido, correo, telefono) VALUES 
(1, 112305, 'Juan', 'Gómez', 'gomezjuan@gmail.com', 30023520),
(2, 102530, 'Nicolle', 'Prada', 'nicolleprada@gmail.com', 32106549),
(3, 335164, 'Martín', 'Berdugo', 'berdugomartin@gmail.com', 31259878),
(4, 351204, 'Nicolás', 'Ortiz', 'nicoortiz@gmail.com', 30012547);

-- Productos
INSERT INTO productos (codigo, nombre, precio_unitario, cantidad_disponible, id_categoria, nit_proveedor) VALUES 
(1100, 'jean', 145000.00, 20, 1, '900123456-1'),
(1101, 'tenis', 360000.00, 10, 1, '900987654-2'),
(1102, 'camisa', 95000.00, 15, 1, '900123456-1');

-- Bodegas
INSERT INTO bodega (id_bodega, nombre, ubicacion) VALUES 
(1, 'Bodega Central Villavicencio', 'Cra 33 # 40-12, Centro'),
(2, 'Bodega Norte Acacías', 'Calle 15 # 10-05, Acacías'),
(3, 'Bodega E-Market Satélite', 'Anillo Vial Km 2');

-- Stock inicial en Bodegas
INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual) VALUES 
(1100, 1, 12),
(1100, 2, 8),
(1101, 1, 6),
(1101, 3, 4),
(1102, 1, 10),
(1102, 2, 5);

-- Pedidos históricos
INSERT INTO pedido (id_pedido, fecha_transaccion, usuario_pedido, total, estado_pedido) VALUES 
(1, '2026-01-26', 1, 360000, 'entregado'),
(2, '2026-09-16', 3, 435000, 'enviado'),
(3, '2026-08-11', 2, 95000, 'pendiente');

-- Detalle de transacciones
INSERT INTO transaccion (id_transaccion, cantidad_vendida, precio_unitario_real, pedido_transaccion, producto_transaccion) VALUES 
(200, 3, 145000.00, 2, 1100),
(201, 1, 360000.00, 1, 1101),
(203, 1, 95000.00, 3, 1102);

-- Facturación de pagos
INSERT INTO factura_pago (id_factura, id_pedido, metodo_pago, fecha_pago, valor_pagado, estado_pago) VALUES 
(1, 1, 'Tarjeta', '2026-01-26 10:15:00', 360000.00, 'Aprobado'),
(2, 2, 'PSE', '2026-09-16 14:30:00', 435000.00, 'Aprobado'),
(3, 3, 'Efectivo', '2026-08-11 09:00:00', 95000.00, 'Pendiente');


-- =============================================================================
-- 3. DISPARADORES (TRIGGERS)
-- =============================================================================
DELIMITER //

-- Trigger 1: Auditoría de cambios de precio unitario en productos
DROP TRIGGER IF EXISTS trg_auditoria_precio_articulo //
CREATE TRIGGER trg_auditoria_precio_articulo
AFTER UPDATE ON productos
FOR EACH ROW
BEGIN
    IF OLD.precio_unitario <> NEW.precio_unitario THEN
        INSERT INTO auditoria_precio_articulo (
            codigo_articulo, 
            precio_anterior, 
            precio_nuevo, 
            fecha_modificacion, 
            usuario_bd
        )
        VALUES (
            OLD.codigo, 
            OLD.precio_unitario, 
            NEW.precio_unitario, 
            NOW(), 
            USER()
        );
    END IF;
END //

-- Trigger 2: Validar existencias antes de registrar en el detalle de la venta
DROP TRIGGER IF EXISTS trg_validar_stock_pedido //
CREATE TRIGGER trg_validar_stock_pedido
BEFORE INSERT ON transaccion
FOR EACH ROW
BEGIN
    DECLARE stock_actual INT;
    
    SELECT cantidad_disponible INTO stock_actual 
    FROM productos 
    WHERE codigo = NEW.producto_transaccion;
    
    IF stock_actual < NEW.cantidad_vendida THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Error: Stock insuficiente para el producto seleccionado.';
    END IF;
END //

DELIMITER ;


-- =============================================================================
-- 4. PROCEDIMIENTOS ALMACENADOS (TRANSACCIONALES)
-- =============================================================================
DELIMITER //

-- Procedimiento 1: Transferencia atómica de stock entre bodegas
DROP PROCEDURE IF EXISTS SP_ActualizarInventarioBodega //
CREATE PROCEDURE SP_ActualizarInventarioBodega(
    IN p_id_articulo INT,
    IN p_bodega_origen INT,
    IN p_bodega_destino INT,
    IN p_cantidad INT
)
BEGIN
    DECLARE v_stock_origen INT DEFAULT 0;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    
    SELECT stock_actual INTO v_stock_origen 
    FROM inventario_bodega 
    WHERE id_articulo = p_id_articulo AND id_bodega = p_bodega_origen
    FOR UPDATE;
    
    IF v_stock_origen >= p_cantidad THEN
        -- Descontar en origen
        UPDATE inventario_bodega 
        SET stock_actual = stock_actual - p_cantidad 
        WHERE id_articulo = p_id_articulo AND id_bodega = p_bodega_origen;
        
        -- Sumar o registrar en destino
        INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual)
        VALUES (p_id_articulo, p_bodega_destino, p_cantidad)
        ON DUPLICATE KEY UPDATE stock_actual = stock_actual + p_cantidad;
        
        COMMIT;
    ELSE
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Stock insuficiente en la bodega de origen.';
    END IF;
END //

-- Procedimiento 2: Registro atómico de Pedido Completo (Cabecera, Detalle, Stock y Pago)
DROP PROCEDURE IF EXISTS SP_RegistrarPedidoCompleto //
CREATE PROCEDURE SP_RegistrarPedidoCompleto(
    IN p_id_usuario INT,
    IN p_codigo_producto INT,
    IN p_cantidad INT,
    IN p_metodo_pago VARCHAR(20)
)
BEGIN
    DECLARE v_precio DECIMAL(10,2);
    DECLARE v_total DECIMAL(10,2);
    DECLARE v_nuevo_pedido_id INT;
    DECLARE v_stock INT;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    
    -- Validar precio y stock
    SELECT precio_unitario, cantidad_disponible INTO v_precio, v_stock 
    FROM productos 
    WHERE codigo = p_codigo_producto FOR UPDATE;
    
    IF v_stock < p_cantidad THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: No hay existencias suficientes.';
    END IF;
    
    SET v_total = v_precio * p_cantidad;
    
    -- Insertar Cabecera
    INSERT INTO pedido (fecha_transaccion, usuario_pedido, total, estado_pedido)
    VALUES (CURDATE(), p_id_usuario, v_total, 'pendiente');
    
    SET v_nuevo_pedido_id = LAST_INSERT_ID();
    
    -- Insertar Detalle en Transacción
    INSERT INTO transaccion (id_transaccion, cantidad_vendida, precio_unitario_real, pedido_transaccion, producto_transaccion)
    VALUES (FLOOR(RAND() * 899999 + 100000), p_cantidad, v_precio, v_nuevo_pedido_id, p_codigo_producto);
    
    -- Descontar del inventario general de productos
    UPDATE productos 
    SET cantidad_disponible = cantidad_disponible - p_cantidad 
    WHERE codigo = p_codigo_producto;
    
    -- Registrar Factura de Pago
    INSERT INTO factura_pago (id_pedido, metodo_pago, fecha_pago, valor_pagado, estado_pago)
    VALUES (v_nuevo_pedido_id, p_metodo_pago, NOW(), v_total, 'Aprobado');
    
    COMMIT;
END //

DELIMITER ;


-- =============================================================================
-- 5. VISTAS ANALÍTICAS
-- =============================================================================

CREATE OR REPLACE VIEW vista_ventas_por_categoria AS
SELECT 
    c.nombre AS categoria,
    COUNT(t.id_transaccion) AS cantidad_ventas,
    IFNULL(SUM(t.cantidad_vendida * t.precio_unitario_real), 0) AS total_recaudado
FROM categoria c
LEFT JOIN productos p ON c.id_categoria = p.id_categoria
LEFT JOIN transaccion t ON p.codigo = t.producto_transaccion
GROUP BY c.id_categoria, c.nombre;

CREATE OR REPLACE VIEW vista_pedidos_resumen AS
SELECT 
    p.id_pedido,
    CONCAT(u.nombre, ' ', u.apellido) AS cliente,
    p.fecha_transaccion,
    p.total,
    p.estado_pedido,
    f.metodo_pago,
    f.estado_pago
FROM pedido p
INNER JOIN usuario u ON p.usuario_pedido = u.id_usuario
LEFT JOIN factura_pago f ON p.id_pedido = f.id_pedido;


-- =============================================================================
-- 6. SEGURIDAD: CREACIÓN DE ROLES, USUARIOS Y ASIGNACIÓN DE PRIVILEGIOS
-- =============================================================================

-- 6.1 Creación de roles
CREATE ROLE IF NOT EXISTS 'Administrador_DB';
CREATE ROLE IF NOT EXISTS 'Cajero_App';

-- 6.2 Asignación de privilegios a los roles
GRANT ALL PRIVILEGES ON parcial.* TO 'Administrador_DB';

GRANT SELECT ON parcial.* TO 'Cajero_App';
GRANT INSERT, UPDATE ON parcial.pedido TO 'Cajero_App';
GRANT INSERT ON parcial.transaccion TO 'Cajero_App';
GRANT INSERT ON parcial.factura_pago TO 'Cajero_App';
GRANT EXECUTE ON PROCEDURE parcial.SP_RegistrarPedidoCompleto TO 'Cajero_App';

-- 6.3 Creación de usuarios de conexión
CREATE USER IF NOT EXISTS 'admin_db'@'localhost' IDENTIFIED BY 'Admin2026*Seguro';
CREATE USER IF NOT EXISTS 'cajero_app'@'localhost' IDENTIFIED BY 'Cajero2026*App';

-- 6.4 Concesión de roles a los usuarios
GRANT 'Administrador_DB' TO 'admin_db'@'localhost';
GRANT 'Cajero_App' TO 'cajero_app'@'localhost';

-- 6.5 Activación automática de roles al iniciar sesión
SET DEFAULT ROLE 'Administrador_DB' FOR 'admin_db'@'localhost';
SET DEFAULT ROLE 'Cajero_App' FOR 'cajero_app'@'localhost';

FLUSH PRIVILEGES;