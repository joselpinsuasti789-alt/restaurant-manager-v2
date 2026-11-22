# Incremento 6 — Operación del restaurante

## 1. Propósito

Implementar el acceso del personal y las operaciones necesarias para aceptar pedidos, asignar mesas o repartidores, preparar pedidos, registrar entregas y controlar las existencias que se consumen al aceptar un pedido.

Este incremento continúa el modelo incremental dentro de las fases tradicionales de análisis, diseño, implementación y pruebas.

## 2. Alcance funcional

- Configuración inicial de la primera cuenta administradora cuando todavía no existe una cuenta admin.
- Inicio de sesión del equipo con roles `admin`, `kitchen` y `courier`.
- El administrador puede crear cuentas de cocina y repartidor.
- El administrador puede registrar mesas e ingresar existencias iniciales o ajustar existencias de productos.
- El administrador consulta pedidos pendientes y, al aceptarlos, asigna una mesa o un repartidor.
- La aceptación descuenta automáticamente las cantidades del inventario y registra movimientos.
- Cocina consulta los pedidos aceptados y cambia sus estados de `accepted` a `preparing` y luego a `ready`.
- El repartidor consulta solamente sus entregas asignadas, marca el pedido como recogido y confirma la entrega.
- El administrador puede cancelar pedidos `pending` o `accepted`; si el pedido ya había descontado inventario y todavía no empezó la preparación, las existencias se restauran y se registra el movimiento inverso.
- El administrador puede completar un pedido de consumo en mesa cuando cocina lo marca como listo; la mesa queda disponible nuevamente.

## 3. Reglas de negocio

1. Solo puede existir una primera cuenta administradora configurada desde el flujo inicial.
2. Solo un administrador activo puede crear empleados, mesas y ajustes de inventario.
3. Los empleados de cocina solo pueden cambiar estados de preparación.
4. Un repartidor solo puede actualizar entregas que le fueron asignadas.
5. Los pedidos a domicilio requieren un repartidor activo al momento de aceptación.
6. Los pedidos de consumo en restaurante requieren una mesa disponible al momento de aceptación.
7. No se acepta un pedido si cualquiera de sus productos tiene existencias insuficientes.
8. La aceptación, asignación y descuento de inventario se ejecutan dentro de una transacción. Si falla una validación, no se acepta parcialmente el pedido.
9. Cocina debe marcar un pedido como listo antes de que el repartidor pueda recogerlo.
10. Solo se permiten transiciones de estado definidas por el flujo operacional.
11. La cancelación requiere un motivo. En este incremento solo se permite cancelar pedidos pendientes o aceptados que todavía no entran en preparación.
12. Un pedido cancelado después de haber sido aceptado restaura las existencias y libera la mesa, si tenía una asignada.
13. La confirmación de entrega completa el pedido a domicilio. El pago en efectivo permanece pendiente hasta su registro en el incremento administrativo posterior.

## 4. Diseño técnico

Nuevos módulos:

- `database/employee_repository.py`: creación de la primera cuenta administradora, creación de empleados y autenticación por rol.
- `database/operations_repository.py`: tablas, inventario, aceptación/cancelación de pedidos, preparación de cocina y entregas.

`main.py` incorpora las pantallas de configuración inicial de administrador, acceso del equipo, panel administrativo, panel de cocina y panel de repartidor.

Nuevas estructuras de datos:

- `employees`
- `restaurant_tables`
- `inventory`
- `inventory_movements`

Se reutilizan las tablas `orders`, `order_items`, `deliveries` y `order_status_history` creadas en el incremento 5.

## 5. Criterios de aceptación

- El primer acceso al portal del equipo permite configurar el administrador si aún no existe.
- El inicio de sesión dirige al panel correspondiente al rol autenticado.
- Las cuentas de cocina y repartidor no pueden ejecutar operaciones administrativas.
- Se pueden registrar mesas y ajustar existencias.
- Un pedido de mesa aceptado ocupa una mesa disponible.
- Un pedido a domicilio aceptado queda asignado a un repartidor activo.
- La aceptación descuenta todas las existencias requeridas o no descuenta ninguna.
- Cocina puede iniciar y finalizar la preparación.
- El repartidor no puede recoger un pedido antes de que cocina lo marque como listo.
- La entrega confirmada completa el pedido.
- La cancelación autorizada revierte el inventario cuando corresponde.
- La finalización del servicio de mesa libera la mesa.

## 6. Pruebas automatizadas

Se incorporan pruebas para:

- Creación única de la cuenta administradora.
- Autenticación y reconocimiento de roles.
- Restricción de creación de empleados a administradores.
- Aceptación de pedidos de mesa y descuento de inventario.
- Rechazo transaccional ante existencias insuficientes.
- Transiciones de cocina.
- Finalización de pedidos en mesa y liberación de mesa.
- Asignación y flujo de entregas.
- Rechazo de recogida antes de que cocina marque el pedido como listo.
- Cancelación administrativa y restauración de existencias.
- Rechazo de cancelación por perfiles sin permisos.

## 7. Pendiente de validación manual

La interfaz gráfica debe probarse en Windows con CustomTkinter. Las pruebas automatizadas validan la lógica de persistencia y las reglas operativas, pero no sustituyen la comprobación visual y de navegación en el computador del usuario.

## 8. Resultado del incremento

El restaurante dispone de un flujo operativo inicial conectado con los pedidos creados por los clientes. Las funciones de pagos, turnos, reportes y administración ampliada se completarán en el incremento 7.
