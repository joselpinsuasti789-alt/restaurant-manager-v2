"""Casos de uso relacionados con la creación y consulta de pedidos."""

from database.order_repository import (
    create_order_record,
    get_customer_order_details,
    get_customer_orders,
)


class OrderService:
    """Coordina las operaciones de pedidos solicitadas por los clientes."""

    @staticmethod
    def place_customer_order(customer, order_type, cart_items, delivery_address="", customer_notes=""):
        if not isinstance(customer, dict) or not customer.get("customer_id"):
            raise ValueError("Debes iniciar sesión para realizar un pedido.")

        return create_order_record(
            customer_id=customer["customer_id"],
            order_type=order_type,
            cart_items=cart_items,
            delivery_address=delivery_address,
            customer_notes=customer_notes,
        )

    @staticmethod
    def list_customer_orders(customer_id):
        return get_customer_orders(customer_id)

    @staticmethod
    def get_customer_order(customer_id, order_id):
        return get_customer_order_details(customer_id, order_id)
