# Restaurant Manager V2

Proyecto académico de aplicación de escritorio para la gestión de un restaurante.

## Enfoque de desarrollo

- **Metodología:** tradicional, organizada en planificación, análisis de requisitos, diseño, implementación, pruebas y entrega/mantenimiento.
- **Modelo de proceso:** incremental. Cada incremento se analiza, diseña, implementa y prueba antes de integrarse con la versión existente.
- **Diagrama de clases:** se elaborará como entregable final, a partir de las clases reales de la versión definitiva.

## Tecnologías

- Python
- CustomTkinter
- SQLite mediante `sqlite3`
- Visual Studio Code

## Estructura

```text
Restaurant_Manager_V2/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── customer_repository.py
│   ├── product_repository.py
│   ├── order_repository.py
│   ├── employee_repository.py
│   ├── operations_repository.py
│   └── administration_repository.py
├── services/
│   ├── __init__.py
│   ├── cart_service.py
│   └── order_service.py
├── data/                 (base de datos local creada al ejecutar)
├── assets/               (recursos gráficos)
├── tests/
│   ├── test_repositories.py
│   ├── test_cart_service.py
│   ├── test_order_repository.py
│   ├── test_operations_repository.py
│   ├── test_administration_repository.py
│   └── test_catalog_and_staff_admin.py
└── docs/
    ├── Documento_Base_Restaurant_Manager_V2.docx
    ├── Incremento_04_Carrito.md
    ├── Incremento_05_Creacion_Pedidos.md
    ├── Incremento_06_Operacion_Restaurante.md
    ├── Incremento_07_Administracion_Ampliada.md
    ├── Incremento_08_Integracion_Pruebas_Finales.md
    └── Matriz_Pruebas_Integracion.md
```

## Instalación en Windows

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Pruebas automatizadas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan bases de datos temporales y no modifican la base de datos de trabajo.

## Funcionalidades incluidas

- Portales de clientes y equipo.
- Registro y autenticación de clientes.
- Catálogo de productos.
- Carrito temporal de compras.
- Creación, historial y detalle de pedidos.
- Configuración inicial de la primera cuenta administradora.
- Autenticación de empleados con roles de administrador, cocina y repartidor.
- Creación administrativa de cuentas de cocina y repartidor.
- Registro y asignación de mesas.
- Ajuste de existencias e historial de movimientos de inventario.
- Aceptación de pedidos con asignación de mesa o repartidor.
- Descuento transaccional de existencias al aceptar pedidos.
- Flujo de preparación de cocina y seguimiento de entregas.
- Cancelación administrativa de pedidos pendientes o aceptados, con reversión de inventario cuando corresponde.
- Administración del catálogo: crear categorías y productos, actualizar precios y controlar disponibilidad.
- Administración de cuentas de empleados: activar o desactivar cuentas con protección de turnos y entregas activas.
- Registro administrativo de pagos en efectivo recibidos para pedidos completados.
- Inicio y cierre de turnos por parte del empleado; consulta administrativa de turnos.
- Reportes por periodo: pedidos, efectivo recibido y pendiente, productos más solicitados y alertas de inventario.

## Datos y persistencia

La base de datos se almacena en `data/restaurant_manager_v2.db` y se crea automáticamente. No utiliza los datos del proyecto personal anterior.

No elimines la base de datos después de registrar clientes o empleados: contiene cuentas, pedidos, catálogo y movimientos.

## Incrementos

1. Estructura inicial de la aplicación.
2. Registro y autenticación de clientes.
3. Catálogo de productos.
4. Carrito de compras.
5. Creación y consulta de pedidos.
6. Operación del restaurante: equipo, mesas, cocina, entregas y descuento de inventario al aceptar.
7. Administración ampliada: catálogo, cuentas de empleados, pagos en efectivo, turnos y reportes.
8. Integración, pruebas finales, documentación de entrega y preparación del diagrama de clases final.

## Validación del Incremento 8

Se añadieron dos pruebas de integración de extremo a extremo: un pedido a domicilio y un pedido para consumir en restaurante. En el entorno de desarrollo se ejecutaron 54 pruebas automatizadas con resultado satisfactorio (54 aprobadas, 0 fallidas). La interfaz gráfica debe validarse manualmente en Windows con la lista de aceptación de `docs/Incremento_08_Integracion_Pruebas_Finales.md`.

El diagrama de clases UML definitivo se elaborará después de completar la aceptación manual y congelar la versión final del código. El diagrama reflejará las clases realmente implementadas y distinguirá el modelo conceptual de las tablas de persistencia.

Consulta los documentos de `docs/` para el análisis, criterios de aceptación y pruebas de cada incremento.
