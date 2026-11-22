"""Funciones administrativas de pagos en efectivo, turnos y reportes."""

from datetime import date
import sqlite3

from database.connection import get_connection


def create_administration_tables():
    """Crea la tabla de turnos sin alterar los datos existentes."""
    connection = get_connection()
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS employee_shifts (
                shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open', 'closed')),
                FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
                    ON DELETE RESTRICT,
                CHECK(
                    (status = 'open' AND ended_at IS NULL)
                    OR (status = 'closed' AND ended_at IS NOT NULL)
                )
            )"""
        )
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_one_open_shift
               ON employee_shifts(employee_id) WHERE status = 'open'"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_shifts_started_at
               ON employee_shifts(started_at DESC)"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_payments_status
               ON payments(payment_status, paid_at)"""
        )
        connection.commit()
    finally:
        connection.close()


def _verify_active_employee(connection, employee_id):
    employee = connection.execute(
        "SELECT employee_id FROM employees WHERE employee_id = ? AND is_active = 1",
        (int(employee_id),),
    ).fetchone()
    if employee is None:
        raise ValueError("El empleado no existe o está inactivo.")


def _verify_admin(connection, admin_id):
    admin = connection.execute(
        """SELECT employee_id FROM employees
           WHERE employee_id = ? AND role = 'admin' AND is_active = 1""",
        (int(admin_id),),
    ).fetchone()
    if admin is None:
        raise ValueError("Solo un administrador activo puede realizar esta operación.")


