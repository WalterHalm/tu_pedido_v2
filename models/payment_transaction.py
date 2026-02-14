from odoo import models

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    def _reconcile_after_done(self):
        result = super()._reconcile_after_done()
        # Los pedidos ya se activan en create()
        return result
