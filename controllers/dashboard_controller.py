from odoo import http, fields
from odoo.http import request
from datetime import timedelta
import json

class DashboardController(http.Controller):
    
    @http.route('/tu_pedido/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        return request.render('tu_pedido_v2.dashboard_template', {})
    
    @http.route('/tu_pedido/get_pedidos', type='json', auth='user')
    def get_pedidos(self, fecha_filtro='hoy', cliente_filtro='', origen_filtro='', estado_filtro=''):
        pedidos_por_estado = {}
        estados = ['nuevo', 'aceptado', 'en_preparacion', 'terminado', 'despachado', 'entregado', 'rechazado']
        
        for estado in estados:
            domain = [('estado_rapido', '=', estado)]
            
            # Filtro de fecha
            if fecha_filtro == 'hoy':
                domain.append(('create_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0)))
            elif fecha_filtro == 'ayer':
                ayer = fields.Datetime.now() - timedelta(days=1)
                domain.extend([
                    ('create_date', '>=', ayer.replace(hour=0, minute=0, second=0)),
                    ('create_date', '<', fields.Datetime.now().replace(hour=0, minute=0, second=0))
                ])
            elif fecha_filtro == 'ultimos_7':
                domain.append(('create_date', '>=', fields.Datetime.now() - timedelta(days=7)))
            
            # Filtro de cliente
            if cliente_filtro:
                domain.append(('partner_id.name', 'ilike', cliente_filtro))
            
            # Filtro de origen
            if origen_filtro == 'web':
                domain.append(('website_id', '!=', False))
            elif origen_filtro == 'pos':
                domain.append(('website_id', '=', False))
            
            orders = request.env['sale.order'].search(domain, order='create_date desc')
            
            pedidos_por_estado[estado] = [{
                'id': order.id,
                'name': order.name,
                'partner_name': order.partner_id.name,
                'productos': self._get_productos_sale_order(order),
                'nota_cocina': order.nota_cocina or '',
                'tiempo_estado_minutos': order.tiempo_estado_minutos,
                'tiempo_total_minutos': order.tiempo_total_minutos,
                'sonido_activo': order.sonido_activo,
                'es_para_envio': order.es_para_envio,
                'origen': 'Web' if order.website_id else 'PoS',
            } for order in orders]
        
        return {'pedidos': pedidos_por_estado}
    
    def _get_productos_sale_order(self, order):
        productos = []
        for line in order.order_line:
            productos.append({
                'name': line.name,
                'qty': line.product_uom_qty,
                'uom': line.product_uom_id.name if line.product_uom_id else 'Unidad'
            })
        return productos
    
    @http.route('/tu_pedido/cambiar_estado', type='json', auth='user')
    def cambiar_estado(self, order_id, nuevo_estado):
        order = request.env['sale.order'].browse(order_id)
        if order.exists():
            order.action_cambiar_estado(nuevo_estado)
            return {'success': True}
        return {'success': False}
    
    @http.route('/tu_pedido/siguiente_estado', type='json', auth='user')
    def siguiente_estado(self, order_id):
        order = request.env['sale.order'].browse(order_id)
        if order.exists():
            order.action_siguiente_estado()
            return {'success': True}
        return {'success': False}
