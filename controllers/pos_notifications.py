from odoo import http
from odoo.http import request
import json

class PosNotificationsController(http.Controller):
    
    def _format_table_name(self, name):
        """Formatear nombre de mesa para separar piso y número"""
        if not name:
            return name
        
        import re
        # Buscar patrón: letras + "Mesa" + números
        match = re.match(r'^([A-Za-z]+)(Mesa)(\d+)$', name)
        if match:
            floor = match.group(1)
            table_num = match.group(3)
            return f"{floor} Mesa {table_num}"
        
        return name

    @http.route('/tu_pedido_v2/pos_delivery_notifications', type='json', auth='user')
    def get_pos_delivery_notifications(self):
        """Obtener notificaciones de delivery para el PoS"""
        notifications = []
        
        # Debug: buscar TODOS los pedidos terminados
        all_terminados = request.env['sale.order'].sudo().search([('estado_rapido', '=', 'terminado')])
        print(f"🔍 Total terminados: {len(all_terminados)}")
        for o in all_terminados:
            print(f"  - {o.name}: es_para_envio={o.es_para_envio}")
        
        # Buscar pedidos delivery terminados (tanto PoS como Sale)
        # PoS orders
        pos_delivery_orders = request.env['pos.order'].sudo().search([
            ('is_delivery', '=', True),
            ('estado_rapido', '=', 'terminado')
        ])
        
        for order in pos_delivery_orders:
            order_name = order.tracking_number or order.name
            # Formatear nombre si es de mesa
            if order_name and not order.tracking_number:
                order_name = self._format_table_name(order_name)
            
            notifications.append({
                'id': f'pos_{order.id}',
                'order_name': order_name,
                'cliente': order.partner_id.name if order.partner_id else 'Cliente PoS',
                'direccion': order.direccion_delivery or 'Sin dirección',
                'telefono': order.telefono_delivery or 'Sin teléfono',
                'tipo': 'pos'
            })
        
        # Sale orders (pedidos web)
        sale_delivery_orders = request.env['sale.order'].sudo().search([
            ('es_para_envio', '=', True),
            ('estado_rapido', '=', 'terminado')
        ])
        print(f"🚚 Delivery terminados: {len(sale_delivery_orders)}")
        
        for order in sale_delivery_orders:
            # Determinar tipo real: web si tiene website_id, pos si tiene tracking en nota_cocina
            tipo = 'web'
            if not order.website_id and order.nota_cocina and '[REF:' in order.nota_cocina:
                tipo = 'pos'
            
            order_name = order.name
            # Formatear nombre si es de mesa (pedidos PoS creados como sale.order)
            if not order.website_id and order.nota_cocina and '[REF:' in order.nota_cocina:
                order_name = self._format_table_name(order_name)
            
            notifications.append({
                'id': f'sale_{order.id}',
                'order_name': order_name,
                'cliente': order.partner_id.name,
                'direccion': order.direccion_entrega_completa or 'Sin dirección',
                'telefono': order.partner_id.phone or order.partner_id.mobile or 'Sin teléfono',
                'tipo': tipo
            })
        
        return {'notifications': notifications}
    
    @http.route('/tu_pedido_v2/pos_pickup_notifications', type='json', auth='user')
    def get_pos_pickup_notifications(self):
        """Obtener notificaciones de pedidos listos para retirar"""
        notifications = []
        
        # Buscar pedidos para retirar terminados (tanto PoS como Sale)
        # PoS orders
        pos_pickup_orders = request.env['pos.order'].sudo().search([
            ('is_delivery', '=', False),
            ('estado_rapido', '=', 'terminado')
        ])
        
        for order in pos_pickup_orders:
            order_name = order.tracking_number or order.name
            # Formatear nombre si es de mesa
            if order_name and not order.tracking_number:
                order_name = self._format_table_name(order_name)
            
            notifications.append({
                'id': f'pos_{order.id}',
                'order_name': order_name,
                'cliente': order.partner_id.name if order.partner_id else 'Cliente PoS',
                'telefono': order.telefono_delivery or 'Sin teléfono',
                'tipo': 'pos'
            })
        
        # Sale orders (pedidos web para retirar)
        sale_pickup_orders = request.env['sale.order'].sudo().search([
            ('es_para_envio', '=', False),
            ('estado_rapido', '=', 'terminado')
        ])
        
        for order in sale_pickup_orders:
            # Determinar tipo real: web si tiene website_id, pos si tiene tracking en nota_cocina
            tipo = 'web'
            if not order.website_id and order.nota_cocina and '[REF:' in order.nota_cocina:
                tipo = 'pos'
            
            order_name = order.name
            # Formatear nombre si es de mesa (pedidos PoS creados como sale.order)
            if not order.website_id and order.nota_cocina and '[REF:' in order.nota_cocina:
                order_name = self._format_table_name(order_name)
            
            notifications.append({
                'id': f'sale_{order.id}',
                'order_name': order_name,
                'cliente': order.partner_id.name,
                'telefono': order.partner_id.phone or order.partner_id.mobile or 'Sin teléfono',
                'tipo': tipo
            })
        
        return {'notifications': notifications}
    
    @http.route('/tu_pedido_v2/pos_web_notifications', type='json', auth='user')
    def get_pos_web_notifications(self):
        """Obtener notificaciones de pedidos web nuevos para el PoS"""
        notifications = []
        
        # Buscar pedidos web en estado nuevo
        web_orders = request.env['sale.order'].sudo().search([
            ('website_id', '!=', False),
            ('estado_rapido', '=', 'nuevo')
        ])
        
        for order in web_orders:
            # Preparar productos
            productos_resumen = []
            for line in order.order_line[:3]:
                productos_resumen.append(f"{line.product_uom_qty}x {line.name}")
            
            productos_text = ', '.join(productos_resumen)
            if len(order.order_line) > 3:
                productos_text += f" y {len(order.order_line) - 3} más"
            
            notifications.append({
                'id': order.id,
                'order_name': order.name,
                'cliente': order.partner_id.name,
                'telefono': order.partner_id.phone or order.partner_id.mobile or 'Sin teléfono',
                'direccion': order.direccion_entrega_completa or 'Retiro en local',
                'es_para_envio': order.es_para_envio,
                'productos': productos_text,
                'amount_total': order.amount_total,
                'create_date': order.create_date.isoformat()
            })
            
            # Marcar como visto para evitar duplicados en la primera carga
            if order.sonido_activo:
                order.sonido_activo = False
        
        return {'notifications': notifications}

    @http.route('/tu_pedido_v2/mark_delivery_dispatched', type='json', auth='user')
    def mark_delivery_dispatched(self):
        """Marcar pedido delivery como despachado"""
        try:
            data = request.get_json_data()
            order_id = data.get('order_id') if data else None
            
            if not order_id:
                return {'success': False, 'message': 'order_id requerido'}
            
            # Determinar si es PoS o Sale order
            if str(order_id).startswith('pos_'):
                real_id = int(order_id.replace('pos_', ''))
                order = request.env['pos.order'].sudo().browse(real_id)
                if order.exists():
                    order.action_cambiar_estado('despachado')
                    return {'success': True}
            elif str(order_id).startswith('sale_'):
                real_id = int(order_id.replace('sale_', ''))
                order = request.env['sale.order'].sudo().browse(real_id)
                if order.exists():
                    order.action_cambiar_estado('despachado')
                    return {'success': True}
            
            return {'success': False, 'message': 'Pedido no encontrado'}
        except Exception as e:
            return {'success': False, 'message': str(e)}