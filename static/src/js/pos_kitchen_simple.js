/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

patch(ActionpadWidget.prototype, {
    get showKitchenButton() {
        const currentOrder = this.pos.get_order();
        return currentOrder && currentOrder.lines.length > 0;
    },

    async sendToKitchen() {
        const currentOrder = this.pos.get_order();
        if (!currentOrder || currentOrder.lines.length === 0) {
            return;
        }

        console.log("DEBUG: Enviando a cocina...");

        try {
            // Crear datos simples del pedido
            let tableName = null;
            if (currentOrder.table_id) {
                // Obtener el nombre del floor (área/piso) desde la mesa
                const floorName = currentOrder.table_id.floor_id ? currentOrder.table_id.floor_id.name : '';
                const tableNumber = currentOrder.table_id.table_number || '';
                tableName = `${floorName}Mesa${tableNumber}`;
            }
            
            const orderData = {
                tracking_number: currentOrder.tracking_number,
                table_name: tableName,  // Problema 2: nombre completo de mesa
                customer_name: currentOrder.partner_id ? currentOrder.partner_id.name : 'Cliente PoS',
                general_note: currentOrder.general_note || currentOrder['general_note'] || '',  // Acceso directo al campo
                products: currentOrder.lines
                    .filter(line => !line.combo_parent_id)  // Solo líneas principales, no items de combo
                    .map(line => ({
                        name: line.full_product_name || line.product_id.display_name,
                        qty: line.qty,
                        note: line.note || '',
                        combo_items: currentOrder.lines
                            .filter(item => item.combo_parent_id && item.combo_parent_id.id === line.id)
                            .map(item => ({
                                name: item.full_product_name || item.product_id.display_name,
                                qty: item.qty
                            }))
                    }))
            };

            // Debug: mostrar información de líneas
            console.log("DEBUG: Todas las líneas:", currentOrder.lines.map(line => ({
                id: line.id,
                name: line.product_id.display_name,
                combo_parent_id: line.combo_parent_id ? line.combo_parent_id.id : null,
                has_combo_parent: !!line.combo_parent_id
            })));
            
            console.log("DEBUG: Enviando pedido a cocina:", {
                tracking_number: orderData.tracking_number,
                table_name: orderData.table_name,
                customer_name: orderData.customer_name,
                has_general_note: !!orderData.general_note,
                products_count: orderData.products.length,
                products: orderData.products
            });

            const response = await fetch('/tu_pedido_v2/crear_pedido_simple', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: orderData
                })
            });

            const result = await response.json();
            console.log("DEBUG: Resultado:", result);
            
            if (result.result && result.result.success) {
                this.env.services.notification.add(`✅ ${result.result.message}`, {
                    type: "success"
                });
            } else {
                const errorMsg = result.result ? result.result.message : 'Error desconocido';
                this.env.services.notification.add(`❌ Error: ${errorMsg}`, {
                    type: "danger"
                });
            }
        } catch (error) {
            console.error("DEBUG: Error completo:", error);
            this.env.services.notification.add(`❌ Error: ${error.message}`, {
                type: "danger"
            });
        }
    }
});