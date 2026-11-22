"""Pruebas del incremento 5: creación y consulta de pedidos."""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.customer_repository import create_customers_table, register_customer
from database.order_repository import (
    create_order_record,
    create_order_tables,
    get_customer_order_details,
    get_customer_orders,
)
from database.product_repository import create_product_tables, get_available_products


class OrderRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "orders_test.db"
        create_customers_table()
        create_product_tables()
        create_order_tables()

        success, message = register_customer(
            "Cliente de Prueba",
            "cliente.pedidos@example.com",
            "3001234567",
            "ClavePrueba123",
        )
        self.assertTrue(success, message)

        conn = connection.get_connection()
        try:
            row = conn.execute(
                "SELECT customer_id FROM customers WHERE email = ?",
                ("cliente.pedidos@example.com",),
            ).fetchone()
            self.customer_id = row["customer_id"]
        finally:
            conn.close()

        self.products = {item["name"]: item for item in get_available_products()}
        self.burger = self.products["Hamburguesa clásica"]
        self.soda = self.products["Gaseosa"]

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_create_delivery_order_and_pending_cash_payment(self):
        order_id = create_order_record(
            self.customer_id,
            "delivery",
            [{**self.burger, "quantity": 2}],
            delivery_address="Calle 10 # 20-30",
            customer_notes="Tocar el timbre.",
        )

        details = get_customer_order_details(self.customer_id, order_id)
        self.assertIsNotNone(details)
        self.assertEqual(details["order_type"], "delivery")
        self.assertEqual(details["status"], "pending")
        self.assertEqual(details["total"], 36000)
        self.assertEqual(details["payment_method"], "cash")
        self.assertEqual(details["payment_status"], "pending")
        self.assertEqual(details["delivery_status"], "pending")
        self.assertEqual(details["items"][0]["product_name"], "Hamburguesa clásica")
        self.assertEqual(details["items"][0]["quantity"], 2)

    def test_create_dine_in_order_without_table_assignment(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.soda, "quantity": 1}],
        )

        details = get_customer_order_details(self.customer_id, order_id)
        self.assertEqual(details["order_type"], "dine_in")
        self.assertIsNone(details["delivery_address"])
        self.assertEqual(details["delivery_status"], "")

        conn = connection.get_connection()
        try:
            order = conn.execute(
                "SELECT table_id FROM orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            self.assertIsNone(order["table_id"])
        finally:
            conn.close()

    def test_empty_cart_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "carrito vacío"):
            create_order_record(self.customer_id, "dine_in", [])

    def test_delivery_requires_address(self):
        with self.assertRaisesRegex(ValueError, "dirección de entrega"):
            create_order_record(
                self.customer_id,
                "delivery",
                [{**self.burger, "quantity": 1}],
            )

    def test_invalid_order_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "tipo de pedido"):
            create_order_record(
                self.customer_id,
                "pickup",
                [{**self.burger, "quantity": 1}],
            )

    def test_price_change_is_rejected(self):
        conn = connection.get_connection()
        try:
            conn.execute(
                "UPDATE products SET price = ? WHERE product_id = ?",
                (19000, self.burger["product_id"]),
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertRaisesRegex(ValueError, "precio.*cambió"):
            create_order_record(
                self.customer_id,
                "dine_in",
                [{**self.burger, "quantity": 1}],
            )

    def test_unavailable_product_is_rejected(self):
        conn = connection.get_connection()
        try:
            conn.execute(
                "UPDATE products SET is_available = 0 WHERE product_id = ?",
                (self.burger["product_id"],),
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertRaisesRegex(ValueError, "ya no está disponible"):
            create_order_record(
                self.customer_id,
                "dine_in",
                [{**self.burger, "quantity": 1}],
            )

    def test_invalid_line_does_not_create_partial_order(self):
        with self.assertRaises(ValueError):
            create_order_record(
                self.customer_id,
                "dine_in",
                [
                    {**self.burger, "quantity": 1},
                    {"product_id": 99999, "price": 500, "quantity": 1},
                ],
            )

        conn = connection.get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) AS total FROM orders").fetchone()["total"]
            self.assertEqual(count, 0)
        finally:
            conn.close()

    def test_customer_order_history_is_scoped_to_customer(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.burger, "quantity": 1}],
        )
        self.assertEqual(len(get_customer_orders(self.customer_id)), 1)
        self.assertEqual(get_customer_orders(self.customer_id + 1000), [])
        self.assertIsNone(get_customer_order_details(self.customer_id + 1000, order_id))

    def test_initial_status_history_is_created(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.soda, "quantity": 1}],
        )
        conn = connection.get_connection()
        try:
            history = conn.execute(
                "SELECT previous_status, new_status FROM order_status_history WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            self.assertIsNone(history["previous_status"])
            self.assertEqual(history["new_status"], "pending")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
