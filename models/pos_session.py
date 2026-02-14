from odoo import models, fields

class PosSession(models.Model):
    _inherit = 'pos.session'
    
    fecha_apertura = fields.Datetime(string='Fecha de Apertura', default=fields.Datetime.now)
    hora_cierre_estimada = fields.Float(string='Hora de Cierre Estimada', default=22.0)
