"""
generar_datos.py
Genera datos sinteticos para las 10 tablas del proyecto Falabella Peru (BD I).
Inserta directamente en PostgreSQL respetando el orden de dependencias:
Categorias -> Vendedores -> Clientes -> Cupones -> Productos -> Ordenes ->
DetalleOrden -> Pagos -> Envios -> Resenas

USO:
    python3 generar_datos.py --escenario 1k
    python3 generar_datos.py --escenario 10k
    python3 generar_datos.py --escenario 100k
    python3 generar_datos.py --escenario 1m

Antes de correr, crea la base correspondiente y aplica schema.sql + triggers.sql:
    createdb falabella_1k
    psql -d falabella_1k -f schema.sql
    psql -d falabella_1k -f triggers.sql
    python3 generar_datos.py --escenario 1k --host localhost --user postgres --password TU_PASSWORD
"""

import argparse
import random
from datetime import timedelta, datetime

import psycopg2
import psycopg2.extras
from faker import Faker

fake = Faker('es')
Faker.seed(42)
random.seed(42)

APELLIDOS_PE = ["Quispe", "Flores", "Rodriguez", "Sanchez", "Garcia", "Chavez", "Diaz", "Torres", "Lopez", "Gonzales",
                "Mendoza", "Mamani", "Ramos"]
DOMINIOS_PE = ["gmail.com", "yahoo.com", "outlook.com", "edu.pe", "hotmail.com", "falabella.com.pe"]

ESCENARIOS = {
    "1k": {
        "clientes": 200, "vendedores": 30, "categorias": 8, "cupones": 50,
        "productos": 300, "ordenes": 1000,
    },
    "10k": {
        "clientes": 2000, "vendedores": 100, "categorias": 8, "cupones": 200,
        "productos": 3000, "ordenes": 10000,
    },
    "100k": {
        "clientes": 20000, "vendedores": 500, "categorias": 8, "cupones": 1000,
        "productos": 30000, "ordenes": 100000,
    },
    "1m": {
        "clientes": 200000, "vendedores": 2000, "categorias": 8, "cupones": 5000,
        "productos": 300000, "ordenes": 1000000,
    },
}

MARCAS = ["Samsung", "LG", "Adidas", "Nike", "Oster", "Bosch", "Generico", "Falabella",
          "Sony", "HP", "Xiaomi", "Philips", "Puma", "Reebok"]
NOMBRES_CATEGORIAS = ["Tecnologia", "Moda", "Hogar", "Deportes", "Belleza",
                      "Electrodomesticos", "Jugueteria", "Mascotas"]
METODOS_PAGO = ["tarjeta", "yape", "plin", "efectivo"]
COURIERS = ["Olva Courier", "Shalom", "Cruz del Sur Cargo", "Urbano", "DHL Peru"]


def conectar(args):
    return psycopg2.connect(
        dbname=args.dbname, host=args.host, port=args.port,
        user=args.user, password=args.password
    )


def batch_insert(cur, query, rows, page_size=5000):
    psycopg2.extras.execute_values(cur, query, rows, page_size=page_size)


def gen_categorias(n):
    return [(NOMBRES_CATEGORIAS[i % len(NOMBRES_CATEGORIAS)],
             fake.sentence(nb_words=8)) for i in range(n)]


def gen_vendedores(n):
    vendedores = []
    rucs_usados = set()
    for _ in range(n):
        ruc = "20" + str(random.randint(100000000, 999999999))
        while ruc in rucs_usados:
            ruc = "20" + str(random.randint(100000000, 999999999))
        rucs_usados.add(ruc)
        vendedores.append((
            fake.company()[:150],
            fake.user_name() + "@tienda.pe",
            ruc,
            round(random.uniform(2.5, 5.0), 2)
        ))
    return vendedores


