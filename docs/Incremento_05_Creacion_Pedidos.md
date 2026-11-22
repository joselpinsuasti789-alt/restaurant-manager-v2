# Incremento 5 — Creación y consulta de pedidos

## 1. Propósito

Permitir que un cliente autenticado convierta los productos de su carrito en un pedido registrado en la base de datos y consulte el estado y el detalle de sus pedidos.

## 2. Actividades del enfoque tradicional

### Análisis

- El cliente puede pedir a domicilio o consumir en el restaurante.
- Para domicilio, la dirección es obligatoria.
- Para consumo en restaurante, el cliente no selecciona mesa: un empleado asignará una mesa disponible cuando el pedido sea atendido.
- El medio de pago de esta versión es efectivo.
- El pago queda pendiente hasta que un empleado registre el cobro en un incremento posterior.
- El pedido se crea con estado `pending`.
- El administrador asignará un repartidor en un incremento posterior.
- El inventario no se descuenta al crear el pedido; se descontará al aceptarlo, según la regla acordada para el proyecto.
- El cliente solo puede consultar los pedidos asociados a su propia cuenta.

### Diseño

Se agregan las tablas `orders`, `order_items`, `payments`, `order_status_history` y `deliveries`.

Se separan responsabilidades:

- `database/order_repository.py`: creación transaccional y consultas de persistencia.
- `services/order_service.py`: casos de uso solicitados por el cliente.
- `main.py`: pantallas de selección de modalidad, confirmación, historial y detalle.

### Implementación

1. El cliente abre el carrito y pulsa **CONTINUAR CON EL PEDIDO**.
2. Selecciona domicilio o consumo en restaurante.
3. Si selecciona domicilio, ingresa una dirección.
4. Puede escribir indicaciones adicionales.
5. Confirma el pedido.
6. El sistema vuelve a consultar los productos y sus precios actuales.
7. En una sola transacción se guardan el pedido, sus líneas, el pago pendiente, el evento inicial de estado y, para domicilio, el registro de entrega pendiente.
8. El carrito se vacía solamente cuando la transacción termina correctamente.
9. El cliente puede consultar “Mis pedidos” y abrir el detalle de cada uno.

### Pruebas

Ejecutar desde la raíz del proyecto:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas automatizadas verifican pedidos a domicilio y en restaurante, pago en efectivo pendiente, validación de dirección, carrito vacío, modalidad incorrecta, producto no disponible, cambio de precio, atomicidad de la transacción, historial inicial y aislamiento de pedidos por cliente.

## 3. Reglas importantes

- Los importes se almacenan como pesos colombianos enteros.
- Los nombres y precios de los productos se guardan como fotografía histórica en `order_items`.
- Si el precio del producto cambió desde que se agregó al carrito, el sistema rechaza la confirmación para que el cliente actualice su carrito.
- La creación del pedido es atómica: no debe quedar un pedido parcial si falla la validación de una línea.
- La mesa se mantiene sin asignar (`table_id = NULL`) en esta etapa.
- La entrega queda en estado `pending`, sin repartidor asignado.
- No se descuenta inventario en este incremento.
- No se procesa un pago en línea ni se marca el pago como recibido.

## 4. Criterios de aceptación

- [ ] El cliente autenticado puede crear un pedido con domicilio y dirección válida.
- [ ] El cliente autenticado puede crear un pedido para consumir en restaurante.
- [ ] No se permite confirmar un carrito vacío.
- [ ] Los productos no disponibles no pueden incluirse en un nuevo pedido.
- [ ] Si cambió el precio, se solicita actualizar el carrito.
- [ ] Se guarda el detalle con nombre, cantidad, precio unitario y subtotal.
- [ ] Se crea un pago en efectivo con estado `pending`.
- [ ] El pedido queda en estado `pending` y se registra su historial inicial.
- [ ] El pedido a domicilio genera una entrega pendiente de asignación.
- [ ] El pedido para restaurante no asigna mesa automáticamente.
- [ ] El cliente solo puede consultar sus propios pedidos.
- [ ] El carrito se vacía después de guardar correctamente el pedido.

## 5. Resultado de pruebas automatizadas

En el entorno de desarrollo se ejecutaron 22 pruebas automatizadas: 4 de repositorios iniciales, 8 del carrito y 10 del repositorio de pedidos. Resultado: **22 pruebas aprobadas**.

La comprobación visual de las pantallas debe realizarse también en el equipo Windows donde se ejecuta CustomTkinter.

## 6. Pendiente para incrementos posteriores

- Aceptación del pedido por personal autorizado.
- Descuento automático del inventario cuando el pedido sea aceptado.
- Asignación de mesa por un empleado.
- Asignación de repartidor por el administrador.
- Actualización de estados por cocina y repartidor.
- Registro del efectivo recibido por el personal.
- Cancelaciones autorizadas por el administrador y reversión de inventario cuando corresponda.
