"""Registro y autenticación de empleados de Restaurant Manager V2."""

import hashlib
import hmac
import os
import sqlite3

from database.connection import get_connection


EMPLOYEE_ROLES = ("admin", "kitchen", "courier")


def _hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}:{key.hex()}"


def create_employee_table():
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'kitchen', 'courier')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def has_admin_account():
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT 1 FROM employees WHERE role = 'admin' AND is_active = 1 LIMIT 1"
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def create_initial_admin(full_name, email, phone, password):
    """Crea la primera cuenta administradora; no permite crear otra desde este flujo."""
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    if not full_name or not email or not phone or not password:
        raise ValueError("Completa todos los campos del administrador.")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT 1 FROM employees WHERE role = 'admin' AND is_active = 1 LIMIT 1"
        ).fetchone()
        if existing:
            raise ValueError("Ya existe una cuenta administradora.")
        cursor = connection.execute(
            """INSERT INTO employees (full_name, email, phone, password_hash, role)
               VALUES (?, ?, ?, ?, 'admin')""",
            (full_name, email, phone, _hash_password(password)),
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_staff_member(full_name, email, phone, password, role, admin_id):
    """Crea personal operativo. La interfaz debe restringir esta acción al administrador."""
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    if role not in ("kitchen", "courier"):
        raise ValueError("Solo se pueden crear cuentas de cocina o repartidor.")
    if not full_name or not email or not phone or not password:
        raise ValueError("Completa todos los campos del empleado.")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        admin = connection.execute(
            "SELECT 1 FROM employees WHERE employee_id = ? AND role = 'admin' AND is_active = 1",
            (int(admin_id),),
        ).fetchone()
        if admin is None:
            raise ValueError("Solo un administrador activo puede crear cuentas del equipo.")
        cursor = connection.execute(
            """INSERT INTO employees (full_name, email, phone, password_hash, role)
               VALUES (?, ?, ?, ?, ?)""",
            (full_name, email, phone, _hash_password(password), role),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ese correo ya está registrado en el equipo.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def authenticate_employee(email, password):
    connection = get_connection()
    try:
        row = connection.execute(
            """SELECT employee_id, full_name, email, phone, password_hash, role
               FROM employees WHERE email = ? AND is_active = 1""",
            ((email or "").strip().lower(),),
        ).fetchone()
        if row is None:
            return False, "Correo o contraseña incorrectos."
        try:
            salt_hex, key_hex = row["password_hash"].split(":", 1)
            entered_key = hashlib.pbkdf2_hmac(
                "sha256", (password or "").encode("utf-8"), bytes.fromhex(salt_hex), 200_000
            )
            if not hmac.compare_digest(entered_key, bytes.fromhex(key_hex)):
                return False, "Correo o contraseña incorrectos."
        except (ValueError, TypeError):
            return False, "No se pudieron verificar las credenciales."

        return True, {
            "employee_id": row["employee_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "phone": row["phone"],
            "role": row["role"],
        }
    finally:
        connection.close()


def list_active_couriers():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT employee_id, full_name, email FROM employees
               WHERE role = 'courier' AND is_active = 1 ORDER BY full_name"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def list_active_employees():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT employee_id, full_name, email, phone, role, is_active, created_at
               FROM employees ORDER BY role, full_name"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def set_employee_active_status(employee_id, is_active, admin_id):
    """Activa o desactiva una cuenta sin eliminar su historial."""
    if is_active not in (True, False, 0, 1):
        raise ValueError("El estado de la cuenta no es válido.")

    employee_id = int(employee_id)
    admin_id = int(admin_id)
    active_value = 1 if is_active else 0

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        admin = connection.execute(
            "SELECT employee_id FROM employees WHERE employee_id = ? AND role = 'admin' AND is_active = 1",
            (admin_id,),
        ).fetchone()
        if admin is None:
            raise ValueError("Solo un administrador activo puede modificar cuentas.")
        if employee_id == admin_id:
            raise ValueError("No puedes desactivar tu propia cuenta.")

        employee = connection.execute(
            "SELECT employee_id, role, is_active FROM employees WHERE employee_id = ?",
            (employee_id,),
        ).fetchone()
        if employee is None:
            raise ValueError("No se encontró el empleado.")
        if employee["is_active"] == active_value:
            raise ValueError("La cuenta ya tiene ese estado.")

        if not active_value:
            open_shift = connection.execute(
                "SELECT shift_id FROM employee_shifts WHERE employee_id = ? AND status = 'open'",
                (employee_id,),
            ).fetchone()
            if open_shift:
                raise ValueError("El empleado debe finalizar su turno antes de desactivar su cuenta.")
            if employee["role"] == "courier":
                active_delivery = connection.execute(
                    """SELECT 1 FROM deliveries
                       WHERE courier_id = ? AND delivery_status IN ('assigned', 'picked_up')
                       LIMIT 1""",
                    (employee_id,),
                ).fetchone()
                if active_delivery:
                    raise ValueError("El repartidor debe completar sus entregas antes de desactivar su cuenta.")
            if employee["role"] == "admin":
                other_admin = connection.execute(
                    "SELECT 1 FROM employees WHERE role = 'admin' AND is_active = 1 AND employee_id != ? LIMIT 1",
                    (employee_id,),
                ).fetchone()
                if other_admin is None:
                    raise ValueError("No puedes desactivar al único administrador activo.")

        connection.execute(
            "UPDATE employees SET is_active = ? WHERE employee_id = ?",
            (active_value, employee_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
