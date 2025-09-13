# Tu Pedido v2 - Sistema de Comidas Rápidas

## Descripción

Sistema completo de gestión de pedidos para restaurantes de comida rápida desarrollado para Odoo 18 Community. Permite gestionar pedidos desde el eCommerce y el módulo de ventas con un dashboard interactivo en tiempo real y sistema de notificaciones unificado.

## Características Principales

### 🎯 Dashboard Interactivo
- Vista Kanban con estados de pedidos: Nuevo → Aceptado → En Preparación → Terminado → Despachado/Retirado → Entregado → Rechazado
- Drag & Drop para cambiar estados de pedidos
- Actualización automática cada 30 segundos
- Notificaciones sonoras para pedidos nuevos (cada 10 segundos hasta aceptar/rechazar)
- Efectos visuales (parpadeo) para pedidos nuevos con desactivación automática

### 🔔 Sistema de Notificaciones Unificado
- **🌐 Notificaciones Web**: Alertas de pedidos nuevos del eCommerce en PoS (botón azul)
- **🚚 Notificaciones Delivery**: Pedidos terminados listos para enviar (botón verde)
- **📍 Notificaciones Pickup**: Pedidos terminados listos para retirar (botón morado)
- Botones flotantes con contadores en tiempo real
- Modales informativos con acciones rápidas (Despachado/Entregado)
- Formateo inteligente de nombres de mesa ("TerrazaMesa5" → "Terraza Mesa 5")

### 📊 Información Detallada de Pedidos
- Nombre del cliente
- Productos con cantidades, unidades de medida y atributos
- Campo "Notas" para instrucciones de cocina
- Tiempo transcurrido por estado y tiempo total
- Botones de acción para cambiar estados

### ⏰ Gestión de Sesiones de Trabajo
- Control de apertura y cierre del restaurante
- Horarios estimados de funcionamiento
- Estadísticas por sesión (pedidos totales, completados, rechazados, tiempo promedio)
- Los clientes solo pueden hacer pedidos cuando hay sesión abierta

### 🛒 Integración con eCommerce
- API para verificar si el restaurante está abierto
- Creación automática de pedidos desde el eCommerce
- Widget para que el cliente vea el estado de su pedido en tiempo real
- Barra de progreso visual del estado del pedido

### 📱 Confirmación del Cliente
- Botón "Recibí mi pedido" cuando el estado llega a "Despachado/Retirado"
- Cambio automático a "Entregado" al confirmar recepción
- Posibilidad de marcar como entregado manualmente desde el dashboard

### 🔄 Automatizaciones
- Pedidos creados automáticamente en estado "Nuevo"
- Confirmación automática de orden de venta al llegar a estado "Terminado"
- Cancelación automática de orden al rechazar pedido
- Detección automática de tipo de entrega (delivery vs pickup)
- Desactivación automática de notificaciones al aceptar/rechazar pedidos
- Asignación automática a sesión de trabajo activa

## Instalación

1. Copiar el módulo a la carpeta de addons de Odoo
2. Actualizar la lista de aplicaciones
3. Instalar el módulo "Tu Pedido - Sistema Comidas Rapidas"

## Configuración Inicial

### 1. Abrir Sesión de Trabajo
- Ir a **Tu Pedido > Control de Sesión**
- Hacer clic en "🟢 Abrir Sesión"
- Configurar horarios estimados de apertura y cierre

### 2. Acceder al Dashboard
- Ir a **Tu Pedido > Dashboard**
- El dashboard mostrará las columnas de estados de pedidos
- Los pedidos nuevos aparecerán automáticamente con sonido y efectos visuales

## Uso del Sistema

### Para el Personal del Restaurante

1. **Dashboard Principal**: Visualizar todos los pedidos organizados por estado
2. **Gestión de Pedidos**: 
   - Arrastrar tarjetas entre columnas para cambiar estados
   - Usar botones "Aceptar/Rechazar" para pedidos nuevos
   - Usar botón "Siguiente" para avanzar estados
3. **Control de Sesión**: Abrir/cerrar el restaurante según horarios
4. **Notificaciones PoS**: 
   - Botón azul: Nuevos pedidos web
   - Botón verde: Pedidos delivery listos
   - Botón morado: Pedidos pickup listos

### Para los Clientes (eCommerce)

1. **Realizar Pedido**: Crear pedido desde el sitio web (solo si el restaurante está abierto)
2. **Seguimiento**: Acceder al widget de estado con el ID del pedido
3. **Confirmación**: Confirmar recepción cuando el pedido esté despachado

