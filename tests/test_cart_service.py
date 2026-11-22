"""Pruebas unitarias de la lógica del carrito.

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -v
"""

import unittest

from services.cart_service import ShoppingCart


class ShoppingCartTests(unittest.TestCase):
    def setUp(self):
        self.cart = ShoppingCart()
        self.burger = {
            "product_id": 1,
            "name": "Hamburguesa clásica",
            "price": 18000,
        }
        self.soda = {
            "product_id": 2,
            "name": "Gaseosa",
            "price": 5000,
        }

    def test_add_product_creates_one_cart_item(self):
        self.cart.add_product(self.burger)
        self.assertEqual(len(self.cart.get_items()), 1)
        self.assertEqual(self.cart.get_item_count(), 1)
        self.assertEqual(self.cart.get_total(), 18000)

    def test_adding_same_product_increases_quantity(self):
        self.cart.add_product(self.burger)
        self.cart.add_product(self.burger, quantity=2)
        item = self.cart.get_items()[0]
        self.assertEqual(item["quantity"], 3)
        self.assertEqual(self.cart.get_total(), 54000)

    def test_update_quantity_changes_total(self):
        self.cart.add_product(self.burger)
        self.cart.update_quantity(1, 3)
        self.assertEqual(self.cart.get_total(), 54000)

    def test_remove_product_removes_item(self):
        self.cart.add_product(self.burger)
        self.assertTrue(self.cart.remove_product(1))
        self.assertTrue(self.cart.is_empty())
        self.assertEqual(self.cart.get_total(), 0)

    def test_total_sums_multiple_products(self):
        self.cart.add_product(self.burger, quantity=2)
        self.cart.add_product(self.soda, quantity=3)
        self.assertEqual(self.cart.get_total(), 51000)
        self.assertEqual(self.cart.get_item_count(), 5)

    def test_clear_empties_cart(self):
        self.cart.add_product(self.burger)
        self.cart.add_product(self.soda)
        self.cart.clear()
        self.assertTrue(self.cart.is_empty())
        self.assertEqual(self.cart.get_total(), 0)

    def test_invalid_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cart.add_product(self.burger, quantity=0)

    def test_invalid_product_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cart.add_product({"product_id": 0, "name": "", "price": -1})


if __name__ == "__main__":
    unittest.main()
