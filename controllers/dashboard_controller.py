from odoo import http, fields
from odoo.http import request
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class PedidoDashboardController(http.Controller):

    # Ruta HTTP eliminada - se usa solo client action
    
    @http.route('/tu_pedido_v2/dashboard_data', type='json', auth='user')
    def dashboard_data(self):
        # Fecha límite para pedidos rechazados (24 horas)
        fecha_limite = datetime.now() - timedelta(hours=24)
        
        # Obtener pedidos de venta (incluir todos los que tienen estado_rapido)
        pedidos_venta = request.env['sale.order'].sudo().search([
            ('estado_rapido', '!=', False),  # Todos los que tienen estado_rapido
            ('estado_rapido', '!=', 'entregado'),
            '|',
            ('estado_rapido', '!=', 'rechazado'),
            ('create_date', '>=', fecha_limite)
        ])
        
        # Corregir pedidos sin estado que tienen tracking en nota_cocina
        pedidos_sin_estado = request.env['sale.order'].sudo().search([
            ('estado_rapido', '=', False),
            ('nota_cocina', 'ilike', '[REF:')
        ])
        
        for pedido in pedidos_sin_estado:
            pedido.write({
                'estado_rapido': 'nuevo',
                'tiempo_inicio_estado': datetime.now(),
                'tiempo_inicio_total': datetime.now(),
                'sonido_activo': True
            })
        
        # Corregir pedidos web sin estado
        pedidos_web_sin_estado = request.env['sale.order'].sudo().search([
            ('website_id', '!=', False),
            ('estado_rapido', '=', False),
            ('state', '=', 'sale')
        ])
        
        for pedido in pedidos_web_sin_estado:
            pedido.write({
                'estado_rapido': 'nuevo',
                'tiempo_inicio_estado': datetime.now(),
                'tiempo_inicio_total': datetime.now(),
                'sonido_activo': True
            })
            pedido._detectar_tipo_entrega()
        
        # Volver a buscar incluyendo los corregidos
        pedidos_venta = request.env['sale.order'].sudo().search([
            ('estado_rapido', '!=', False),  # Todos los que tienen estado_rapido
            ('estado_rapido', '!=', 'entregado'),
            '|',
            ('estado_rapido', '!=', 'rechazado'),
            ('create_date', '>=', fecha_limite)
        ])
        
        # Logs de depuración removidos para producción
        
        # Debug logs removidos para producción
        
        # Obtener pedidos PoS enviados a cocina (incluir cancelados, excluir rechazados antiguos)
        pedidos_pos = request.env['pos.order'].sudo().search([
            ('enviado_a_cocina', '=', True),
            ('estado_rapido', '!=', False),
            ('estado_rapido', '!=', 'entregado'),
            '|',
            ('estado_rapido', '!=', 'rechazado'),
            ('create_date', '>=', fecha_limite)
        ]) if 'pos.order' in request.env else request.env['pos.order'].sudo().browse([])
        
        # Debug logs removidos para producción
        
        estados = [
            ('nuevo', 'Nuevo'),
            ('aceptado', 'Aceptado'), 
            ('preparacion', 'En Preparación'),
            ('terminado', 'Terminado'),
            ('despachado', 'Despachado/Retirado'),
            ('rechazado', 'Rechazado')
        ]
        
        columnas = []
        for estado_key, estado_nombre in estados:
            orders_data = []
            
            # Procesar pedidos de venta
            ordenes_venta = pedidos_venta.filtered(lambda p: p.estado_rapido == estado_key)
            for orden in ordenes_venta:
                # Verificar delivery para pedidos terminados
                if estado_key == 'terminado' and hasattr(orden, 'es_para_envio'):
                    orden._detectar_tipo_entrega()
                
                productos = self._get_productos_sale_order(orden)
                
                # Forzar detección de tipo de entrega si no se ha hecho
                if hasattr(orden, 'es_para_envio') and not orden.es_para_envio and not getattr(orden, 'direccion_entrega_completa', ''):
                    orden._detectar_tipo_entrega()
                
                # Verificar cancelación de sale.order y PoS correspondiente
                is_cancelled = orden.state == 'cancel'
                motivo_cancelacion = ''
                
                # Verificar si hay nota de cancelación en nota_cocina
                if '[CANCELADO]' in (orden.nota_cocina or ''):
                    is_cancelled = True
                    motivo_cancelacion = 'Pedido cancelado desde PoS'
                elif orden.state == 'cancel':
                    motivo_cancelacion = 'Pedido cancelado desde Ventas'
                
                # Debug para cancelaciones
                if is_cancelled:
                    _logger.info(f"DEBUG: Pedido cancelado detectado: {orden.name}, motivo: {motivo_cancelacion}")
                
                orders_data.append({
                    'id': orden.id,
                    'name': self._format_table_name(orden.name),
                    'partner_id': [orden.partner_id.id, orden.partner_id.name or 'Cliente'],
                    'estado_rapido': orden.estado_rapido,
                    'nota_cocina': getattr(orden, 'nota_cocina', '') or '',
                    'productos': productos,
                    'tiempo_estado': orden.tiempo_estado_minutos,
                    'tiempo_total': orden.tiempo_total_minutos,
                    'sonido_activo': getattr(orden, 'sonido_activo', False),
                    'cliente_confirmo_recepcion': getattr(orden, 'cliente_confirmo_recepcion', False),
                    'tiene_reclamo': getattr(orden, 'tiene_reclamo', False),
                    'descripcion_reclamo': getattr(orden, 'descripcion_reclamo', '') or '',
                    'productos_modificados': getattr(orden, 'productos_modificados', False),
                    'productos_snapshot': bool(getattr(orden, 'productos_snapshot', False)),
                    'es_para_envio': getattr(orden, 'es_para_envio', False),
                    'direccion_entrega_completa': getattr(orden, 'direccion_entrega_completa', '') or '',
                    'pedido_cancelado': is_cancelled,
                    'motivo_cancelacion': motivo_cancelacion,
                    'tipo_pedido': 'web',
                    'mesa': '',
                    'comensales': 0
                })
            
            # Procesar pedidos PoS si existen
            if pedidos_pos:
                # Solo mostrar pedidos en su estado actual, cancelados mantienen su estado pero con indicador
                ordenes_pos = pedidos_pos.filtered(lambda p: p.estado_rapido == estado_key)
                
                for orden in ordenes_pos:
                    productos = self._get_productos_pos_order(orden)
                    
                    # Obtener información de ubicación
                    mesa_info = ''
                    if getattr(orden, 'is_delivery', False):
                        direccion = getattr(orden, 'direccion_delivery', '') or 'Sin dirección'
                        telefono = getattr(orden, 'telefono_delivery', '') or 'Sin teléfono'
                        mesa_info = f"📍 {direccion} | 📞 {telefono}"
                    elif hasattr(orden, 'table_id') and orden.table_id:
                        mesa_info = f"Mesa {orden.table_id.table_number}"
                    
                    # Obtener notas de cocina
                    nota_cocina = ''
                    # Nota general de la orden
                    if hasattr(orden, 'general_note') and orden.general_note:
                        nota_cocina = orden.general_note
                    
                    # Agregar notas de las líneas de productos
                    line_notes = []
                    for line in orden.lines:
                        if hasattr(line, 'customer_note') and line.customer_note:
                            line_notes.append(f"{line.product_id.name}: {line.customer_note}")
                        elif hasattr(line, 'note') and line.note:
                            line_notes.append(f"{line.product_id.name}: {line.note}")
                    
                    if line_notes:
                        if nota_cocina:
                            nota_cocina += " | " + " | ".join(line_notes)
                        else:
                            nota_cocina = " | ".join(line_notes)
                    
                    # Determinar el nombre a mostrar: Delivery, Piso Mesa# o tracking_number
                    display_name = orden.tracking_number  # Por defecto
                    if getattr(orden, 'is_delivery', False):
                        display_name = f"🚚 DELIVERY {orden.tracking_number}"
                    elif hasattr(orden, 'table_id') and orden.table_id:
                        floor_name = orden.table_id.floor_id.name if orden.table_id.floor_id else 'Piso'
                        table_num = orden.table_id.table_number
                        display_name = f"{floor_name} Mesa {table_num}"  # Added space
                    
                    orders_data.append({
                        'id': f'pos_{orden.id}',
                        'name': display_name,
                        'partner_id': [orden.partner_id.id if orden.partner_id else 0, orden.partner_id.name if orden.partner_id else 'Cliente PoS'],
                        'estado_rapido': orden.estado_rapido,
                        'nota_cocina': nota_cocina,
                        'productos': productos,
                        'tiempo_estado': orden.tiempo_estado_minutos,
                        'tiempo_total': orden.tiempo_total_minutos,
                        'sonido_activo': orden.sonido_activo,
                        'cliente_confirmo_recepcion': False,
                        'tiene_reclamo': False,
                        'descripcion_reclamo': '',
                        'productos_modificados': False,
                        'es_para_envio': getattr(orden, 'is_delivery', False),
                        'direccion_entrega_completa': getattr(orden, 'direccion_delivery', '') or '',
                        'pedido_cancelado': orden.state == 'cancel',
                        'motivo_cancelacion': 'Pedido cancelado desde PoS' if orden.state == 'cancel' else '',
                        'tipo_pedido': getattr(orden, 'tipo_pedido', 'mostrador'),
                        'mesa': mesa_info,
                        'comensales': getattr(orden, 'customer_count', 0) or 0
                    })
            
            columnas.append({
                'key': estado_key,
                'title': estado_nombre,
                'orders': orders_data,
                'count': len(orders_data)
            })
        
        return {'columns': columnas}
    
    def _format_table_name(self, name):
        """Format table name to separate floor and table number"""
        if not name:
            return name
        
        # Look for pattern like "TerrazaMesa3" -> "Terraza Mesa 3"
        import re
        # Match pattern: letters + "Mesa" + numbers
        match = re.match(r'^([A-Za-z]+)(Mesa)(\d+)$', name)
        if match:
            floor = match.group(1)
            table_num = match.group(3)
            return f"{floor} Mesa {table_num}"
        
        return name
    
    def _check_pos_cancellation(self, sale_order):
        """Check if corresponding PoS order is cancelled"""
        try:
            # Extract tracking number from nota_cocina
            nota_cocina = sale_order.nota_cocina or ''
            if '[REF:' not in nota_cocina:
                return False
            
            start = nota_cocina.find('[REF:') + 5
            end = nota_cocina.find(']', start)
            if end == -1:
                return False
            
            tracking_number = nota_cocina[start:end]
            
            # Search cancelled PoS order with matching tracking
            cancelled_pos_order = request.env['pos.order'].sudo().search([
                ('state', '=', 'cancel'),
                ('tracking_number', '=', tracking_number)
            ], limit=1)
            
            if cancelled_pos_order:
                _logger.info(f"DEBUG: Found cancelled PoS order {cancelled_pos_order.name} with tracking {tracking_number}")
                return True
            
            return False
        except Exception as e:
            _logger.info(f"DEBUG: Error checking PoS cancellation: {e}")
            return False
    
    def _get_productos_sale_order(self, orden):
        """Obtener productos de sale.order"""
        productos = []
        completados = orden.get_productos_completados()
        
        for line in orden.order_line:
            producto_info = {
                'id': line.id,  # ID de la línea para poder marcarla
                'name': line.name,  # Usar line.name que contiene el nombre completo con combos
                'qty': line.product_uom_qty,
                'uom': line.product_uom.name,
                'attributes': [],
                'completado': line.id in completados  # Si está marcado como completado
            }
            
            # Agregar atributos del producto si existen
            if hasattr(line, 'product_no_variant_attribute_value_ids'):
                for attr in line.product_no_variant_attribute_value_ids:
                    producto_info['attributes'].append({
                        'attribute': attr.attribute_id.name,
                        'value': attr.name
                    })
            if hasattr(line, 'product_template_attribute_value_ids'):
                for attr in line.product_template_attribute_value_ids:
                    producto_info['attributes'].append({
                        'attribute': attr.attribute_id.name,
                        'value': attr.name
                    })
            
            productos.append(producto_info)
        return productos
    
    def _get_productos_pos_order(self, orden):
        """Obtener productos de pos.order"""
        productos = []
        for line in orden.lines:
            productos.append({
                'name': line.product_id.name,
                'qty': line.qty,
                'uom': line.product_id.uom_id.name,
                'attributes': []  # PoS no maneja atributos complejos
            })
        return productos

    @http.route('/tu_pedido_v2/cambiar_estado', type='json', auth='user')
    def cambiar_estado(self, order_id, nuevo_estado):
        try:
            # Determinar si es pedido PoS o Sale
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                orden = request.env['pos.order'].sudo().browse(real_id)
            else:
                # Asegurar que order_id es entero para sale.order
                order_id = int(order_id) if isinstance(order_id, str) and order_id.isdigit() else order_id
                orden = request.env['sale.order'].sudo().browse(order_id)
            
            if orden.exists():
                orden.action_cambiar_estado(nuevo_estado)
                return {'success': True, 'message': f'Estado cambiado a {nuevo_estado}'}
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/tu_pedido_v2/aceptar_pedido', type='json', auth='user')
    def aceptar_pedido(self, order_id):
        try:
            # Determinar si es pedido PoS o Sale
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                orden = request.env['pos.order'].sudo().browse(real_id)
                if orden.exists():
                    orden.action_cambiar_estado('aceptado')
                    return {'success': True, 'message': 'Pedido PoS aceptado'}
            else:
                orden = request.env['sale.order'].sudo().browse(order_id)
                if orden.exists():
                    wizard = request.env['tu_pedido_v2.aceptar_pedido_wizard'].sudo().create({
                        'order_id': order_id,
                        'tiempo_estimado': 30
                    })
                    wizard.action_aceptar()
                    return {'success': True, 'message': 'Pedido aceptado'}
            
            return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/tu_pedido_v2/rechazar_pedido', type='json', auth='user')
    def rechazar_pedido(self, order_id, motivo='Sin especificar'):
        try:
            # Determinar si es pedido PoS o Sale
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                orden = request.env['pos.order'].sudo().browse(real_id)
                if orden.exists():
                    orden.action_cambiar_estado('rechazado')
                    return {'success': True, 'message': 'Pedido PoS rechazado'}
            else:
                orden = request.env['sale.order'].sudo().browse(order_id)
                if orden.exists():
                    wizard = request.env['tu_pedido_v2.rechazar_pedido_wizard'].sudo().create({
                        'order_id': order_id,
                        'motivo_rechazo': motivo
                    })
                    wizard.action_rechazar()
                    return {'success': True, 'message': 'Pedido rechazado'}
            
            return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/tu_pedido_v2/siguiente_estado', type='json', auth='user')
    def siguiente_estado(self, order_id):
        try:
            # Determinar si es pedido PoS o Sale
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                orden = request.env['pos.order'].sudo().browse(real_id)
            else:
                order_id = int(order_id) if isinstance(order_id, str) and order_id.isdigit() else order_id
                orden = request.env['sale.order'].sudo().browse(order_id)
            
            if orden.exists():
                result = orden.action_siguiente_estado()
                if result:
                    return {'success': True, 'message': 'Estado avanzado'}
                else:
                    return {'success': False, 'message': 'Error al cambiar estado'}
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/tu_pedido_v2/pos_enviar_cocina', type='json', auth='user')
    def pos_enviar_cocina(self, order_id):
        """Enviar pedido PoS a cocina"""
        try:
            orden = request.env['pos.order'].sudo().browse(order_id)
            if orden.exists():
                result = orden.action_enviar_a_cocina()
                return {'success': True, 'message': 'Pedido enviado a cocina'}
            else:
                return {'success': False, 'message': 'Pedido no encontrado'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/tu_pedido_v2/toggle_producto', type='json', auth='user')
    def toggle_producto_completado(self, order_id, line_id):
        """Marcar/desmarcar producto como completado"""
        try:
            # Solo funciona para sale.order por ahora
            if str(order_id).startswith('pos_'):
                return {'success': False, 'message': 'No disponible para pedidos PoS'}
            
            orden = request.env['sale.order'].sudo().browse(order_id)
            if orden.exists():
                result = orden.toggle_producto_completado(line_id)
                return result
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @http.route('/tu_pedido_v2/get_detalles_cambios', type='json', auth='user')
    def get_detalles_cambios(self, order_id):
        """Obtener detalles de cambios en productos"""
        try:
            orden = request.env['sale.order'].sudo().browse(order_id)
            if orden.exists():
                detalles = orden.get_detalles_cambios()
                return {'success': True, 'detalles': detalles}
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @http.route('/tu_pedido_v2/aceptar_cambios_productos', type='json', auth='user')
    def aceptar_cambios_productos(self, order_id, motivo=''):
        """Aceptar cambios en productos"""
        try:
            orden = request.env['sale.order'].sudo().browse(order_id)
            if orden.exists():
                orden.action_marcar_productos_revisados()
                return {'success': True, 'message': 'Cambios aceptados'}
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @http.route('/tu_pedido_v2/rechazar_cambios_productos', type='json', auth='user')
    def rechazar_cambios_productos(self, order_id, motivo=''):
        """Rechazar cambios en productos"""
        try:
            orden = request.env['sale.order'].sudo().browse(order_id)
            if orden.exists():
                # Marcar como rechazado y agregar motivo
                orden.write({
                    'productos_modificados': False,
                    'nota_cocina': f"{orden.nota_cocina or ''} | CAMBIOS RECHAZADOS: {motivo}"
                })
                return {'success': True, 'message': 'Cambios rechazados'}
            else:
                return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @http.route('/tu_pedido_v2/confirmar_cancelacion', type='json', auth='user')
    def confirmar_cancelacion(self, order_id, notas=''):
        """Confirmar cancelación y mover a rechazado"""
        try:
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                orden = request.env['pos.order'].sudo().browse(real_id)
                if orden.exists():
                    orden.write({'estado_rapido': 'rechazado'})
                    return {'success': True, 'message': 'Pedido movido a rechazado'}
            else:
                orden = request.env['sale.order'].sudo().browse(order_id)
                if orden.exists():
                    orden.write({'estado_rapido': 'rechazado'})
                    return {'success': True, 'message': 'Pedido movido a rechazado'}
            
            return {'success': False, 'message': 'Orden no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}