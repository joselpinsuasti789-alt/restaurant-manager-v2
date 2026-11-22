"""Punto de entrada e interfaz gráfica de Restaurant Manager V2."""

import sqlite3
from datetime import date, timedelta

import customtkinter as ctk

from config import (
    APP_NAME,
    APP_VERSION,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    THEME,
    COLOR_THEME,
    CURRENCY_SYMBOL,
)
from database.connection import get_connection
from database.customer_repository import (
    create_customers_table,
    register_customer,
    authenticate_customer,
)
from database.product_repository import (
    create_product_tables,
    get_available_products,
    get_product_categories,
    get_admin_product_catalog,
    create_product_category,
    create_catalog_product,
    update_catalog_product,
    set_product_availability,
)
from database.order_repository import create_order_tables
from services.cart_service import ShoppingCart
from services.order_service import OrderService
from database.employee_repository import (
    create_employee_table,
    has_admin_account,
    create_initial_admin,
    authenticate_employee,
    create_staff_member,
    list_active_couriers,
    list_active_employees,
    set_employee_active_status,
)
from database.operations_repository import (
    create_operations_tables,
    add_restaurant_table,
    list_restaurant_tables,
    list_inventory_products,
    set_product_stock,
    get_pending_orders,
    get_admin_active_orders,
    accept_order,
    get_kitchen_orders,
    update_kitchen_order_status,
    get_courier_deliveries,
    update_courier_delivery_status,
    complete_dine_in_order,
    cancel_order,
)
from database.administration_repository import (
    create_administration_tables,
    get_current_employee_shift,
    start_employee_shift,
    end_employee_shift,
    get_open_employee_shifts,
    get_recent_employee_shifts,
    get_cash_payment_queue,
    record_cash_payment,
    get_recent_cash_payments,
    get_admin_report,
)


