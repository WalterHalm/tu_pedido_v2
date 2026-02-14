# Changelog - Tu Pedido v2

Todos los cambios notables de este proyecto serán documentados en este archivo.

---

## [2.3.0] - 2025-01-15

### ✨ Nuevas Funcionalidades

#### Control de Compras por Sesión PoS
- El sitio web solo permite realizar compras cuando hay una sesión PoS abierta
- Banner visual en el carrito indicando si el local está abierto o cerrado
- Página personalizada `/shop/closed` cuando el local está cerrado
- Verificación automática cada 30 segundos para detectar apertura

#### Filtros Avanzados en Dashboard
- **Filtro por Fecha**: Hoy (por defecto), Ayer, Últimos 7 días, Todos
- **Filtro por Cliente**: Búsqueda en tiempo real por nombre
- **Filtro por Origen**: Web o Punto de Venta
- **Filtro por Estado**: Todos los estados del pedido
- Botón "Limpiar Filtros" para resetear

#### Optimización de Pedidos Web
- Los pedidos del eCommerce solo aparecen en el dashboard después de confirmar el pago
- Eliminado el problema de pedidos en borrador apareciendo en el dashboard
- Campo `estado_rapido` sin valor por defecto para evitar activación prematura

### 🔧 Mejoras

#### Dashboard
- Filtro por defecto muestra solo pedidos de "Hoy"
- Mejor organización al instalar en nuevas bases de datos
- Corrección de filtro de origen (Web vs PoS)
- Agregado campo `create_date` para filtros de fecha

#### Experiencia del Cliente
- Mejor manejo de errores en confirmación de recepción
- Mensajes más amigables al confirmar entrega
- Corrección de error "undefined" en alertas JavaScript

#### Código
- Eliminado archivo `shop_confirmation.js` en desuso
- Limpieza de assets en manifest
- Corrección de nombres de modelos en wizards
- Optimización de controladores

### 🐛 Correcciones

- Corregido error 404 en wizard `tu_pedido.aceptar_pedido_wizard` → `tu_pedido_v2.aceptar_pedido_wizard`
- Corregido error AttributeError en método `checkout` del controlador
- Corregido filtro de fecha que no funcionaba correctamente
- Corregido filtro de origen que no distinguía entre Web y PoS

### 📚 Documentación

- Actualizado README.md con nuevas funcionalidades
- Creado CHANGELOG.md para seguimiento de versiones
- Documentación de control de compras por sesión PoS
- Documentación de filtros avanzados

---

## [2.2.0] - 2025-01-10

### ✨ Nuevas Funcionalidades

#### Página de Confirmación Mejorada
- Número de pedido destacado y visible
- Barra de progreso en tiempo real con porcentajes
- Detalle completo de productos ordenados con precios
- Información de entrega (delivery o pickup)
- Dirección completa si es delivery
- Tiempo transcurrido y estimado
- Actualización automática cada 30 segundos
- Botones para confirmar recepción o reportar problemas

#### Filtro de Dashboard
- Solo muestra pedidos del día actual por defecto
- Mejora la organización y rendimiento
- Se reinicia automáticamente a las 00:00

### 🔧 Mejoras

- Mejor experiencia visual con cards y sombras
- Emojis intuitivos para cada estado del pedido
- Enlace directo al portal de pedidos (/my/orders)
- Diseño responsive para dispositivos móviles
- Colores más intuitivos y profesionales

---

## [2.1.0] - 2025-01-05

### ✨ Nuevas Funcionalidades

#### Sistema de Notificaciones Unificado
- **Notificaciones Web**: Pedidos nuevos del eCommerce (botón azul)
- **Notificaciones Delivery**: Pedidos terminados para envío (botón verde)
- **Notificaciones Pickup**: Pedidos terminados para retiro (botón morado)
- Botones flotantes con contadores en tiempo real
- Modales informativos con acciones rápidas

#### Dashboard Interactivo
- Vista Kanban con drag & drop
- 7 estados de pedidos
- Notificaciones sonoras automáticas
- Efectos visuales para pedidos nuevos
- Seguimiento de tiempos por estado

#### Integración eCommerce
- API para verificar estado del restaurante
- Creación automática de pedidos
- Widget de seguimiento para clientes
- Confirmación de recepción por el cliente

### 🔧 Mejoras

- Formateo inteligente de nombres de mesa
- Detección automática de tipo de entrega
- Automatización de confirmación de órdenes
- Sistema de reclamos para clientes

---

## [2.0.0] - 2024-12-20

### ✨ Release Inicial

- Dashboard básico de pedidos
- Integración con PoS
- Estados de pedidos
- Notificaciones básicas

---

## Formato del Changelog

Este changelog sigue el formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

### Tipos de Cambios

- `✨ Nuevas Funcionalidades` - para nuevas características
- `🔧 Mejoras` - para cambios en funcionalidades existentes
- `🐛 Correcciones` - para corrección de bugs
- `📚 Documentación` - para cambios en documentación
- `🗑️ Deprecado` - para características que serán removidas
- `❌ Removido` - para características removidas
- `🔒 Seguridad` - para correcciones de seguridad
