from odoo import models, fields, api
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    estado_rapido = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('en_preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado')
    ], string='Estado Rápido', default=False)
    
    nota_cocina = fields.Text(string='Notas de Cocina')
    tiempo_inicio_estado = fields.Datetime(string='Inicio Estado Actual')
    tiempo_inicio_total = fields.Datetime(string='Inicio Total')
    sonido_activo = fields.Boolean(string='Sonido Activo', default=False)
    es_para_envio = fields.Boolean(string='Es para Envío', default=False)
    direccion_entrega_completa = fields.Text(string='Dirección Completa')
    cliente_confirmo_recepcion = fields.Boolean(string='Cliente Confirmó Recepción', default=False)
    tiempo_estimado_entrega = fields.Integer(string='Tiempo Estimado (min)', default=30)
    tiene_reclamo = fields.Boolean(string='Tiene Reclamo', default=False)
    descripcion_reclamo = fields.Text(string='Descripción del Reclamo')
    productos_modificados = fields.Boolean(string='Productos Modificados', default=False)
    
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
    
    @api.model
    def create(self, vals_list):
        # Odoo 19: create() siempre recibe lista
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        
        for vals in vals_list:
            # Pedidos web: activar inmediatamente
            if vals.get('website_id'):
                vals.update({
                    'estado_rapido': 'nuevo',
                    'tiempo_inicio_estado': fields.Datetime.now(),
                    'tiempo_inicio_total': fields.Datetime.now(),
                    'sonido_activo': True,
                })
                # Detectar tipo de entrega
                if vals.get('partner_shipping_id'):
                    partner_shipping = self.env['res.partner'].browse(vals['partner_shipping_id'])
                    if partner_shipping.street or partner_shipping.city:
                        vals['es_para_envio'] = True
                        vals['direccion_entrega_completa'] = self._format_address(partner_shipping)
        
        return super().create(vals_list)
    
    def _format_address(self, partner):
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        if partner.city:
            parts.append(partner.city)
        if partner.state_id:
            parts.append(partner.state_id.name)
        if partner.zip:
            parts.append(partner.zip)
        return ', '.join(parts)
    
    def action_cambiar_estado(self, nuevo_estado):
        self.ensure_one()
        if self.estado_rapido != nuevo_estado:
            vals = {
                'estado_rapido': nuevo_estado,
                'tiempo_inicio_estado': fields.Datetime.now()
            }
            if self.estado_rapido == 'nuevo' and nuevo_estado != 'nuevo':
                vals['sonido_activo'] = False
            
            if nuevo_estado == 'terminado':
                self.action_confirm()
            elif nuevo_estado == 'rechazado':
                self.action_cancel()
            
            self.write(vals)
        return True
    
    def action_siguiente_estado(self):
        estados = ['nuevo', 'aceptado', 'en_preparacion', 'terminado', 'despachado', 'entregado']
        if self.estado_rapido in estados:
            idx = estados.index(self.estado_rapido)
            if idx < len(estados) - 1:
                self.action_cambiar_estado(estados[idx + 1])
        return True
    
    def action_confirmar_recepcion_cliente(self):
        self.write({
            'cliente_confirmo_recepcion': True,
            'estado_rapido': 'entregado'
        })
        return True
    
    def action_reportar_problema(self, descripcion):
        self.write({
            'tiene_reclamo': True,
            'descripcion_reclamo': descripcion
        })
        return True
