-- =============================================================================
-- PROYECTO FINAL: SISTEMA INTEGRAL E-MARKET EXPRESS
-- CURSO: BASES DE DATOS (Cód. 603401) - UNIVERSIDAD DE LOS LLANOS
-- SCRIPT SQL CONSOLIDADO (DDL, DML, TRIGGERS, PROCEDIMIENTOS, VISTAS Y ROLES)
-- =============================================================================

-- Configuración de codificación UTF-8 para soporte de tildes y caracteres especiales
SET NAMES utf8mb4;

DROP DATABASE IF EXISTS parcial;
CREATE DATABASE parcial CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE parcial;

-- =============================================================================
-- 1. DDL: CREACIÓN DE TABLAS, RESTRICCIONES E ÍNDICES
-- =============================================================================

-- 1.1 Tabla: usuario (Administradores, Cajeros y Clientes del sistema)
CREATE TABLE usuario (
    id_usuario INT(11) NOT NULL AUTO_INCREMENT,
    cedula INT(11) NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    correo VARCHAR(50) NOT NULL UNIQUE,
    telefono VARCHAR(20) NOT NULL,
    contrasena VARCHAR(255) DEFAULT NULL,
    rol ENUM('Administrador', 'Cajero', 'Cliente') NOT NULL DEFAULT 'Cliente',
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
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado_pedido VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_pedido),
    INDEX idx_pedido_fecha (fecha_transaccion),
    CONSTRAINT fk_pedido_usuario FOREIGN KEY (usuario_pedido) REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_estado_texto FOREIGN KEY (estado_pedido) REFERENCES estado(estado) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.9 Tabla: transaccion (Detalle del pedido)
