from odoo import models, fields, api

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    def _reconcile_after_done(self):
        """Override para interceptar cuando se confirma el pedido web"""
        result = super()._reconcile_after_done()
        
        # Verificar si hay sale.order asociada y es de website
        for tx in self:
            if tx.sale_order_ids:
                for order in tx.sale_order_ids:
                    if order.website_id and not order.estado_rapido:
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.info(f"🌐 PEDIDO WEB CONFIRMADO VIA PAGO: {order.name} - Website: {order.website_id}")
                        
                        order.estado_rapido = 'nuevo'
                        order.tiempo_inicio_estado = fields.Datetime.now()
                        order.tiempo_inicio_total = fields.Datetime.now()
                        order.sonido_activo = True
                        order._detectar_tipo_entrega()
                        order._notificar_pedido_web_pos()
        
        return result