"""Pruebas del incremento 6: equipo y operación del restaurante."""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.customer_repository import create_customers_table, register_customer
from database.employee_repository import (
    create_employee_table,
    create_initial_admin,
    create_staff_member,
    authenticate_employee,
    has_admin_account,
)
from database.order_repository import create_order_record, create_order_tables
from database.operations_repository import (
    create_operations_tables,
    add_restaurant_table,
    list_restaurant_tables,
    list_inventory_products,
    set_product_stock,
    accept_order,
    get_kitchen_orders,
    update_kitchen_order_status,
    get_courier_deliveries,
    update_courier_delivery_status,
    cancel_order,
    complete_dine_in_order,
)
from database.product_repository import create_product_tables, get_available_products


class OperationsRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "operations_test.db"

        create_customers_table()
        create_product_tables()
        create_order_tables()
        create_employee_table()
        create_operations_tables()

        register_customer(
            "Cliente Operaciones", "operaciones@example.com", "3001112233", "Cliente12345"
        )
        conn = connection.get_connection()
        try:
            self.customer_id = conn.execute(
                "SELECT customer_id FROM customers WHERE email = ?",
                ("operaciones@example.com",),
            ).fetchone()["customer_id"]
        finally:
            conn.close()

        self.admin_id = create_initial_admin(
            "Admin Prueba", "admin.ops@example.com", "3000000000", "Admin12345"
        )
        self.kitchen_id = create_staff_member(
            "Cocinero Prueba", "cocina.ops@example.com", "3000000001", "Cocina12345", "kitchen", self.admin_id
        )
        self.courier_id = create_staff_member(
            "Repartidor Prueba", "repartidor.ops@example.com", "3000000002", "Reparto12345", "courier", self.admin_id
        )

        products = {item["name"]: item for item in get_available_products()}
        self.burger = products["Hamburguesa clásica"]
        self.soda = products["Gaseosa"]
        set_product_stock(self.burger["product_id"], 10, 2, self.admin_id)
        set_product_stock(self.soda["product_id"], 10, 2, self.admin_id)
        self.table_id = add_restaurant_table("1", 4, self.admin_id)

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def _create_dine_in_order(self, product=None, quantity=2):
        product = product or self.burger
        return create_order_record(
            self.customer_id, "dine_in", [{**product, "quantity": quantity}]
        )

    def _create_delivery_order(self, product=None, quantity=2):
        product = product or self.burger
        return create_order_record(
            self.customer_id,
            "delivery",
            [{**product, "quantity": quantity}],
            delivery_address="Calle 10 # 20-30",
        )

    def test_first_admin_can_be_created_only_once(self):
        self.assertTrue(has_admin_account())
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            create_initial_admin("Otro Admin", "otro@example.com", "3111111111", "OtraClave123")

    def test_employee_authentication_returns_role(self):
        success, employee = authenticate_employee("cocina.ops@example.com", "Cocina12345")
        self.assertTrue(success)
        self.assertEqual(employee["role"], "kitchen")
        success, message = authenticate_employee("cocina.ops@example.com", "incorrecta")
        self.assertFalse(success)

    def test_only_admin_can_create_staff(self):
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            create_staff_member(
                "Otro Cocinero", "otro.cocinero@example.com", "3003334444",
                "Clave12345", "kitchen", self.kitchen_id,
            )

    def test_admin_accepts_dine_in_order_assigns_table_and_deducts_stock(self):
        order_id = self._create_dine_in_order(quantity=2)
        accept_order(order_id, self.admin_id, table_id=self.table_id)

        conn = connection.get_connection()
        try:
            order = conn.execute(
                "SELECT status, table_id FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()
            stock = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.burger["product_id"],),
            ).fetchone()["stock_quantity"]
            table = conn.execute(
                "SELECT status FROM restaurant_tables WHERE table_id = ?", (self.table_id,)
            ).fetchone()["status"]
        finally:
            conn.close()

        self.assertEqual(order["status"], "accepted")
        self.assertEqual(order["table_id"], self.table_id)
        self.assertEqual(stock, 8)
        self.assertEqual(table, "occupied")

    def test_insufficient_inventory_does_not_partially_accept_order(self):
        order_id = self._create_dine_in_order(quantity=11)
        with self.assertRaisesRegex(ValueError, "Existencias insuficientes"):
            accept_order(order_id, self.admin_id, table_id=self.table_id)

        conn = connection.get_connection()
        try:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()["status"]
            stock = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.burger["product_id"],),
            ).fetchone()["stock_quantity"]
            table_status = conn.execute(
                "SELECT status FROM restaurant_tables WHERE table_id = ?", (self.table_id,)
            ).fetchone()["status"]
        finally:
            conn.close()
        self.assertEqual(order_status, "pending")
        self.assertEqual(stock, 10)
        self.assertEqual(table_status, "available")

    def test_kitchen_moves_order_from_accepted_to_preparing_to_ready(self):
        order_id = self._create_dine_in_order(quantity=1)
        accept_order(order_id, self.admin_id, table_id=self.table_id)
        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        kitchen_orders = get_kitchen_orders()
        self.assertFalse(any(item["order_id"] == order_id for item in kitchen_orders))

        conn = connection.get_connection()
        try:
            status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()["status"]
        finally:
            conn.close()
        self.assertEqual(status, "ready")

    def test_admin_completes_dine_in_and_releases_table(self):
        order_id = self._create_dine_in_order(quantity=1)
        accept_order(order_id, self.admin_id, table_id=self.table_id)
        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        complete_dine_in_order(order_id, self.admin_id)
        self.assertEqual(list_restaurant_tables()[0]["status"], "available")

    def test_delivery_assignment_and_courier_workflow(self):
        order_id = self._create_delivery_order(quantity=1)
        accept_order(order_id, self.admin_id, courier_id=self.courier_id)
        assigned = get_courier_deliveries(self.courier_id)
        self.assertEqual(assigned[0]["order_id"], order_id)

        with self.assertRaisesRegex(ValueError, "Cocina debe marcar"):
            update_courier_delivery_status(order_id, self.courier_id, "picked_up")

        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        update_courier_delivery_status(order_id, self.courier_id, "picked_up")
        update_courier_delivery_status(order_id, self.courier_id, "delivered")

        conn = connection.get_connection()
        try:
            status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()["status"]
            delivery_status = conn.execute(
                "SELECT delivery_status FROM deliveries WHERE order_id = ?", (order_id,)
            ).fetchone()["delivery_status"]
        finally:
            conn.close()
        self.assertEqual(status, "completed")
        self.assertEqual(delivery_status, "delivered")

    def test_admin_cancellation_restores_stock_and_releases_table(self):
        order_id = self._create_dine_in_order(quantity=2)
        accept_order(order_id, self.admin_id, table_id=self.table_id)
        cancel_order(order_id, self.admin_id, "El cliente solicitó cancelar.")

        conn = connection.get_connection()
        try:
            status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()["status"]
            stock = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.burger["product_id"],),
            ).fetchone()["stock_quantity"]
            table_status = conn.execute(
                "SELECT status FROM restaurant_tables WHERE table_id = ?", (self.table_id,)
            ).fetchone()["status"]
        finally:
            conn.close()
        self.assertEqual(status, "cancelled")
        self.assertEqual(stock, 10)
        self.assertEqual(table_status, "available")

    def test_cannot_cancel_order_from_non_admin_role(self):
        order_id = self._create_dine_in_order(quantity=1)
        with self.assertRaisesRegex(ValueError, "no tiene permisos"):
            cancel_order(order_id, self.kitchen_id, "Intento no autorizado")


if __name__ == "__main__":
    unittest.main()