def get_current_employee_shift(employee_id):
    connection = get_connection()
    try:
        row = connection.execute(
            """SELECT shift_id, employee_id, started_at, status
               FROM employee_shifts
               WHERE employee_id = ? AND status = 'open'
               ORDER BY shift_id DESC LIMIT 1""",
            (int(employee_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def start_employee_shift(employee_id):
    """Abre un turno para el empleado autenticado. Solo permite uno activo."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_active_employee(connection, employee_id)
        existing = connection.execute(
            "SELECT shift_id FROM employee_shifts WHERE employee_id = ? AND status = 'open'",
            (int(employee_id),),
        ).fetchone()
        if existing:
            raise ValueError("Ya tienes un turno abierto.")
        cursor = connection.execute(
            "INSERT INTO employee_shifts (employee_id) VALUES (?)",
            (int(employee_id),),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ya tienes un turno abierto.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def end_employee_shift(employee_id):
    """Cierra el turno activo del empleado autenticado."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_active_employee(connection, employee_id)
        shift = connection.execute(
            """SELECT shift_id FROM employee_shifts
               WHERE employee_id = ? AND status = 'open'""",
            (int(employee_id),),
        ).fetchone()
        if shift is None:
            raise ValueError("No tienes un turno abierto para finalizar.")
        connection.execute(
            """UPDATE employee_shifts
               SET ended_at = CURRENT_TIMESTAMP, status = 'closed'
               WHERE shift_id = ?""",
            (shift["shift_id"],),
        )
        connection.commit()
        return shift["shift_id"]
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_open_employee_shifts():
    """Lista los turnos activos de todos los empleados para administración."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT s.shift_id, s.started_at, e.employee_id,
                      e.full_name, e.email, e.role
               FROM employee_shifts s
               JOIN employees e ON e.employee_id = s.employee_id
               WHERE s.status = 'open'
               ORDER BY s.started_at, e.full_name"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_recent_employee_shifts(limit=30):
    try:
        limit = int(limit)
    except (TypeError, ValueError) as error:
        raise ValueError("El límite debe ser un número entero.") from error
    limit = max(1, min(limit, 200))
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT s.shift_id, s.started_at, s.ended_at, s.status,
                      e.full_name, e.email, e.role
               FROM employee_shifts s
               JOIN employees e ON e.employee_id = s.employee_id
               ORDER BY s.shift_id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_cash_payment_queue():
    """Pagos en efectivo pendientes, indicando si el pedido ya se completó."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT p.payment_id, p.order_id, p.amount, p.payment_status,
                      o.status AS order_status, o.order_type, o.created_at,
                      c.full_name AS customer_name
               FROM payments p
               JOIN orders o ON o.order_id = p.order_id
               JOIN customers c ON c.customer_id = o.customer_id
               WHERE p.payment_status = 'pending'
                 AND o.status != 'cancelled'
               ORDER BY o.created_at, o.order_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def record_cash_payment(order_id, admin_id):
    """Registra efectivo recibido. Solo para pedidos completados y una sola vez."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_admin(connection, admin_id)
        row = connection.execute(
            """SELECT o.status AS order_status, p.payment_status, p.amount
               FROM orders o
               JOIN payments p ON p.order_id = o.order_id
               WHERE o.order_id = ?""",
            (int(order_id),),
        ).fetchone()
        if row is None:
            raise ValueError("No se encontró el pedido o su registro de pago.")
        if row["order_status"] == "cancelled":
            raise ValueError("No se puede registrar el pago de un pedido cancelado.")
        if row["order_status"] != "completed":
            raise ValueError("El pedido debe estar completado antes de registrar el efectivo recibido.")
        if row["payment_status"] != "pending":
            raise ValueError("Este pago ya fue registrado o no está pendiente.")

        connection.execute(
            """UPDATE payments
               SET payment_status = 'paid', received_by = ?, paid_at = CURRENT_TIMESTAMP
               WHERE order_id = ? AND payment_status = 'pending'""",
            (int(admin_id), int(order_id)),
        )
        connection.commit()
        return int(row["amount"])
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_recent_cash_payments(limit=50):
    try:
        limit = int(limit)
    except (TypeError, ValueError) as error:
        raise ValueError("El límite debe ser un número entero.") from error
    limit = max(1, min(limit, 200))
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT p.payment_id, p.order_id, p.amount, p.payment_status,
                      p.paid_at, c.full_name AS customer_name,
                      e.full_name AS received_by_name
               FROM payments p
               JOIN orders o ON o.order_id = p.order_id
               JOIN customers c ON c.customer_id = o.customer_id
               LEFT JOIN employees e ON e.employee_id = p.received_by
               WHERE p.payment_status = 'paid'
               ORDER BY p.paid_at DESC, p.payment_id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _validate_date_range(start_date, end_date):
    try:
        start = date.fromisoformat(str(start_date))
        end = date.fromisoformat(str(end_date))
    except (TypeError, ValueError) as error:
        raise ValueError("Las fechas deben tener el formato AAAA-MM-DD.") from error
    if start > end:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    return start.isoformat(), end.isoformat()


def get_admin_report(start_date, end_date):
    """Resumen administrativo para el periodo indicado (fechas inclusivas)."""
    start_date, end_date = _validate_date_range(start_date, end_date)
    connection = get_connection()
    try:
        order_summary = connection.execute(
            """SELECT
                   COUNT(*) AS total_orders,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_orders,
                   SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
                   SUM(CASE WHEN order_type = 'delivery' THEN 1 ELSE 0 END) AS delivery_orders,
                   SUM(CASE WHEN order_type = 'dine_in' THEN 1 ELSE 0 END) AS dine_in_orders
               FROM orders
               WHERE date(created_at) BETWEEN ? AND ?""",
            (start_date, end_date),
        ).fetchone()

        payment_summary = connection.execute(
            """SELECT
                   COALESCE(SUM(CASE WHEN p.payment_status = 'paid'
                       THEN p.amount ELSE 0 END), 0) AS cash_collected,
                   COALESCE(SUM(CASE WHEN p.payment_status = 'pending'
                       AND o.status != 'cancelled' THEN p.amount ELSE 0 END), 0) AS cash_pending,
                   SUM(CASE WHEN p.payment_status = 'paid' THEN 1 ELSE 0 END) AS paid_count
               FROM payments p
               JOIN orders o ON o.order_id = p.order_id
               WHERE date(COALESCE(p.paid_at, o.created_at)) BETWEEN ? AND ?""",
            (start_date, end_date),
        ).fetchone()

        top_products = connection.execute(
            """SELECT oi.product_name, SUM(oi.quantity) AS units_sold,
                      SUM(oi.subtotal) AS requested_amount
               FROM order_items oi
               JOIN orders o ON o.order_id = oi.order_id
               WHERE date(o.created_at) BETWEEN ? AND ?
                 AND o.status != 'cancelled'
               GROUP BY oi.product_id, oi.product_name
               ORDER BY units_sold DESC, oi.product_name
               LIMIT 5""",
            (start_date, end_date),
        ).fetchall()

        low_stock = connection.execute(
            """SELECT p.product_id, p.name, i.stock_quantity, i.minimum_stock
               FROM inventory i
               JOIN products p ON p.product_id = i.product_id
               WHERE p.is_available = 1
                 AND i.stock_quantity <= i.minimum_stock
               ORDER BY i.stock_quantity, p.name"""
        ).fetchall()

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_orders": int(order_summary["total_orders"] or 0),
            "completed_orders": int(order_summary["completed_orders"] or 0),
            "cancelled_orders": int(order_summary["cancelled_orders"] or 0),
            "delivery_orders": int(order_summary["delivery_orders"] or 0),
            "dine_in_orders": int(order_summary["dine_in_orders"] or 0),
            "cash_collected": int(payment_summary["cash_collected"] or 0),
            "cash_pending": int(payment_summary["cash_pending"] or 0),
            "paid_count": int(payment_summary["paid_count"] or 0),
            "top_products": [dict(row) for row in top_products],
            "low_stock": [dict(row) for row in low_stock],
        }
    finally:
        connection.close()
