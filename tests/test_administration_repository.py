"""Pruebas del incremento 7: pagos, turnos e informes administrativos."""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.administration_repository import (
    create_administration_tables,
    start_employee_shift,
    end_employee_shift,
    get_current_employee_shift,
    get_open_employee_shifts,
    get_cash_payment_queue,
    record_cash_payment,
    get_recent_cash_payments,
    get_admin_report,
)
from database.customer_repository import create_customers_table, register_customer
from database.employee_repository import (
    create_employee_table,
    create_initial_admin,
    create_staff_member,
)
from database.order_repository import create_order_record, create_order_tables
from database.operations_repository import (
    create_operations_tables,
    add_restaurant_table,
    set_product_stock,
    accept_order,
    update_kitchen_order_status,
    complete_dine_in_order,
    update_courier_delivery_status,
)
from database.product_repository import create_product_tables, get_available_products


class AdministrationRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "administration_test.db"

        create_customers_table()
        create_product_tables()
        create_order_tables()
        create_employee_table()
        create_operations_tables()
        create_administration_tables()

        register_customer("Cliente Admin", "cliente.admin@example.com", "3001112233", "Cliente12345")
        conn = connection.get_connection()
        try:
            self.customer_id = conn.execute(
                "SELECT customer_id FROM customers WHERE email = ?",
                ("cliente.admin@example.com",),
            ).fetchone()["customer_id"]
        finally:
            conn.close()

        self.admin_id = create_initial_admin(
            "Admin Prueba", "admin.v7@example.com", "3000000000", "Admin12345"
        )
        self.kitchen_id = create_staff_member(
            "Cocinero Prueba", "kitchen.v7@example.com", "3000000001", "Cocina12345", "kitchen", self.admin_id
        )
        self.courier_id = create_staff_member(
            "Repartidor Prueba", "courier.v7@example.com", "3000000002", "Reparto12345", "courier", self.admin_id
        )

        self.products = {item["name"]: item for item in get_available_products()}
        self.burger = self.products["Hamburguesa clásica"]
        set_product_stock(self.burger["product_id"], 20, 3, self.admin_id)
        self.table_id = add_restaurant_table("A1", 4, self.admin_id)

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def _complete_dine_in_order(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.burger, "quantity": 1}],
        )
        accept_order(order_id, self.admin_id, table_id=self.table_id)
        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        complete_dine_in_order(order_id, self.admin_id)
        return order_id

    def _complete_delivery_order(self):
        order_id = create_order_record(
            self.customer_id,
            "delivery",
            [{**self.burger, "quantity": 1}],
            delivery_address="Calle 10 # 20-30",
        )
        accept_order(order_id, self.admin_id, courier_id=self.courier_id)
        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        update_courier_delivery_status(order_id, self.courier_id, "picked_up")
        update_courier_delivery_status(order_id, self.courier_id, "delivered")
        return order_id

    def test_employee_can_start_and_end_shift(self):
        shift_id = start_employee_shift(self.kitchen_id)
        self.assertGreater(shift_id, 0)
        self.assertIsNotNone(get_current_employee_shift(self.kitchen_id))
        end_employee_shift(self.kitchen_id)
        self.assertIsNone(get_current_employee_shift(self.kitchen_id))

    def test_employee_cannot_open_two_shifts(self):
        start_employee_shift(self.kitchen_id)
        with self.assertRaisesRegex(ValueError, "Ya tienes un turno abierto"):
            start_employee_shift(self.kitchen_id)

    def test_employee_cannot_end_shift_when_none_is_open(self):
        with self.assertRaisesRegex(ValueError, "No tienes un turno abierto"):
            end_employee_shift(self.kitchen_id)

    def test_admin_can_see_open_shifts(self):
        start_employee_shift(self.kitchen_id)
        shifts = get_open_employee_shifts()
        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0]["employee_id"], self.kitchen_id)

    def test_cash_payment_cannot_be_recorded_before_order_completion(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.burger, "quantity": 1}],
        )
        with self.assertRaisesRegex(ValueError, "debe estar completado"):
            record_cash_payment(order_id, self.admin_id)

    def test_admin_can_record_cash_payment_for_completed_order(self):
        order_id = self._complete_dine_in_order()
        amount = record_cash_payment(order_id, self.admin_id)
        self.assertEqual(amount, self.burger["price"])
        history = get_recent_cash_payments()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["order_id"], order_id)
        self.assertEqual(history[0]["payment_status"], "paid")

    def test_cash_payment_cannot_be_recorded_twice(self):
        order_id = self._complete_dine_in_order()
        record_cash_payment(order_id, self.admin_id)
        with self.assertRaisesRegex(ValueError, "ya fue registrado"):
            record_cash_payment(order_id, self.admin_id)

    def test_non_admin_cannot_record_cash_payment(self):
        order_id = self._complete_dine_in_order()
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            record_cash_payment(order_id, self.kitchen_id)

    def test_cash_payment_queue_contains_pending_payment(self):
        order_id = create_order_record(
            self.customer_id,
            "dine_in",
            [{**self.burger, "quantity": 1}],
        )
        queue = get_cash_payment_queue()
        self.assertTrue(any(item["order_id"] == order_id for item in queue))

    def test_admin_report_summarizes_orders_and_payments(self):
        order_id = self._complete_dine_in_order()
        record_cash_payment(order_id, self.admin_id)
        from datetime import date
        today = date.today().isoformat()
        report = get_admin_report(today, today)
        self.assertGreaterEqual(report["total_orders"], 1)
        self.assertGreaterEqual(report["completed_orders"], 1)
        self.assertGreaterEqual(report["cash_collected"], self.burger["price"])
        self.assertTrue(report["top_products"])

    def test_report_rejects_invalid_date_range(self):
        with self.assertRaisesRegex(ValueError, "formato AAAA-MM-DD"):
            get_admin_report("21/11/2026", "2026-11-21")
        with self.assertRaisesRegex(ValueError, "posterior"):
            get_admin_report("2026-11-22", "2026-11-21")


if __name__ == "__main__":
    unittest.main()
