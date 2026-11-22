# Incremento 8 — Integración y pruebas finales

## 1. Propósito

Integrar y verificar los módulos desarrollados en los incrementos anteriores para comprobar que los principales procesos de Restaurant Manager V2 funcionan de manera coordinada.

Este incremento cierra la implementación funcional prevista. La aceptación visual de la interfaz debe completarse en el equipo Windows donde se ejecutará la aplicación. Después de esa aceptación se elaborará el diagrama de clases final, conforme al requisito académico.

## 2. Relación con la metodología y el modelo de proceso

El proyecto se organiza mediante una metodología tradicional con fases de planificación, análisis, diseño, implementación, pruebas y entrega/mantenimiento.

El modelo de proceso incremental se aplica construyendo el producto por entregas funcionales. Cada incremento incorpora capacidades a la versión anterior y se verifica antes de continuar.

En este octavo incremento se realiza la integración de los componentes desarrollados y se ejecutan pruebas que recorren procesos completos, no solamente funciones aisladas.

## 3. Alcance de la integración

Se integran los siguientes procesos:

1. Registro y autenticación de clientes.
2. Consulta del catálogo de productos.
3. Administración del carrito en memoria.
4. Creación del pedido a partir del carrito.
5. Aceptación administrativa del pedido.
6. Descuento de existencias al aceptar el pedido.
7. Preparación del pedido por parte de cocina.
8. Asignación y actualización de la entrega por parte del repartidor.
9. Finalización del pedido y registro del pago en efectivo.
10. Consulta del historial del cliente y del reporte administrativo.
11. Flujo de consumo en mesa, incluida la liberación de la mesa.

## 4. Pruebas de integración automatizadas

Se incorporó `tests/test_end_to_end_workflow.py`, que utiliza una base de datos temporal independiente para no modificar los datos de trabajo del usuario.

### Caso E2E-01 — Pedido a domicilio

**Precondiciones:** existen un cliente, un administrador, un empleado de cocina, un repartidor, productos disponibles y existencias configuradas.

**Pasos:**

1. El cliente se autentica.
2. Agrega dos hamburguesas clásicas y una gaseosa al carrito.
3. El servicio crea el pedido de domicilio con dirección.
4. Se comprueba que el pedido queda pendiente y el pago en efectivo queda pendiente.
5. Se comprueba que las existencias no se descuentan al crear el pedido.
6. El administrador acepta el pedido y asigna al repartidor.
7. Se comprueba el descuento de dos hamburguesas y una gaseosa del inventario.
8. Cocina cambia el pedido a preparación y luego a listo.
9. El repartidor marca recogido y entregado.
10. El administrador registra el efectivo recibido.
11. Se comprueban el historial del cliente y el reporte administrativo.

**Resultado esperado:** pedido completado, entrega marcada como entregada, pago registrado y cifras del reporte consistentes.

### Caso E2E-02 — Pedido para consumir en restaurante

**Precondiciones:** existe un cliente, un administrador, un empleado de cocina, una mesa disponible y existencias suficientes.

**Pasos:**

1. El cliente agrega un producto al carrito.
2. Se crea un pedido para consumir en restaurante.
3. El administrador acepta el pedido y asigna una mesa disponible.
4. Se verifica que la mesa quede ocupada.
5. Cocina marca el pedido en preparación y luego como listo.
6. El administrador completa el servicio.
7. Se verifica que la mesa vuelva a estar disponible.
8. El administrador registra el efectivo recibido.

**Resultado esperado:** pedido completado, mesa liberada y pago registrado.

## 5. Resultado de pruebas automatizadas

Al preparar este incremento se ejecutó el conjunto completo de pruebas:

```powershell
python -m unittest discover -s tests -v
```

**Resultado obtenido en el entorno de desarrollo:** 54 pruebas aprobadas, 0 fallidas.

Las pruebas cubren repositorios, carrito, pedidos, operación del restaurante, administración y dos recorridos integrales de extremo a extremo.

La comprobación de sintaxis de los archivos Python también se ejecutó satisfactoriamente.

Este resultado no sustituye la prueba manual de interfaz en Windows. La prueba visual y de navegación debe registrarse después de ejecutar la aplicación en el computador de entrega.

## 6. Lista de aceptación manual en Windows

Marcar cada punto después de ejecutarlo en el equipo donde se presentará el proyecto.

- [ ] La aplicación abre sin errores.
- [ ] Un cliente puede registrarse e iniciar sesión.
- [ ] El cliente puede consultar el catálogo.
- [ ] El cliente puede agregar, quitar y cambiar cantidades en el carrito.
- [ ] El cliente puede crear un pedido a domicilio.
- [ ] El cliente puede crear un pedido para consumir en restaurante.
- [ ] El cliente puede consultar su historial y el detalle de sus pedidos.
- [ ] El administrador puede iniciar sesión y consultar pedidos pendientes.
- [ ] El administrador puede aceptar pedidos y asignar mesa o repartidor.
- [ ] Cocina puede cambiar el estado de preparación.
- [ ] El repartidor puede actualizar una entrega asignada.
- [ ] El inventario se descuenta al aceptar pedidos.
- [ ] El administrador puede cancelar pedidos permitidos y consultar las existencias restauradas cuando corresponda.
- [ ] El administrador puede administrar productos, categorías y personal.
- [ ] Los empleados pueden iniciar y finalizar turnos.
- [ ] El administrador puede registrar pagos en efectivo de pedidos completados.
- [ ] Los reportes muestran resultados para el periodo seleccionado.

## 7. Pendiente para el cierre académico

Una vez que la lista de aceptación manual se haya completado y se congele la versión final del código, se elaborará el diagrama de clases UML final.

El diagrama deberá corresponder a la estructura efectivamente implementada. No se deben presentar como clases de Python entidades que solo existan como tablas o registros en SQLite. Si se documenta el modelo conceptual del dominio, deberá identificarse claramente como tal.

También se consolidarán las evidencias de pruebas, el manual de usuario y el documento de entrega.

## 8. Criterio de finalización

El incremento se considera implementado en el entorno de desarrollo porque las pruebas automatizadas de integración pasan. La entrega académica se considerará aceptada cuando, además, se complete la lista manual en Windows, se documenten sus resultados y se preparen los entregables finales, incluido el diagrama de clases.
