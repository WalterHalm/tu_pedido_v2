from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

class ShopStatusController(http.Controller):
    
    @http.route('/shop/status', type='json', auth='public')
    def shop_status(self):
        """API para verificar si el local está abierto"""
        info_sesion = request.env['pos.session'].sudo().get_info_sesion_abierta()
        return info_sesion


class WebsiteSaleInheritStatus(WebsiteSale):
    
    @http.route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
    def cart(self, **post):
        """Sobrescribir carrito para agregar estado del local"""
        response = super(WebsiteSaleInheritStatus, self).cart(**post)
        
        # Agregar información de sesión PoS
        if hasattr(response, 'qcontext'):
            info_sesion = request.env['pos.session'].sudo().get_info_sesion_abierta()
            response.qcontext['restaurante_abierto'] = info_sesion['abierto']
            response.qcontext['info_sesion'] = info_sesion
        
        return response