CREATE TABLE transaccion (
    id_transaccion INT(11) NOT NULL AUTO_INCREMENT,
    cantidad_vendida INT(11) NOT NULL,
    precio_unitario_real DECIMAL(10,2) NOT NULL,
    pedido_transaccion INT(11) NOT NULL,
    producto_transaccion INT(11) NOT NULL,
    PRIMARY KEY (id_transaccion),
    CONSTRAINT chk_cantidad_positiva CHECK (cantidad_vendida > 0),
    CONSTRAINT fk_transaccion_pedido FOREIGN KEY (pedido_transaccion) REFERENCES pedido(id_pedido) ON UPDATE CASCADE ON DELETE CASCADE,
    -- RESTRICT impide borrar productos que ya tienen ventas registradas en el historial
    CONSTRAINT fk_transaccion_producto FOREIGN KEY (producto_transaccion) REFERENCES productos(codigo) ON UPDATE CASCADE ON DELETE RESTRICT
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
(3, 'Cuidado Personal', 'Productos naturales, aromáticos y cosméticos'),
(5, 'Casual', 'Ropa casual'),
(6, 'Deportiva', 'Ropa deportiva'),
(7, 'Oversized', 'Ropa ancha'),
(8, 'Mujer', 'Ropa de mujer'),
(9, 'Hombre', 'Ropa de hombre');

-- Proveedores
INSERT INTO proveedor (nit, nombre, contacto, ciudad) VALUES 
('900123456-1', 'Textiles del Llano S.A.S', '3105551234', 'Villavicencio'),
('900987654-2', 'Distribuidora Moda Colombia', '3208889900', 'Bogotá'),
('800456789-3', 'Cosméticos & Salud Natural', '3157774411', 'Medellín'),
('879463208-6', 'Laboratorios Funat', '3116521452', 'Bogotá');

-- Usuarios (Clientes y Cajeros de prueba con contraseñas protegidas mediante PBKDF2-SHA256)
-- Nota de demostración: el cajero #5 ('cajero1@emarket.com') corresponde a la clave 'Cajero2026*App' y los clientes a '123456'.
INSERT INTO usuario (id_usuario, cedula, nombre, apellido, correo, telefono, contrasena, rol) VALUES 
(1, 112305, 'Juan', 'Gómez', 'gomezjuan@gmail.com', '30023520', 'pbkdf2_sha256$120000$UeZmqlyVoshJPBRu4pea3Q$_4201SblVZ9-IE7r7MWr9OVFBZ8dKO5U5etq7Vmvfo0', 'Cliente'),
(2, 102530, 'Nicolle', 'Prada', 'nicolleprada@gmail.com', '32106549', 'pbkdf2_sha256$120000$_xvrX07jeaoIduHtNQ0eDQ$tqn2xoyABCySvi9CECB-UXUsHYC7eg9h9BORSXbWqv0', 'Cliente'),
(3, 335164, 'Martín', 'Berdugo', 'berdugomartin@gmail.com', '31259878', 'pbkdf2_sha256$120000$hJJMruKggJHbfaQ7XwAKNA$QnD30HpbsQk0JBEJLLY0F9aJ9LL4ThEkM8-aACf8qkE', 'Cliente'),
(4, 351204, 'Nicolás', 'Ortiz', 'nicoortiz@gmail.com', '30012547', 'pbkdf2_sha256$120000$3YPEaCf2pOsKpYaoZ2DfGA$zbtum-1zA2XuBfhbeHgb9CYCu86fZKDwkr7E8uy8uok', 'Cliente'),
(5, 1009876, 'Carlos', 'Cajero', 'cajero1@emarket.com', '3115559988', 'pbkdf2_sha256$120000$rH7K2RIkHLaFM4GFaeg1BA$icNbsvCyESkm2cJXnTHihOCqHcre1k_FQ-4-AknqLiE', 'Cajero'),
(6, 11225222, 'alejo', 'flor', 'floralejo@gmal.cm', '31256234', 'pbkdf2_sha256$120000$XsqN5qusQQ20U8VCFTK3nw$cZ5rO15CStT0plXGggBGURtP9KIB6x1qzJ-LNucFN4o', 'Cliente');

-- Productos
INSERT INTO productos (codigo, nombre, precio_unitario, cantidad_disponible, id_categoria, nit_proveedor) VALUES 
(1100, 'jean', 145000.00, 19, 1, '900123456-1'),
(1101, 'tenis', 360000.00, 10, 1, '900987654-2'),
(1102, 'camisa', 95000.00, 15, 1, '900123456-1'),
(1103, 'chaqueta', 220000.00, 8, 5, '900987654-2'),
(1104, 'gorra', 55000.00, 23, 5, '900987654-2'),
(1105, 'medias', 25000.00, 15, 6, '900987654-2'),
(1107, 'correa', 45000.00, 9, 9, '900987654-2'),
(2000, 'Purgante', 10000.00, 11, 3, '879463208-6');

-- Bodegas
INSERT INTO bodega (id_bodega, nombre, ubicacion) VALUES 
(1, 'Bodega Central Villavicencio', 'Cra 33 # 40-12, Centro'),
(2, 'Bodega Norte Acacías', 'Calle 15 # 10-05, Acacías'),
(3, 'Bodega E-Market Satélite', 'Anillo Vial Km 2');

-- Stock inicial en Bodegas
-- La suma del stock de todas las bodegas coincide con productos.cantidad_disponible.
INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual) VALUES 
(1100, 1, 11),
(1100, 2, 8),
(1101, 1, 6),
(1101, 3, 4),
(1102, 1, 10),
(1102, 2, 5),
(1103, 1, 8),
(1104, 1, 23),
(1105, 1, 15),
(1107, 1, 9),
(2000, 1, 11);

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

-- Trigger 3: Registrar en la Bodega 1 (predeterminada) el stock inicial de un producto nuevo
DROP TRIGGER IF EXISTS trg_stock_inicial_bodega //
CREATE TRIGGER trg_stock_inicial_bodega
AFTER INSERT ON productos
FOR EACH ROW
BEGIN
    IF NEW.cantidad_disponible > 0 AND EXISTS (SELECT 1 FROM bodega WHERE id_bodega = 1) THEN
        INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual)
        VALUES (NEW.codigo, 1, NEW.cantidad_disponible)
        ON DUPLICATE KEY UPDATE stock_actual = stock_actual + NEW.cantidad_disponible;
    END IF;
END //

