CREATE TABLE Clientes (
                          id_cliente SERIAL PRIMARY KEY,
                          nombre VARCHAR(100) NOT NULL,
                          apellido VARCHAR(100) NOT NULL,
                          email VARCHAR(150) NOT NULL UNIQUE,
                          telefono VARCHAR(20),
                          fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
                          dni CHAR(8) NOT NULL UNIQUE
);

CREATE TABLE Categorias (
                            id_categoria SERIAL PRIMARY KEY,
                            nombre VARCHAR(80) NOT NULL,
                            descripcion VARCHAR(200)
);

CREATE TABLE Vendedores (
                            id_vendedor SERIAL PRIMARY KEY,
                            nombre_tienda VARCHAR(150) NOT NULL,
                            email VARCHAR(150),
                            ruc CHAR(11) NOT NULL UNIQUE,
                            calificacion DECIMAL(3,2) DEFAULT 0 CHECK (calificacion BETWEEN 0 AND 5)
);

CREATE TABLE Productos (
                           id_producto SERIAL PRIMARY KEY,
                           nombre VARCHAR(200) NOT NULL,
                           descripcion VARCHAR(500),
                           precio DECIMAL(10,2) NOT NULL CHECK (precio > 0),
                           stock INTEGER NOT NULL CHECK (stock >= 0),
                           marca VARCHAR(100),
                           tipo VARCHAR(30) CHECK (tipo IN ('fisico','digital')),
                           id_categoria INTEGER NOT NULL REFERENCES Categorias(id_categoria),
                           id_vendedor INTEGER NOT NULL REFERENCES Vendedores(id_vendedor)
);

CREATE TABLE Cupones (
                         id_cupon SERIAL PRIMARY KEY,
                         codigo VARCHAR(30) NOT NULL UNIQUE,
                         descuento DECIMAL(5,2) NOT NULL CHECK (descuento > 0),
                         tipo_descuento VARCHAR(20) NOT NULL CHECK (tipo_descuento IN ('porcentaje','monto_fijo')),
                         fecha_vencimiento DATE NOT NULL,
                         usos_maximos INTEGER NOT NULL CHECK (usos_maximos > 0),
                         usos_actuales INTEGER NOT NULL DEFAULT 0 CHECK (usos_actuales >= 0)
);

CREATE TABLE Ordenes (
                         id_orden SERIAL PRIMARY KEY,
                         fecha_orden TIMESTAMP NOT NULL DEFAULT NOW(),
                         estado VARCHAR(30) NOT NULL CHECK (estado IN ('pendiente','pagada','en_despacho','entregada','cancelada')),
                         total DECIMAL(10,2) NOT NULL DEFAULT 0,
                         id_cliente INTEGER NOT NULL REFERENCES Clientes(id_cliente),
                         id_cupon INTEGER REFERENCES Cupones(id_cupon)
);

CREATE TABLE DetalleOrden (
                              id_orden INTEGER NOT NULL REFERENCES Ordenes(id_orden) ON DELETE CASCADE,
                              id_producto INTEGER NOT NULL REFERENCES Productos(id_producto),
                              cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                              precio_unitario DECIMAL(10,2) NOT NULL CHECK (precio_unitario > 0),
                              subtotal DECIMAL(10,2) NOT NULL,
                              PRIMARY KEY (id_orden, id_producto)
);

CREATE TABLE Pagos (
                       id_pago SERIAL PRIMARY KEY,
                       metodo VARCHAR(50) NOT NULL CHECK (metodo IN ('tarjeta','yape','plin','efectivo')),
                       estado VARCHAR(30) NOT NULL CHECK (estado IN ('aprobado','rechazado','pendiente')),
                       fecha_pago TIMESTAMP NOT NULL DEFAULT NOW(),
                       monto DECIMAL(10,2) NOT NULL CHECK (monto > 0),
                       codigo_autorizacion VARCHAR(50),
                       id_orden INTEGER NOT NULL UNIQUE REFERENCES Ordenes(id_orden)
);

CREATE TABLE Envios (
                        id_envio SERIAL PRIMARY KEY,
                        direccion_destino VARCHAR(300) NOT NULL,
                        estado_envio VARCHAR(30) NOT NULL CHECK (estado_envio IN ('preparando','despachado','en_camino','entregado','devuelto')),
                        fecha_despacho TIMESTAMP,
                        fecha_entrega TIMESTAMP,
                        courier VARCHAR(100),
                        numero_seguimiento VARCHAR(50),
                        id_orden INTEGER NOT NULL UNIQUE REFERENCES Ordenes(id_orden)
);

CREATE TABLE Resenas (
                         id_resena SERIAL PRIMARY KEY,
                         puntuacion INTEGER NOT NULL CHECK (puntuacion BETWEEN 1 AND 5),
                         comentario VARCHAR(1000),
                         fecha DATE NOT NULL DEFAULT CURRENT_DATE,
                         id_cliente INTEGER NOT NULL REFERENCES Clientes(id_cliente),
                         id_orden INTEGER NOT NULL,
                         id_producto INTEGER NOT NULL,
                         UNIQUE (id_orden, id_producto),
                         FOREIGN KEY (id_orden, id_producto) REFERENCES DetalleOrden(id_orden, id_producto)
);

--Calcular el subtotal automáticamente
CREATE OR REPLACE FUNCTION fn_subtotal() RETURNS TRIGGER AS $$
BEGIN
    NEW.subtotal := NEW.cantidad * NEW.precio_unitario;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subtotal
    BEFORE INSERT OR UPDATE ON DetalleOrden
    FOR EACH ROW EXECUTE FUNCTION fn_subtotal();

--Recalcular el total de la orden
CREATE OR REPLACE FUNCTION fn_total_orden() RETURNS TRIGGER AS $$
BEGIN
    UPDATE Ordenes
    SET total = (SELECT COALESCE(SUM(subtotal),0) FROM DetalleOrden WHERE id_orden = NEW.id_orden)
    WHERE id_orden = NEW.id_orden;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_total_orden
    AFTER INSERT OR UPDATE ON DetalleOrden
    FOR EACH ROW EXECUTE FUNCTION fn_total_orden();

--Descuento de stock al confirmarse el pago (estado pasa a verse como 'pagada')
CREATE OR REPLACE FUNCTION fn_descontar_stock() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'pagada' AND OLD.estado IS DISTINCT FROM 'pagada' THEN
        UPDATE Productos p
        SET stock = stock - d.cantidad
        FROM DetalleOrden d
        WHERE d.id_orden = NEW.id_orden AND p.id_producto = d.id_producto;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_descontar_stock
    AFTER UPDATE ON Ordenes
    FOR EACH ROW EXECUTE FUNCTION fn_descontar_stock();

--Incrementador de usos_actuales del cupon cuando creas la orden
CREATE OR REPLACE FUNCTION fn_usar_cupon() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id_cupon IS NOT NULL THEN
        UPDATE Cupones SET usos_actuales = usos_actuales + 1
        WHERE id_cupon = NEW.id_cupon AND usos_actuales < usos_maximos;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usar_cupon
    AFTER INSERT ON Ordenes
    FOR EACH ROW EXECUTE FUNCTION fn_usar_cupon();