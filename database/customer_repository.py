"""Operaciones de persistencia y autenticación de clientes."""

import hashlib
import hmac
import os
import sqlite3

from database.connection import get_connection


PBKDF2_ITERATIONS = 200_000


def create_customers_table():
    """Crea la tabla de clientes si todavía no existe."""
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def _build_password_hash(password):
    """Devuelve una sal aleatoria y una clave derivada de la contraseña."""
    salt = os.urandom(16)
    password_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}:{password_key.hex()}"


def register_customer(full_name, email, phone, password):
    """Registra un cliente. Devuelve (éxito, mensaje)."""
    full_name = full_name.strip()
    email = email.strip().lower()
    phone = phone.strip()

    if not all((full_name, email, phone, password)):
        return False, "Todos los campos son obligatorios."

    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."

    password_hash = _build_password_hash(password)
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO customers (full_name, email, phone, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, email, phone, password_hash),
        )
        connection.commit()
        return True, "Cliente registrado correctamente."
    except sqlite3.IntegrityError:
        return False, "Este correo electrónico ya está registrado."
    except sqlite3.Error as error:
        return False, f"No se pudo registrar el cliente: {error}"
    finally:
        connection.close()


def authenticate_customer(email, password):
    """Verifica credenciales y devuelve los datos no sensibles del cliente."""
    email = email.strip().lower()
    connection = get_connection()

    try:
        customer = connection.execute(
            """
            SELECT customer_id, full_name, email, phone, password_hash
            FROM customers
            WHERE email = ? AND is_active = 1
            """,
            (email,),
        ).fetchone()

        if customer is None:
            return False, "Correo o contraseña incorrectos."

        try:
            salt_hex, key_hex = customer["password_hash"].split(":", 1)
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)
        except (ValueError, TypeError):
            return False, "No se pudieron verificar las credenciales."

        entered_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )

        if not hmac.compare_digest(entered_key, expected_key):
            return False, "Correo o contraseña incorrectos."

        customer_data = {
            "customer_id": customer["customer_id"],
            "full_name": customer["full_name"],
            "email": customer["email"],
            "phone": customer["phone"],
        }
        return True, customer_data
    except sqlite3.Error as error:
        return False, f"Error al iniciar sesión: {error}"
    finally:
        connection.close()