-- Trigger 4: Sincronizar inventario_bodega cada vez que cambie productos.cantidad_disponible
--   * Si el stock AUMENTA (devoluciones / reintegros / ajuste manual): se suma a la Bodega 1.
--   * Si el stock DISMINUYE (ventas): se descuenta primero de la Bodega 1 y,
--     si no alcanza, de las demás bodegas en orden ascendente.
--   * La variable de sesión @sync_desde_bodega = 1 evita el doble ajuste cuando la
--     aplicación recalcula productos a partir de inventario_bodega.
DROP TRIGGER IF EXISTS trg_sincronizar_stock_bodega //
CREATE TRIGGER trg_sincronizar_stock_bodega
AFTER UPDATE ON productos
FOR EACH ROW
BEGIN
    DECLARE v_diferencia INT DEFAULT 0;
    DECLARE v_restante INT DEFAULT 0;
    DECLARE v_bodega INT DEFAULT NULL;
    DECLARE v_stock_bodega INT DEFAULT 0;
    DECLARE v_descuento INT DEFAULT 0;

    IF IFNULL(@sync_desde_bodega, 0) = 0
       AND OLD.cantidad_disponible <> NEW.cantidad_disponible THEN

        SET v_diferencia = NEW.cantidad_disponible - OLD.cantidad_disponible;

        IF v_diferencia > 0 THEN
            IF EXISTS (SELECT 1 FROM bodega WHERE id_bodega = 1) THEN
                INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual)
                VALUES (NEW.codigo, 1, v_diferencia)
                ON DUPLICATE KEY UPDATE stock_actual = stock_actual + v_diferencia;
            END IF;
        ELSE
            SET v_restante = -v_diferencia;
            descontar: WHILE v_restante > 0 DO
                SET v_bodega = NULL;
                SELECT id_bodega, stock_actual INTO v_bodega, v_stock_bodega
                FROM inventario_bodega
                WHERE id_articulo = NEW.codigo AND stock_actual > 0
                ORDER BY (id_bodega = 1) DESC, id_bodega ASC
                LIMIT 1;

                IF v_bodega IS NULL THEN
                    LEAVE descontar;
                END IF;

                SET v_descuento = LEAST(v_stock_bodega, v_restante);
                UPDATE inventario_bodega
                SET stock_actual = stock_actual - v_descuento
                WHERE id_articulo = NEW.codigo AND id_bodega = v_bodega;

                SET v_restante = v_restante - v_descuento;
            END WHILE descontar;
        END IF;
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

    -- Validaciones estrictas de entrada antes de iniciar la transacción
    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: La cantidad a transferir debe ser un entero mayor que cero.';
    END IF;

    IF p_bodega_origen = p_bodega_destino THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: La bodega de origen y la de destino deben ser distintas.';
    END IF;

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

