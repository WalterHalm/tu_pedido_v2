/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.setupWebOrderListener();
    },

    setupWebOrderListener() {
        // Escuchar notificaciones de pedidos web (efectivo Y banco)
        this.env.services.bus_service.addEventListener(
            "notification",
            this.onWebOrderNotification.bind(this)
        );
    },

    async onWebOrderNotification({ detail: notifications }) {
        for (const { payload, type } of notifications) {
            if (type === "tu_pedido_web_pos_load") {
                await this.handleWebOrder(payload);
            }
        }
    },

    async handleWebOrder(orderData) {
        try {
            console.log("🔔 PEDIDO WEB RECIBIDO:", orderData);

            // Determinar tipo de notificación según método de pago
            const isPaid = orderData.estado_pago === 'Pagado';
            const title = isPaid 
                ? _t("Pedido Web - Pago Confirmado") 
                : _t("Pedido Web - Pago Pendiente");
            const message = isPaid
                ? _t("Pedido %s con pago confirmado por %s", orderData.order_name, orderData.metodo_pago)
                : _t("Pedido %s con pago pendiente en efectivo", orderData.order_name);

            // Mostrar notificación al cajero
            this.env.services.notification.add(message, {
                title: title,
                type: "info",
                sticky: true,
            });

            // Cargar automáticamente el sale.order en PoS usando settleSO nativo
            await this.loadWebOrderToPos(orderData.order_id, orderData);

        } catch (error) {
            console.error("Error procesando pedido web:", error);
            this.env.services.notification.add(
                _t("Error cargando pedido web: %s", error.message),
                { type: "danger" }
            );
        }
    },

    async loadWebOrderToPos(saleOrderId, orderData) {
        try {
            console.log("📦 Cargando sale.order en PoS:", saleOrderId);

            // Usar el método nativo _getSaleOrder para obtener el pedido completo
            const sale_order = await this._getSaleOrder(saleOrderId);

            if (!sale_order) {
                throw new Error("Sale order no encontrado");
            }

            console.log("📋 Sale order cargado:", sale_order);

            // Verificar si ya hay una orden activa con líneas
            const currentOrder = this.get_order();
            if (currentOrder && currentOrder.lines.length > 0) {
                // Crear nueva orden para el pedido web
                this.add_new_order();
                console.log("➕ Nueva orden creada para pedido web");
            }

            // Establecer fiscal position si existe
            const orderFiscalPos = sale_order.fiscal_position_id &&
                this.models["account.fiscal.position"].find(
                    (position) => position.id === sale_order.fiscal_position_id
                );
            
            if (orderFiscalPos) {
                this.get_order().update({
                    fiscal_position_id: orderFiscalPos,
                });
            }

            // Establecer cliente
            if (sale_order.partner_id) {
                this.get_order().set_partner(sale_order.partner_id);
            }

            // Usar el método nativo settleSO para cargar el pedido completo
            // Esto crea pos.order.line con sale_order_origin_id y sale_order_line_id
            await this.settleSO(sale_order, orderFiscalPos);
            
            console.log("✅ Pedido cargado en PoS usando settleSO nativo");

            // Mostrar información adicional del pedido
            const isPaid = orderData.estado_pago === 'Pagado';
            const infoMessage = isPaid
                ? _t("Pedido %s cargado. Pago YA confirmado (%s). Envíe a cocina.", 
                     sale_order.name, orderData.metodo_pago)
                : _t("Pedido %s cargado. Pago PENDIENTE en efectivo. Cobre y envíe a cocina.", 
                     sale_order.name);

            this.env.services.notification.add(infoMessage, {
                title: _t("Pedido Listo"),
                type: "success",
            });

        } catch (error) {
            console.error("Error cargando pedido en PoS:", error);
            throw error;
        }
    },
});
