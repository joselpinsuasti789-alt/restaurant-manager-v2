# Matriz de pruebas de integración — Restaurant Manager V2

| ID | Proceso | Verificación principal | Resultado automatizado |
|---|---|---|---|
| E2E-01 | Pedido a domicilio | Cliente, carrito, pedido, aceptación, inventario, cocina, reparto, pago e informe | Aprobado |
| E2E-02 | Pedido en mesa | Cliente, pedido, asignación de mesa, cocina, liberación y pago | Aprobado |
| INT-03 | Control de existencias | No descontar al crear; descontar al aceptar; impedir aceptación parcial | Aprobado en pruebas de operaciones e integración |
| INT-04 | Cancelación autorizada | Solo administrador; reversión de existencias cuando aplica | Aprobado en pruebas de operaciones |
| INT-05 | Seguridad por roles | Restringir operaciones administrativas y operativas a roles autorizados | Aprobado en pruebas de repositorios |
| INT-06 | Pago en efectivo | No registrar antes de completar; impedir doble registro | Aprobado en pruebas administrativas |
| INT-07 | Turnos | Abrir y cerrar turno; impedir dos turnos abiertos | Aprobado en pruebas administrativas |
| INT-08 | Reportes | Consolidar pedidos, pagos, productos y alertas de inventario | Aprobado en pruebas administrativas |

## Ejecución

Desde la carpeta raíz del proyecto:

```powershell
python -m unittest discover -s tests -v
```

Resultado del entorno de desarrollo al preparar el Incremento 8: **54 pruebas ejecutadas, 54 aprobadas, 0 fallidas**.

La matriz automatizada no sustituye la lista manual de aceptación visual descrita en `Incremento_08_Integracion_Pruebas_Finales.md`.
