"""Persistencia de mesas, inventario y operaciones de empleados."""

import sqlite3

from database.connection import get_connection


ORDER_STATUS_LABELS = {
    "pending": "Pendiente",
    "accepted": "Aceptado",
    "preparing": "En preparación",
    "ready": "Listo",
    "completed": "Completado",
    "cancelled": "Cancelado",
}


def create_operations_tables():
    connection = get_connection()
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS restaurant_tables (
                table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number TEXT NOT NULL UNIQUE,
                capacity INTEGER NOT NULL CHECK(capacity > 0),
                status TEXT NOT NULL DEFAULT 'available'
                    CHECK(status IN ('available', 'occupied', 'maintenance')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS inventory (
                product_id INTEGER PRIMARY KEY,
                stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
                minimum_stock INTEGER NOT NULL DEFAULT 0 CHECK(minimum_stock >= 0),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE RESTRICT
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS inventory_movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL CHECK(movement_type IN ('adjustment', 'out', 'in')),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                previous_stock INTEGER NOT NULL CHECK(previous_stock >= 0),
                new_stock INTEGER NOT NULL CHECK(new_stock >= 0),
                reason TEXT NOT NULL,
                employee_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE RESTRICT
            )"""
        )
        connection.execute(
            """INSERT OR IGNORE INTO inventory (product_id, stock_quantity, minimum_stock)
               SELECT product_id, 0, 0 FROM products"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_operations ON orders(status, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_deliveries_courier ON deliveries(courier_id, delivery_status)"
        )
        connection.commit()
    finally:
        connection.close()


def add_restaurant_table(table_number, capacity, admin_id):
    table_number = (str(table_number or "")).strip()
    try:
        capacity = int(capacity)
    except (TypeError, ValueError) as error:
        raise ValueError("La capacidad debe ser un número entero.") from error
    if not table_number:
        raise ValueError("Debes indicar el número o nombre de la mesa.")
    if capacity < 1 or capacity > 30:
        raise ValueError("La capacidad debe estar entre 1 y 30 personas.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, admin_id, "admin")
        cursor = connection.execute(
            "INSERT INTO restaurant_tables (table_number, capacity) VALUES (?, ?)",
            (table_number, capacity),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ya existe una mesa con ese número o nombre.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_restaurant_tables(available_only=False):
    connection = get_connection()
    try:
        query = "SELECT * FROM restaurant_tables WHERE is_active = 1"
        if available_only:
            query += " AND status = 'available'"
        query += " ORDER BY table_number"
        return [dict(row) for row in connection.execute(query).fetchall()]
    finally:
        connection.close()


def list_inventory_products():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT p.product_id, p.name, p.price, c.name AS category_name,
                      i.stock_quantity, i.minimum_stock
               FROM products p
               JOIN categories c ON c.category_id = p.category_id
               LEFT JOIN inventory i ON i.product_id = p.product_id
               ORDER BY c.name, p.name"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def set_product_stock(product_id, new_quantity, minimum_stock, admin_id):
    try:
        product_id = int(product_id)
        new_quantity = int(new_quantity)
        minimum_stock = int(minimum_stock)
        admin_id = int(admin_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Las cantidades deben ser números enteros.") from error
    if new_quantity < 0 or minimum_stock < 0:
        raise ValueError("Las existencias y el mínimo no pueden ser negativos.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, admin_id, "admin")
        product = connection.execute(
            "SELECT product_id FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        if product is None:
            raise ValueError("No se encontró el producto.")
        current = connection.execute(
            "SELECT stock_quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        previous = current["stock_quantity"] if current else 0
        connection.execute(
            """INSERT INTO inventory (product_id, stock_quantity, minimum_stock, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(product_id) DO UPDATE SET
                   stock_quantity = excluded.stock_quantity,
                   minimum_stock = excluded.minimum_stock,
                   updated_at = CURRENT_TIMESTAMP""",
            (product_id, new_quantity, minimum_stock),
        )
        delta = abs(new_quantity - previous)
        if delta:
            connection.execute(
                """INSERT INTO inventory_movements
                   (product_id, movement_type, quantity, previous_stock, new_stock, reason, employee_id)
                   VALUES (?, 'adjustment', ?, ?, ?, 'Ajuste manual de inventario', ?)""",
                (product_id, delta, previous, new_quantity, admin_id),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_pending_orders():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT o.order_id, o.order_type, o.status, o.total, o.created_at,
                      o.delivery_address, o.customer_notes, c.full_name AS customer_name,
                      c.phone AS customer_phone
               FROM orders o JOIN customers c ON c.customer_id = o.customer_id
               WHERE o.status = 'pending'
               ORDER BY o.created_at, o.order_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_admin_active_orders():
    """Pedidos aceptados/en preparación/listos que requieren seguimiento administrativo."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT o.order_id, o.order_type, o.status, o.total, o.created_at,
                      o.delivery_address, o.table_id, c.full_name AS customer_name,
                      rt.table_number, COALESCE(d.delivery_status, '') AS delivery_status,
                      e.full_name AS courier_name
               FROM orders o
               JOIN customers c ON c.customer_id = o.customer_id
               LEFT JOIN restaurant_tables rt ON rt.table_id = o.table_id
               LEFT JOIN deliveries d ON d.order_id = o.order_id
               LEFT JOIN employees e ON e.employee_id = d.courier_id
               WHERE o.status IN ('accepted', 'preparing', 'ready')
               ORDER BY o.created_at, o.order_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_order_items_for_operations(order_id):
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT product_id, product_name, quantity, unit_price, subtotal
               FROM order_items WHERE order_id = ? ORDER BY order_item_id""",
            (int(order_id),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _verify_employee(connection, employee_id, role):
    employee = connection.execute(
        "SELECT employee_id FROM employees WHERE employee_id = ? AND role = ? AND is_active = 1",
        (int(employee_id), role),
    ).fetchone()
    if employee is None:
        raise ValueError("El empleado no tiene permisos para realizar esta operación.")


def accept_order(order_id, admin_id, table_id=None, courier_id=None):
    """Acepta un pedido, asigna mesa/repartidor y descuenta inventario atómicamente."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, admin_id, "admin")
        order = connection.execute(
            "SELECT order_id, order_type, status, table_id FROM orders WHERE order_id = ?",
            (int(order_id),),
        ).fetchone()
        if order is None or order["status"] != "pending":
            raise ValueError("El pedido ya no está pendiente o no existe.")

        items = connection.execute(
            "SELECT product_id, product_name, quantity FROM order_items WHERE order_id = ?",
            (int(order_id),),
        ).fetchall()
        if not items:
            raise ValueError("El pedido no contiene productos.")

        if order["order_type"] == "dine_in":
            if table_id is None:
                raise ValueError("Debes asignar una mesa disponible.")
            table = connection.execute(
                "SELECT table_id FROM restaurant_tables WHERE table_id = ? AND status = 'available' AND is_active = 1",
                (int(table_id),),
            ).fetchone()
            if table is None:
                raise ValueError("La mesa seleccionada ya no está disponible.")
        else:
            if courier_id is None:
                raise ValueError("Debes asignar un repartidor.")
            _verify_employee(connection, courier_id, "courier")

        # Validar todas las existencias antes de descontar cualquier producto.
        for item in items:
            stock = connection.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (item["product_id"],),
            ).fetchone()
            available = stock["stock_quantity"] if stock else 0
            if available < item["quantity"]:
                raise ValueError(
                    f'Existencias insuficientes para "{item["product_name"]}". Disponibles: {available}.'
                )

        # Descontar inventario y registrar cada movimiento dentro de la transacción.
        for item in items:
            stock = connection.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (item["product_id"],),
            ).fetchone()
            previous = stock["stock_quantity"]
            new_stock = previous - item["quantity"]
            connection.execute(
                "UPDATE inventory SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
                (new_stock, item["product_id"]),
            )
            connection.execute(
                """INSERT INTO inventory_movements
                   (product_id, movement_type, quantity, previous_stock, new_stock, reason, employee_id)
                   VALUES (?, 'out', ?, ?, ?, ?, ?)""",
                (item["product_id"], item["quantity"], previous, new_stock,
                 f"Descuento por aceptación del pedido #{order_id}", int(admin_id)),
            )

        if order["order_type"] == "dine_in":
            connection.execute(
                "UPDATE restaurant_tables SET status = 'occupied' WHERE table_id = ?",
                (int(table_id),),
            )
        else:
            connection.execute(
                """UPDATE deliveries SET courier_id = ?, assigned_by = ?,
                   delivery_status = 'assigned', assigned_at = CURRENT_TIMESTAMP
                   WHERE order_id = ?""",
                (int(courier_id), int(admin_id), int(order_id)),
            )

        connection.execute(
            """UPDATE orders SET status = 'accepted', employee_id = ?, table_id = ?,
               updated_at = CURRENT_TIMESTAMP WHERE order_id = ?""",
            (int(admin_id), int(table_id) if table_id is not None else None, int(order_id)),
        )
        connection.execute(
            """INSERT INTO order_status_history
               (order_id, previous_status, new_status, changed_by_employee_id, notes)
               VALUES (?, 'pending', 'accepted', ?, 'Pedido aceptado por administración.')""",
            (int(order_id), int(admin_id)),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_kitchen_orders():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT o.order_id, o.order_type, o.status, o.total, o.created_at,
                      o.table_id, c.full_name AS customer_name,
                      rt.table_number
               FROM orders o JOIN customers c ON c.customer_id = o.customer_id
               LEFT JOIN restaurant_tables rt ON rt.table_id = o.table_id
               WHERE o.status IN ('accepted', 'preparing')
               ORDER BY o.created_at, o.order_id"""
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["items"] = [dict(line) for line in connection.execute(
                "SELECT product_name, quantity FROM order_items WHERE order_id = ? ORDER BY order_item_id",
                (item["order_id"],),
            ).fetchall()]
            result.append(item)
        return result
    finally:
        connection.close()


def update_kitchen_order_status(order_id, kitchen_employee_id, new_status):
    if new_status not in ("preparing", "ready"):
        raise ValueError("Estado de preparación no válido.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, kitchen_employee_id, "kitchen")
        order = connection.execute(
            "SELECT status FROM orders WHERE order_id = ?", (int(order_id),)
        ).fetchone()
        allowed = {"accepted": "preparing", "preparing": "ready"}
        if order is None or allowed.get(order["status"]) != new_status:
            raise ValueError("La transición de estado no está permitida.")
        previous = order["status"]
        connection.execute(
            "UPDATE orders SET status = ?, employee_id = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (new_status, int(kitchen_employee_id), int(order_id)),
        )
        connection.execute(
            """INSERT INTO order_status_history
               (order_id, previous_status, new_status, changed_by_employee_id, notes)
               VALUES (?, ?, ?, ?, 'Actualización realizada por cocina.')""",
            (int(order_id), previous, new_status, int(kitchen_employee_id)),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_courier_deliveries(courier_id):
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT d.delivery_id, d.order_id, d.delivery_status,
                      o.total, o.delivery_address, o.customer_notes, o.status AS order_status,
                      c.full_name AS customer_name, c.phone AS customer_phone
               FROM deliveries d
               JOIN orders o ON o.order_id = d.order_id
               JOIN customers c ON c.customer_id = o.customer_id
               WHERE d.courier_id = ? AND d.delivery_status IN ('assigned', 'picked_up')
               ORDER BY d.assigned_at, d.order_id""",
            (int(courier_id),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def update_courier_delivery_status(order_id, courier_id, new_status):
    if new_status not in ("picked_up", "delivered"):
        raise ValueError("Estado de entrega no válido.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, courier_id, "courier")
        delivery = connection.execute(
            """SELECT delivery_status FROM deliveries
               WHERE order_id = ? AND courier_id = ?""",
            (int(order_id), int(courier_id)),
        ).fetchone()
        transitions = {"assigned": "picked_up", "picked_up": "delivered"}
        if delivery is None or transitions.get(delivery["delivery_status"]) != new_status:
            raise ValueError("La transición de entrega no está permitida o no te pertenece.")
        previous_delivery = delivery["delivery_status"]
        order = connection.execute(
            "SELECT status FROM orders WHERE order_id = ?", (int(order_id),)
        ).fetchone()
        if new_status == "picked_up" and order["status"] != "ready":
            raise ValueError("Cocina debe marcar el pedido como listo antes de recogerlo.")
        if new_status == "picked_up":
            connection.execute(
                """UPDATE deliveries SET delivery_status = 'picked_up',
                   picked_up_at = CURRENT_TIMESTAMP WHERE order_id = ?""",
                (int(order_id),),
            )
        else:
            connection.execute(
                """UPDATE deliveries SET delivery_status = 'delivered',
                   delivered_at = CURRENT_TIMESTAMP WHERE order_id = ?""",
                (int(order_id),),
            )
            if order["status"] != "ready":
                raise ValueError("El pedido debe estar marcado como listo antes de entregarlo.")
            connection.execute(
                "UPDATE orders SET status = 'completed', employee_id = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (int(courier_id), int(order_id)),
            )
            connection.execute(
                """INSERT INTO order_status_history
                   (order_id, previous_status, new_status, changed_by_employee_id, notes)
                   VALUES (?, 'ready', 'completed', ?, 'Entrega confirmada por el repartidor.')""",
                (int(order_id), int(courier_id)),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def complete_dine_in_order(order_id, admin_id):
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, admin_id, "admin")
        order = connection.execute(
            "SELECT status, order_type, table_id FROM orders WHERE order_id = ?",
            (int(order_id),),
        ).fetchone()
        if order is None or order["order_type"] != "dine_in" or order["status"] != "ready":
            raise ValueError("Solo se pueden completar pedidos de mesa que estén listos.")
        connection.execute(
            "UPDATE orders SET status = 'completed', employee_id = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (int(admin_id), int(order_id)),
        )
        connection.execute(
            "UPDATE restaurant_tables SET status = 'available' WHERE table_id = ?",
            (order["table_id"],),
        )
        connection.execute(
            """INSERT INTO order_status_history
               (order_id, previous_status, new_status, changed_by_employee_id, notes)
               VALUES (?, 'ready', 'completed', ?, 'Servicio de mesa completado por administración.')""",
            (int(order_id), int(admin_id)),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def cancel_order(order_id, admin_id, reason):
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Debes indicar el motivo de la cancelación.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_employee(connection, admin_id, "admin")
        order = connection.execute(
            "SELECT status, table_id FROM orders WHERE order_id = ?", (int(order_id),)
        ).fetchone()
        if order is None or order["status"] not in ("pending", "accepted"):
            raise ValueError("Solo se pueden cancelar pedidos pendientes o aceptados que aún no estén en preparación.")
        previous = order["status"]
        if previous == "accepted":
            items = connection.execute(
                "SELECT product_id, quantity, product_name FROM order_items WHERE order_id = ?",
                (int(order_id),),
            ).fetchall()
            for item in items:
                current = connection.execute(
                    "SELECT stock_quantity FROM inventory WHERE product_id = ?", (item["product_id"],)
                ).fetchone()
                old_stock = current["stock_quantity"] if current else 0
                new_stock = old_stock + item["quantity"]
                connection.execute(
                    "UPDATE inventory SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
                    (new_stock, item["product_id"]),
                )
                connection.execute(
                    """INSERT INTO inventory_movements
                       (product_id, movement_type, quantity, previous_stock, new_stock, reason, employee_id)
                       VALUES (?, 'in', ?, ?, ?, ?, ?)""",
                    (item["product_id"], item["quantity"], old_stock, new_stock,
                     f"Reversión por cancelación del pedido #{order_id}: {reason}", int(admin_id)),
                )
            if order["table_id"] is not None:
                connection.execute(
                    "UPDATE restaurant_tables SET status = 'available' WHERE table_id = ?",
                    (order["table_id"],),
                )
            connection.execute(
                """UPDATE deliveries SET courier_id = NULL, assigned_by = NULL,
                   delivery_status = 'pending', assigned_at = NULL
                   WHERE order_id = ?""",
                (int(order_id),),
            )
        connection.execute(
            "UPDATE orders SET status = 'cancelled', employee_id = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (int(admin_id), int(order_id)),
        )
        connection.execute(
            """INSERT INTO order_status_history
               (order_id, previous_status, new_status, changed_by_employee_id, notes)
               VALUES (?, ?, 'cancelled', ?, ?)""",
            (int(order_id), previous, int(admin_id), reason),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
