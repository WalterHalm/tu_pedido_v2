from odoo import models, fields, api, tools
from datetime import datetime, timedelta
import json

class TuPedidoAnalytics(models.Model):
    _name = 'tu_pedido.analytics'
    _description = 'Analytics de Pedidos'
    _auto = False
    _order = 'fecha desc, hora desc'

    # Campos principales
    fecha = fields.Date(string='Fecha')
    hora = fields.Datetime(string='Hora')
    pedido_id = fields.Many2one('sale.order', string='Pedido')
    pedido_nombre = fields.Char(string='Número Pedido')
    cliente_id = fields.Many2one('res.partner', string='Cliente')
    cliente_nombre = fields.Char(string='Cliente')
    
    # Estados y tiempos
    estado_actual = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado')
    
    tiempo_preparacion = fields.Integer(string='Tiempo Preparación (min)')
    tiempo_total = fields.Integer(string='Tiempo Total (min)')
    
    # Tipo y categorización
    tipo_pedido = fields.Selection([
        ('web', 'eCommerce'),
        ('pos', 'Punto de Venta'),
    ], string='Origen')
    
    tipo_entrega = fields.Selection([
        ('delivery', 'Delivery'),
        ('pickup', 'Retiro en Local'),
    ], string='Tipo Entrega')
    
    # Métricas financieras
    monto_total = fields.Float(string='Monto Total')
    cantidad_productos = fields.Integer(string='Cantidad Productos')
    
    # Métricas de tiempo por períodos
    hora_del_dia = fields.Integer(string='Hora del Día')
    dia_semana = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    ], string='Día de la Semana')
    
    mes = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Mes')
    
    # Campos computados para análisis
    eficiencia = fields.Float(string='Eficiencia (%)', compute='_compute_eficiencia')
    categoria_tiempo = fields.Selection([
        ('rapido', 'Rápido (< 15 min)'),
        ('normal', 'Normal (15-30 min)'),
        ('lento', 'Lento (30-60 min)'),
        ('muy_lento', 'Muy Lento (> 60 min)'),
    ], string='Categoría Tiempo', compute='_compute_categoria_tiempo')
    
    @api.depends('estado_actual')
    def _compute_eficiencia(self):
        for record in self:
            if record.estado_actual == 'entregado':
                record.eficiencia = 100.0
            elif record.estado_actual == 'rechazado':
                record.eficiencia = 0.0
            else:
                record.eficiencia = 50.0
    
    @api.depends('tiempo_total')
    def _compute_categoria_tiempo(self):
        for record in self:
            if record.tiempo_total < 15:
                record.categoria_tiempo = 'rapido'
            elif record.tiempo_total < 30:
                record.categoria_tiempo = 'normal'
            elif record.tiempo_total < 60:
                record.categoria_tiempo = 'lento'
            else:
                record.categoria_tiempo = 'muy_lento'

    def init(self):
        """Crear vista SQL para analytics"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    DATE(so.create_date) as fecha,
                    so.create_date as hora,
                    so.id as pedido_id,
                    so.name as pedido_nombre,
                    so.partner_id as cliente_id,
                    rp.name as cliente_nombre,
                    so.estado_rapido as estado_actual,
                    CASE 
                        WHEN so.tiempo_inicio_estado IS NOT NULL AND NOW() > so.tiempo_inicio_estado 
                        THEN GREATEST(0, EXTRACT(EPOCH FROM (NOW() - so.tiempo_inicio_estado))/60)::integer
                        ELSE 0
                    END as tiempo_preparacion,
                    CASE 
                        WHEN so.tiempo_inicio_total IS NOT NULL AND NOW() > so.tiempo_inicio_total 
                        THEN GREATEST(0, EXTRACT(EPOCH FROM (NOW() - so.tiempo_inicio_total))/60)::integer
                        ELSE 0
                    END as tiempo_total,
                    CASE 
                        WHEN so.website_id IS NOT NULL THEN 'web'
                        ELSE 'pos'
                    END as tipo_pedido,
                    CASE 
                        WHEN so.es_para_envio = true THEN 'delivery'
                        ELSE 'pickup'
                    END as tipo_entrega,
                    so.amount_total as monto_total,
                    (SELECT COUNT(*) FROM sale_order_line sol WHERE sol.order_id = so.id) as cantidad_productos,
                    EXTRACT(hour FROM so.create_date) as hora_del_dia,
                    EXTRACT(dow FROM so.create_date) as dia_semana,
                    EXTRACT(month FROM so.create_date) as mes
                FROM sale_order so
                LEFT JOIN res_partner rp ON rp.id = so.partner_id
                WHERE so.estado_rapido IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    row_number() OVER () + 100000 AS id,
                    DATE(po.date_order) as fecha,
                    po.date_order as hora,
                    po.id as pedido_id,
                    po.name as pedido_nombre,
                    po.partner_id as cliente_id,
                    rp.name as cliente_nombre,
                    po.estado_rapido as estado_actual,
                    CASE 
                        WHEN po.tiempo_inicio_estado IS NOT NULL AND NOW() > po.tiempo_inicio_estado 
                        THEN GREATEST(0, EXTRACT(EPOCH FROM (NOW() - po.tiempo_inicio_estado))/60)::integer
                        ELSE 0
                    END as tiempo_preparacion,
                    CASE 
                        WHEN po.tiempo_inicio_total IS NOT NULL AND NOW() > po.tiempo_inicio_total 
                        THEN GREATEST(0, EXTRACT(EPOCH FROM (NOW() - po.tiempo_inicio_total))/60)::integer
                        ELSE 0
                    END as tiempo_total,
                    'pos' as tipo_pedido,
                    CASE 
                        WHEN po.is_delivery = true THEN 'delivery'
                        ELSE 'pickup'
                    END as tipo_entrega,
                    po.amount_total as monto_total,
                    (SELECT COUNT(*) FROM pos_order_line pol WHERE pol.order_id = po.id) as cantidad_productos,
                    EXTRACT(hour FROM po.date_order) as hora_del_dia,
                    EXTRACT(dow FROM po.date_order) as dia_semana,
                    EXTRACT(month FROM po.date_order) as mes
                FROM pos_order po
                LEFT JOIN res_partner rp ON rp.id = po.partner_id
                WHERE po.estado_rapido IS NOT NULL
                    AND po.enviado_a_cocina = true
            )
        """ % self._table)


