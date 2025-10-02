from odoo import models, fields, api, tools

class TiempoDiarioEstado(models.Model):
    _name = 'tu_pedido.tiempo.diario.estado'
    _description = 'Tiempo Diario por Estado'
    _auto = False
    _order = 'fecha desc, estado'

    # Campos principales
    fecha = fields.Date(string='Fecha')
    estado = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado')
    
    # Métricas por día
    total_pedidos = fields.Integer(string='Total Pedidos')
    tiempo_promedio = fields.Integer(string='Tiempo Promedio (min)')
    tiempo_total = fields.Integer(string='Tiempo Total (min)')
    tiempo_minimo = fields.Integer(string='Tiempo Mínimo (min)')
    tiempo_maximo = fields.Integer(string='Tiempo Máximo (min)')
    
    # Campos para filtros
    dia_semana = fields.Selection([
        ('1', 'Lunes'), ('2', 'Martes'), ('3', 'Miércoles'),
        ('4', 'Jueves'), ('5', 'Viernes'), ('6', 'Sábado'), ('7', 'Domingo')
    ], string='Día de la Semana')
    
    mes = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Mes')

    def init(self):
        """Crear vista SQL para tiempos diarios por estado"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    DATE(eh.fecha_cambio) as fecha,
                    eh.estado_anterior as estado,
                    COUNT(*) as total_pedidos,
                    FLOOR(AVG(eh.minutos_en_estado_anterior))::integer as tiempo_promedio,
                    SUM(eh.minutos_en_estado_anterior) as tiempo_total,
                    MIN(eh.minutos_en_estado_anterior) as tiempo_minimo,
                    MAX(eh.minutos_en_estado_anterior) as tiempo_maximo,
                    EXTRACT(dow FROM eh.fecha_cambio) as dia_semana,
                    EXTRACT(month FROM eh.fecha_cambio) as mes
                FROM tu_pedido_estado_historial eh
                WHERE eh.estado_anterior IS NOT NULL 
                    AND eh.minutos_en_estado_anterior >= 0
                    AND eh.minutos_en_estado_anterior IS NOT NULL
                GROUP BY 
                    DATE(eh.fecha_cambio),
                    eh.estado_anterior,
                    EXTRACT(dow FROM eh.fecha_cambio),
                    EXTRACT(month FROM eh.fecha_cambio)
                ORDER BY 
                    DATE(eh.fecha_cambio) DESC,
                    eh.estado_anterior
            )
        """ % self._table)