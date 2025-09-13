from odoo import models, fields, api

class AceptarPedidoWizard(models.TransientModel):
    _name = 'tu_pedido_v2.aceptar_pedido_wizard'
    _description = 'Wizard para Aceptar Pedido'

    order_id = fields.Many2one('sale.order', string='Pedido', required=True)
    tiempo_estimado = fields.Integer(string='Tiempo estimado (minutos)', default=30)
    direccion_entrega = fields.Text(string='Dirección de entrega', compute='_compute_direccion_entrega', store=True, readonly=False)
    retira_en_local = fields.Boolean(string='Retira en local', default=False)
    notas_adicionales = fields.Text(string='Notas adicionales')
    
    @api.depends('order_id')
    def _compute_direccion_entrega(self):
        for record in self:
            if record.order_id and record.order_id.partner_shipping_id:
                record.direccion_entrega = record.order_id.partner_shipping_id.contact_address or ''
            elif record.order_id and record.order_id.partner_id:
                record.direccion_entrega = record.order_id.partner_id.contact_address or ''
            else:
                record.direccion_entrega = ''

    def action_aceptar(self):
        self.order_id.write({
            'estado_rapido': 'aceptado',
            'tiempo_estimado_entrega': self.tiempo_estimado,
            'tiempo_inicio_estado': fields.Datetime.now(),
            'sonido_activo': False,
            'nota_cocina': self.notas_adicionales or self.order_id.nota_cocina
        })
        return {'type': 'ir.actions.act_window_close'}


class RechazarPedidoWizard(models.TransientModel):
    _name = 'tu_pedido_v2.rechazar_pedido_wizard'
    _description = 'Wizard para Rechazar Pedido'

    order_id = fields.Many2one('sale.order', string='Pedido', required=True)
    motivo_rechazo = fields.Text(string='Motivo del rechazo', required=True)

    def action_rechazar(self):
        self.order_id.write({
            'estado_rapido': 'rechazado',
            'motivo_rechazo': self.motivo_rechazo,
            'tiempo_inicio_estado': fields.Datetime.now(),
            'sonido_activo': False
        })
        self.order_id.action_cancel()
        return {'type': 'ir.actions.act_window_close'}