def gen_clientes(n):
    clientes = []
    dnis_usados = set()
    for i in range(n):
        dni = str(random.randint(10000000, 99999999))
        while dni in dnis_usados:
            dni = str(random.randint(10000000, 99999999))
        dnis_usados.add(dni)

        nombre = fake.first_name()
        apellido = random.choice(APELLIDOS_PE)
        email = f"{nombre.lower()}.{apellido.lower()}{i}@{random.choice(DOMINIOS_PE)}"
        telefono = "9" + str(random.randint(10000000, 99999999))
        fecha_registro = fake.date_time_between(start_date='-2y', end_date='now')
        clientes.append((nombre, apellido, email, telefono, fecha_registro, dni))
    return clientes


def gen_cupones(n):
    cupones = []
    for i in range(n):
        tipo = random.choice(['porcentaje', 'monto_fijo'])
        descuento = round(random.uniform(5, 50), 2) if tipo == 'porcentaje' else round(random.uniform(5, 100), 2)
        if random.random() < 0.3:
            fecha_venc = fake.date_between(start_date='today', end_date='+30d')
        else:
            fecha_venc = fake.date_between(start_date='-1y', end_date='+1y')
        usos_max = random.randint(50, 1000)
        usos_act = random.randint(0, int(usos_max * 0.4))
        codigo = f"CUP{i:07d}{random.choice('ABCDEFGH')}"
        cupones.append((codigo, descuento, tipo, fecha_venc, usos_max, usos_act))
    return cupones


def gen_productos(n, id_categorias, id_vendedores):
    productos = []
    for _ in range(n):
        precio = round(random.uniform(10, 5000), 2)
        stock = 0 if random.random() < 0.08 else random.randint(1, 500)
        tipo = random.choices(['fisico', 'digital'], weights=[90, 10])[0]
        productos.append((
            fake.catch_phrase()[:200], fake.text(max_nb_chars=300), precio, stock,
            random.choice(MARCAS), tipo,
            random.choice(id_categorias), random.choice(id_vendedores)
        ))
    return productos


def gen_ordenes(n, id_clientes, id_cupones):
    ordenes = []
    estados = ['pendiente', 'pagada', 'en_despacho', 'entregada', 'cancelada']
    pesos_estado = [5, 15, 15, 60, 5]
    for _ in range(n):
        fecha = fake.date_time_between(start_date='-2y', end_date='now')
        estado = random.choices(estados, weights=pesos_estado)[0]
        id_cupon = random.choice(id_cupones) if random.random() < 0.25 else None
        ordenes.append((fecha, estado, 0.0, random.choice(id_clientes), id_cupon))
    return ordenes


def gen_detalle_y_pagos_y_envios(cur, ordenes_insertadas, id_productos, precios_productos):
    detalle_rows = []
    pago_rows = []
    envio_rows = []

    for id_orden, estado in ordenes_insertadas:
        n_items = random.randint(1, 5)
        productos_orden = random.sample(id_productos, min(n_items, len(id_productos)))
        monto_total_estimado = 0.0

        for id_prod in productos_orden:
            cantidad = random.randint(1, 4)
            precio_unit = precios_productos[id_prod]
            subtotal = round(cantidad * precio_unit, 2)
            monto_total_estimado += subtotal
            detalle_rows.append((id_orden, id_prod, cantidad, precio_unit, subtotal))

        if monto_total_estimado <= 0:
            monto_total_estimado = 10.00

        if estado != 'pendiente':
            metodo = random.choice(METODOS_PAGO)
            estado_pago = 'aprobado' if estado != 'cancelada' else random.choice(['rechazado', 'aprobado'])
            fecha_pago = fake.date_time_between(start_date='-2y', end_date='now')
            cod_auth = fake.bothify(text='AUTH-########').upper()
            pago_rows.append((metodo, estado_pago, fecha_pago, round(monto_total_estimado, 2), cod_auth, id_orden))

        if estado in ('en_despacho', 'entregada'):
            estado_envio = 'entregado' if estado == 'entregada' else random.choice(['despachado', 'en_camino'])
            fecha_despacho = fake.date_time_between(start_date='-2y', end_date='now')
            fecha_entrega = fecha_despacho + timedelta(
                days=random.randint(1, 7)) if estado_envio == 'entregado' else None
            envio_rows.append((
                fake.address()[:300], estado_envio, fecha_despacho, fecha_entrega,
                random.choice(COURIERS), fake.bothify(text='TRK-########').upper(), id_orden
            ))

    return detalle_rows, pago_rows, envio_rows


