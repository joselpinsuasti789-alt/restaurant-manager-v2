"""Pruebas de administración del catálogo y cuentas del personal."""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.customer_repository import create_customers_table
from database.employee_repository import (
    create_employee_table,
    create_initial_admin,
    create_staff_member,
    set_employee_active_status,
    authenticate_employee,
)
from database.operations_repository import create_operations_tables
from database.product_repository import (
    create_product_tables,
    get_product_categories,
    get_admin_product_catalog,
    create_product_category,
    create_catalog_product,
    update_catalog_product,
    set_product_availability,
    get_available_products,
)
from database.order_repository import create_order_tables
from database.administration_repository import create_administration_tables, start_employee_shift


class CatalogAndStaffAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "catalog_admin_test.db"

        create_customers_table()
        create_product_tables()
        create_order_tables()
        create_employee_table()
        create_operations_tables()
        create_administration_tables()

        self.admin_id = create_initial_admin(
            "Administradora", "admin.catalog@example.com", "3001111000", "Admin12345"
        )
        self.kitchen_id = create_staff_member(
            "Cocinero", "cocina.catalog@example.com", "3001111001", "Cocina12345", "kitchen", self.admin_id
        )

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_admin_can_create_category(self):
        category_id = create_product_category("Postres", "Dulces", self.admin_id)
        categories = get_product_categories()
        self.assertTrue(any(item["category_id"] == category_id for item in categories))

    def test_duplicate_category_is_rejected(self):
        create_product_category("Postres", "Dulces", self.admin_id)
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            create_product_category("Postres", "Otra descripción", self.admin_id)

    def test_admin_can_create_product_and_inventory_record(self):
        category = next(item for item in get_product_categories() if item["name"] == "Bebidas")
        product_id = create_catalog_product(category["category_id"], "Té frío", "Té con hielo", 6500, self.admin_id)
        catalog = get_admin_product_catalog()
        self.assertTrue(any(item["product_id"] == product_id for item in catalog))
        conn = connection.get_connection()
        try:
            inventory = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?", (product_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(inventory["stock_quantity"], 0)

    def test_admin_can_update_price_and_availability(self):
        product = next(item for item in get_admin_product_catalog() if item["name"] == "Gaseosa")
        update_catalog_product(product["product_id"], product["name"], product["description"], 5500, self.admin_id)
        set_product_availability(product["product_id"], False, self.admin_id)
        updated = next(item for item in get_admin_product_catalog() if item["product_id"] == product["product_id"])
        self.assertEqual(updated["price"], 5500)
        self.assertEqual(updated["is_available"], 0)
        self.assertFalse(any(item["product_id"] == product["product_id"] for item in get_available_products()))

    def test_non_admin_cannot_manage_catalog(self):
        category = get_product_categories()[0]
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            create_catalog_product(category["category_id"], "Producto no autorizado", "", 1000, self.kitchen_id)

    def test_admin_can_deactivate_and_reactivate_staff(self):
        set_employee_active_status(self.kitchen_id, False, self.admin_id)
        success, _ = authenticate_employee("cocina.catalog@example.com", "Cocina12345")
        self.assertFalse(success)
        set_employee_active_status(self.kitchen_id, True, self.admin_id)
        success, employee = authenticate_employee("cocina.catalog@example.com", "Cocina12345")
        self.assertTrue(success)
        self.assertEqual(employee["employee_id"], self.kitchen_id)

    def test_employee_with_open_shift_cannot_be_deactivated(self):
        start_employee_shift(self.kitchen_id)
        with self.assertRaisesRegex(ValueError, "finalizar su turno"):
            set_employee_active_status(self.kitchen_id, False, self.admin_id)

    def test_admin_cannot_deactivate_own_account(self):
        with self.assertRaisesRegex(ValueError, "tu propia cuenta"):
            set_employee_active_status(self.admin_id, False, self.admin_id)

    def test_non_admin_cannot_change_employee_status(self):
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            set_employee_active_status(self.kitchen_id, False, self.kitchen_id)


if __name__ == "__main__":
    unittest.main()
