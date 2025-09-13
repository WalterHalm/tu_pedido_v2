/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Sistema de notificaciones para pedidos web en PoS
class PosWebNotifications {
    constructor(pos) {
        this.pos = pos;
        this.init();
    }

    init() {
        // Escuchar notificaciones del bus
        this.pos.env.services.bus_service.addEventListener("notification", this.onNotification.bind(this));
    }

    onNotification({ detail: notifications }) {
        for (const { payload, type } of notifications) {
            if (type === "tu_pedido_web_notification") {
                this.showWebOrderNotification(payload);
            }
        }
    }

    showWebOrderNotification(data) {
        let productsList = data.productos.map(p => `${p.qty}x ${p.name}`).join(', ');
        if (data.total_productos > 3) {
            productsList += ` y ${data.total_productos - 3} más`;
        }

        const tipoEntrega = data.es_para_envio ? '🚚 ENVÍO' : '🏪 RETIRO';
        const direccionInfo = data.es_para_envio ? `📍 ${data.direccion}` : '📍 Retiro en local';

        // Usar el servicio de notificaciones de PoS
        this.pos.env.services.notification.add(
            `🌐 NUEVO PEDIDO WEB - ${tipoEntrega}\n\n${direccionInfo}\n📞 ${data.telefono}\n👤 ${data.cliente}\n\n🍽️ ${productsList}\n💰 $${data.amount_total}`,
            {
                title: "Pedido Web Recibido",
                type: "warning",
                sticky: true,
                buttons: [
                    {
                        name: "Ver Dashboard",
                        primary: true,
                        onClick: () => window.open('/web#action=tu_pedido_v2.action_pedido_dashboard', '_blank')
                    },
                    {
                        name: "Marcar Visto",
                        onClick: () => {}
                    }
                ]
            }
        );
    }
}

// Patch del PosStore para inicializar las notificaciones web
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        // Inicializar sistema de notificaciones web
        setTimeout(() => {
            window.posWebNotifications = new PosWebNotifications(this);
        }, 2000);
    }
});