def gen_resenas(detalle_keys, id_clientes_por_orden, max_resenas):
    resenas = []
    muestra = random.sample(detalle_keys, min(max_resenas, len(detalle_keys)))
    for id_orden, id_producto in muestra:
        puntuacion = random.choices([1, 2, 3, 4, 5], weights=[5, 5, 15, 35, 40])[0]
        comentario = fake.sentence(nb_words=15) if random.random() < 0.7 else None
        fecha = fake.date_between(start_date='-2y', end_date='today')
        id_cliente = id_clientes_por_orden[id_orden]
        resenas.append((puntuacion, comentario, fecha, id_cliente, id_orden, id_producto))
    return resenas


def main():
    parser = argparse.ArgumentParser(description="Generador de datos sinteticos Falabella BD I")
    parser.add_argument("--escenario", choices=ESCENARIOS.keys(), required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    parser.add_argument("--dbname", default=None)
    args = parser.parse_args()
    if args.dbname is None:
        args.dbname = f"falabella_{args.escenario}"

    cfg = ESCENARIOS[args.escenario]
    print(f"=== Generando escenario '{args.escenario}' en base '{args.dbname}' ===")

    conn = conectar(args)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Insertando Categorias...")
        cats = gen_categorias(cfg["categorias"])
        batch_insert(cur, "INSERT INTO Categorias (nombre, descripcion) VALUES %s RETURNING id_categoria", cats)
        cur.execute("SELECT id_categoria FROM Categorias")
        id_categorias = [r[0] for r in cur.fetchall()]

        print("Insertando Vendedores...")
        vends = gen_vendedores(cfg["vendedores"])
        batch_insert(cur, "INSERT INTO Vendedores (nombre_tienda, email, ruc, calificacion) VALUES %s", vends)
        cur.execute("SELECT id_vendedor FROM Vendedores")
        id_vendedores = [r[0] for r in cur.fetchall()]

        print(f"Insertando {cfg['clientes']} Clientes...")
        clientes = gen_clientes(cfg["clientes"])
        batch_insert(cur, "INSERT INTO Clientes (nombre, apellido, email, telefono, fecha_registro, dni) VALUES %s",
                     clientes)
        cur.execute("SELECT id_cliente FROM Clientes")
        id_clientes = [r[0] for r in cur.fetchall()]

        print("Insertando Cupones...")
        cupones = gen_cupones(cfg["cupones"])
        batch_insert(cur,
                     "INSERT INTO Cupones (codigo, descuento, tipo_descuento, fecha_vencimiento, usos_maximos, usos_actuales) VALUES %s",
                     cupones)
        cur.execute("SELECT id_cupon FROM Cupones")
        id_cupones = [r[0] for r in cur.fetchall()]

        print(f"Insertando {cfg['productos']} Productos...")
        productos = gen_productos(cfg["productos"], id_categorias, id_vendedores)
        batch_insert(cur,
                     "INSERT INTO Productos (nombre, descripcion, precio, stock, marca, tipo, id_categoria, id_vendedor) VALUES %s",
                     productos)
        cur.execute("SELECT id_producto, precio FROM Productos")
        rows = cur.fetchall()
        id_productos = [r[0] for r in rows]
        precios_productos = {r[0]: float(r[1]) for r in rows}

        conn.commit()
        print("Tablas base (sin dependencias de Ordenes) confirmadas.")

        print(f"Insertando {cfg['ordenes']} Ordenes...")
        cur.execute("ALTER TABLE Ordenes DISABLE TRIGGER trg_usar_cupon;")
        cur.execute("ALTER TABLE Ordenes DISABLE TRIGGER trg_descontar_stock;")
        cur.execute("ALTER TABLE DetalleOrden DISABLE TRIGGER trg_subtotal;")
        cur.execute("ALTER TABLE DetalleOrden DISABLE TRIGGER trg_total_orden;")

        ordenes = gen_ordenes(cfg["ordenes"], id_clientes, id_cupones)
        batch_insert(
            cur,
            "INSERT INTO Ordenes (fecha_orden, estado, total, id_cliente, id_cupon) VALUES %s RETURNING id_orden, estado, id_cliente",
            ordenes, page_size=5000
        )
        cur.execute("SELECT id_orden, estado, id_cliente FROM Ordenes")
        ordenes_full = cur.fetchall()
        ordenes_insertadas = [(r[0], r[1]) for r in ordenes_full]
        clientes_por_orden = {r[0]: r[2] for r in ordenes_full}
        conn.commit()
        print("Ordenes confirmadas.")

        print("Generando DetalleOrden, Pagos y Envios (esto toma mas tiempo)...")
        detalle_rows, pago_rows, envio_rows = gen_detalle_y_pagos_y_envios(
            cur, ordenes_insertadas, id_productos, precios_productos
        )

        print(f"  -> {len(detalle_rows)} filas DetalleOrden")
        batch_insert(
            cur,
            "INSERT INTO DetalleOrden (id_orden, id_producto, cantidad, precio_unitario, subtotal) VALUES %s",
            detalle_rows, page_size=5000
        )

        print(f"  -> {len(pago_rows)} filas Pagos")
        batch_insert(
            cur,
            "INSERT INTO Pagos (metodo, estado, fecha_pago, monto, codigo_autorizacion, id_orden) VALUES %s",
            pago_rows, page_size=5000
        )

        print(f"  -> {len(envio_rows)} filas Envios")
        batch_insert(
            cur,
            "INSERT INTO Envios (direccion_destino, estado_envio, fecha_despacho, fecha_entrega, courier, numero_seguimiento, id_orden) VALUES %s",
            envio_rows, page_size=5000
        )
        conn.commit()
        print("DetalleOrden, Pagos, Envios confirmados.")

        print("Recalculando subtotal, total de orden y monto de pago...")
        cur.execute("UPDATE DetalleOrden SET subtotal = cantidad * precio_unitario;")
        cur.execute("""
            UPDATE Ordenes o
            SET total = sub.suma
            FROM (SELECT id_orden, SUM(subtotal) AS suma FROM DetalleOrden GROUP BY id_orden) sub
            WHERE o.id_orden = sub.id_orden;
        """)
        cur.execute("""
            UPDATE Pagos p
            SET monto = o.total
            FROM Ordenes o
            WHERE p.id_orden = o.id_orden;
        """)
        conn.commit()

        print("Insertando Resenas...")
        cur.execute("SELECT id_orden, id_producto FROM DetalleOrden")
        detalle_keys = cur.fetchall()
        max_resenas = max(1, int(len(detalle_keys) * 0.3))
        resenas = gen_resenas(detalle_keys, clientes_por_orden, max_resenas)
        batch_insert(
            cur,
            "INSERT INTO Resenas (puntuacion, comentario, fecha, id_cliente, id_orden, id_producto) VALUES %s",
            resenas, page_size=5000
        )
        conn.commit()
        print(f"  -> {len(resenas)} resenas insertadas.")

        cur.execute("ALTER TABLE Ordenes ENABLE TRIGGER trg_usar_cupon;")
        cur.execute("ALTER TABLE Ordenes ENABLE TRIGGER trg_descontar_stock;")
        cur.execute("ALTER TABLE DetalleOrden ENABLE TRIGGER trg_subtotal;")
        cur.execute("ALTER TABLE DetalleOrden ENABLE TRIGGER trg_total_orden;")
        conn.commit()

        print(f"\n=== Escenario '{args.escenario}' generado con exito en '{args.dbname}' ===")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()