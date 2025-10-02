from odoo import http, fields
from odoo.http import request
import json
from datetime import datetime, timedelta

class AnalyticsController(http.Controller):

    @http.route('/tu_pedido_v2/analytics_data', type='json', auth='user')
    def get_analytics_data(self, **kwargs):
        """Obtener datos de analytics para dashboard"""
        try:
            fecha_inicio = kwargs.get('fecha_inicio', fields.Date.today())
            fecha_fin = kwargs.get('fecha_fin', fields.Date.today())
            
            # Métricas principales
            analytics = request.env['tu_pedido.analytics'].sudo().search([
                ('fecha', '>=', fecha_inicio),
                ('fecha', '<=', fecha_fin)
            ])
            
            # Pedidos por hora
            pedidos_por_hora = {}
            for record in analytics:
                hora = record.hora_del_dia
                if hora not in pedidos_por_hora:
                    pedidos_por_hora[hora] = 0
                pedidos_por_hora[hora] += 1
            
            # Tiempo promedio por estado
            tiempos_por_estado = {}
            for estado in ['nuevo', 'aceptado', 'preparacion', 'terminado', 'despachado', 'entregado']:
                records_estado = analytics.filtered(lambda r: r.estado_actual == estado)
                if records_estado:
                    tiempos_por_estado[estado] = sum(records_estado.mapped('tiempo_total')) / len(records_estado)
                else:
                    tiempos_por_estado[estado] = 0
            
            # Top productos (simulado - necesitaría análisis de líneas)
            top_productos = [
                {'nombre': 'Pizza Margarita', 'cantidad': 23, 'ingresos': 1150.0},
                {'nombre': 'Hamburguesa Clásica', 'cantidad': 18, 'ingresos': 900.0},
                {'nombre': 'Papas Fritas', 'cantidad': 15, 'ingresos': 300.0},
            ]
            
            # Eficiencia por tipo
            eficiencia_delivery = analytics.filtered(lambda r: r.tipo_entrega == 'delivery')
            eficiencia_pickup = analytics.filtered(lambda r: r.tipo_entrega == 'pickup')
            
            return {
                'success': True,
                'data': {
                    'pedidos_por_hora': pedidos_por_hora,
                    'tiempos_por_estado': tiempos_por_estado,
                    'top_productos': top_productos,
                    'total_pedidos': len(analytics),
                    'ingresos_total': sum(analytics.mapped('monto_total')),
                    'tiempo_promedio': sum(analytics.mapped('tiempo_total')) / len(analytics) if analytics else 0,
                    'eficiencia_delivery': len(eficiencia_delivery.filtered(lambda r: r.estado_actual == 'entregado')) / len(eficiencia_delivery) * 100 if eficiencia_delivery else 0,
                    'eficiencia_pickup': len(eficiencia_pickup.filtered(lambda r: r.estado_actual == 'entregado')) / len(eficiencia_pickup) * 100 if eficiencia_pickup else 0,
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/tu_pedido_v2/metricas_tiempo_real', type='json', auth='user')
    def get_metricas_tiempo_real(self):
        """Métricas en tiempo real para widgets"""
        try:
            hoy = fields.Date.today()
            
            # Pedidos de hoy
            pedidos_hoy = request.env['tu_pedido.analytics'].sudo().search([
                ('fecha', '=', hoy)
            ])
            
            # Comparación con ayer
            ayer = hoy - timedelta(days=1)
            pedidos_ayer = request.env['tu_pedido.analytics'].sudo().search([
                ('fecha', '=', ayer)
            ])
            
            # Promedio últimos 7 días
            fecha_7_dias = hoy - timedelta(days=7)
            pedidos_semana = request.env['tu_pedido.analytics'].sudo().search([
                ('fecha', '>=', fecha_7_dias),
                ('fecha', '<', hoy)
            ])
            promedio_semanal = len(pedidos_semana) / 7 if pedidos_semana else 0
            
            return {
                'success': True,
                'metricas': {
                    'pedidos_hoy': len(pedidos_hoy),
                    'pedidos_ayer': len(pedidos_ayer),
                    'variacion_diaria': ((len(pedidos_hoy) - len(pedidos_ayer)) / len(pedidos_ayer) * 100) if pedidos_ayer else 0,
                    'promedio_semanal': round(promedio_semanal, 1),
                    'tiempo_promedio_hoy': sum(pedidos_hoy.mapped('tiempo_total')) / len(pedidos_hoy) if pedidos_hoy else 0,
                    'ingresos_hoy': sum(pedidos_hoy.mapped('monto_total')),
                    'eficiencia_hoy': len(pedidos_hoy.filtered(lambda r: r.estado_actual == 'entregado')) / len(pedidos_hoy) * 100 if pedidos_hoy else 0,
                    'pedidos_por_hora_actual': len(pedidos_hoy.filtered(lambda r: r.hora_del_dia == datetime.now().hour)),
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/tu_pedido_v2/export_analytics', type='http', auth='user')
    def export_analytics(self, **kwargs):
        """Exportar datos de analytics a CSV"""
        try:
            fecha_inicio = kwargs.get('fecha_inicio', fields.Date.today())
            fecha_fin = kwargs.get('fecha_fin', fields.Date.today())
            
            analytics = request.env['tu_pedido.analytics'].sudo().search([
                ('fecha', '>=', fecha_inicio),
                ('fecha', '<=', fecha_fin)
            ])
            
            # Generar CSV
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                'Fecha', 'Hora', 'Pedido', 'Cliente', 'Estado', 
                'Tiempo Total', 'Tipo Pedido', 'Tipo Entrega', 'Monto'
            ])
            
            # Datos
            for record in analytics:
                writer.writerow([
                    record.fecha,
                    record.hora,
                    record.pedido_nombre,
                    record.cliente_nombre,
                    record.estado_actual,
                    record.tiempo_total,
                    record.tipo_pedido,
                    record.tipo_entrega,
                    record.monto_total
                ])
            
            output.seek(0)
            
            return request.make_response(
                output.getvalue(),
                headers=[
                    ('Content-Type', 'text/csv'),
                    ('Content-Disposition', f'attachment; filename=analytics_{fecha_inicio}_{fecha_fin}.csv')
                ]
            )
        except Exception as e:
            return request.make_response(f'Error: {str(e)}', status=500)