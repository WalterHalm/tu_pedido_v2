from odoo import http, fields
from odoo.http import request
import json

class EcommerceController(http.Controller):

    @http.route('/tu_pedido_v2/estado_restaurante', type='json', auth='public')
    def estado_restaurante(self):
        """API para verificar si el restaurante está abierto (siempre abierto ahora)"""
        try:
            return {
                'success': True,
                'abierto': True,
                'fecha_apertura': fields.Datetime.now().isoformat(),
                'hora_cierre_estimada': 22.0,
                'mensaje': 'Restaurante abierto'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'abierto': True
            }

    @http.route('/tu_pedido_v2/estado_pedido/<int:order_id>', type='json', auth='public')
    def estado_pedido(self, order_id):
        """API para que el cliente consulte el estado de su pedido"""
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return {
                    'success': False,
                    'error': 'Pedido no encontrado'
                }
            
            # Mapear estados para el cliente
            estados_cliente = {
                'nuevo': {'nombre': 'Recibido', 'progreso': 10, 'descripcion': 'Tu pedido ha sido recibido'},
                'aceptado': {'nombre': 'Confirmado', 'progreso': 25, 'descripcion': 'Tu pedido ha sido confirmado'},
                'preparacion': {'nombre': 'En Preparación', 'progreso': 50, 'descripcion': 'Estamos preparando tu pedido'},
                'terminado': {'nombre': 'Listo', 'progreso': 75, 'descripcion': 'Tu pedido está listo'},
                'despachado': {'nombre': 'Despachado', 'progreso': 90, 'descripcion': 'Tu pedido ha sido despachado'},
                'entregado': {'nombre': 'Entregado', 'progreso': 100, 'descripcion': 'Pedido entregado exitosamente'},
                'rechazado': {'nombre': 'Rechazado', 'progreso': 0, 'descripcion': 'Lo sentimos, tu pedido fue rechazado'}
            }
            
            estado_actual = estados_cliente.get(order.estado_rapido, {
                'nombre': 'Desconocido', 
                'progreso': 0, 
                'descripcion': 'Estado desconocido'
            })
            
            return {
                'success': True,
                'pedido': {
                    'id': order.id,
                    'nombre': order.name,
                    'cliente': order.partner_id.name,
                    'estado_codigo': order.estado_rapido,
                    'estado': estado_actual,
                    'tiempo_transcurrido': order.tiempo_total_minutos,
                    'puede_confirmar_recepcion': order.estado_rapido == 'despachado' and not order.cliente_confirmo_recepcion,
                    'productos': [{
                        'nombre': line.product_id.name,
                        'cantidad': line.product_uom_qty,
                        'precio': line.price_unit
                    } for line in order.order_line]
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/tu_pedido_v2/confirmar_recepcion/<int:order_id>', type='json', auth='public')
    def confirmar_recepcion(self, order_id):
        """API para que el cliente confirme que recibió su pedido"""
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return {
                    'success': False,
                    'error': 'Pedido no encontrado'
                }
            
            if order.estado_rapido != 'despachado':
                return {
                    'success': False,
                    'error': 'El pedido no está en estado despachado'
                }
            
            order.action_cliente_confirma_recepcion()
            
            return {
                'success': True,
                'mensaje': 'Recepción confirmada exitosamente'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/tu_pedido_v2/crear_pedido', type='json', auth='public', methods=['POST'])
    def crear_pedido_ecommerce(self, **kwargs):
        """API para crear pedidos desde el eCommerce"""
        try:
            
            # Obtener datos del pedido
            partner_id = kwargs.get('partner_id')
            productos = kwargs.get('productos', [])
            nota_cocina = kwargs.get('nota_cocina', '')
            
            if not partner_id or not productos:
                return {
                    'success': False,
                    'error': 'Datos incompletos para crear el pedido'
                }
            
            # Crear el pedido
            order_vals = {
                'partner_id': partner_id,
                'state': 'draft',
                'nota_cocina': nota_cocina,
                'order_line': []
            }
            
            # Agregar líneas de productos
            for producto in productos:
                line_vals = (0, 0, {
                    'product_id': producto['product_id'],
                    'product_uom_qty': producto['quantity'],
                    'price_unit': producto.get('price_unit', 0)
                })
                order_vals['order_line'].append(line_vals)
            
            order = request.env['sale.order'].sudo().create(order_vals)
            
            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'mensaje': 'Pedido creado exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/tu_pedido_v2/widget_estado/<int:order_id>', type='http', auth='public')
    def widget_estado_pedido(self, order_id):
        """Widget HTML para mostrar el estado del pedido al cliente"""
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.render('tu_pedido_v2.widget_pedido_no_encontrado')
            
            return request.render('tu_pedido_v2.widget_estado_pedido', {
                'order': order,
                'estados_progreso': {
                    'nuevo': 10,
                    'aceptado': 25,
                    'preparacion': 50,
                    'terminado': 75,
                    'despachado': 90,
                    'entregado': 100,
                    'rechazado': 0
                }
            })
        except Exception as e:
            return f"<div class='alert alert-danger'>Error: {str(e)}</div>"

    @http.route('/tu_pedido_v2/generar_reclamo/<int:order_id>', type='json', auth='public')
    def generar_reclamo(self, order_id, **kwargs):
        try:
            motivo = kwargs.get('motivo', '')
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return {
                    'success': False,
                    'error': 'Pedido no encontrado'
                }
            
            order.write({
                'tiene_reclamo': True,
                'descripcion_reclamo': motivo
            })
            
            return {
                'success': True,
                'mensaje': 'Reclamo generado exitosamente'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }