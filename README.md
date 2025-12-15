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
- **Filtros avanzados**:
  - 📅 Por fecha: Hoy (por defecto), Ayer, Últimos 7 días, Todos
  - 👤 Por cliente: Búsqueda por nombre
  - 🌐 Por origen: Web o Punto de Venta
  - 📊 Por estado: Todos los estados disponibles

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

### 🛒 Integración con eCommerce
- API para verificar si el restaurante está abierto
- **Control de compras por sesión PoS**: Solo permite compras cuando hay sesión PoS abierta
- Banner de estado en carrito (abierto/cerrado)
- Página personalizada cuando el local está cerrado
- Creación automática de pedidos desde el eCommerce (solo al confirmar pago)
- **Página de confirmación mejorada** con:
  - Número de pedido destacado
  - Barra de progreso en tiempo real
  - Detalle completo de productos ordenados
  - Información de entrega (delivery o pickup)
  - Dirección completa si es delivery
  - Tiempo transcurrido y estimado
  - Actualización automática cada 30 segundos
- Widget en portal del cliente (/my/orders) con seguimiento completo

### 📱 Confirmación del Cliente
- Botón "Recibí mi pedido" en página de confirmación cuando el estado llega a "Despachado/Retirado"
- Botón "Tengo un Problema" para generar reclamos
- Cambio automático a "Entregado" al confirmar recepción
- Posibilidad de marcar como entregado manualmente desde el dashboard
- Interfaz amigable con emojis y colores intuitivos

### 🔄 Automatizaciones
- Pedidos creados automáticamente en estado "Nuevo"
- Confirmación automática de orden de venta al llegar a estado "Terminado"
- Cancelación automática de orden al rechazar pedido
- Detección automática de tipo de entrega (delivery vs pickup)
- Desactivación automática de notificaciones al aceptar/rechazar pedidos
- Formateo automático de nombres de mesa en notificaciones

## Instalación

1. Copiar el módulo a la carpeta de addons de Odoo
2. Reiniciar el servidor Odoo
3. Actualizar la lista de aplicaciones (Apps > Update Apps List)
4. Buscar "Tu Pedido v2" e instalar el módulo

## Configuración Inicial

### 1. Acceder al Dashboard
- Ir a **Tu Pedido > Dashboard**
- El dashboard mostrará las columnas de estados de pedidos
- Los pedidos nuevos aparecerán automáticamente con sonido y efectos visuales

### 2. Configurar PoS (si usas Punto de Venta)
- Abrir una sesión PoS
- Los botones de notificaciones aparecerán automáticamente
- Usar el botón "Enviar a Cocina" para enviar pedidos al dashboard

## Uso del Sistema

### Para el Personal del Restaurante

1. **Dashboard Principal**: Visualizar todos los pedidos organizados por estado
2. **Gestión de Pedidos**: 
   - Arrastrar tarjetas entre columnas para cambiar estados
   - Usar botones "Aceptar/Rechazar" para pedidos nuevos
   - Usar botón "Siguiente" para avanzar estados
3. **Notificaciones PoS**: 
   - Botón azul: Nuevos pedidos web
   - Botón verde: Pedidos delivery listos
   - Botón morado: Pedidos pickup listos

### Para los Clientes (eCommerce)

1. **Realizar Pedido**: Crear pedido desde el sitio web
2. **Página de Confirmación**: Después del pago, ver:
   - Número de pedido
   - Estado en tiempo real con barra de progreso
   - Detalle completo de productos
   - Información de entrega (dirección si es delivery)
   - Tiempo transcurrido y estimado
3. **Seguimiento Continuo**: La página se actualiza automáticamente cada 30 segundos
4. **Confirmación de Recepción**: Cuando el pedido esté despachado, confirmar recepción o reportar problemas
5. **Portal de Pedidos**: Acceder a /my/orders para ver historial completo

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
- `tiempo_estimado_entrega`: Tiempo estimado de entrega en minutos
- `tiene_reclamo`: Boolean si el cliente generó un reclamo
- `descripcion_reclamo`: Descripción del reclamo del cliente

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

## Funcionalidades Principales

### ✅ Dashboard Interactivo
- Vista Kanban con drag & drop
- Estados en tiempo real
- Notificaciones automáticas
- Seguimiento de tiempos

### ✅ Sistema de Notificaciones
- 3 tipos de notificaciones PoS
- Botones flotantes con contadores
- Modales informativos
- Formateo inteligente

### ✅ Integración Completa
- eCommerce y PoS unificados
- APIs para seguimiento
- Confirmación de cliente
- Automatizaciones inteligentes

## Soporte

- **Repositorio**: https://github.com/WalterHalm/tu_pedido_v2
- **Issues**: Reportar problemas en GitHub
- **Documentación**: Ver archivos incluidos en el módulo

## Licencia

LGPL-3

---

**Versión**: 2.3.0  
**Última actualización**: Enero 2025  
**Autor**: Walter Halm - Tu Pedido v2

---

## Changelog v2.3.0

### ✨ Nuevas Funcionalidades
- **Control de compras por sesión PoS**: El sitio web solo permite compras cuando hay sesión PoS abierta
- **Filtros avanzados en dashboard**: Filtrar por fecha, cliente, origen (Web/PoS) y estado
- **Pedidos solo al confirmar pago**: Los pedidos web aparecen en dashboard solo después del pago confirmado
- **Banner de estado en carrito**: Indica si el local está abierto o cerrado
- **Página /shop/closed**: Vista personalizada cuando el local está cerrado

### 🔧 Mejoras v2.3.0
- Filtro por defecto muestra pedidos de "Hoy"
- Mejor manejo de errores en confirmación de recepción
- Corrección de wizard para aceptar/rechazar pedidos
- Eliminación de código JavaScript en desuso
- Optimización de controladores

---

## Changelog v2.2.0

### ✨ Nuevas Funcionalidades
- **Página de confirmación mejorada**: Interfaz completa con toda la información del pedido
- **Detalles de productos**: El cliente ve exactamente qué ordenó con precios
- **Información de entrega**: Muestra dirección completa si es delivery o indica retiro en local
- **Botones de acción**: Confirmar recepción o reportar problemas directamente

### 🔧 Mejoras
- Mejor experiencia visual con cards y colores
- Emojis intuitivos para cada estado
- Actualización automática de estado cada 30 segundos
- Enlace directo al portal de pedidos
- Diseño responsive para móviles