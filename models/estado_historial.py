from odoo import models, fields, api, tools
from datetime import datetime

class EstadoHistorial(models.Model):
    _name = 'tu_pedido.estado.historial'
    _description = 'Historial de Estados de Pedidos'
    _order = 'fecha_cambio desc'

    pedido_id = fields.Many2one('sale.order', string='Pedido', required=True, ondelete='cascade')
    pedido_nombre = fields.Char(related='pedido_id.name', string='Número Pedido', store=True)
    
    estado_anterior = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado Anterior')
    
    estado_nuevo = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado Nuevo', required=True)
    
    fecha_cambio = fields.Datetime(string='Fecha de Cambio', default=fields.Datetime.now, required=True)
    minutos_en_estado_anterior = fields.Integer(string='Minutos en Estado Anterior')
    
    # Campos para análisis
    mes = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Mes', compute='_compute_periodo', store=True)
    
    año = fields.Integer(string='Año', compute='_compute_periodo', store=True)
    
    @api.depends('fecha_cambio')
    def _compute_periodo(self):
        for record in self:
            if record.fecha_cambio:
                record.mes = str(record.fecha_cambio.month)
                record.año = record.fecha_cambio.year
            else:
                record.mes = False
                record.año = False


class EstadoAnalytics(models.Model):
    _name = 'tu_pedido.estado.analytics'
    _description = 'Analytics por Estado'
    _auto = False
    _order = 'año desc, mes desc'

    # Campos de agrupación
    año = fields.Integer(string='Año')
    mes = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Mes')
    
    estado = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado')
    
    # Métricas
    total_pedidos = fields.Integer(string='Total Pedidos')
    tiempo_promedio = fields.Integer(string='Tiempo Promedio (min)')
    tiempo_total = fields.Integer(string='Tiempo Total (min)')
    tiempo_minimo = fields.Integer(string='Tiempo Mínimo (min)')
    tiempo_maximo = fields.Integer(string='Tiempo Máximo (min)')

    def init(self):
        """Crear vista SQL para analytics por estado"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    EXTRACT(year FROM eh.fecha_cambio) as año,
                    EXTRACT(month FROM eh.fecha_cambio) as mes,
                    eh.estado_anterior as estado,
                    COUNT(*) as total_pedidos,
                    FLOOR(AVG(eh.minutos_en_estado_anterior))::integer as tiempo_promedio,
                    SUM(eh.minutos_en_estado_anterior) as tiempo_total,
                    MIN(eh.minutos_en_estado_anterior) as tiempo_minimo,
                    MAX(eh.minutos_en_estado_anterior) as tiempo_maximo
                FROM tu_pedido_estado_historial eh
                WHERE eh.estado_anterior IS NOT NULL 
                    AND eh.minutos_en_estado_anterior >= 0
                    AND eh.minutos_en_estado_anterior IS NOT NULL
                GROUP BY 
                    EXTRACT(year FROM eh.fecha_cambio),
                    EXTRACT(month FROM eh.fecha_cambio),
                    eh.estado_anterior
                ORDER BY 
                    EXTRACT(year FROM eh.fecha_cambio) DESC,
                    EXTRACT(month FROM eh.fecha_cambio) DESC
            )
        """ % self._table)