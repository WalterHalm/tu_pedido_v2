/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ShopConfirmationTracking = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    
    start: function () {
        if (window.location.pathname === '/shop/confirmation') {
            this._addTrackingButton();
        }
        return this._super.apply(this, arguments);
    },
    
    _addTrackingButton: function () {
        const orderId = this._getOrderIdFromPage();
        if (orderId) {
            const buttonHtml = `
                <div class="container mt-4 mb-4">
                    <div class="row">
                        <div class="col-12 text-center">
                            <a href="/my/orders/${orderId}" class="btn btn-primary btn-lg">
                                <i class="fa fa-truck"></i> Seguimiento del Pedido
                            </a>
                            <p class="text-muted mt-2">
                                <small>Ver el estado en tiempo real</small>
                            </p>
                        </div>
                    </div>
                </div>
            `;
            $('body').append(buttonHtml);
        }
    },
    
    _getOrderIdFromPage: function () {
        const match = window.location.search.match(/order_id=(\d+)/);
        return match ? match[1] : null;
    }
});

export default publicWidget.registry.ShopConfirmationTracking;