-- Procedimiento 2: Registro atómico de Pedido Completo (Cabecera, Detalle, Stock y Factura única)
DROP PROCEDURE IF EXISTS SP_RegistrarPedidoCompleto //
CREATE PROCEDURE SP_RegistrarPedidoCompleto(
    IN p_id_usuario INT,
    IN p_carrito_json LONGTEXT,
    IN p_metodo_pago VARCHAR(20)
)
BEGIN
    DECLARE v_total DECIMAL(10,2) DEFAULT 0;
    DECLARE v_nuevo_pedido_id INT;
    DECLARE v_num_items INT DEFAULT 0;
    DECLARE i INT DEFAULT 0;
    DECLARE v_codigo INT;
    DECLARE v_cantidad INT;
    DECLARE v_precio DECIMAL(10,2);
    DECLARE v_stock INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    IF JSON_VALID(p_carrito_json) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Formato JSON de productos inválido.';
    END IF;

    SET v_num_items = JSON_LENGTH(p_carrito_json);
    IF v_num_items <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: El carrito está vacío.';
    END IF;

    -- 1. Validar existencias y acumular total de la compra
    WHILE i < v_num_items DO
        SET v_codigo = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].codigo'))) AS UNSIGNED);
        SET v_cantidad = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].cantidad'))) AS SIGNED);

        IF v_cantidad <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: La cantidad de cada producto debe ser mayor a cero.';
        END IF;

        SET v_precio = NULL;
        SET v_stock = NULL;

        SELECT precio_unitario, cantidad_disponible 
        INTO v_precio, v_stock 
        FROM productos 
        WHERE codigo = v_codigo 
        FOR UPDATE;

        IF v_precio IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Uno de los productos no existe en la base de datos.';
        END IF;

        IF v_stock < v_cantidad THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Existencias insuficientes para uno de los productos.';
        END IF;

        SET v_total = v_total + (v_precio * v_cantidad);
        SET i = i + 1;
    END WHILE;

    -- 2. Insertar UNA ÚNICA Cabecera de Pedido para toda la compra
    INSERT INTO pedido (fecha_transaccion, usuario_pedido, total, estado_pedido)
    VALUES (CURDATE(), p_id_usuario, v_total, 'pendiente');

    SET v_nuevo_pedido_id = LAST_INSERT_ID();

    -- 3. Insertar cada producto como ítem de detalle en transaccion y descontar inventario
    SET i = 0;
    WHILE i < v_num_items DO
        SET v_codigo = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].codigo'))) AS UNSIGNED);
        SET v_cantidad = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].cantidad'))) AS SIGNED);

        SELECT precio_unitario INTO v_precio FROM productos WHERE codigo = v_codigo;

        -- id_transaccion se genera automáticamente con AUTO_INCREMENT
        INSERT INTO transaccion (cantidad_vendida, precio_unitario_real, pedido_transaccion, producto_transaccion)
        VALUES (v_cantidad, v_precio, v_nuevo_pedido_id, v_codigo);

        -- El trigger trg_sincronizar_stock_bodega descuenta también de inventario_bodega (Bodega 1 primero)
        UPDATE productos 
        SET cantidad_disponible = cantidad_disponible - v_cantidad 
        WHERE codigo = v_codigo;

        SET i = i + 1;
    END WHILE;

    -- 4. Registrar UNA ÚNICA Factura de Pago para toda la compra
    INSERT INTO factura_pago (id_pedido, metodo_pago, fecha_pago, valor_pagado, estado_pago)
    VALUES (v_nuevo_pedido_id, p_metodo_pago, NOW(), v_total, 'Aprobado');

    COMMIT;
END //

