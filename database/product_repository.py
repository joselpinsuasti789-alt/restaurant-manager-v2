"""Operaciones para inicializar y consultar el catálogo de productos."""

import sqlite3

from database.connection import get_connection


INITIAL_CATEGORIES = [
    ("Hamburguesas", "Nuestras hamburguesas"),
    ("Acompañamientos", "Complementos para tus comidas"),
    ("Bebidas", "Bebidas frías y naturales"),
]

INITIAL_PRODUCTS = [
    ("Hamburguesas", "Hamburguesa clásica", "Carne, queso, lechuga y tomate.", 18000),
    ("Hamburguesas", "Hamburguesa doble", "Doble carne y doble queso.", 25000),
    ("Acompañamientos", "Papas fritas", "Porción de papas fritas.", 8000),
    ("Bebidas", "Limonada natural", "Limonada preparada naturalmente.", 7000),
    ("Bebidas", "Gaseosa", "Bebida gaseosa personal.", 5000),
]


def create_product_tables():
    """Crea categorías y productos e inserta un catálogo de demostración."""
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL CHECK (price >= 0),
                image_path TEXT,
                is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1)),
                FOREIGN KEY (category_id) REFERENCES categories(category_id),
                UNIQUE (name, category_id)
            )
            """
        )

        for category in INITIAL_CATEGORIES:
            connection.execute(
                "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
                category,
            )

        for category_name, name, description, price in INITIAL_PRODUCTS:
            category = connection.execute(
                "SELECT category_id FROM categories WHERE name = ?",
                (category_name,),
            ).fetchone()

            if category is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO products
                        (category_id, name, description, price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (category["category_id"], name, description, price),
                )

        connection.commit()
    finally:
        connection.close()


def get_available_products():
    """Devuelve los productos disponibles con el nombre de su categoría."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                products.product_id,
                products.name,
                products.description,
                products.price,
                categories.name AS category_name
            FROM products
            INNER JOIN categories
                ON products.category_id = categories.category_id
            WHERE products.is_available = 1
              AND categories.is_active = 1
            ORDER BY categories.name, products.name
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _verify_admin(connection, admin_id):
    admin = connection.execute(
        "SELECT employee_id FROM employees WHERE employee_id = ? AND role = 'admin' AND is_active = 1",
        (int(admin_id),),
    ).fetchone()
    if admin is None:
        raise ValueError("Solo un administrador activo puede administrar el catálogo.")


def get_product_categories():
    """Devuelve las categorías activas para formularios administrativos."""
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT category_id, name, description FROM categories WHERE is_active = 1 ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_admin_product_catalog():
    """Devuelve todos los productos y sus categorías, incluidos los no disponibles."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT p.product_id, p.name, p.description, p.price,
                      p.is_available, c.category_id, c.name AS category_name
               FROM products p
               JOIN categories c ON c.category_id = p.category_id
               ORDER BY c.name, p.name"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_product_category(name, description, admin_id):
    name = (name or "").strip()
    description = (description or "").strip()
    if not name:
        raise ValueError("Debes indicar el nombre de la categoría.")
    if len(name) > 80 or len(description) > 250:
        raise ValueError("El nombre o la descripción de la categoría son demasiado largos.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_admin(connection, admin_id)
        cursor = connection.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (name, description or None),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ya existe una categoría con ese nombre.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_catalog_product(category_id, name, description, price, admin_id):
    name = (name or "").strip()
    description = (description or "").strip()
    try:
        category_id = int(category_id)
        price = int(price)
    except (TypeError, ValueError) as error:
        raise ValueError("La categoría y el precio deben ser válidos.") from error
    if not name:
        raise ValueError("Debes indicar el nombre del producto.")
    if len(name) > 120 or len(description) > 500:
        raise ValueError("El nombre o la descripción del producto son demasiado largos.")
    if price < 0:
        raise ValueError("El precio no puede ser negativo.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_admin(connection, admin_id)
        category = connection.execute(
            "SELECT category_id FROM categories WHERE category_id = ? AND is_active = 1",
            (category_id,),
        ).fetchone()
        if category is None:
            raise ValueError("La categoría seleccionada no existe o está inactiva.")
        cursor = connection.execute(
            """INSERT INTO products (category_id, name, description, price)
               VALUES (?, ?, ?, ?)""",
            (category_id, name, description or None, price),
        )
        product_id = cursor.lastrowid
        # Toda referencia nueva debe tener un registro de existencias.
        connection.execute(
            "INSERT INTO inventory (product_id, stock_quantity, minimum_stock) VALUES (?, 0, 0)",
            (product_id,),
        )
        connection.commit()
        return product_id
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ya existe un producto con ese nombre en la categoría seleccionada.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_catalog_product(product_id, name, description, price, admin_id):
    name = (name or "").strip()
    description = (description or "").strip()
    try:
        product_id = int(product_id)
        price = int(price)
    except (TypeError, ValueError) as error:
        raise ValueError("El producto y el precio deben ser válidos.") from error
    if not name:
        raise ValueError("El nombre del producto es obligatorio.")
    if len(name) > 120 or len(description) > 500:
        raise ValueError("El nombre o la descripción del producto son demasiado largos.")
    if price < 0:
        raise ValueError("El precio no puede ser negativo.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_admin(connection, admin_id)
        cursor = connection.execute(
            """UPDATE products SET name = ?, description = ?, price = ?
               WHERE product_id = ?""",
            (name, description or None, price, product_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("No se encontró el producto que deseas actualizar.")
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Ya existe otro producto con ese nombre en la misma categoría.") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def set_product_availability(product_id, is_available, admin_id):
    if is_available not in (True, False, 0, 1):
        raise ValueError("El estado de disponibilidad no es válido.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_admin(connection, admin_id)
        cursor = connection.execute(
            "UPDATE products SET is_available = ? WHERE product_id = ?",
            (1 if is_available else 0, int(product_id)),
        )
        if cursor.rowcount != 1:
            raise ValueError("No se encontró el producto.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
