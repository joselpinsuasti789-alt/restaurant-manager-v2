"""Lógica de negocio del carrito de compras (almacenado en memoria)."""


class ShoppingCart:
    """Administra productos, cantidades y totales de una sesión de cliente.

    El carrito es temporal: vive en memoria mientras la aplicación permanece
    abierta y se limpia al cerrar la sesión. La persistencia llegará con los
    pedidos en un incremento posterior.
    """

    def __init__(self):
        self._items = {}

    def add_product(self, product, quantity=1):
        """Agrega un producto o aumenta su cantidad si ya está en el carrito."""
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError("La cantidad debe ser un número entero mayor que cero.")

        try:
            product_id = int(product["product_id"])
            name = str(product["name"]).strip()
            price = int(product["price"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("El producto no contiene datos válidos.") from error

        if product_id < 1 or not name or price < 0:
            raise ValueError("El producto no contiene datos válidos.")

        if product_id in self._items:
            self._items[product_id]["quantity"] += quantity
            # Actualiza nombre y precio con los datos actuales del catálogo.
            self._items[product_id]["name"] = name
            self._items[product_id]["price"] = price
        else:
            self._items[product_id] = {
                "product_id": product_id,
                "name": name,
                "price": price,
                "quantity": quantity,
            }

    def update_quantity(self, product_id, quantity):
        """Establece una nueva cantidad. Debe ser al menos uno."""
        product_id = int(product_id)

        if product_id not in self._items:
            raise KeyError("El producto no está en el carrito.")

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError("La cantidad debe ser un número entero mayor que cero.")

        self._items[product_id]["quantity"] = quantity

    def remove_product(self, product_id):
        """Elimina un producto. Devuelve True si estaba en el carrito."""
        return self._items.pop(int(product_id), None) is not None

    def clear(self):
        """Vacía por completo el carrito."""
        self._items.clear()

    def get_items(self):
        """Devuelve una copia de los artículos para no exponer el estado interno."""
        return [item.copy() for item in self._items.values()]

    def get_item_count(self):
        """Devuelve la suma de unidades de todos los productos."""
        return sum(item["quantity"] for item in self._items.values())

    def get_total(self):
        """Calcula el total en pesos colombianos enteros."""
        return sum(item["price"] * item["quantity"] for item in self._items.values())

    def is_empty(self):
        """Indica si no hay productos agregados."""
        return not self._items
