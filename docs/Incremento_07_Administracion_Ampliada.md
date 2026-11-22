# Incremento 7 — Administración ampliada

## 1. Identificación

**Proyecto:** Restaurant Manager V2  
**Modelo de proceso:** Incremental  
**Fase tradicional relacionada:** Implementación y pruebas, con análisis y diseño del incremento documentados antes de incorporarlo.

## 2. Objetivo

Ampliar las capacidades administrativas del sistema para gestionar el catálogo, controlar las cuentas del personal, registrar pagos en efectivo, gestionar turnos y consultar reportes del restaurante.

## 3. Alcance funcional

### 3.1 Administración del catálogo

- Crear categorías.
- Registrar productos dentro de categorías activas.
- Actualizar nombre, descripción y precio de productos.
- Marcar productos como disponibles o no disponibles sin eliminar el registro.
- Crear automáticamente el registro inicial de inventario para un producto nuevo.
- Conservar el nombre y precio histórico guardado en los pedidos anteriores.

### 3.2 Administración de cuentas del personal

- Consultar cuentas de empleados activas e inactivas.
- Desactivar y reactivar cuentas desde el panel administrativo.
- No permitir que el administrador desactive su propia cuenta desde esta opción.
- No permitir desactivar al último administrador activo.
- No permitir desactivar una cuenta con turno abierto.
- No permitir desactivar un repartidor con entregas asignadas o recogidas pendientes.
- Conservar los registros históricos de empleados.

### 3.3 Pagos en efectivo

- Consultar pagos pendientes.
- Registrar el efectivo recibido por un administrador.
- Registrar quién recibió el dinero y la fecha del pago.
- Evitar registrar dos veces un mismo pago.
- Permitir registrar el pago únicamente cuando el pedido esté completado y no cancelado.
- Consultar los pagos recibidos recientemente.

### 3.4 Turnos

- Permitir que cada empleado activo abra su propio turno.
- Permitir que el empleado cierre su turno.
- Evitar que un empleado tenga dos turnos abiertos simultáneamente.
- Permitir al administrador consultar los turnos abiertos y el historial reciente.
- Mantener los turnos como registros históricos; no se eliminan al cerrar sesión.

### 3.5 Reportes

El administrador puede generar un resumen para un rango de fechas que incluye:

- Cantidad de pedidos registrados, completados y cancelados.
- Pedidos a domicilio y pedidos en mesa.
- Efectivo recibido y efectivo pendiente.
- Productos más solicitados.
- Productos cuyas existencias son iguales o inferiores al mínimo configurado.

## 4. Reglas de negocio

1. Solo un administrador activo puede modificar el catálogo y las cuentas del personal.
2. Los productos no se eliminan físicamente cuando dejan de venderse; se marcan como no disponibles.
3. Los precios se almacenan como pesos colombianos enteros. Los pedidos existentes conservan su precio histórico.
4. El pago en efectivo solo se registra cuando el pedido está completado.
5. Un pago solo puede pasar de pendiente a pagado una vez.
6. Cada empleado puede tener un único turno abierto.
7. Una cuenta con turno abierto no puede desactivarse.
8. Un repartidor con entregas en curso no puede desactivarse.
9. El informe valida el formato AAAA-MM-DD y que la fecha inicial no sea posterior a la final.

## 5. Diseño técnico

### Archivos principales

- `database/administration_repository.py`: operaciones de pagos, turnos y reportes.
- `database/product_repository.py`: operaciones de administración del catálogo.
- `database/employee_repository.py`: activación y desactivación controlada de cuentas.
- `main.py`: pantallas administrativas, navegación, formularios y acciones.
- `tests/test_administration_repository.py`: pruebas de pagos, turnos y reportes.
- `tests/test_catalog_and_staff_admin.py`: pruebas de catálogo y cuentas del personal.

### Persistencia adicional

Se agrega la tabla `employee_shifts`. También se incorporan índices para consultar turnos y pagos. Las tablas existentes de clientes, empleados, pedidos, productos y pagos se conservan. La inicialización utiliza `CREATE TABLE IF NOT EXISTS` y no elimina registros.

## 6. Pruebas realizadas

Las pruebas automatizadas cubren:

- Inicio y cierre de turnos.
- Rechazo de turnos duplicados.
- Protección de las acciones administrativas por rol.
- Registro único de pagos en efectivo.
- Rechazo del pago antes de completar un pedido.
- Generación y validación de reportes por fechas.
- Creación de categorías y productos.
- Actualización de precios y disponibilidad.
- Activación y desactivación de empleados.
- Protección de empleados con turnos o entregas activas.

**Resultado en el entorno de desarrollo:** 52 pruebas automatizadas aprobadas en total para el proyecto. La interfaz gráfica debe validarse manualmente en Windows.

## 7. Criterios de aceptación

El incremento se considera aceptado cuando:

- El administrador puede crear categorías y productos y modificar precio y disponibilidad.
- El administrador puede activar o desactivar cuentas respetando las restricciones.
- Los empleados pueden iniciar y finalizar sus propios turnos.
- El administrador puede consultar turnos abiertos e historial.
- El administrador puede marcar como recibido un pago en efectivo de un pedido completado.
- El sistema impide registrar un pago dos veces.
- Los reportes muestran los resultados para el rango seleccionado.
- Los incrementos anteriores siguen funcionando.

## 8. Resultado del incremento

Se amplía el portal administrativo de Restaurant Manager V2. El sistema ya permite administrar catálogo y personal, registrar pagos en efectivo, controlar turnos y consultar reportes. Este incremento se integra con los pedidos, la cocina, las entregas y el inventario implementados anteriormente.

## 9. Pendiente de validación manual

Ejecutar la aplicación en Windows y verificar visualmente las pantallas de Productos, Personal, Pagos, Turnos y Reportes. Probar un pedido completado, registrar su efectivo y confirmar que aparezca en el reporte.
