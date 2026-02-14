from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    estado_rapido = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('en_preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado')
    ], string='Estado Rápido', default=False)
    
    is_delivery = fields.Boolean(string='Es Delivery', default=False)
    direccion_delivery = fields.Char(string='Dirección de Envío')
    telefono_delivery = fields.Char(string='Teléfono de Contacto')
    enviado_a_cocina = fields.Boolean(string='Enviado a Cocina', default=False)
    tiempo_inicio_estado = fields.Datetime(string='Inicio Estado Actual')
    tiempo_inicio_total = fields.Datetime(string='Inicio Total')
    sonido_activo = fields.Boolean(string='Sonido Activo', default=False)
    
    tiempo_estado_minutos = fields.Integer(string='Minutos en Estado', compute='_compute_tiempos')
    tiempo_total_minutos = fields.Integer(string='Minutos Totales', compute='_compute_tiempos')
    
    @api.depends('tiempo_inicio_estado', 'tiempo_inicio_total')
    def _compute_tiempos(self):
        for record in self:
            now = fields.Datetime.now()
            if record.tiempo_inicio_estado:
                delta = now - record.tiempo_inicio_estado
                record.tiempo_estado_minutos = int(delta.total_seconds() / 60)
            else:
                record.tiempo_estado_minutos = 0
            
            if record.tiempo_inicio_total:
                delta = now - record.tiempo_inicio_total
                record.tiempo_total_minutos = int(delta.total_seconds() / 60)
            else:
                record.tiempo_total_minutos = 0
    
    def action_cambiar_estado(self, nuevo_estado):
        self.ensure_one()
        if self.estado_rapido != nuevo_estado:
            vals = {
                'estado_rapido': nuevo_estado,
                'tiempo_inicio_estado': fields.Datetime.now()
            }
            if self.estado_rapido == 'nuevo' and nuevo_estado != 'nuevo':
                vals['sonido_activo'] = False
            self.write(vals)
        return True