## APIs Disponibles

#### APIs eCommerce
### `/tu_pedido/estado_restaurante`
Verifica si el restaurante está abierto
```json
{
  "success": true,
  "abierto": true,
  "fecha_apertura": "2024-01-15T08:00:00",
  "hora_cierre_estimada": 22.0
}
```

### `/tu_pedido/estado_pedido/<order_id>`
Consulta el estado de un pedido específico
```json
{
  "success": true,
  "pedido": {
    "id": 123,
    "estado": {
      "nombre": "En Preparación",
      "progreso": 50,
      "descripcion": "Estamos preparando tu pedido"
    },
    "tiempo_transcurrido": 15,
    "puede_confirmar_recepcion": false
  }
}
```

#### APIs Notificaciones PoS
### `/tu_pedido_v2/pos_delivery_notifications`
Obtiene pedidos delivery terminados para notificar

### `/tu_pedido_v2/pos_pickup_notifications`
Obtiene pedidos pickup terminados para notificar

### `/tu_pedido_v2/pos_web_notifications`
Obtiene pedidos web nuevos para notificar

### `/tu_pedido_v2/mark_delivery_dispatched`
Marca pedido como despachado desde notificaciones

### `/tu_pedido/confirmar_recepcion/<order_id>`
Permite al cliente confirmar que recibió su pedido

### `/tu_pedido/widget_estado/<order_id>`
Widget HTML para mostrar el estado del pedido al cliente

## Estados del Pedido

1. **Nuevo**: Pedido recién creado, esperando aceptación/rechazo
2. **Aceptado**: Pedido confirmado por el restaurante
3. **En Preparación**: Pedido en proceso de preparación
4. **Terminado**: Pedido listo para despacho
5. **Despachado/Retirado**: Pedido entregado al cliente o listo para retiro
6. **Entregado**: Cliente confirmó recepción del pedido
7. **Rechazado**: Pedido rechazado por el restaurante

## Campos Adicionales en Órdenes de Venta

- `estado_rapido`: Estado del pedido en el dashboard
- `nota_cocina`: Notas especiales para la cocina
- `tiempo_inicio_estado`: Timestamp del inicio del estado actual
- `tiempo_inicio_total`: Timestamp de creación del pedido
- `cliente_confirmo_recepcion`: Boolean si el cliente confirmó recepción
- `sonido_activo`: Boolean para activar notificaciones sonoras (se desactiva automáticamente)
- `es_para_envio`: Boolean para detectar delivery vs pickup automáticamente
- `direccion_entrega_completa`: Dirección completa para delivery
- `tiempo_estado_minutos`: Minutos en el estado actual (computado)
- `tiempo_total_minutos`: Minutos totales desde creación (computado)
- `sesion_trabajo_id`: Relación con la sesión de trabajo

## Campos Adicionales en Órdenes PoS

- `estado_rapido`: Estado del pedido en el dashboard
- `is_delivery`: Boolean para indicar si es delivery
- `direccion_delivery`: Dirección de entrega para delivery
- `telefono_delivery`: Teléfono de contacto
- `enviado_a_cocina`: Boolean si fue enviado al dashboard

## Compatibilidad

- **Odoo Version**: 18.0 Community
- **Dependencias**: sale, website_sale, portal, point_of_sale, pos_restaurant
- **Navegadores**: Chrome, Firefox, Safari, Edge (con soporte para Web Audio API)
- **Dispositivos**: Desktop, Tablet (responsive design)

## Versiones y Mejoras

### v2.1 - Sistema de Notificaciones Completo (Enero 2025)
- ✅ Sistema unificado de notificaciones PoS
- ✅ Notificaciones web, delivery y pickup
- ✅ Formateo automático de nombres de mesa
- ✅ Desactivación automática de alertas
- ✅ Limpieza y optimización de código

### v2.0 - Notificaciones Pickup
- ✅ Notificaciones para pedidos listos para retirar
- ✅ Detección automática de tipo de entrega
- ✅ Botones flotantes independientes

### v1.9 - Mejoras Dashboard
- ✅ Efectos visuales mejorados
- ✅ Sincronización sonido/visual
- ✅ Corrección de estados

### v1.8 - Notificaciones Web
- ✅ Alertas de pedidos eCommerce en PoS
- ✅ Integración completa web-PoS

## Soporte

Para soporte técnico o consultas sobre el módulo, contactar al desarrollador.

## Licencia

LGPL-3

---

**Versión**: 2.1  
**Última actualización**: Enero 2025  
**Autor**: Walter - Tu Pedido v2