class RestaurantApp(ctk.CTk):
    """Ventana principal y navegación de la aplicación."""

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self.current_customer = None
        self.current_employee = None
        self.cart = ShoppingCart()
        self.order_service = OrderService()
        self.database_status_message = "Comprobando conexión..."
        self.database_status_color = "gray"

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self.show_welcome()
        self.initialize_database()

    # --------------------------------------------------
    # UTILIDADES GENERALES
    # --------------------------------------------------

    def clear_screen(self):
        """Elimina los componentes de la pantalla actual."""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    @staticmethod
    def format_currency(amount):
        """Formatea un importe entero como pesos colombianos."""
        return f"{CURRENCY_SYMBOL}{amount:,}".replace(",", ".")

    def show_message(self, parent, message, color="gray"):
        """Muestra un mensaje informativo dentro de un contenedor."""
        label = ctk.CTkLabel(
            parent,
            text=message,
            text_color=color,
            font=("Arial", 13),
            wraplength=520,
        )
        label.pack(pady=8)
        return label

    # --------------------------------------------------
    # PANTALLA INICIAL
    # --------------------------------------------------

    def show_welcome(self):
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(
            frame,
            text="RESTAURANT MANAGER",
            font=("Arial", 34, "bold"),
        ).pack(pady=(90, 10))

        ctk.CTkLabel(
            frame,
            text="Bienvenido a nuestro restaurante",
            font=("Arial", 17),
        ).pack(pady=10)

        buttons_frame = ctk.CTkFrame(frame, fg_color="transparent")
        buttons_frame.pack(pady=45)

        ctk.CTkButton(
            buttons_frame,
            text="CLIENTES",
            width=230,
            height=110,
            font=("Arial", 20, "bold"),
            command=self.show_customer_portal,
        ).grid(row=0, column=0, padx=15)

        ctk.CTkButton(
            buttons_frame,
            text="EQUIPO",
            width=230,
            height=110,
            font=("Arial", 20, "bold"),
            fg_color="#465363",
            hover_color="#34404E",
            command=self.show_team_portal,
        ).grid(row=0, column=1, padx=15)

        self.database_status_label = ctk.CTkLabel(
            frame,
            text=self.database_status_message,
            text_color=self.database_status_color,
            font=("Arial", 13),
        )
        self.database_status_label.pack(side="bottom", pady=20)

    # --------------------------------------------------
    # PORTAL DE CLIENTES
    # --------------------------------------------------

    def show_customer_portal(self, message="", message_color="gray"):
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=40, pady=40)

        ctk.CTkLabel(
            frame,
            text="PORTAL DE CLIENTES",
            font=("Arial", 30, "bold"),
        ).pack(pady=(65, 15))

        ctk.CTkLabel(
            frame,
            text="Bienvenido. Accede a nuestro restaurante.",
            font=("Arial", 16),
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="CREAR CUENTA",
            width=260,
            height=48,
            command=self.show_registration_form,
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="INICIAR SESIÓN",
            width=260,
            height=48,
            command=self.show_login_form,
        ).pack(pady=10)

        if message:
            self.show_message(frame, message, message_color)

        ctk.CTkButton(
            frame,
            text="Volver al inicio",
            width=200,
            fg_color="transparent",
            border_width=1,
            command=self.show_welcome,
        ).pack(pady=25)

    # --------------------------------------------------
    # REGISTRO DE CLIENTES
    # --------------------------------------------------

    def show_registration_form(self):
        self.clear_screen()

        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=20)

        ctk.CTkLabel(
            frame,
            text="CREAR CUENTA",
            font=("Arial", 30, "bold"),
        ).pack(pady=(15, 20))

        self.name_entry = ctk.CTkEntry(
            frame, width=350, height=42, placeholder_text="Nombre completo"
        )
        self.name_entry.pack(pady=7)

        self.email_entry = ctk.CTkEntry(
            frame, width=350, height=42, placeholder_text="Correo electrónico"
        )
        self.email_entry.pack(pady=7)

        self.phone_entry = ctk.CTkEntry(
            frame, width=350, height=42, placeholder_text="Teléfono"
        )
        self.phone_entry.pack(pady=7)

        self.password_entry = ctk.CTkEntry(
            frame,
            width=350,
            height=42,
            placeholder_text="Contraseña (mínimo 8 caracteres)",
            show="*",
        )
        self.password_entry.pack(pady=7)

        self.confirm_password_entry = ctk.CTkEntry(
            frame,
            width=350,
            height=42,
            placeholder_text="Confirmar contraseña",
            show="*",
        )
        self.confirm_password_entry.pack(pady=7)

        self.registration_message_label = self.show_message(frame, "")

        ctk.CTkButton(
            frame,
            text="REGISTRARME",
            width=250,
            height=45,
            command=self.register_customer_action,
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="Volver",
            width=180,
            fg_color="transparent",
            border_width=1,
            command=self.show_customer_portal,
        ).pack(pady=8)

    def register_customer_action(self):
        full_name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if not all((full_name, email, phone, password, confirm_password)):
            self.registration_message_label.configure(
                text="Debes completar todos los campos.", text_color="#E74C3C"
            )
            return

        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            self.registration_message_label.configure(
                text="Ingresa un correo electrónico válido.", text_color="#E74C3C"
            )
            return

        if len(password) < 8:
            self.registration_message_label.configure(
                text="La contraseña debe tener al menos 8 caracteres.",
                text_color="#E74C3C",
            )
            return

        if password != confirm_password:
            self.registration_message_label.configure(
                text="Las contraseñas no coinciden.", text_color="#E74C3C"
            )
            return

        success, message = register_customer(full_name, email, phone, password)
        if success:
            self.show_customer_portal(message, "#2ECC71")
        else:
            self.registration_message_label.configure(
                text=message, text_color="#E74C3C"
            )

    # --------------------------------------------------
    # INICIO DE SESIÓN DE CLIENTES
    # --------------------------------------------------

    def show_login_form(self):
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(
            frame,
            text="INICIAR SESIÓN",
            font=("Arial", 30, "bold"),
        ).pack(pady=(65, 25))

        self.login_email_entry = ctk.CTkEntry(
            frame, width=350, height=45, placeholder_text="Correo electrónico"
        )
        self.login_email_entry.pack(pady=10)

        self.login_password_entry = ctk.CTkEntry(
            frame,
            width=350,
            height=45,
            placeholder_text="Contraseña",
            show="*",
        )
        self.login_password_entry.pack(pady=10)

        self.login_message_label = self.show_message(frame, "")

        ctk.CTkButton(
            frame,
            text="INGRESAR",
            width=250,
            height=45,
            command=self.login_customer_action,
        ).pack(pady=15)

        ctk.CTkButton(
            frame,
            text="Volver",
            width=180,
            fg_color="transparent",
            border_width=1,
            command=self.show_customer_portal,
        ).pack(pady=8)

    def login_customer_action(self):
        email = self.login_email_entry.get().strip()
        password = self.login_password_entry.get()

        if not email or not password:
            self.login_message_label.configure(
                text="Ingresa tu correo y contraseña.", text_color="#E74C3C"
            )
            return

        success, result = authenticate_customer(email, password)
        if success:
            self.cart.clear()
            self.show_customer_dashboard(result)
        else:
            self.login_message_label.configure(text=result, text_color="#E74C3C")

    # --------------------------------------------------
    # PANEL DEL CLIENTE
    # --------------------------------------------------

    def show_customer_dashboard(self, customer):
        self.current_customer = customer
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=40, pady=40)

        ctk.CTkLabel(
            frame,
            text=f"¡Hola, {customer['full_name']}!",
            font=("Arial", 30, "bold"),
        ).pack(pady=(55, 15))

        ctk.CTkLabel(
            frame,
            text="Has iniciado sesión correctamente.",
            font=("Arial", 16),
        ).pack(pady=8)

        ctk.CTkLabel(
            frame,
            text=f"Correo: {customer['email']}\nTeléfono: {customer['phone']}",
            font=("Arial", 15),
            justify="left",
        ).pack(pady=18)

        ctk.CTkButton(
            frame,
            text="VER MENÚ DE PRODUCTOS",
            width=280,
            height=50,
            command=self.show_product_menu,
        ).pack(pady=12)

        ctk.CTkButton(
            frame,
            text=f"VER CARRITO ({self.cart.get_item_count()})",
            width=280,
            height=45,
            command=self.show_cart,
        ).pack(pady=8)

        ctk.CTkButton(
            frame,
            text="MIS PEDIDOS",
            width=280,
            height=45,
            command=self.show_customer_orders,
        ).pack(pady=8)

        ctk.CTkButton(
            frame,
            text="CERRAR SESIÓN",
            width=220,
            height=45,
            fg_color="#465363",
            hover_color="#34404E",
            command=self.logout_customer,
        ).pack(pady=18)

    # --------------------------------------------------
    # CATÁLOGO DE PRODUCTOS
    # --------------------------------------------------

    def show_product_menu(self, message=""):
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=25, pady=18)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(
            header,
            text="NUESTRO MENÚ",
            font=("Arial", 30, "bold"),
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            header,
            text=f"VER CARRITO ({self.cart.get_item_count()} productos)",
            width=235,
            height=42,
            font=("Arial", 14, "bold"),
            command=self.show_cart,
        ).pack(side="right", padx=8)

        ctk.CTkLabel(
            frame,
            text="Consulta los productos disponibles",
            font=("Arial", 15),
        ).pack(pady=(0, 5))

        if message:
            self.show_message(frame, message, "#2ECC71")

        products_frame = ctk.CTkScrollableFrame(frame, height=430)
        products_frame.pack(expand=True, fill="both", padx=8, pady=8)
        products_frame.grid_columnconfigure(0, weight=1)
        products_frame.grid_columnconfigure(1, weight=1)

        try:
            products = get_available_products()
            if not products:
                ctk.CTkLabel(
                    products_frame,
                    text="No hay productos disponibles.",
                    font=("Arial", 16),
                ).pack(pady=30)
            else:
                for index, product in enumerate(products):
                    card = ctk.CTkFrame(products_frame)
                    card.grid(
                        row=index // 2,
                        column=index % 2,
                        padx=10,
                        pady=10,
                        sticky="nsew",
                    )

                    ctk.CTkLabel(
                        card,
                        text=product["category_name"],
                        font=("Arial", 12),
                        text_color="#3498DB",
                    ).pack(pady=(14, 4))

                    ctk.CTkLabel(
                        card,
                        text=product["name"],
                        font=("Arial", 18, "bold"),
                        wraplength=260,
                    ).pack(pady=4)

                    ctk.CTkLabel(
                        card,
                        text=product["description"] or "Sin descripción",
                        font=("Arial", 13),
                        wraplength=260,
                    ).pack(pady=4)

                    ctk.CTkLabel(
                        card,
                        text=self.format_currency(product["price"]),
                        font=("Arial", 18, "bold"),
                        text_color="#2ECC71",
                    ).pack(pady=(5, 8))

                    ctk.CTkButton(
                        card,
                        text="AGREGAR AL CARRITO",
                        width=190,
                        command=lambda selected_product=product: self.add_product_to_cart(
                            selected_product
                        ),
                    ).pack(pady=(4, 14))
        except Exception as error:
            ctk.CTkLabel(
                products_frame,
                text=f"No fue posible cargar los productos: {error}",
                text_color="#E74C3C",
                wraplength=600,
            ).pack(pady=30)

        # Barra inferior fija: permite acceder al carrito aunque el catálogo
        # tenga muchos productos y el cliente haya desplazado la lista.
        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x", pady=(5, 2))

        ctk.CTkButton(
            footer,
            text=f"🛒 ABRIR CARRITO ({self.cart.get_item_count()})",
            width=250,
            height=46,
            font=("Arial", 14, "bold"),
            command=self.show_cart,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            footer,
            text="VOLVER AL PANEL",
            width=220,
            height=46,
            fg_color="transparent",
            border_width=1,
            command=lambda: self.show_customer_dashboard(self.current_customer),
        ).pack(side="right", padx=8)

    def add_product_to_cart(self, product):
        """Agrega al carrito un producto seleccionado del catálogo."""
        try:
            self.cart.add_product(product)
        except (KeyError, TypeError, ValueError) as error:
            self.show_product_menu(f"No se pudo agregar el producto: {error}")
            return

        self.show_product_menu(f"{product['name']} se agregó al carrito.")

    # --------------------------------------------------
    # CARRITO DE COMPRAS
    # --------------------------------------------------

    def show_cart(self, message=""):
        self.clear_screen()

        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=20)

        ctk.CTkLabel(
            frame,
            text="MI CARRITO",
            font=("Arial", 30, "bold"),
        ).pack(pady=(5, 8))

        if message:
            self.show_message(frame, message, "#2ECC71")

        if self.cart.is_empty():
            ctk.CTkLabel(
                frame,
                text="Tu carrito está vacío.",
                font=("Arial", 17),
            ).pack(pady=35)
        else:
            items_frame = ctk.CTkScrollableFrame(frame, height=390)
            items_frame.pack(expand=True, fill="both", padx=8, pady=8)
            items_frame.grid_columnconfigure(0, weight=1)

            for row_index, item in enumerate(self.cart.get_items()):
                product_frame = ctk.CTkFrame(items_frame)
                product_frame.grid(
                    row=row_index,
                    column=0,
                    sticky="ew",
                    padx=5,
                    pady=6,
                )
                product_frame.grid_columnconfigure(0, weight=1)

                details_frame = ctk.CTkFrame(product_frame, fg_color="transparent")
                details_frame.grid(row=0, column=0, sticky="w", padx=12, pady=10)

                ctk.CTkLabel(
                    details_frame,
                    text=item["name"],
                    font=("Arial", 16, "bold"),
                ).pack(anchor="w")

                ctk.CTkLabel(
                    details_frame,
                    text=(
                        f"Precio unitario: {self.format_currency(item['price'])}"
                        f"   |   Subtotal: {self.format_currency(item['price'] * item['quantity'])}"
                    ),
                    font=("Arial", 12),
                ).pack(anchor="w", pady=(3, 0))

                controls = ctk.CTkFrame(product_frame, fg_color="transparent")
                controls.grid(row=0, column=1, sticky="e", padx=10, pady=10)

                ctk.CTkButton(
                    controls,
                    text="−",
                    width=34,
                    command=lambda product_id=item["product_id"]: self.decrease_cart_quantity(
                        product_id
                    ),
                ).pack(side="left", padx=3)

                ctk.CTkLabel(
                    controls,
                    text=str(item["quantity"]),
                    width=28,
                    font=("Arial", 15, "bold"),
                ).pack(side="left", padx=3)

                ctk.CTkButton(
                    controls,
                    text="+",
                    width=34,
                    command=lambda product_id=item["product_id"]: self.increase_cart_quantity(
                        product_id
                    ),
                ).pack(side="left", padx=3)

                ctk.CTkButton(
                    controls,
                    text="Eliminar",
                    width=75,
                    fg_color="#A93226",
                    hover_color="#922B21",
                    command=lambda product_id=item["product_id"]: self.remove_cart_product(
                        product_id
                    ),
                ).pack(side="left", padx=5)

        summary_frame = ctk.CTkFrame(frame, fg_color="transparent")
        summary_frame.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            summary_frame,
            text=f"Unidades: {self.cart.get_item_count()}",
            font=("Arial", 14),
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            summary_frame,
            text=f"TOTAL: {self.format_currency(self.cart.get_total())}",
            font=("Arial", 20, "bold"),
            text_color="#2ECC71",
        ).pack(side="right", padx=8)

        buttons_frame = ctk.CTkFrame(frame, fg_color="transparent")
        buttons_frame.pack(pady=8)

        ctk.CTkButton(
            buttons_frame,
            text="SEGUIR COMPRANDO",
            width=190,
            command=self.show_product_menu,
        ).grid(row=0, column=0, padx=6, pady=5)

        if not self.cart.is_empty():
            ctk.CTkButton(
                buttons_frame,
                text="VACIAR CARRITO",
                width=160,
                fg_color="#A93226",
                hover_color="#922B21",
                command=self.clear_cart,
            ).grid(row=0, column=1, padx=6, pady=5)

        if not self.cart.is_empty():
            ctk.CTkButton(
                frame,
                text="CONTINUAR CON EL PEDIDO",
                width=280,
                height=48,
                font=("Arial", 14, "bold"),
                command=self.show_order_type_selection,
            ).pack(pady=(8, 5))

        ctk.CTkButton(
            frame,
            text="VOLVER AL PANEL",
            width=190,
            fg_color="transparent",
            border_width=1,
            command=lambda: self.show_customer_dashboard(self.current_customer),
        ).pack(pady=5)

        if not self.cart.is_empty():
            ctk.CTkLabel(
                frame,
                text="La confirmación y creación de pedidos se incorporará en el siguiente incremento.",
                font=("Arial", 11),
                text_color="gray",
                wraplength=650,
            ).pack(pady=(3, 0))

    def increase_cart_quantity(self, product_id):
        """Aumenta en una unidad la cantidad de un producto."""
        for item in self.cart.get_items():
            if item["product_id"] == product_id:
                self.cart.update_quantity(product_id, item["quantity"] + 1)
                break
        self.show_cart()

    def decrease_cart_quantity(self, product_id):
        """Disminuye una unidad; si llega a cero, elimina el producto."""
        for item in self.cart.get_items():
            if item["product_id"] == product_id:
                if item["quantity"] == 1:
                    self.cart.remove_product(product_id)
                else:
                    self.cart.update_quantity(product_id, item["quantity"] - 1)
                break
        self.show_cart()

    def remove_cart_product(self, product_id):
        """Elimina una línea completa del carrito."""
        self.cart.remove_product(product_id)
        self.show_cart("Producto eliminado del carrito.")

    def clear_cart(self):
        """Vacía el carrito después de la acción del cliente."""
        self.cart.clear()
        self.show_cart("El carrito se vació correctamente.")

    # --------------------------------------------------
    # INCREMENTO 5: CREACIÓN Y CONSULTA DE PEDIDOS
    # --------------------------------------------------

    def show_order_type_selection(self):
        """Permite elegir entre domicilio y consumo en restaurante."""
        if self.cart.is_empty():
            self.show_cart("Agrega al menos un producto antes de continuar.")
            return

        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=35, pady=30)

        ctk.CTkLabel(
            frame,
            text="¿CÓMO DESEAS RECIBIR TU PEDIDO?",
            font=("Arial", 26, "bold"),
            wraplength=760,
        ).pack(pady=(45, 15))

        ctk.CTkLabel(
            frame,
            text=f"Total de tu compra: {self.format_currency(self.cart.get_total())}",
            font=("Arial", 19, "bold"),
            text_color="#2ECC71",
        ).pack(pady=12)

        options = ctk.CTkFrame(frame, fg_color="transparent")
        options.pack(pady=30)

        ctk.CTkButton(
            options,
            text="PEDIDO A DOMICILIO",
            width=260,
            height=90,
            font=("Arial", 17, "bold"),
            command=lambda: self.show_order_checkout("delivery"),
        ).grid(row=0, column=0, padx=12, pady=10)

        ctk.CTkButton(
            options,
            text="CONSUMIR EN RESTAURANTE",
            width=260,
            height=90,
            font=("Arial", 16, "bold"),
            fg_color="#465363",
            hover_color="#34404E",
            command=lambda: self.show_order_checkout("dine_in"),
        ).grid(row=0, column=1, padx=12, pady=10)

        ctk.CTkLabel(
            frame,
            text=(
                "El pago se realizará en efectivo.\n"
                "Para consumir en el restaurante, nuestro personal te asignará una mesa disponible."
            ),
            font=("Arial", 13),
            text_color="gray",
            justify="center",
            wraplength=700,
        ).pack(pady=15)

        ctk.CTkButton(
            frame,
            text="VOLVER AL CARRITO",
            width=210,
            fg_color="transparent",
            border_width=1,
            command=self.show_cart,
        ).pack(pady=20)

    def show_order_checkout(self, order_type):
        """Muestra los datos necesarios para confirmar un pedido."""
        if self.cart.is_empty():
            self.show_cart("Tu carrito está vacío.")
            return

        self.checkout_order_type = order_type
        self.clear_screen()

        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=35, pady=20)

        title = "DATOS DEL DOMICILIO" if order_type == "delivery" else "PEDIDO EN RESTAURANTE"
        ctk.CTkLabel(
            frame,
            text=title,
            font=("Arial", 28, "bold"),
        ).pack(pady=(12, 8))

        ctk.CTkLabel(
            frame,
            text="Resumen de tu compra",
            font=("Arial", 16, "bold"),
        ).pack(pady=(10, 5))

        for item in self.cart.get_items():
            line_total = item["price"] * item["quantity"]
            ctk.CTkLabel(
                frame,
                text=(
                    f'{item["quantity"]} x {item["name"]}  —  '
                    f'{self.format_currency(line_total)}'
                ),
                font=("Arial", 13),
            ).pack(pady=2)

        ctk.CTkLabel(
            frame,
            text=f"TOTAL: {self.format_currency(self.cart.get_total())}",
            font=("Arial", 21, "bold"),
            text_color="#2ECC71",
        ).pack(pady=12)

        self.delivery_address_entry = None
        if order_type == "delivery":
            ctk.CTkLabel(
                frame,
                text="Dirección de entrega (obligatoria)",
                font=("Arial", 13, "bold"),
            ).pack(pady=(10, 4))
            self.delivery_address_entry = ctk.CTkEntry(
                frame,
                width=420,
                height=42,
                placeholder_text="Ej. Calle 10 # 20-30, barrio...",
            )
            self.delivery_address_entry.pack(pady=5)
        else:
            ctk.CTkLabel(
                frame,
                text=(
                    "El pedido quedará pendiente de aceptación.\n"
                    "Un empleado te asignará una mesa disponible."
                ),
                font=("Arial", 13),
                text_color="gray",
                justify="center",
            ).pack(pady=10)

        ctk.CTkLabel(
            frame,
            text="Indicaciones adicionales (opcional)",
            font=("Arial", 13, "bold"),
        ).pack(pady=(12, 4))

        self.order_notes_textbox = ctk.CTkTextbox(
            frame,
            width=420,
            height=75,
        )
        self.order_notes_textbox.pack(pady=5)

        ctk.CTkLabel(
            frame,
            text="Método de pago: efectivo. El pago quedará pendiente hasta que sea recibido.",
            font=("Arial", 12),
            text_color="gray",
            wraplength=650,
        ).pack(pady=10)

        self.checkout_message_label = self.show_message(frame, "")

        ctk.CTkButton(
            frame,
            text="CONFIRMAR PEDIDO",
            width=280,
            height=48,
            font=("Arial", 15, "bold"),
            command=lambda: self.place_customer_order_action(order_type),
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="VOLVER",
            width=190,
            fg_color="transparent",
            border_width=1,
            command=self.show_order_type_selection,
        ).pack(pady=8)

    def place_customer_order_action(self, order_type):
        """Valida el formulario y solicita la creación transaccional del pedido."""
        address = (
            self.delivery_address_entry.get().strip()
            if order_type == "delivery" and self.delivery_address_entry
            else ""
        )
        notes = self.order_notes_textbox.get("1.0", "end").strip()
        order_total = self.cart.get_total()

        try:
            order_id = self.order_service.place_customer_order(
                customer=self.current_customer,
                order_type=order_type,
                cart_items=self.cart.get_items(),
                delivery_address=address,
                customer_notes=notes,
            )
        except ValueError as error:
            self.checkout_message_label.configure(
                text=str(error),
                text_color="#E74C3C",
            )
            return
        except sqlite3.Error as error:
            self.checkout_message_label.configure(
                text=f"No fue posible guardar el pedido: {error}",
                text_color="#E74C3C",
            )
            return

        self.cart.clear()
        self.show_order_confirmation(order_id, order_type, order_total)

    def show_order_confirmation(self, order_id, order_type, total):
        """Confirma al cliente que el pedido quedó guardado."""
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=35, pady=35)

        ctk.CTkLabel(
            frame,
            text="¡PEDIDO REGISTRADO!",
            font=("Arial", 30, "bold"),
            text_color="#2ECC71",
        ).pack(pady=(55, 15))

        order_type_label = "Domicilio" if order_type == "delivery" else "Consumo en restaurante"
        ctk.CTkLabel(
            frame,
            text=(
                f"Número de pedido: #{order_id}\n"
                f"Modalidad: {order_type_label}\n"
                f"Total: {self.format_currency(total)}\n"
                "Estado: Pendiente de aceptación\n"
                "Pago: Efectivo — pendiente"
            ),
            font=("Arial", 16),
            justify="left",
        ).pack(pady=20)

        extra_message = (
            "El domicilio está pendiente de asignación por el administrador."
            if order_type == "delivery"
            else "El personal del restaurante asignará una mesa disponible."
        )
        ctk.CTkLabel(
            frame,
            text=extra_message,
            font=("Arial", 13),
            text_color="gray",
            wraplength=650,
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="VER MIS PEDIDOS",
            width=240,
            height=45,
            command=self.show_customer_orders,
        ).pack(pady=10)

        ctk.CTkButton(
            frame,
            text="VOLVER AL PANEL",
            width=220,
            fg_color="transparent",
            border_width=1,
            command=lambda: self.show_customer_dashboard(self.current_customer),
        ).pack(pady=8)

    def show_customer_orders(self):
        """Muestra el historial de pedidos del cliente autenticado."""
        if not self.current_customer:
            self.show_customer_portal("Inicia sesión para consultar tus pedidos.", "#E74C3C")
            return

        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=20)

        ctk.CTkLabel(
            frame,
            text="MIS PEDIDOS",
            font=("Arial", 30, "bold"),
        ).pack(pady=(5, 12))

        orders = self.order_service.list_customer_orders(self.current_customer["customer_id"])
        if not orders:
            ctk.CTkLabel(
                frame,
                text="Todavía no tienes pedidos registrados.",
                font=("Arial", 16),
            ).pack(pady=35)
        else:
            list_frame = ctk.CTkScrollableFrame(frame, height=440)
            list_frame.pack(expand=True, fill="both", padx=8, pady=8)

            status_labels = {
                "pending": "Pendiente",
                "accepted": "Aceptado",
                "preparing": "En preparación",
                "ready": "Listo",
                "completed": "Completado",
                "cancelled": "Cancelado",
            }
            payment_labels = {"pending": "Pendiente", "paid": "Pagado", "refunded": "Reembolsado"}

            for index, order in enumerate(orders):
                card = ctk.CTkFrame(list_frame)
                card.grid(row=index, column=0, sticky="ew", padx=6, pady=6)
                card.grid_columnconfigure(0, weight=1)

                order_type_label = "Domicilio" if order["order_type"] == "delivery" else "En restaurante"
                summary = (
                    f'Pedido #{order["order_id"]}  |  {order_type_label}\n'
                    f'Fecha: {order["created_at"]}\n'
                    f'Estado: {status_labels.get(order["status"], order["status"])}\n'
                    f'Total: {self.format_currency(order["total"])}  |  '
                    f'Pago: {payment_labels.get(order["payment_status"], order["payment_status"])}'
                )
                ctk.CTkLabel(
                    card,
                    text=summary,
                    font=("Arial", 13),
                    justify="left",
                ).grid(row=0, column=0, sticky="w", padx=12, pady=10)

                ctk.CTkButton(
                    card,
                    text="VER DETALLE",
                    width=125,
                    command=lambda selected_id=order["order_id"]: self.show_customer_order_details(selected_id),
                ).grid(row=0, column=1, padx=12, pady=10)

        ctk.CTkButton(
            frame,
            text="VOLVER AL PANEL",
            width=210,
            fg_color="transparent",
            border_width=1,
            command=lambda: self.show_customer_dashboard(self.current_customer),
        ).pack(pady=10)

    def show_customer_order_details(self, order_id):
        """Muestra el detalle de un pedido perteneciente al cliente actual."""
        details = self.order_service.get_customer_order(
            self.current_customer["customer_id"],
            order_id,
        )
        if details is None:
            self.show_customer_orders()
            return

        self.clear_screen()
        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=35, pady=20)

        status_labels = {
            "pending": "Pendiente",
            "accepted": "Aceptado",
            "preparing": "En preparación",
            "ready": "Listo",
            "completed": "Completado",
            "cancelled": "Cancelado",
        }
        payment_labels = {"pending": "Pendiente", "paid": "Pagado", "refunded": "Reembolsado"}
        delivery_labels = {"pending": "Pendiente de asignación", "assigned": "Repartidor asignado", "picked_up": "En camino", "delivered": "Entregado"}

        ctk.CTkLabel(
            frame,
            text=f'DETALLE DEL PEDIDO #{details["order_id"]}',
            font=("Arial", 26, "bold"),
        ).pack(pady=(10, 15))

        order_type_label = "Domicilio" if details["order_type"] == "delivery" else "Consumo en restaurante"
        information = (
            f"Modalidad: {order_type_label}\n"
            f"Fecha: {details['created_at']}\n"
            f"Estado: {status_labels.get(details['status'], details['status'])}\n"
            f"Método de pago: Efectivo\n"
            f"Estado del pago: {payment_labels.get(details['payment_status'], details['payment_status'])}"
        )
        if details["order_type"] == "delivery":
            information += (
                f'\nDirección: {details["delivery_address"]}'
                f'\nEntrega: {delivery_labels.get(details["delivery_status"], details["delivery_status"])}'
            )
        if details["customer_notes"]:
            information += f'\nIndicaciones: {details["customer_notes"]}'

        ctk.CTkLabel(
            frame,
            text=information,
            font=("Arial", 14),
            justify="left",
        ).pack(anchor="w", padx=12, pady=10)

        ctk.CTkLabel(
            frame,
            text="Productos del pedido",
            font=("Arial", 17, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 5))

        for item in details["items"]:
            ctk.CTkLabel(
                frame,
                text=(
                    f'{item["quantity"]} x {item["product_name"]}  |  '
                    f'{self.format_currency(item["unit_price"])} c/u  |  '
                    f'{self.format_currency(item["subtotal"])}'
                ),
                font=("Arial", 13),
            ).pack(anchor="w", padx=18, pady=3)

        ctk.CTkLabel(
            frame,
            text=f'TOTAL: {self.format_currency(details["total"])}',
            font=("Arial", 21, "bold"),
            text_color="#2ECC71",
        ).pack(anchor="e", padx=15, pady=18)

        ctk.CTkButton(
            frame,
            text="VOLVER A MIS PEDIDOS",
            width=220,
            command=self.show_customer_orders,
        ).pack(pady=15)

    def logout_customer(self):
        """Cierra la sesión y elimina los artículos temporales del carrito."""
        self.current_customer = None
        self.cart.clear()
        self.show_welcome()

    # --------------------------------------------------
    # PORTAL DEL EQUIPO Y CONFIGURACIÓN DEL ADMINISTRADOR
    # --------------------------------------------------

    def show_team_portal(self):
        """Muestra el primer registro de administrador o el acceso del equipo."""
        if has_admin_account():
            self.show_employee_login()
        else:
            self.show_initial_admin_setup()

    def show_initial_admin_setup(self):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=22)

        ctk.CTkLabel(
            frame, text="CONFIGURACIÓN INICIAL",
            font=("Arial", 28, "bold"),
        ).pack(pady=(10, 6))
        ctk.CTkLabel(
            frame,
            text="Crea la primera cuenta administradora del restaurante.",
            font=("Arial", 14),
        ).pack(pady=(0, 12))

        self.admin_name_entry = ctk.CTkEntry(frame, width=360, placeholder_text="Nombre completo")
        self.admin_name_entry.pack(pady=6)
        self.admin_email_entry = ctk.CTkEntry(frame, width=360, placeholder_text="Correo electrónico")
        self.admin_email_entry.pack(pady=6)
        self.admin_phone_entry = ctk.CTkEntry(frame, width=360, placeholder_text="Teléfono")
        self.admin_phone_entry.pack(pady=6)
        self.admin_password_entry = ctk.CTkEntry(
            frame, width=360, placeholder_text="Contraseña (mínimo 8 caracteres)", show="*"
        )
        self.admin_password_entry.pack(pady=6)
        self.admin_confirm_entry = ctk.CTkEntry(
            frame, width=360, placeholder_text="Confirmar contraseña", show="*"
        )
        self.admin_confirm_entry.pack(pady=6)
        self.admin_setup_message = ctk.CTkLabel(frame, text="", font=("Arial", 12))
        self.admin_setup_message.pack(pady=6)

        ctk.CTkButton(
            frame, text="CREAR ADMINISTRADOR", width=260, height=44,
            command=self.create_initial_admin_action,
        ).pack(pady=8)
        ctk.CTkButton(
            frame, text="VOLVER", width=180, fg_color="transparent", border_width=1,
            command=self.show_welcome,
        ).pack(pady=5)

    def create_initial_admin_action(self):
        name = self.admin_name_entry.get().strip()
        email = self.admin_email_entry.get().strip()
        phone = self.admin_phone_entry.get().strip()
        password = self.admin_password_entry.get()
        confirmation = self.admin_confirm_entry.get()

        if not all((name, email, phone, password, confirmation)):
            self.admin_setup_message.configure(
                text="Completa todos los campos.", text_color="#E74C3C"
            )
            return
        if "@" not in email or "." not in email:
            self.admin_setup_message.configure(
                text="Ingresa un correo electrónico válido.", text_color="#E74C3C"
            )
            return
        if password != confirmation:
            self.admin_setup_message.configure(
                text="Las contraseñas no coinciden.", text_color="#E74C3C"
            )
            return
        try:
            create_initial_admin(name, email, phone, password)
            self.show_employee_login("Administrador creado. Ahora inicia sesión.")
        except (ValueError, sqlite3.Error) as error:
            self.admin_setup_message.configure(text=str(error), text_color="#E74C3C")

    # --------------------------------------------------
    # AUTENTICACIÓN DEL EQUIPO
    # --------------------------------------------------

    def show_employee_login(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=30, pady=35)

        ctk.CTkLabel(frame, text="ACCESO DEL EQUIPO", font=("Arial", 30, "bold")).pack(pady=(35, 15))
        ctk.CTkLabel(
            frame, text="Ingresa con las credenciales asignadas por administración.",
            font=("Arial", 14),
        ).pack(pady=5)

        self.employee_email_entry = ctk.CTkEntry(
            frame, width=350, height=42, placeholder_text="Correo electrónico"
        )
        self.employee_email_entry.pack(pady=8)
        self.employee_password_entry = ctk.CTkEntry(
            frame, width=350, height=42, placeholder_text="Contraseña", show="*"
        )
        self.employee_password_entry.pack(pady=8)
        self.employee_login_message = ctk.CTkLabel(frame, text=message, font=("Arial", 12))
        self.employee_login_message.pack(pady=8)

        ctk.CTkButton(
            frame, text="INGRESAR", width=240, height=44,
            command=self.login_employee_action,
        ).pack(pady=10)
        ctk.CTkButton(
            frame, text="VOLVER AL INICIO", width=200,
            fg_color="transparent", border_width=1, command=self.show_welcome,
        ).pack(pady=8)

    def login_employee_action(self):
        email = self.employee_email_entry.get().strip()
        password = self.employee_password_entry.get()
        if not email or not password:
            self.employee_login_message.configure(
                text="Ingresa el correo y la contraseña.", text_color="#E74C3C"
            )
            return
        success, result = authenticate_employee(email, password)
        if not success:
            self.employee_login_message.configure(text=result, text_color="#E74C3C")
            return
        self.current_employee = result
        self.show_employee_dashboard()

    def show_employee_dashboard(self, message=""):
        if not self.current_employee:
            self.show_employee_login()
            return
        role = self.current_employee["role"]
        if role == "admin":
            self.show_admin_dashboard(message)
        elif role == "kitchen":
            self.show_kitchen_dashboard(message)
        elif role == "courier":
            self.show_courier_dashboard(message)
        else:
            self.logout_employee()

    def add_employee_shift_controls(self, parent):
        """Muestra el estado del turno y permite abrirlo o cerrarlo."""
        if not self.current_employee:
            return
        shift = get_current_employee_shift(self.current_employee["employee_id"])
        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", padx=6, pady=(0, 8))
        if shift:
            label_text = f"Turno activo desde: {shift['started_at']}"
            button_text = "FINALIZAR TURNO"
        else:
            label_text = "No tienes un turno abierto."
            button_text = "INICIAR TURNO"
        ctk.CTkLabel(controls, text=label_text, font=("Arial", 12)).pack(side="left")
        ctk.CTkButton(
            controls,
            text=button_text,
            width=150,
            height=32,
            command=self.toggle_employee_shift_action,
        ).pack(side="right")

    def toggle_employee_shift_action(self):
        if not self.current_employee:
            return
        employee_id = self.current_employee["employee_id"]
        try:
            current_shift = get_current_employee_shift(employee_id)
            if current_shift:
                end_employee_shift(employee_id)
                message = "Turno finalizado correctamente."
            else:
                start_employee_shift(employee_id)
                message = "Turno iniciado correctamente."
            self.show_employee_dashboard(message)
        except (ValueError, sqlite3.Error) as error:
            self.show_employee_dashboard(f"No se pudo actualizar el turno: {error}")

    def logout_employee(self):
        if self.current_employee:
            try:
                active_shift = get_current_employee_shift(self.current_employee["employee_id"])
            except sqlite3.Error as error:
                self.show_employee_dashboard(f"No se pudo comprobar el turno: {error}")
                return
            if active_shift:
                self.show_employee_dashboard("Finaliza tu turno antes de cerrar sesión.")
                return
        self.current_employee = None
        self.show_welcome()

    # --------------------------------------------------
    # NAVEGACIÓN ADMINISTRATIVA
    # --------------------------------------------------

    def add_admin_navigation(self, parent, title):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            header,
            text=title,
            font=("Arial", 25, "bold"),
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            header,
            text=f"Administrador: {self.current_employee['full_name']}",
            font=("Arial", 12),
        ).pack(side="right", padx=5)

        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 10))
        buttons = [
            ("Pendientes", self.show_admin_dashboard),
            ("Activos", self.show_admin_active_orders),
            ("Mesas", self.show_table_management),
            ("Inventario", self.show_inventory_management),
            ("Personal", self.show_staff_management),
            ("Productos", self.show_product_management),
            ("Pagos", self.show_payment_management),
            ("Turnos", self.show_shift_management),
            ("Reportes", self.show_admin_reports),
        ]
        for index, (label, callback) in enumerate(buttons):
            ctk.CTkButton(
                nav,
                text=label,
                width=135,
                height=32,
                command=callback,
            ).grid(row=index // 5, column=index % 5, padx=3, pady=3, sticky="ew")
        for column in range(5):
            nav.grid_columnconfigure(column, weight=1)
        ctk.CTkButton(
            nav,
            text="Cerrar sesión",
            width=135,
            height=32,
            fg_color="#465363",
            hover_color="#34404E",
            command=self.logout_employee,
        ).grid(row=1, column=4, padx=3, pady=3, sticky="ew")
        self.add_employee_shift_controls(parent)

    def show_admin_dashboard(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "PEDIDOS PENDIENTES")
        if message:
            self.show_message(frame, message, "#2ECC71")

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=4, pady=4)
        orders = get_pending_orders()
        if not orders:
            ctk.CTkLabel(scroll, text="No hay pedidos pendientes de aceptación.", font=("Arial", 16)).pack(pady=35)
            return

        available_tables = list_restaurant_tables(available_only=True)
        couriers = list_active_couriers()
        for order in orders:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=8)
            mode = "Domicilio" if order["order_type"] == "delivery" else "Consumo en restaurante"
            ctk.CTkLabel(
                card,
                text=f"Pedido #{order['order_id']} · {order['customer_name']} · {mode} · {self.format_currency(order['total'])}",
                font=("Arial", 15, "bold"), wraplength=850,
            ).pack(anchor="w", padx=12, pady=(10, 4))
            if order["order_type"] == "delivery":
                ctk.CTkLabel(
                    card, text=f"Dirección: {order['delivery_address']}", font=("Arial", 13)
                ).pack(anchor="w", padx=12, pady=2)
                courier_values = [f"{item['employee_id']} | {item['full_name']}" for item in couriers]
                if courier_values:
                    selector = ctk.CTkOptionMenu(card, values=courier_values, width=260)
                    selector.pack(anchor="w", padx=12, pady=6)
                    enabled = True
                else:
                    selector = None
                    ctk.CTkLabel(card, text="Primero debes crear una cuenta de repartidor.", text_color="#E0A030").pack(anchor="w", padx=12, pady=6)
                    enabled = False
                ctk.CTkButton(
                    card, text="ACEPTAR Y ASIGNAR REPARTIDOR", width=260,
                    state="normal" if enabled else "disabled",
                    command=lambda oid=order["order_id"], widget=selector: self.accept_delivery_order_action(oid, widget),
                ).pack(anchor="w", padx=12, pady=(4, 10))
            else:
                table_values = [
                    f"{item['table_id']} | Mesa {item['table_number']} · {item['capacity']} puestos"
                    for item in available_tables
                ]
                if table_values:
                    selector = ctk.CTkOptionMenu(card, values=table_values, width=300)
                    selector.pack(anchor="w", padx=12, pady=6)
                    enabled = True
                else:
                    selector = None
                    ctk.CTkLabel(card, text="No hay mesas disponibles. Registra o libera una mesa.", text_color="#E0A030").pack(anchor="w", padx=12, pady=6)
                    enabled = False
                ctk.CTkButton(
                    card, text="ACEPTAR Y ASIGNAR MESA", width=250,
                    state="normal" if enabled else "disabled",
                    command=lambda oid=order["order_id"], widget=selector: self.accept_dine_in_order_action(oid, widget),
                ).pack(anchor="w", padx=12, pady=(4, 10))
            ctk.CTkButton(
                card, text="CANCELAR PEDIDO", width=170,
                fg_color="#8C3030", hover_color="#6E2424",
                command=lambda oid=order["order_id"]: self.cancel_order_action(oid),
            ).pack(anchor="e", padx=12, pady=(0, 10))

    def accept_dine_in_order_action(self, order_id, selector):
        try:
            if selector is None:
                raise ValueError("No hay una mesa disponible para asignar.")
            table_id = int(selector.get().split("|", 1)[0].strip())
            accept_order(order_id, self.current_employee["employee_id"], table_id=table_id)
            self.show_admin_dashboard(f"Pedido #{order_id} aceptado y mesa asignada. Inventario actualizado.")
        except (ValueError, sqlite3.Error) as error:
            self.show_admin_dashboard(f"No se pudo aceptar el pedido: {error}")

    def accept_delivery_order_action(self, order_id, selector):
        try:
            if selector is None:
                raise ValueError("No hay un repartidor activo para asignar.")
            courier_id = int(selector.get().split("|", 1)[0].strip())
            accept_order(order_id, self.current_employee["employee_id"], courier_id=courier_id)
            self.show_admin_dashboard(f"Pedido #{order_id} aceptado y repartidor asignado. Inventario actualizado.")
        except (ValueError, sqlite3.Error) as error:
            self.show_admin_dashboard(f"No se pudo aceptar el pedido: {error}")

    def cancel_order_action(self, order_id):
        dialog = ctk.CTkInputDialog(
            text=f"Indica el motivo para cancelar el pedido #{order_id}:",
            title="Cancelar pedido",
        )
        reason = dialog.get_input()
        if not reason:
            return
        try:
            cancel_order(order_id, self.current_employee["employee_id"], reason)
            self.show_admin_dashboard(f"Pedido #{order_id} cancelado. Se registró el motivo.")
        except (ValueError, sqlite3.Error) as error:
            self.show_admin_dashboard(f"No se pudo cancelar: {error}")

    def show_admin_active_orders(self):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "PEDIDOS ACTIVOS")
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=4, pady=4)
        orders = get_admin_active_orders()
        if not orders:
            ctk.CTkLabel(scroll, text="No hay pedidos activos.", font=("Arial", 16)).pack(pady=35)
            return
        labels = {"accepted": "Aceptado", "preparing": "En preparación", "ready": "Listo"}
        for order in orders:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=7)
            mode = "Domicilio" if order["order_type"] == "delivery" else f"Mesa {order['table_number']}"
            details = f"Pedido #{order['order_id']} · {order['customer_name']} · {mode} · {labels[order['status']]} · {self.format_currency(order['total'])}"
            ctk.CTkLabel(card, text=details, font=("Arial", 14, "bold"), wraplength=850).pack(anchor="w", padx=12, pady=10)
            if order["status"] == "ready" and order["order_type"] == "dine_in":
                ctk.CTkButton(
                    card, text="FINALIZAR SERVICIO Y LIBERAR MESA", width=300,
                    command=lambda oid=order["order_id"]: self.complete_dine_in_order_action(oid),
                ).pack(anchor="w", padx=12, pady=(0, 10))
            if order["status"] == "accepted":
                ctk.CTkButton(
                    card, text="CANCELAR PEDIDO", width=180,
                    fg_color="#8C3030", hover_color="#6E2424",
                    command=lambda oid=order["order_id"]: self.cancel_order_action(oid),
                ).pack(anchor="w", padx=12, pady=(0, 10))

    def complete_dine_in_order_action(self, order_id):
        try:
            complete_dine_in_order(order_id, self.current_employee["employee_id"])
            self.show_admin_active_orders()
        except (ValueError, sqlite3.Error) as error:
            self.show_admin_active_orders()
            self.show_message(self.main_container, str(error), "#E74C3C")

    # --------------------------------------------------
    # ADMINISTRACIÓN DE MESAS E INVENTARIO
    # --------------------------------------------------

    def show_table_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=25, pady=18)
        self.add_admin_navigation(frame, "GESTIÓN DE MESAS")
        if message:
            self.show_message(frame, message, "#2ECC71")

        form = ctk.CTkFrame(frame)
        form.pack(fill="x", padx=5, pady=8)
        self.table_number_entry = ctk.CTkEntry(form, width=190, placeholder_text="Número o nombre de mesa")
        self.table_number_entry.pack(side="left", padx=8, pady=10)
        self.table_capacity_entry = ctk.CTkEntry(form, width=150, placeholder_text="Capacidad")
        self.table_capacity_entry.pack(side="left", padx=8, pady=10)
        ctk.CTkButton(
            form, text="AGREGAR MESA", command=self.add_table_action
        ).pack(side="left", padx=8, pady=10)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=8)
        tables = list_restaurant_tables()
        if not tables:
            ctk.CTkLabel(scroll, text="Todavía no hay mesas registradas.").pack(pady=20)
        for table in tables:
            status = {"available": "Disponible", "occupied": "Ocupada", "maintenance": "Mantenimiento"}.get(table["status"], table["status"])
            ctk.CTkLabel(
                scroll,
                text=f"Mesa {table['table_number']} · Capacidad: {table['capacity']} · Estado: {status}",
                font=("Arial", 14),
            ).pack(anchor="w", padx=12, pady=8)

    def add_table_action(self):
        try:
            add_restaurant_table(
                self.table_number_entry.get(),
                self.table_capacity_entry.get(),
                self.current_employee["employee_id"],
            )
            self.show_table_management("Mesa registrada correctamente.")
        except (ValueError, sqlite3.Error) as error:
            self.show_table_management(f"No se pudo registrar la mesa: {error}")

    def show_inventory_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "CONTROL DE INVENTARIO")
        ctk.CTkLabel(
            frame,
            text="Registra las existencias iniciales o ajusta el stock. La aceptación de pedidos descuenta unidades automáticamente.",
            font=("Arial", 12), wraplength=900,
        ).pack(anchor="w", padx=8, pady=(0, 8))
        if message:
            self.show_message(frame, message, "#2ECC71")
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=5)
        products = list_inventory_products()
        for product in products:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=7, pady=6)
            ctk.CTkLabel(
                card,
                text=f"{product['name']} · Stock actual: {product['stock_quantity']} · Mínimo: {product['minimum_stock']}",
                font=("Arial", 13, "bold"),
            ).pack(anchor="w", padx=10, pady=(8, 3))
            controls = ctk.CTkFrame(card, fg_color="transparent")
            controls.pack(anchor="w", padx=6, pady=(2, 8))
            quantity_entry = ctk.CTkEntry(controls, width=145, placeholder_text="Nueva existencia")
            quantity_entry.pack(side="left", padx=4)
            minimum_entry = ctk.CTkEntry(controls, width=135, placeholder_text="Stock mínimo")
            minimum_entry.pack(side="left", padx=4)
            ctk.CTkButton(
                controls, text="GUARDAR", width=110,
                command=lambda pid=product["product_id"], q=quantity_entry, m=minimum_entry: self.save_product_stock_action(pid, q, m),
            ).pack(side="left", padx=4)

    def save_product_stock_action(self, product_id, quantity_entry, minimum_entry):
        try:
            set_product_stock(
                product_id,
                quantity_entry.get(),
                minimum_entry.get() or 0,
                self.current_employee["employee_id"],
            )
            self.show_inventory_management("Existencias actualizadas y movimiento registrado.")
        except (ValueError, sqlite3.Error) as error:
            self.show_inventory_management(f"No se pudo actualizar el inventario: {error}")

    # --------------------------------------------------
    # ADMINISTRACIÓN DEL PERSONAL
    # --------------------------------------------------

    def show_staff_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=25, pady=18)
        self.add_admin_navigation(frame, "GESTIÓN DEL PERSONAL")
        if message:
            self.show_message(frame, message, "#2ECC71")

        form = ctk.CTkFrame(frame)
        form.pack(fill="x", padx=5, pady=8)
        self.staff_name_entry = ctk.CTkEntry(form, width=230, placeholder_text="Nombre completo")
        self.staff_name_entry.pack(padx=8, pady=5)
        self.staff_email_entry = ctk.CTkEntry(form, width=230, placeholder_text="Correo electrónico")
        self.staff_email_entry.pack(padx=8, pady=5)
        self.staff_phone_entry = ctk.CTkEntry(form, width=230, placeholder_text="Teléfono")
        self.staff_phone_entry.pack(padx=8, pady=5)
        self.staff_password_entry = ctk.CTkEntry(form, width=230, placeholder_text="Contraseña (mín. 8)", show="*")
        self.staff_password_entry.pack(padx=8, pady=5)
        self.staff_role_menu = ctk.CTkOptionMenu(form, values=["Cocina", "Repartidor"], width=230)
        self.staff_role_menu.pack(padx=8, pady=5)
        ctk.CTkButton(form, text="CREAR CUENTA DE EMPLEADO", command=self.create_staff_action).pack(padx=8, pady=10)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=8)
        employees = list_active_employees()
        role_names = {"admin": "Administrador", "kitchen": "Cocina", "courier": "Repartidor"}
        for employee in employees:
            employee_row = ctk.CTkFrame(scroll)
            employee_row.pack(fill="x", padx=8, pady=5)
            status = "Activo" if employee["is_active"] else "Inactivo"
            ctk.CTkLabel(
                employee_row,
                text=f"{employee['full_name']} · {employee['email']} · {role_names.get(employee['role'], employee['role'])} · {status}",
                font=("Arial", 12),
            ).pack(side="left", padx=10, pady=8)
            next_status = not bool(employee["is_active"])
            button_text = "DESACTIVAR" if employee["is_active"] else "REACTIVAR"
            is_self = employee["employee_id"] == self.current_employee["employee_id"]
            ctk.CTkButton(
                employee_row,
                text=button_text,
                width=115,
                state="disabled" if is_self else "normal",
                command=lambda eid=employee["employee_id"], active=next_status: self.set_employee_status_action(eid, active),
            ).pack(side="right", padx=8, pady=5)

    def set_employee_status_action(self, employee_id, is_active):
        try:
            set_employee_active_status(
                employee_id,
                is_active,
                self.current_employee["employee_id"],
            )
            message = "Cuenta activada correctamente." if is_active else "Cuenta desactivada correctamente."
            self.show_staff_management(message)
        except (ValueError, sqlite3.Error) as error:
            self.show_staff_management(f"No se pudo modificar la cuenta: {error}")

    def create_staff_action(self):
        role = "kitchen" if self.staff_role_menu.get() == "Cocina" else "courier"
        try:
            create_staff_member(
                self.staff_name_entry.get(),
                self.staff_email_entry.get(),
                self.staff_phone_entry.get(),
                self.staff_password_entry.get(),
                role,
                self.current_employee["employee_id"],
            )
            self.show_staff_management("Cuenta del empleado creada correctamente.")
        except (ValueError, sqlite3.Error) as error:
            self.show_staff_management(f"No se pudo crear la cuenta: {error}")

    # --------------------------------------------------
    # ADMINISTRACIÓN DEL CATÁLOGO
    # --------------------------------------------------

    def show_product_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "ADMINISTRACIÓN DE PRODUCTOS")
        if message:
            self.show_message(frame, message, "#2ECC71")

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=6)

        category_form = ctk.CTkFrame(scroll)
        category_form.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(category_form, text="CREAR CATEGORÍA", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.new_category_name_entry = ctk.CTkEntry(category_form, width=260, placeholder_text="Nombre de la categoría")
        self.new_category_name_entry.pack(anchor="w", padx=10, pady=4)
        self.new_category_description_entry = ctk.CTkEntry(category_form, width=420, placeholder_text="Descripción (opcional)")
        self.new_category_description_entry.pack(anchor="w", padx=10, pady=4)
        ctk.CTkButton(
            category_form, text="CREAR CATEGORÍA", width=180,
            command=self.create_category_action,
        ).pack(anchor="w", padx=10, pady=(4, 10))

        categories = get_product_categories()
        product_form = ctk.CTkFrame(scroll)
        product_form.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(product_form, text="AGREGAR PRODUCTO", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.new_product_name_entry = ctk.CTkEntry(product_form, width=300, placeholder_text="Nombre del producto")
        self.new_product_name_entry.pack(anchor="w", padx=10, pady=4)
        self.new_product_description_entry = ctk.CTkEntry(product_form, width=420, placeholder_text="Descripción del producto")
        self.new_product_description_entry.pack(anchor="w", padx=10, pady=4)
        self.new_product_price_entry = ctk.CTkEntry(product_form, width=180, placeholder_text="Precio en pesos (COP)")
        self.new_product_price_entry.pack(anchor="w", padx=10, pady=4)
        category_values = [f"{item['category_id']} | {item['name']}" for item in categories]
        self.new_product_category_menu = ctk.CTkOptionMenu(
            product_form,
            values=category_values or ["Sin categorías"],
            width=260,
        )
        self.new_product_category_menu.pack(anchor="w", padx=10, pady=4)
        ctk.CTkButton(
            product_form,
            text="GUARDAR PRODUCTO",
            width=180,
            state="normal" if categories else "disabled",
            command=self.create_catalog_product_action,
        ).pack(anchor="w", padx=10, pady=(4, 10))

        ctk.CTkLabel(scroll, text="CATÁLOGO ACTUAL", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(18, 6))
        catalog = get_admin_product_catalog()
        if not catalog:
            ctk.CTkLabel(scroll, text="Todavía no hay productos registrados.").pack(anchor="w", padx=10, pady=8)
        for product in catalog:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=5)
            status = "Disponible" if product["is_available"] else "No disponible"
            ctk.CTkLabel(
                card,
                text=f"{product['name']} · {product['category_name']} · {self.format_currency(product['price'])} · {status}",
                font=("Arial", 13, "bold"),
            ).pack(anchor="w", padx=10, pady=(8, 4))
            ctk.CTkLabel(card, text=product["description"] or "Sin descripción", font=("Arial", 11)).pack(anchor="w", padx=10, pady=2)
            controls = ctk.CTkFrame(card, fg_color="transparent")
            controls.pack(fill="x", padx=8, pady=(4, 8))
            price_entry = ctk.CTkEntry(controls, width=150, placeholder_text="Nuevo precio")
            price_entry.pack(side="left", padx=3)
            price_entry.insert(0, str(product["price"]))
            ctk.CTkButton(
                controls,
                text="ACTUALIZAR PRECIO",
                width=160,
                command=lambda p=product, e=price_entry: self.update_catalog_product_action(p, e),
            ).pack(side="left", padx=3)
            next_available = not bool(product["is_available"])
            ctk.CTkButton(
                controls,
                text="MARCAR NO DISPONIBLE" if product["is_available"] else "HABILITAR PRODUCTO",
                width=190,
                fg_color="#465363",
                hover_color="#34404E",
                command=lambda pid=product["product_id"], value=next_available: self.toggle_product_availability_action(pid, value),
            ).pack(side="left", padx=3)

    def create_category_action(self):
        try:
            create_product_category(
                self.new_category_name_entry.get(),
                self.new_category_description_entry.get(),
                self.current_employee["employee_id"],
            )
            self.show_product_management("Categoría creada correctamente.")
        except (ValueError, sqlite3.Error) as error:
            self.show_product_management(f"No se pudo crear la categoría: {error}")

    def create_catalog_product_action(self):
        try:
            selected = self.new_product_category_menu.get()
            if "|" not in selected:
                raise ValueError("Primero debes crear una categoría activa.")
            category_id = int(selected.split("|", 1)[0].strip())
            product_id = create_catalog_product(
                category_id,
                self.new_product_name_entry.get(),
                self.new_product_description_entry.get(),
                self.new_product_price_entry.get(),
                self.current_employee["employee_id"],
            )
            self.show_product_management(f"Producto creado correctamente. Código: {product_id}.")
        except (ValueError, sqlite3.Error) as error:
            self.show_product_management(f"No se pudo crear el producto: {error}")

    def update_catalog_product_action(self, product, price_entry):
        try:
            update_catalog_product(
                product["product_id"],
                product["name"],
                product["description"] or "",
                price_entry.get(),
                self.current_employee["employee_id"],
            )
            self.show_product_management("Precio actualizado. Los pedidos anteriores conservan su precio histórico.")
        except (ValueError, sqlite3.Error) as error:
            self.show_product_management(f"No se pudo actualizar el precio: {error}")

    def toggle_product_availability_action(self, product_id, is_available):
        try:
            set_product_availability(
                product_id,
                is_available,
                self.current_employee["employee_id"],
            )
            message = "Producto habilitado en el catálogo." if is_available else "Producto marcado como no disponible."
            self.show_product_management(message)
        except (ValueError, sqlite3.Error) as error:
            self.show_product_management(f"No se pudo cambiar la disponibilidad: {error}")

    # --------------------------------------------------
    # PAGOS EN EFECTIVO
    # --------------------------------------------------

    def show_payment_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "GESTIÓN DE PAGOS")
        if message:
            self.show_message(frame, message, "#2ECC71")

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=6)

        ctk.CTkLabel(
            scroll, text="PAGOS PENDIENTES", font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=8, pady=(8, 5))
        pending = get_cash_payment_queue()
        if not pending:
            ctk.CTkLabel(scroll, text="No hay pagos pendientes.", font=("Arial", 13)).pack(anchor="w", padx=10, pady=8)
        for payment in pending:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=6)
            order_mode = "Domicilio" if payment["order_type"] == "delivery" else "Consumo en mesa"
            ctk.CTkLabel(
                card,
                text=f"Pedido #{payment['order_id']} · {payment['customer_name']} · {order_mode} · {self.format_currency(payment['amount'])}",
                font=("Arial", 14, "bold"), wraplength=850,
            ).pack(anchor="w", padx=10, pady=(8, 3))
            ctk.CTkLabel(
                card,
                text=f"Estado del pedido: {payment['order_status']} · Estado del pago: pendiente",
                font=("Arial", 12),
            ).pack(anchor="w", padx=10, pady=3)
            can_receive = payment["order_status"] == "completed"
            button_text = "REGISTRAR EFECTIVO RECIBIDO" if can_receive else "DISPONIBLE AL COMPLETAR EL PEDIDO"
            ctk.CTkButton(
                card,
                text=button_text,
                width=260,
                state="normal" if can_receive else "disabled",
                command=lambda oid=payment["order_id"]: self.record_cash_payment_action(oid),
            ).pack(anchor="e", padx=10, pady=(4, 8))

        ctk.CTkLabel(
            scroll, text="ÚLTIMOS PAGOS REGISTRADOS", font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=8, pady=(18, 5))
        history = get_recent_cash_payments()
        if not history:
            ctk.CTkLabel(scroll, text="Todavía no hay pagos registrados.", font=("Arial", 13)).pack(anchor="w", padx=10, pady=8)
        for payment in history:
            ctk.CTkLabel(
                scroll,
                text=f"Pedido #{payment['order_id']} · {payment['customer_name']} · {self.format_currency(payment['amount'])} · Recibió: {payment['received_by_name'] or 'Administrador'} · {payment['paid_at']}",
                font=("Arial", 12), wraplength=950, justify="left",
            ).pack(anchor="w", padx=12, pady=5)

    def record_cash_payment_action(self, order_id):
        try:
            amount = record_cash_payment(order_id, self.current_employee["employee_id"])
            self.show_payment_management(
                f"Pago en efectivo de {self.format_currency(amount)} registrado correctamente."
            )
        except (ValueError, sqlite3.Error) as error:
            self.show_payment_management(f"No se pudo registrar el pago: {error}")

    # --------------------------------------------------
    # CONTROL DE TURNOS
    # --------------------------------------------------

    def show_shift_management(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "CONTROL DE TURNOS")
        if message:
            self.show_message(frame, message, "#2ECC71")

        role_names = {"admin": "Administrador", "kitchen": "Cocina", "courier": "Repartidor"}
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=6)
        ctk.CTkLabel(scroll, text="TURNOS ABIERTOS", font=("Arial", 18, "bold")).pack(anchor="w", padx=8, pady=8)
        open_shifts = get_open_employee_shifts()
        if not open_shifts:
            ctk.CTkLabel(scroll, text="No hay empleados con turnos abiertos.", font=("Arial", 13)).pack(anchor="w", padx=10, pady=8)
        for shift in open_shifts:
            ctk.CTkLabel(
                scroll,
                text=f"{shift['full_name']} · {role_names.get(shift['role'], shift['role'])} · Inicio: {shift['started_at']}",
                font=("Arial", 13),
            ).pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(scroll, text="HISTORIAL RECIENTE", font=("Arial", 18, "bold")).pack(anchor="w", padx=8, pady=(20, 8))
        recent = get_recent_employee_shifts(40)
        for shift in recent:
            status = "Abierto" if shift["status"] == "open" else "Cerrado"
            end_text = shift["ended_at"] or "En curso"
            ctk.CTkLabel(
                scroll,
                text=f"{shift['full_name']} · {role_names.get(shift['role'], shift['role'])} · {status} · {shift['started_at']} → {end_text}",
                font=("Arial", 12), wraplength=900,
            ).pack(anchor="w", padx=12, pady=4)

    # --------------------------------------------------
    # REPORTES ADMINISTRATIVOS
    # --------------------------------------------------

    def show_admin_reports(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=22, pady=18)
        self.add_admin_navigation(frame, "REPORTES ADMINISTRATIVOS")
        if message:
            self.show_message(frame, message, "#E0A030")

        today = date.today()
        default_start = (today - timedelta(days=29)).isoformat()
        default_end = today.isoformat()

        filters = ctk.CTkFrame(frame)
        filters.pack(fill="x", padx=5, pady=8)
        ctk.CTkLabel(filters, text="Desde (AAAA-MM-DD)").pack(side="left", padx=(10, 4), pady=10)
        start_entry = ctk.CTkEntry(filters, width=130)
        start_entry.pack(side="left", padx=4, pady=10)
        start_entry.insert(0, default_start)
        ctk.CTkLabel(filters, text="Hasta (AAAA-MM-DD)").pack(side="left", padx=(10, 4), pady=10)
        end_entry = ctk.CTkEntry(filters, width=130)
        end_entry.pack(side="left", padx=4, pady=10)
        end_entry.insert(0, default_end)

        results_frame = ctk.CTkScrollableFrame(frame)
        results_frame.pack(expand=True, fill="both", padx=5, pady=8)
        ctk.CTkLabel(
            results_frame,
            text="Selecciona el periodo y presiona GENERAR REPORTE.",
            font=("Arial", 15),
        ).pack(pady=35)
        ctk.CTkButton(
            filters,
            text="GENERAR REPORTE",
            width=170,
            command=lambda: self.run_admin_report_action(start_entry, end_entry, results_frame),
        ).pack(side="left", padx=12, pady=8)

    def run_admin_report_action(self, start_entry, end_entry, results_frame):
        try:
            report = get_admin_report(start_entry.get().strip(), end_entry.get().strip())
        except (ValueError, sqlite3.Error) as error:
            self.show_admin_reports(f"No se pudo generar el reporte: {error}")
            return

        for widget in results_frame.winfo_children():
            widget.destroy()

        metrics = [
            ("Pedidos registrados", report["total_orders"]),
            ("Pedidos completados", report["completed_orders"]),
            ("Pedidos cancelados", report["cancelled_orders"]),
            ("Pedidos a domicilio", report["delivery_orders"]),
            ("Pedidos en mesa", report["dine_in_orders"]),
            ("Pagos recibidos", report["paid_count"]),
            ("Efectivo recibido", self.format_currency(report["cash_collected"])),
            ("Efectivo pendiente", self.format_currency(report["cash_pending"])),
        ]
        ctk.CTkLabel(
            results_frame,
            text=f"Resumen del {report['start_date']} al {report['end_date']}",
            font=("Arial", 17, "bold"),
        ).pack(anchor="w", padx=8, pady=8)

        metric_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        metric_frame.pack(fill="x", padx=4, pady=4)
        for index, (label, value) in enumerate(metrics):
            card = ctk.CTkFrame(metric_frame)
            card.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=("Arial", 11)).pack(padx=8, pady=(10, 3))
            ctk.CTkLabel(card, text=str(value), font=("Arial", 17, "bold")).pack(padx=8, pady=(2, 10))
        for column in range(4):
            metric_frame.grid_columnconfigure(column, weight=1)

        ctk.CTkLabel(results_frame, text="PRODUCTOS MÁS SOLICITADOS", font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(18, 5))
        if report["top_products"]:
            for product in report["top_products"]:
                ctk.CTkLabel(
                    results_frame,
                    text=f"{product['product_name']} · {product['units_sold']} unidades · {self.format_currency(product['requested_amount'])}",
                    font=("Arial", 12),
                ).pack(anchor="w", padx=12, pady=3)
        else:
            ctk.CTkLabel(results_frame, text="No hay productos solicitados en este periodo.").pack(anchor="w", padx=12, pady=3)

        ctk.CTkLabel(results_frame, text="ALERTAS DE INVENTARIO", font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(18, 5))
        if report["low_stock"]:
            for product in report["low_stock"]:
                ctk.CTkLabel(
                    results_frame,
                    text=f"{product['name']} · Existencias: {product['stock_quantity']} · Mínimo: {product['minimum_stock']}",
                    text_color="#E0A030", font=("Arial", 12),
                ).pack(anchor="w", padx=12, pady=3)
        else:
            ctk.CTkLabel(results_frame, text="No hay productos por debajo del mínimo configurado.").pack(anchor="w", padx=12, pady=3)

    # --------------------------------------------------
    # PANEL DE COCINA
    # --------------------------------------------------

    def show_kitchen_dashboard(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=25, pady=18)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(header, text="PANEL DE COCINA", font=("Arial", 27, "bold")).pack(side="left")
        ctk.CTkButton(header, text="CERRAR SESIÓN", width=140, command=self.logout_employee).pack(side="right")
        ctk.CTkLabel(frame, text=f"Empleado: {self.current_employee['full_name']}", font=("Arial", 13)).pack(anchor="w", padx=8)
        self.add_employee_shift_controls(frame)
        if message:
            self.show_message(frame, message, "#2ECC71")
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=8)
        orders = get_kitchen_orders()
        if not orders:
            ctk.CTkLabel(scroll, text="No hay pedidos pendientes de preparación.", font=("Arial", 16)).pack(pady=30)
        for order in orders:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=8)
            mode = f"Mesa {order['table_number']}" if order["order_type"] == "dine_in" else "Domicilio"
            ctk.CTkLabel(
                card, text=f"Pedido #{order['order_id']} · {order['customer_name']} · {mode} · {order['status']}",
                font=("Arial", 15, "bold"),
            ).pack(anchor="w", padx=12, pady=(10, 5))
            for item in order["items"]:
                ctk.CTkLabel(card, text=f"{item['quantity']} × {item['product_name']}", font=("Arial", 13)).pack(anchor="w", padx=18, pady=2)
            new_status = "preparing" if order["status"] == "accepted" else "ready"
            button_text = "INICIAR PREPARACIÓN" if new_status == "preparing" else "MARCAR COMO LISTO"
            ctk.CTkButton(
                card, text=button_text, width=230,
                command=lambda oid=order["order_id"], status=new_status: self.update_kitchen_order_action(oid, status),
            ).pack(anchor="w", padx=12, pady=10)

    def update_kitchen_order_action(self, order_id, new_status):
        try:
            update_kitchen_order_status(order_id, self.current_employee["employee_id"], new_status)
            self.show_kitchen_dashboard("Estado del pedido actualizado.")
        except (ValueError, sqlite3.Error) as error:
            self.show_kitchen_dashboard(f"No se pudo actualizar: {error}")

    # --------------------------------------------------
    # PANEL DEL REPARTIDOR
    # --------------------------------------------------

    def show_courier_dashboard(self, message=""):
        self.clear_screen()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=25, pady=18)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(header, text="PANEL DE REPARTIDOR", font=("Arial", 27, "bold")).pack(side="left")
        ctk.CTkButton(header, text="CERRAR SESIÓN", width=140, command=self.logout_employee).pack(side="right")
        ctk.CTkLabel(frame, text=f"Repartidor: {self.current_employee['full_name']}", font=("Arial", 13)).pack(anchor="w", padx=8)
        self.add_employee_shift_controls(frame)
        if message:
            self.show_message(frame, message, "#2ECC71")
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(expand=True, fill="both", padx=5, pady=8)
        deliveries = get_courier_deliveries(self.current_employee["employee_id"])
        if not deliveries:
            ctk.CTkLabel(scroll, text="No tienes entregas asignadas actualmente.", font=("Arial", 16)).pack(pady=30)
        for delivery in deliveries:
            card = ctk.CTkFrame(scroll)
            card.pack(fill="x", padx=8, pady=8)
            ctk.CTkLabel(
                card,
                text=f"Pedido #{delivery['order_id']} · {delivery['customer_name']} · {self.format_currency(delivery['total'])}",
                font=("Arial", 15, "bold"),
            ).pack(anchor="w", padx=12, pady=(10, 5))
            ctk.CTkLabel(
                card,
                text=f"Dirección: {delivery['delivery_address']}\nTeléfono: {delivery['customer_phone']}\nIndicaciones: {delivery['customer_notes'] or 'Sin indicaciones'}\nEstado: {delivery['delivery_status']}",
                font=("Arial", 13), justify="left",
            ).pack(anchor="w", padx=12, pady=5)
            new_status = "picked_up" if delivery["delivery_status"] == "assigned" else "delivered"
            button_text = "MARCAR PEDIDO RECOGIDO" if new_status == "picked_up" else "CONFIRMAR ENTREGA"
            ctk.CTkButton(
                card, text=button_text, width=240,
                command=lambda oid=delivery["order_id"], status=new_status: self.update_delivery_action(oid, status),
            ).pack(anchor="w", padx=12, pady=10)

    def update_delivery_action(self, order_id, new_status):
        try:
            update_courier_delivery_status(order_id, self.current_employee["employee_id"], new_status)
            self.show_courier_dashboard("Estado de entrega actualizado.")
        except (ValueError, sqlite3.Error) as error:
            self.show_courier_dashboard(f"No se pudo actualizar: {error}")

    # --------------------------------------------------
    # INICIALIZACIÓN DE LA BASE DE DATOS
    # --------------------------------------------------

    def initialize_database(self):
        try:
            connection = get_connection()
            try:
                connection.execute("SELECT 1")
            finally:
                connection.close()

            create_customers_table()
            create_product_tables()
            create_order_tables()
            create_employee_table()
            create_operations_tables()
            create_administration_tables()

            self.database_status_message = "Base de datos conectada correctamente"
            self.database_status_color = "#2ECC71"
        except Exception as error:
            self.database_status_message = f"Error de conexión: {error}"
            self.database_status_color = "#E74C3C"

        self.database_status_label.configure(
            text=self.database_status_message,
            text_color=self.database_status_color,
        )


def main():
    """Configura el tema y ejecuta la aplicación."""
    ctk.set_appearance_mode(THEME)
    ctk.set_default_color_theme(COLOR_THEME)

    app = RestaurantApp()
    app.mainloop()


if __name__ == "__main__":
    main()
