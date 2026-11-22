"""Pruebas de integración de extremo a extremo de Restaurant Manager V2.

Estas pruebas conectan clientes, catálogo, carrito, pedidos, operación,
turnos, pagos e informes usando una base de datos temporal.
"""

import tempfile
import unittest
from pathlib import Path

from database import connection
from database.administration_repository import (
    create_administration_tables,
    start_employee_shift,
    end_employee_shift,
    record_cash_payment,
    get_admin_report,
)
from database.customer_repository import (
    create_customers_table,
    register_customer,
    authenticate_customer,
)
from database.employee_repository import (
    create_employee_table,
    create_initial_admin,
    create_staff_member,
)
from database.operations_repository import (
    create_operations_tables,
    add_restaurant_table,
    set_product_stock,
    list_restaurant_tables,
    accept_order,
    update_kitchen_order_status,
    update_courier_delivery_status,
)
from database.order_repository import (
    create_order_tables,
    get_customer_order_details,
    get_customer_orders,
)
from database.product_repository import create_product_tables, get_available_products
from services.cart_service import ShoppingCart
from services.order_service import OrderService


class EndToEndWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp_directory.name) / "end_to_end.db"

        # Inicializar el mismo conjunto de tablas que utiliza la aplicación.
        create_customers_table()
        create_product_tables()
        create_order_tables()
        create_employee_table()
        create_operations_tables()
        create_administration_tables()

        success, message = register_customer(
            "Cliente Integracion",
            "cliente.integracion@example.com",
            "3001112233",
            "Cliente12345",
        )
        self.assertTrue(success, message)

        login_success, self.customer = authenticate_customer(
            "cliente.integracion@example.com",
            "Cliente12345",
        )
        self.assertTrue(login_success)

        self.admin_id = create_initial_admin(
            "Admin Integracion",
            "admin.integracion@example.com",
            "3000000000",
            "Admin12345",
        )
        self.kitchen_id = create_staff_member(
            "Cocina Integracion",
            "cocina.integracion@example.com",
            "3000000001",
            "Cocina12345",
            "kitchen",
            self.admin_id,
        )
        self.courier_id = create_staff_member(
            "Repartidor Integracion",
            "repartidor.integracion@example.com",
            "3000000002",
            "Reparto12345",
            "courier",
            self.admin_id,
        )

        catalog = {product["name"]: product for product in get_available_products()}
        self.burger = catalog["Hamburguesa clásica"]
        self.soda = catalog["Gaseosa"]

        set_product_stock(self.burger["product_id"], 20, 3, self.admin_id)
        set_product_stock(self.soda["product_id"], 20, 3, self.admin_id)

        self.table_id = add_restaurant_table("I-01", 4, self.admin_id)

        self.cart = ShoppingCart()
        self.order_service = OrderService()

    def tearDown(self):
        connection.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def _create_order_from_cart(self, order_type, address=None):
        return self.order_service.place_customer_order(
            customer=self.customer,
            order_type=order_type,
            cart_items=self.cart.get_items(),
            delivery_address=address,
            customer_notes="Prueba integral de Restaurant Manager V2",
        )

    def test_delivery_from_customer_cart_to_cash_payment_and_report(self):
        """Cliente -> carrito -> pedido -> admin -> cocina -> courier -> pago -> informe."""
        # Los empleados inician sus turnos.
        start_employee_shift(self.admin_id)
        start_employee_shift(self.kitchen_id)
        start_employee_shift(self.courier_id)

        # El cliente arma el carrito y crea el pedido de domicilio.
        self.cart.add_product(self.burger, quantity=2)
        self.cart.add_product(self.soda, quantity=1)
        self.assertEqual(self.cart.get_total(), 41000)

        order_id = self._create_order_from_cart(
            "delivery",
            address="Calle 10 # 20-30, Cali",
        )
        self.cart.clear()
        self.assertTrue(self.cart.is_empty())

        details = get_customer_order_details(self.customer["customer_id"], order_id)
        self.assertEqual(details["status"], "pending")
        self.assertEqual(details["payment_status"], "pending")
        self.assertEqual(details["total"], 41000)

        # El inventario no se descuenta al crear el pedido.
        conn = connection.get_connection()
        try:
            stock_before_acceptance = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.burger["product_id"],),
            ).fetchone()["stock_quantity"]
        finally:
            conn.close()
        self.assertEqual(stock_before_acceptance, 20)

        # Al aceptar el pedido, el inventario se descuenta transaccionalmente.
        accept_order(order_id, self.admin_id, courier_id=self.courier_id)
        conn = connection.get_connection()
        try:
            stock_after_acceptance = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.burger["product_id"],),
            ).fetchone()["stock_quantity"]
            soda_stock_after_acceptance = conn.execute(
                "SELECT stock_quantity FROM inventory WHERE product_id = ?",
                (self.soda["product_id"],),
            ).fetchone()["stock_quantity"]
        finally:
            conn.close()
        self.assertEqual(stock_after_acceptance, 18)
        self.assertEqual(soda_stock_after_acceptance, 19)
        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")
        update_courier_delivery_status(order_id, self.courier_id, "picked_up")
        update_courier_delivery_status(order_id, self.courier_id, "delivered")

        completed = get_customer_order_details(self.customer["customer_id"], order_id)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["delivery_status"], "delivered")

        # Solo se registra el efectivo cuando el pedido está completado.
        collected = record_cash_payment(order_id, self.admin_id)
        self.assertEqual(collected, 41000)

        history = get_customer_orders(self.customer["customer_id"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["payment_status"], "paid")

        report = get_admin_report("2000-01-01", "2999-12-31")
        self.assertEqual(report["total_orders"], 1)
        self.assertEqual(report["completed_orders"], 1)
        self.assertEqual(report["cash_collected"], 41000)
        self.assertEqual(report["cash_pending"], 0)

        # Cerrar los turnos al finalizar la operación.
        end_employee_shift(self.courier_id)
        end_employee_shift(self.kitchen_id)
        end_employee_shift(self.admin_id)

    def test_dine_in_order_assigns_and_releases_table_then_records_payment(self):
        """Cliente -> pedido en mesa -> asignación -> cocina -> mesa liberada -> pago."""
        self.cart.add_product(self.burger, quantity=1)
        order_id = self._create_order_from_cart("dine_in")

        before_acceptance = list_restaurant_tables(available_only=True)
        self.assertEqual(len(before_acceptance), 1)

        accept_order(order_id, self.admin_id, table_id=self.table_id)
        occupied = list_restaurant_tables()
        self.assertEqual(occupied[0]["status"], "occupied")

        update_kitchen_order_status(order_id, self.kitchen_id, "preparing")
        update_kitchen_order_status(order_id, self.kitchen_id, "ready")

        from database.operations_repository import complete_dine_in_order
        complete_dine_in_order(order_id, self.admin_id)

        available_again = list_restaurant_tables(available_only=True)
        self.assertEqual(len(available_again), 1)
        self.assertEqual(available_again[0]["table_id"], self.table_id)

        details = get_customer_order_details(self.customer["customer_id"], order_id)
        self.assertEqual(details["status"], "completed")
        self.assertEqual(details["order_type"], "dine_in")
        self.assertEqual(record_cash_payment(order_id, self.admin_id), self.burger["price"])


if __name__ == "__main__":
    unittest.main()