-- Procedimiento 3: Modificación atómica de Pedido Existente y actualización de su Factura
DROP PROCEDURE IF EXISTS SP_ModificarPedidoExistente //
CREATE PROCEDURE SP_ModificarPedidoExistente(
    IN p_id_pedido INT,
    IN p_id_usuario INT,
    IN p_carrito_json LONGTEXT,
    IN p_metodo_pago VARCHAR(20)
)
BEGIN
    DECLARE v_total DECIMAL(10,2) DEFAULT 0;
    DECLARE v_num_items INT DEFAULT 0;
    DECLARE i INT DEFAULT 0;
    DECLARE v_codigo INT;
    DECLARE v_cantidad INT;
    DECLARE v_precio DECIMAL(10,2);
    DECLARE v_stock INT;
    DECLARE v_existe_pedido INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT COUNT(*) INTO v_existe_pedido FROM pedido WHERE id_pedido = p_id_pedido;
    IF v_existe_pedido = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: El pedido especificado no existe.';
    END IF;

    IF JSON_VALID(p_carrito_json) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Formato JSON de productos inválido.';
    END IF;

    SET v_num_items = JSON_LENGTH(p_carrito_json);
    IF v_num_items <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: El pedido modificado debe tener al menos un producto.';
    END IF;

    -- 1. Reintegrar al inventario los artículos previos del pedido
    CREATE TEMPORARY TABLE IF NOT EXISTS temp_reintegrar_stock (
        id_prod INT,
        cant INT
    );
    TRUNCATE TABLE temp_reintegrar_stock;

    INSERT INTO temp_reintegrar_stock (id_prod, cant)
    SELECT producto_transaccion, cantidad_vendida 
    FROM transaccion 
    WHERE pedido_transaccion = p_id_pedido;

    UPDATE productos p
    INNER JOIN temp_reintegrar_stock t ON p.codigo = t.id_prod
    SET p.cantidad_disponible = p.cantidad_disponible + t.cant;

    DROP TEMPORARY TABLE IF EXISTS temp_reintegrar_stock;

    -- 2. Validar existencias con los nuevos artículos y calcular el nuevo total
    SET i = 0;
    WHILE i < v_num_items DO
        SET v_codigo = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].codigo'))) AS UNSIGNED);
        SET v_cantidad = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].cantidad'))) AS SIGNED);

        IF v_cantidad <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: La cantidad de cada producto debe ser mayor a cero.';
        END IF;

        SET v_precio = NULL;
        SET v_stock = NULL;

        SELECT precio_unitario, cantidad_disponible 
        INTO v_precio, v_stock 
        FROM productos 
        WHERE codigo = v_codigo 
        FOR UPDATE;

        IF v_precio IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Uno de los productos no existe en la base de datos.';
        END IF;

        IF v_stock < v_cantidad THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Existencias insuficientes para uno de los productos al actualizar.';
        END IF;

        SET v_total = v_total + (v_precio * v_cantidad);
        SET i = i + 1;
    END WHILE;

    -- 3. Eliminar los detalles anteriores en transaccion
    DELETE FROM transaccion WHERE pedido_transaccion = p_id_pedido;

    -- 4. Insertar los nuevos detalles y descontar el inventario actualizado
    SET i = 0;
    WHILE i < v_num_items DO
        SET v_codigo = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].codigo'))) AS UNSIGNED);
        SET v_cantidad = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_carrito_json, CONCAT('$[', i, '].cantidad'))) AS SIGNED);

        SELECT precio_unitario INTO v_precio FROM productos WHERE codigo = v_codigo;

        -- id_transaccion se genera automáticamente con AUTO_INCREMENT
        INSERT INTO transaccion (cantidad_vendida, precio_unitario_real, pedido_transaccion, producto_transaccion)
        VALUES (v_cantidad, v_precio, p_id_pedido, v_codigo);

        UPDATE productos 
        SET cantidad_disponible = cantidad_disponible - v_cantidad 
        WHERE codigo = v_codigo;

        SET i = i + 1;
    END WHILE;

    -- 5. Actualizar la cabecera del pedido (total y cliente si cambió)
    UPDATE pedido 
    SET total = v_total, usuario_pedido = p_id_usuario 
    WHERE id_pedido = p_id_pedido;

    -- 6. Actualizar la factura existente asociada al pedido
    UPDATE factura_pago 
    SET valor_pagado = v_total, metodo_pago = p_metodo_pago, fecha_pago = NOW()
    WHERE id_pedido = p_id_pedido;

    IF ROW_COUNT() = 0 THEN
        INSERT INTO factura_pago (id_pedido, metodo_pago, fecha_pago, valor_pagado, estado_pago)
        VALUES (p_id_pedido, p_metodo_pago, NOW(), v_total, 'Aprobado');
    END IF;

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

CREATE OR REPLACE VIEW vista_clientes_frecuentes AS
SELECT u.id_usuario, CONCAT(u.nombre, ' ', u.apellido) AS cliente,
       COUNT(p.id_pedido) AS total_pedidos,
       SUM(p.total) AS total_gastado
FROM usuario u
INNER JOIN pedido p ON u.id_usuario = p.usuario_pedido
GROUP BY u.id_usuario, u.nombre, u.apellido
HAVING COUNT(p.id_pedido) >= 1 AND SUM(p.total) >= 100000;

CREATE OR REPLACE VIEW vista_productos_sobre_promedio AS
SELECT p.codigo, p.nombre, p.precio_unitario,
       (SELECT ROUND(AVG(precio_unitario), 2) FROM productos) AS promedio_catalogo
FROM productos p
WHERE p.precio_unitario > (SELECT AVG(precio_unitario) FROM productos);

-- =============================================================================
-- 6. SEGURIDAD: ROLES, MÍNIMO PRIVILEGIO (GRANT / REVOKE) Y USUARIOS
-- =============================================================================

