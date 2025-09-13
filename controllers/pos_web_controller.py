from odoo import http
from odoo.http import request
from datetime import datetime, timedelta

class PosWebController(http.Controller):

    @http.route('/tu_pedido_v2/pedidos_web_activos', type='json', auth='user')
    def pedidos_web_activos(self):
        """Obtener pedidos web activos para mostrar en PoS"""
        try:
            # Buscar pedidos web activos (no entregados ni rechazados)
            pedidos = request.env['sale.order'].sudo().search([
                ('website_id', '!=', False),  # Solo pedidos web
                ('estado_rapido', 'not in', ['entregado', 'rechazado']),
                ('state', '=', 'sale'),  # Solo confirmados
                ('create_date', '>=', datetime.now() - timedelta(hours=12))  # Últimas 12 horas
            ], order='create_date desc', limit=10)

            pedidos_data = []
            for pedido in pedidos:
                # Obtener primeros 2 productos
                productos = []
                for line in pedido.order_line[:2]:
                    productos.append({
                        'name': line.name,
                        'qty': line.product_uom_qty
                    })

                pedidos_data.append({
                    'id': pedido.id,
                    'name': pedido.name,
                    'cliente': pedido.partner_id.name,
                    'telefono': pedido.partner_id.phone or pedido.partner_id.mobile or '',
                    'estado': pedido.estado_rapido,
                    'estado_display': dict(pedido._fields['estado_rapido'].selection)[pedido.estado_rapido],
                    'es_para_envio': pedido.es_para_envio,
                    'direccion': pedido.direccion_entrega_completa or 'Retiro en local',
                    'productos': productos,
                    'total_productos': len(pedido.order_line),
                    'amount_total': pedido.amount_total,
                    'create_date': pedido.create_date.isoformat(),
                    'tiempo_transcurrido': pedido.tiempo_total_minutos
                })

            return {
                'success': True,
                'pedidos': pedidos_data,
                'count': len(pedidos_data)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'pedidos': []
            }