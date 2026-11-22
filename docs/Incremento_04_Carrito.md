# Incremento 4: Carrito de compras

## 1. Identificación

- **Proyecto:** Restaurant Manager V2
- **Incremento:** 4 - Carrito de compras
- **Modelo de proceso:** Incremental
- **Enfoque de desarrollo:** fases tradicionales de análisis, diseño, implementación y pruebas aplicadas al incremento.
- **Estado:** Implementación preparada; pendiente de validación manual en Windows.

## 2. Análisis del incremento

### Objetivo

Permitir que un cliente autenticado seleccione productos del catálogo, administre las cantidades y consulte el importe total de su selección antes de que se construya el proceso de creación del pedido.

### Requisitos funcionales

- **RF-CAR-01:** El cliente puede agregar al carrito un producto mostrado como disponible en el catálogo.
- **RF-CAR-02:** Si agrega nuevamente un producto que ya está en el carrito, debe aumentar su cantidad.
- **RF-CAR-03:** El cliente puede aumentar la cantidad de un producto.
- **RF-CAR-04:** El cliente puede disminuir la cantidad de un producto. Al disminuir desde una unidad, el producto se elimina.
- **RF-CAR-05:** El cliente puede eliminar una línea completa del carrito.
- **RF-CAR-06:** El cliente puede vaciar todo el carrito.
- **RF-CAR-07:** El sistema calcula el subtotal de cada línea y el total general.
- **RF-CAR-08:** El cliente puede regresar al catálogo sin perder la selección.
- **RF-CAR-09:** Al cerrar la sesión, el carrito temporal se vacía.

### Requisitos no funcionales y reglas

- **RNF-CAR-01:** Los importes se calculan con números enteros en pesos colombianos (COP).
- **RNF-CAR-02:** La lógica del carrito debe estar separada de la interfaz gráfica.
- **RNF-CAR-03:** Las cantidades deben ser números enteros positivos.
- **RNF-CAR-04:** Las operaciones del carrito no deben cambiar el precio almacenado en el catálogo.
- **RNF-CAR-05:** El carrito es temporal y permanece en memoria durante la sesión de la aplicación. La persistencia y la conversión del carrito en un pedido se desarrollarán en el incremento de pedidos.

## 3. Diseño

### Componentes

- `services/cart_service.py`: clase `ShoppingCart`, responsable de agregar, actualizar, eliminar, consultar y vaciar artículos, además de calcular unidades y total.
- `main.py`: presenta el catálogo y la pantalla del carrito. Envía las acciones del usuario al servicio y muestra los resultados.
- `tests/test_cart_service.py`: pruebas unitarias de la lógica del carrito.

### Flujo principal

1. El cliente inicia sesión.
2. Abre el catálogo.
3. Selecciona «Agregar al carrito» en un producto.
4. El sistema registra el producto o aumenta su cantidad.
5. El cliente abre el carrito y consulta cantidades, subtotales y total.
6. Puede modificar cantidades, eliminar líneas, vaciar el carrito o volver al catálogo.
7. Al cerrar sesión, el carrito se limpia.

### Fórmula de cálculo

- Subtotal de una línea = precio unitario × cantidad.
- Total de la compra = suma de los subtotales de todas las líneas.

## 4. Implementación

La lógica se implementa en `ShoppingCart`, en un módulo separado de la interfaz. La clase mantiene un diccionario en memoria identificado por `product_id`. La interfaz consulta copias de los artículos para evitar modificar directamente el estado interno del servicio. El acceso al carrito queda disponible desde el encabezado y desde una barra inferior fija del catálogo, para que no dependa de la posición del desplazamiento.

No se crea todavía una tabla de carrito ni de pedidos. Esa persistencia se diseñará en el incremento correspondiente a pedidos, después de definir los datos y estados que debe conservar una orden.

## 5. Plan de pruebas y criterios de aceptación

| Código | Prueba | Resultado esperado |
|---|---|---|
| PC-01 | Agregar un producto | Aparece una línea con cantidad 1 y el precio correspondiente. |
| PC-02 | Agregar dos veces el mismo producto | Se conserva una sola línea y aumenta la cantidad. |
| PC-03 | Aumentar cantidad | Se actualizan cantidad, subtotal y total. |
| PC-04 | Disminuir cantidad | Se reduce la cantidad y se recalculan los importes. |
| PC-05 | Disminuir desde cantidad 1 | El producto se elimina del carrito. |
| PC-06 | Eliminar un producto | Desaparece la línea seleccionada. |
| PC-07 | Vaciar carrito | No quedan productos y el total es $0. |
| PC-08 | Agregar diferentes productos | El total es la suma correcta de todos los subtotales. |
| PC-09 | Cerrar sesión | El carrito queda vacío para la siguiente sesión. |
| PC-10 | Volver al catálogo | Los productos seleccionados siguen en el carrito. |

**Resultado de pruebas automatizadas:** 8 pruebas unitarias del carrito y 4 pruebas de repositorios ejecutadas correctamente (12 pruebas en total; resultado: OK).

**Resultado de pruebas manuales en la interfaz:** pendiente de validación por el usuario en Windows. La interfaz debe comprobarse en el entorno donde está instalado CustomTkinter.

## 6. Criterio de cierre del incremento

El incremento se considerará aceptado cuando las pruebas automatizadas pasen y las pruebas manuales PC-01 a PC-10 se completen sin errores que impidan el uso del carrito. Después podrá integrarse como funcionalidad validada de la versión y se continuará con el incremento de creación de pedidos.