-- 6.1 Recreación limpia de roles para garantizar ausencia de privilegios heredados
DROP ROLE IF EXISTS 'Administrador_DB';
DROP ROLE IF EXISTS 'Cajero_App';

CREATE ROLE 'Administrador_DB';
CREATE ROLE 'Cajero_App';

-- 6.2 Creación de usuarios de conexión
CREATE USER IF NOT EXISTS 'admin_db'@'localhost' IDENTIFIED BY 'Admin2026*Seguro';
CREATE USER IF NOT EXISTS 'admin_db'@'127.0.0.1' IDENTIFIED BY 'Admin2026*Seguro';
CREATE USER IF NOT EXISTS 'admin_db'@'%' IDENTIFIED BY 'Admin2026*Seguro';

CREATE USER IF NOT EXISTS 'cajero_app'@'localhost' IDENTIFIED BY 'Cajero2026*App';
CREATE USER IF NOT EXISTS 'cajero_app'@'127.0.0.1' IDENTIFIED BY 'Cajero2026*App';
CREATE USER IF NOT EXISTS 'cajero_app'@'%' IDENTIFIED BY 'Cajero2026*App';

-- 6.3 Limpieza previa de privilegios directos mediante REVOKE (idempotente)
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'admin_db'@'localhost', 'admin_db'@'127.0.0.1', 'admin_db'@'%';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'cajero_app'@'localhost', 'cajero_app'@'127.0.0.1', 'cajero_app'@'%';

-- 6.4 Privilegios del rol Administrador_DB (acotado al esquema parcial)
GRANT ALL PRIVILEGES ON parcial.* TO 'Administrador_DB';

-- 6.5 Privilegios de MÍNIMO PRIVILEGIO para el rol Cajero_App
-- Lectura estricta solo sobre tablas operativas de caja y catálogo (excluye auditoria_precio_articulo y vistas gerenciales)
GRANT SELECT ON parcial.usuario TO 'Cajero_App';
GRANT SELECT ON parcial.estado TO 'Cajero_App';
GRANT SELECT ON parcial.categoria TO 'Cajero_App';
GRANT SELECT ON parcial.proveedor TO 'Cajero_App';
GRANT SELECT ON parcial.bodega TO 'Cajero_App';
GRANT SELECT ON parcial.inventario_bodega TO 'Cajero_App';
GRANT SELECT ON parcial.productos TO 'Cajero_App';
GRANT SELECT ON parcial.pedido TO 'Cajero_App';
GRANT SELECT ON parcial.transaccion TO 'Cajero_App';
GRANT SELECT ON parcial.factura_pago TO 'Cajero_App';
GRANT SELECT ON parcial.vista_pedidos_resumen TO 'Cajero_App';

-- Escritura acotada a clientes y punto de venta, con endurecimiento explícito vía REVOKE
GRANT INSERT, UPDATE, DELETE ON parcial.usuario TO 'Cajero_App';
-- El cajero puede registrar y consultar clientes, pero no alterar roles/contraseñas de cuentas existentes
REVOKE UPDATE ON parcial.usuario FROM 'Cajero_App';

GRANT INSERT, UPDATE, DELETE ON parcial.pedido TO 'Cajero_App';
-- El cajero nunca puede eliminar pedidos históricos (solo registrar y actualizar estado)
REVOKE DELETE ON parcial.pedido FROM 'Cajero_App';

GRANT INSERT, DELETE ON parcial.transaccion TO 'Cajero_App';

GRANT INSERT, UPDATE, DELETE ON parcial.factura_pago TO 'Cajero_App';
-- El cajero nunca puede borrar facturas emitidas
REVOKE DELETE ON parcial.factura_pago FROM 'Cajero_App';

-- Mínimo privilegio por columna sobre productos:
-- Se revoca INSERT/UPDATE/DELETE general para evitar cambios de precios o borrados,
-- conservando únicamente SELECT y UPDATE sobre cantidad_disponible.
GRANT INSERT, UPDATE, DELETE ON parcial.productos TO 'Cajero_App';
REVOKE INSERT, UPDATE, DELETE ON parcial.productos FROM 'Cajero_App';
GRANT UPDATE (cantidad_disponible) ON parcial.productos TO 'Cajero_App';

