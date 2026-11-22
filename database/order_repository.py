"""Persistencia transaccional de pedidos, líneas, pagos y entregas."""

import sqlite3

from database.connection import get_connection


ORDER_STATUSES = ("pending", "accepted", "preparing", "ready", "completed", "cancelled")
DELIVERY_STATUSES = ("pending", "assigned", "picked_up", "delivered")


def create_order_tables():
    """Crea las tablas necesarias para registrar pedidos sin borrar datos existentes."""
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                employee_id INTEGER,
                table_id INTEGER,
                order_type TEXT NOT NULL CHECK (order_type IN ('delivery', 'dine_in')),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'preparing', 'ready', 'completed', 'cancelled')),
                subtotal INTEGER NOT NULL CHECK (subtotal >= 0),
                total INTEGER NOT NULL CHECK (total >= 0),
                delivery_address TEXT,
                customer_notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT,
                CHECK (
                    (order_type = 'delivery' AND delivery_address IS NOT NULL AND length(trim(delivery_address)) > 0)
                    OR
                    (order_type = 'dine_in' AND delivery_address IS NULL)
                )
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                subtotal INTEGER NOT NULL CHECK (subtotal >= 0),
                notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                amount INTEGER NOT NULL CHECK (amount >= 0),
                payment_method TEXT NOT NULL CHECK (payment_method = 'cash'),
                payment_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (payment_status IN ('pending', 'paid', 'refunded')),
                received_by INTEGER,
                paid_at TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS order_status_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                previous_status TEXT,
                new_status TEXT NOT NULL
                    CHECK (new_status IN ('pending', 'accepted', 'preparing', 'ready', 'completed', 'cancelled')),
                changed_by_employee_id INTEGER,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS deliveries (
                delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                courier_id INTEGER,
                assigned_by INTEGER,
                delivery_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (delivery_status IN ('pending', 'assigned', 'picked_up', 'delivered')),
                assigned_at TEXT,
                picked_up_at TEXT,
                delivered_at TEXT,
                delivery_notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT
            )
            """
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_created "
            "ON orders(customer_id, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)"
        )
        connection.commit()
    finally:
        connection.close()


def create_order_record(customer_id, order_type, cart_items, delivery_address=None, customer_notes=None):
    """Crea pedido y registros asociados dentro de una única transacción.

    Los nombres y precios se vuelven a consultar en el catálogo y se guardan como
    fotografía histórica en order_items. No descuenta inventario: eso ocurre al
    aceptar el pedido, según las reglas del proyecto.
    """
    if order_type not in ("delivery", "dine_in"):
        raise ValueError("El tipo de pedido no es válido.")

    if not isinstance(cart_items, list) or not cart_items:
        raise ValueError("No puedes crear un pedido con el carrito vacío.")

    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError) as error:
        raise ValueError("El cliente no es válido.") from error

    if customer_id < 1:
        raise ValueError("El cliente no es válido.")

    if order_type == "delivery":
        delivery_address = (delivery_address or "").strip()
        if not delivery_address:
            raise ValueError("Debes ingresar la dirección de entrega.")
        if len(delivery_address) > 300:
            raise ValueError("La dirección no puede superar los 300 caracteres.")
    else:
        delivery_address = None

    customer_notes = (customer_notes or "").strip()
    if len(customer_notes) > 500:
        raise ValueError("Las indicaciones no pueden superar los 500 caracteres.")

    normalized_items = []
    seen_product_ids = set()
    for item in cart_items:
        if not isinstance(item, dict):
            raise ValueError("Hay un producto inválido en el carrito.")
        try:
            product_id = int(item["product_id"])
            quantity = item["quantity"]
            cart_price = int(item["price"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Hay un producto con información incompleta.") from error

        if product_id < 1 or isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Las cantidades de los productos deben ser enteros mayores que cero.")
        if product_id in seen_product_ids:
            raise ValueError("El carrito contiene un producto duplicado.")
        if cart_price < 0:
            raise ValueError("El precio de un producto no es válido.")

        seen_product_ids.add(product_id)
        normalized_items.append((product_id, quantity, cart_price))

    connection = get_connection()
    try:
        # Inicia una transacción de escritura para evitar cambios de precio/stock
        # entre la validación del catálogo y la creación del pedido.
        connection.execute("BEGIN IMMEDIATE")

        customer = connection.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ? AND is_active = 1",
            (customer_id,),
        ).fetchone()
        if customer is None:
            raise ValueError("No se encontró una cuenta de cliente activa.")

        validated_items = []
        subtotal = 0
        for product_id, quantity, cart_price in normalized_items:
            product = connection.execute(
                """
                SELECT products.product_id, products.name, products.price
                FROM products
                INNER JOIN categories ON categories.category_id = products.category_id
                WHERE products.product_id = ?
                  AND products.is_available = 1
                  AND categories.is_active = 1
                """,
                (product_id,),
            ).fetchone()

            if product is None:
                raise ValueError("Uno de los productos ya no está disponible. Actualiza el catálogo.")
            if product["price"] != cart_price:
                raise ValueError(
                    f'El precio de "{product["name"]}" cambió. Regresa al catálogo y actualiza tu carrito.'
                )

            line_subtotal = product["price"] * quantity
            subtotal += line_subtotal
            validated_items.append(
                (product["product_id"], product["name"], quantity, product["price"], line_subtotal)
            )

        cursor = connection.execute(
            """
            INSERT INTO orders (
                customer_id, order_type, status, subtotal, total,
                delivery_address, customer_notes
            )
            VALUES (?, ?, 'pending', ?, ?, ?, ?)
            """,
            (customer_id, order_type, subtotal, subtotal, delivery_address, customer_notes or None),
        )
        order_id = cursor.lastrowid

        for product_id, product_name, quantity, unit_price, line_subtotal in validated_items:
            connection.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_name, quantity, unit_price, subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order_id, product_id, product_name, quantity, unit_price, line_subtotal),
            )

        connection.execute(
            """
            INSERT INTO payments (order_id, amount, payment_method, payment_status)
            VALUES (?, ?, 'cash', 'pending')
            """,
            (order_id, subtotal),
        )

        connection.execute(
            """
            INSERT INTO order_status_history (order_id, previous_status, new_status, notes)
            VALUES (?, NULL, 'pending', 'Pedido creado por el cliente.')
            """,
            (order_id,),
        )

        if order_type == "delivery":
            connection.execute(
                """
                INSERT INTO deliveries (order_id, delivery_status)
                VALUES (?, 'pending')
                """,
                (order_id,),
            )

        connection.commit()
        return order_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_customer_orders(customer_id):
    """Devuelve el historial resumido de pedidos de un cliente."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                orders.order_id,
                orders.order_type,
                orders.status,
                orders.total,
                orders.created_at,
                payments.payment_status,
                COALESCE(deliveries.delivery_status, '') AS delivery_status
            FROM orders
            INNER JOIN payments ON payments.order_id = orders.order_id
            LEFT JOIN deliveries ON deliveries.order_id = orders.order_id
            WHERE orders.customer_id = ?
            ORDER BY orders.created_at DESC, orders.order_id DESC
            """,
            (int(customer_id),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_customer_order_details(customer_id, order_id):
    """Devuelve el pedido y sus productos, verificando que pertenezca al cliente."""
    connection = get_connection()
    try:
        order = connection.execute(
            """
            SELECT
                orders.order_id,
                orders.customer_id,
                orders.order_type,
                orders.status,
                orders.subtotal,
                orders.total,
                orders.delivery_address,
                orders.customer_notes,
                orders.created_at,
                payments.payment_method,
                payments.payment_status,
                COALESCE(deliveries.delivery_status, '') AS delivery_status
            FROM orders
            INNER JOIN payments ON payments.order_id = orders.order_id
            LEFT JOIN deliveries ON deliveries.order_id = orders.order_id
            WHERE orders.order_id = ? AND orders.customer_id = ?
            """,
            (int(order_id), int(customer_id)),
        ).fetchone()

        if order is None:
            return None

        items = connection.execute(
            """
            SELECT product_id, product_name, quantity, unit_price, subtotal
            FROM order_items
            WHERE order_id = ?
            ORDER BY order_item_id
            """,
            (int(order_id),),
        ).fetchall()

        result = dict(order)
        result["items"] = [dict(item) for item in items]
        return result
    finally:
        connection.close()
