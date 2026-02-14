from odoo import models, fields, api

class PosSession(models.Model):
    _inherit = 'pos.session'
    
    @api.model
    def hay_sesion_abierta(self):
        """Verificar si hay alguna sesión PoS abierta"""
        sesion = self.search([('state', '=', 'opened')], limit=1)
        return bool(sesion)
    
    @api.model
    def get_info_sesion_abierta(self):
        """Obtener información de la sesión abierta"""
        sesion = self.search([('state', '=', 'opened')], limit=1)
        if sesion:
            return {
                'abierto': True,
                'sesion_id': sesion.id,
                'nombre': sesion.name,
                'fecha_apertura': sesion.start_at.isoformat() if sesion.start_at else False,
                'usuario': sesion.user_id.name
            }
        return {'abierto': False}
