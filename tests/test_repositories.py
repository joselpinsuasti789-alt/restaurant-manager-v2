"""Pruebas básicas de los repositorios de clientes y productos.

Ejecutar desde la carpeta raíz del proyecto:
    python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.customer_repository import (
    authenticate_customer,
    create_customers_table,
    register_customer,
)
from database.product_repository import (
    create_product_tables,
    get_available_products,
)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "test_database.db"
        create_customers_table()
        create_product_tables()

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_register_and_authenticate_customer(self):
        success, message = register_customer(
            "Cliente de Prueba",
            "cliente@example.com",
            "3001234567",
            "ClavePrueba123",
        )
        self.assertTrue(success, message)

        login_success, customer = authenticate_customer(
            "cliente@example.com",
            "ClavePrueba123",
        )
        self.assertTrue(login_success)
        self.assertEqual(customer["full_name"], "Cliente de Prueba")
        self.assertNotIn("password_hash", customer)

    def test_duplicate_email_is_rejected(self):
        register_customer("Cliente Uno", "igual@example.com", "3000000001", "ClavePrueba123")
        success, message = register_customer(
            "Cliente Dos",
            "IGUAL@example.com",
            "3000000002",
            "ClavePrueba123",
        )
        self.assertFalse(success)
        self.assertIn("ya está registrado", message)

    def test_wrong_password_is_rejected(self):
        register_customer("Cliente", "login@example.com", "3001234567", "ClavePrueba123")
        success, message = authenticate_customer("login@example.com", "NoEsLaClave")
        self.assertFalse(success)
        self.assertIn("incorrectos", message)

    def test_demo_catalog_contains_five_products(self):
        products = get_available_products()
        self.assertEqual(len(products), 5)
        self.assertTrue(all(product["price"] >= 0 for product in products))


if __name__ == "__main__":
    unittest.main()