class TuPedidoMetricasRealTime(models.TransientModel):
    _name = 'tu_pedido.metricas.realtime'
    _description = 'Métricas en Tiempo Real'

    fecha_inicio = fields.Datetime(string='Desde', default=lambda self: fields.Datetime.now().replace(hour=0, minute=0, second=0))
    fecha_fin = fields.Datetime(string='Hasta', default=lambda self: fields.Datetime.now().replace(hour=23, minute=59, second=59))
    
    # Métricas calculadas
    pedidos_hoy = fields.Integer(string='Pedidos Hoy', compute='_compute_metricas')
    pedidos_promedio = fields.Float(string='Promedio Histórico', compute='_compute_metricas')
    tiempo_promedio = fields.Float(string='Tiempo Promedio (min)', compute='_compute_metricas')
    ingresos_hoy = fields.Float(string='Ingresos Hoy', compute='_compute_metricas')
    meta_diaria = fields.Float(string='Meta Diaria', default=5000.0)
    eficiencia_general = fields.Float(string='Eficiencia (%)', compute='_compute_metricas')
    
    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_metricas(self):
        for record in self:
            # Pedidos de hoy
            pedidos_hoy = self.env['tu_pedido.analytics'].search_count([
                ('fecha', '=', fields.Date.today())
            ])
            record.pedidos_hoy = pedidos_hoy
            
            # Promedio histórico (últimos 30 días)
            fecha_30_dias = fields.Date.today() - timedelta(days=30)
            pedidos_historicos = self.env['tu_pedido.analytics'].search([
                ('fecha', '>=', fecha_30_dias),
                ('fecha', '<', fields.Date.today())
            ])
            record.pedidos_promedio = len(pedidos_historicos) / 30 if pedidos_historicos else 0
            
            # Tiempo promedio
            tiempos = pedidos_historicos.mapped('tiempo_total')
            record.tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
            
            # Ingresos de hoy
            ingresos = self.env['tu_pedido.analytics'].search([
                ('fecha', '=', fields.Date.today())
            ])
            record.ingresos_hoy = sum(ingresos.mapped('monto_total'))
            
            # Eficiencia
            completados = self.env['tu_pedido.analytics'].search_count([
                ('fecha', '=', fields.Date.today()),
                ('estado_actual', '=', 'entregado')
            ])
            record.eficiencia_general = (completados / pedidos_hoy * 100) if pedidos_hoy > 0 else 0