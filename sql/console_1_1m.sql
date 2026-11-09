--Prueba para que se vean la cantidad de filas
SELECT COUNT(*) FROM DetalleOrden;

--Indices
CREATE INDEX idx_cupones_vencimiento ON Cupones(fecha_vencimiento);
CREATE INDEX idx_productos_categoria_stock ON Productos(id_categoria, stock);
CREATE INDEX idx_ordenes_cupon ON Ordenes(id_cupon);
CREATE INDEX idx_detalleorden_producto ON DetalleOrden(id_producto);

--Consulta
EXPLAIN ANALYZE
SELECT c.codigo, c.descuento, c.tipo_descuento, c.fecha_vencimiento,
       c.usos_actuales, c.usos_maximos,
       cat.nombre AS categoria_mas_afectada,
       COUNT(DISTINCT p.id_producto) AS productos_sin_stock
FROM Cupones c
         JOIN Ordenes o ON o.id_cupon = c.id_cupon
         JOIN DetalleOrden d ON d.id_orden = o.id_orden
         JOIN Productos p ON p.id_producto = d.id_producto
         JOIN Categorias cat ON cat.id_categoria = p.id_categoria
WHERE c.fecha_vencimiento BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
  AND p.id_categoria = (
    SELECT p2.id_categoria
    FROM Productos p2
    WHERE p2.stock = 0
    GROUP BY p2.id_categoria
    ORDER BY COUNT(*) DESC
    LIMIT 1
)
GROUP BY c.id_cupon, c.codigo, c.descuento, c.tipo_descuento,
         c.fecha_vencimiento, c.usos_actuales, c.usos_maximos, cat.nombre
HAVING c.usos_actuales < (c.usos_maximos * 0.5)
ORDER BY c.fecha_vencimiento ASC;

--Vaciar
VACUUM;

