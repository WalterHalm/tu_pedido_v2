/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PosWebWidget extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            pedidos_web: [],
            loading: false,
            mostrar_widget: false
        });

        onMounted(() => {
            this.cargarPedidosWeb();
            this.startAutoRefresh();
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    async cargarPedidosWeb() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/tu_pedido_v2/pedidos_web_activos");
            this.state.pedidos_web = result.pedidos || [];
            this.state.mostrar_widget = this.state.pedidos_web.length > 0;
        } catch (error) {
            this.state.pedidos_web = [];
        } finally {
            this.state.loading = false;
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.cargarPedidosWeb();
        }, 30000); // Actualizar cada 30 segundos
    }

    toggleWidget() {
        this.state.mostrar_widget = !this.state.mostrar_widget;
    }

    abrirDashboard() {
        window.open('/web#action=tu_pedido_v2.action_pedido_dashboard', '_blank');
    }

    formatearTiempo(create_date) {
        const ahora = new Date();
        const creado = new Date(create_date);
        const diff = Math.floor((ahora - creado) / (1000 * 60)); // minutos
        
        if (diff < 1) return 'Ahora';
        if (diff < 60) return `${diff}m`;
        const horas = Math.floor(diff / 60);
        const mins = diff % 60;
        return `${horas}h ${mins}m`;
    }
}

PosWebWidget.template = "tu_pedido_v2.PosWebWidget";

registry.category("pos_screens").add("PosWebWidget", PosWebWidget);