-- Ejecución restringida únicamente a los procedimientos transaccionales de venta
-- (se excluye SP_ActualizarInventarioBodega y tablas maestras/auditoría)
GRANT EXECUTE ON PROCEDURE parcial.SP_RegistrarPedidoCompleto TO 'Cajero_App';
GRANT EXECUTE ON PROCEDURE parcial.SP_ModificarPedidoExistente TO 'Cajero_App';

-- 6.6 Concesión de roles y permisos de administración de respaldo a admin_db
GRANT 'Administrador_DB' TO 'admin_db'@'localhost', 'admin_db'@'127.0.0.1', 'admin_db'@'%';
GRANT 'Cajero_App' TO 'cajero_app'@'localhost', 'cajero_app'@'127.0.0.1', 'cajero_app'@'%';

-- Mínimo privilegio global para admin_db: control total sobre 'parcial.*' y permisos de monitoreo/respaldo,
-- sin otorgar permisos destructivos sobre tablas del sistema mysql.*
GRANT ALL PRIVILEGES ON parcial.* TO 'admin_db'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON parcial.* TO 'admin_db'@'127.0.0.1' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON parcial.* TO 'admin_db'@'%' WITH GRANT OPTION;
GRANT PROCESS, RELOAD, SHOW DATABASES ON *.* TO 'admin_db'@'localhost';
GRANT PROCESS, RELOAD, SHOW DATABASES ON *.* TO 'admin_db'@'127.0.0.1';
GRANT PROCESS, RELOAD, SHOW DATABASES ON *.* TO 'admin_db'@'%';

-- 6.7 Activación automática de roles al iniciar sesión
SET DEFAULT ROLE 'Administrador_DB' FOR 'admin_db'@'localhost';
SET DEFAULT ROLE 'Administrador_DB' FOR 'admin_db'@'127.0.0.1';
SET DEFAULT ROLE 'Administrador_DB' FOR 'admin_db'@'%';

SET DEFAULT ROLE 'Cajero_App' FOR 'cajero_app'@'localhost';
SET DEFAULT ROLE 'Cajero_App' FOR 'cajero_app'@'127.0.0.1';
SET DEFAULT ROLE 'Cajero_App' FOR 'cajero_app'@'%';

FLUSH PRIVILEGES;


-- =============================================================================
-- 7. AUDITORÍA DE PRIVILEGIOS Y POLÍTICA DE BACKUP / RESTORE
-- =============================================================================

-- Verificación inmediata de privilegios efectivos asignados a cada rol
SHOW GRANTS FOR 'Administrador_DB';
SHOW GRANTS FOR 'Cajero_App';

/*
  POLÍTICA Y COMANDOS OFICIALES DE RESPALDO Y RECUPERACIÓN (MariaDB / XAMPP):
  También disponible de forma automatizada en: script base/backup_restore.bat

  1. BACKUP COMPLETO (esquema, datos, vistas, triggers, procedimientos y eventos):
     "C:\xampp\mysql\bin\mysqldump.exe" --host=localhost --port=3306 --user=root ^
       --single-transaction --routines --triggers --events --add-drop-database ^
       --databases parcial --default-character-set=utf8mb4 ^
       --result-file="script base\backups\backup_parcial_YYYYMMDD_HHMMSS.sql"

  2. BACKUP SOLO ESTRUCTURA (DDL + rutinas + triggers, sin datos):
     "C:\xampp\mysql\bin\mysqldump.exe" --host=localhost --port=3306 --user=root ^
       --no-data --routines --triggers --events --add-drop-database ^
       --databases parcial --default-character-set=utf8mb4 ^
       --result-file="script base\backups\estructura_parcial_YYYYMMDD_HHMMSS.sql"

  3. RESTORE (recuperación total desde archivo .sql):
     "C:\xampp\mysql\bin\mysql.exe" --host=localhost --port=3306 --user=root ^
       --default-character-set=utf8mb4 < "script base\backups\backup_parcial_YYYYMMDD_HHMMSS.sql"
*/