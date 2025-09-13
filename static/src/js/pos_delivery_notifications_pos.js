/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Sistema de notificaciones para PoS
class PosDeliveryNotifications {
    constructor(pos) {
        this.pos = pos;
        this.checkInterval = null;
        this.currentNotifications = [];
        this.init();
    }

    init() {
        // Iniciar revisión cada 15 segundos
        this.checkInterval = setInterval(() => {
            this.checkDeliveryNotifications();
        }, 15000);
        
        // Revisar inmediatamente después de 3 segundos
        setTimeout(() => this.checkDeliveryNotifications(), 3000);
    }

    async checkDeliveryNotifications() {
        try {
            // Verificar notificaciones de delivery
            const deliveryResponse = await fetch('/tu_pedido_v2/pos_delivery_notifications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            const deliveryResult = await deliveryResponse.json();
            
            if (deliveryResult.result && deliveryResult.result.notifications && deliveryResult.result.notifications.length > 0) {
                this.showNotifications(deliveryResult.result.notifications);
            }
            
            // Verificar notificaciones de pedidos web nuevos
            const webResponse = await fetch('/tu_pedido_v2/pos_web_notifications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            const webResult = await webResponse.json();
            
            if (webResult.result && webResult.result.notifications) {
                // Obtener IDs de pedidos actuales del servidor
                const serverOrderIds = webResult.result.notifications.map(n => n.id.toString());
                
                // Remover pedidos que ya no están en el servidor (fueron despachados)
                if (this.currentWebNotifications) {
                    this.currentWebNotifications = this.currentWebNotifications.filter(notif => 
                        serverOrderIds.includes(notif.id.toString())
                    );
                }
                
                // Agregar nuevos pedidos
                if (webResult.result.notifications.length > 0) {
                    this.showWebNotifications(webResult.result.notifications);
                }
                
                // Actualizar botón
                this.updateWebFloatingButton();
            }
            
            // Verificar notificaciones de pedidos listos para retirar
            const pickupResponse = await fetch('/tu_pedido_v2/pos_pickup_notifications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            const pickupResult = await pickupResponse.json();
            
            if (pickupResult.result && pickupResult.result.notifications && pickupResult.result.notifications.length > 0) {
                this.showPickupNotifications(pickupResult.result.notifications);
            } else {
                this.currentPickupNotifications = [];
                this.updatePickupFloatingButton();
            }
        } catch (error) {
            console.log('Error checking notifications:', error);
        }
    }

    showNotifications(notifications) {
        this.currentNotifications = notifications;
        this.updateFloatingButton();
    }

    updateFloatingButton() {
        const count = this.currentNotifications.length;
        let floatingBtn = document.querySelector('.pos-delivery-float-btn');
        
        if (count > 0) {
            if (!floatingBtn) {
                floatingBtn = document.createElement('button');
                floatingBtn.className = 'pos-delivery-float-btn';
                floatingBtn.onclick = () => this.showModal();
                document.body.appendChild(floatingBtn);
            }
            floatingBtn.innerHTML = `🚚 Pedidos Listos para Enviar <span class="badge">${count}</span>`;
        } else {
            if (floatingBtn) {
                floatingBtn.remove();
            }
        }
    }

    showModal() {
        const modal = document.createElement('div');
        modal.className = 'pos-delivery-modal';
        modal.innerHTML = `
            <div class="pos-delivery-modal-content">
                <div class="pos-delivery-modal-header">
                    <h3>🚚 Pedidos Listos para Enviar (${this.currentNotifications.length})</h3>
                    <button class="pos-delivery-modal-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="pos-delivery-modal-list">
                    ${this.currentNotifications.map(notif => this.createModalItem(notif)).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Cerrar con ESC
        const closeHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', closeHandler);
            }
        };
        document.addEventListener('keydown', closeHandler);
    }

    createModalItem(notification) {
        const tipoIcon = notification.tipo === 'pos' ? '🏪' : '🌍';
        const tipoText = notification.tipo === 'pos' ? 'PoS' : 'Web';
        
        return `
            <div class="pos-delivery-modal-item">
                <div class="pos-delivery-toast-title">🚚 DELIVERY LISTO ${tipoIcon}</div>
                <div class="pos-delivery-toast-type">${tipoText}: ${notification.order_name}</div>
                <div class="pos-delivery-toast-client">👤 ${notification.cliente}</div>
                <div class="pos-delivery-toast-address">📍 ${notification.direccion}</div>
                <div class="pos-delivery-toast-phone">📞 ${notification.telefono}</div>
                <button class="pos-delivery-toast-btn" onclick="window.posDeliverySystem.markAsDispatchedFromModal('${notification.id}')">✅ Despachado</button>
            </div>
        `;
    }

    async markAsDispatched(orderId, element) {
        try {
            const response = await fetch('/tu_pedido_v2/mark_delivery_dispatched', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({order_id: orderId})
            });
            
            element.remove();
        } catch (error) {
            console.error('Error marking as dispatched:', error);
        }
    }

    async markAsDispatchedFromModal(orderId) {
        try {
            const response = await fetch('/tu_pedido_v2/mark_delivery_dispatched', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({order_id: orderId})
            });
            
            // Remover de la lista actual
            this.currentNotifications = this.currentNotifications.filter(n => n.id !== orderId);
            
            // Actualizar botón flotante
            this.updateFloatingButton();
            
            // Cerrar modal si no hay más pedidos
            if (this.currentNotifications.length === 0) {
                const modal = document.querySelector('.pos-delivery-modal');
                if (modal) modal.remove();
            } else {
                // Actualizar modal
                const modal = document.querySelector('.pos-delivery-modal');
                if (modal) {
                    modal.remove();
                    this.showModal();
                }
            }
        } catch (error) {
            console.error('Error marking as dispatched:', error);
        }
    }
    
    showWebNotifications(notifications) {
        // Inicializar si no existe
        if (!this.currentWebNotifications) {
            this.currentWebNotifications = [];
        }
        
        // Solo agregar pedidos que no estén ya en la lista
        notifications.forEach(newNotif => {
            const exists = this.currentWebNotifications.find(existing => existing.id == newNotif.id);
            if (!exists) {
                this.currentWebNotifications.push(newNotif);
            }
        });
        
        this.updateWebFloatingButton();
    }
    
    updateWebFloatingButton() {
        const count = this.currentWebNotifications.length;
        let floatingBtn = document.querySelector('.pos-web-float-btn');
        
        if (count > 0) {
            if (!floatingBtn) {
                floatingBtn = document.createElement('button');
                floatingBtn.className = 'pos-web-float-btn';
                floatingBtn.onclick = () => this.showWebModal();
                document.body.appendChild(floatingBtn);
            }
            floatingBtn.innerHTML = `🌐 Pedidos Web <span class="badge">${count}</span>`;
        } else {
            if (floatingBtn) {
                floatingBtn.remove();
            }
        }
    }
    
    showWebModal() {
        const modal = document.createElement('div');
        modal.className = 'pos-delivery-modal';
        modal.innerHTML = `
            <div class="pos-delivery-modal-content">
                <div class="pos-delivery-modal-header">
                    <h3>🌐 Nuevos Pedidos Web (${this.currentWebNotifications.length})</h3>
                    <button class="pos-delivery-modal-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="pos-delivery-modal-list">
                    ${this.currentWebNotifications.map(notif => this.createWebModalItem(notif)).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Cerrar con ESC
        const closeHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', closeHandler);
            }
        };
        document.addEventListener('keydown', closeHandler);
    }
    
    createWebModalItem(notification) {
        const tipoIcon = notification.es_para_envio ? '🚚' : '🏪';
        const tipoText = notification.es_para_envio ? 'ENVÍO' : 'RETIRO';
        
        return `
            <div class="pos-delivery-modal-item">
                <div class="pos-delivery-toast-title">🌐 PEDIDO WEB ${tipoIcon}</div>
                <div class="pos-delivery-toast-type">${tipoText}: ${notification.order_name}</div>
                <div class="pos-delivery-toast-client">👤 ${notification.cliente}</div>
                <div class="pos-delivery-toast-address">📍 ${notification.direccion}</div>
                <div class="pos-delivery-toast-phone">📞 ${notification.telefono}</div>
                <div class="pos-delivery-toast-products">🍽️ ${notification.productos}</div>
                <div class="pos-delivery-toast-total">💰 $${notification.amount_total}</div>
                <button class="pos-delivery-toast-btn" onclick="window.posDeliverySystem.markWebAsViewed('${notification.id}')">Ver Dashboard</button>
            </div>
        `;
    }
    
    async markWebAsViewed(orderId) {
        // Solo abrir dashboard, NO remover la notificación
        window.open('/web#action=tu_pedido_v2.action_pedido_dashboard', '_blank');
        
        // Cerrar modal pero mantener botón flotante
        const modal = document.querySelector('.pos-delivery-modal');
        if (modal) modal.remove();
    }
    
    showPickupNotifications(notifications) {
        this.currentPickupNotifications = notifications;
        this.updatePickupFloatingButton();
    }
    
    updatePickupFloatingButton() {
        const count = this.currentPickupNotifications.length;
        let floatingBtn = document.querySelector('.pos-pickup-float-btn');
        
        if (count > 0) {
            if (!floatingBtn) {
                floatingBtn = document.createElement('button');
                floatingBtn.className = 'pos-pickup-float-btn';
                floatingBtn.onclick = () => this.showPickupModal();
                document.body.appendChild(floatingBtn);
            }
            floatingBtn.innerHTML = `📍 Pedidos Listos para Retirar <span class="badge">${count}</span>`;
        } else {
            if (floatingBtn) {
                floatingBtn.remove();
            }
        }
    }
    
    showPickupModal() {
        const modal = document.createElement('div');
        modal.className = 'pos-delivery-modal';
        modal.innerHTML = `
            <div class="pos-delivery-modal-content">
                <div class="pos-delivery-modal-header">
                    <h3>📍 Pedidos Listos para Retirar (${this.currentPickupNotifications.length})</h3>
                    <button class="pos-delivery-modal-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="pos-delivery-modal-list">
                    ${this.currentPickupNotifications.map(notif => this.createPickupModalItem(notif)).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    createPickupModalItem(notification) {
        const tipoIcon = notification.tipo === 'pos' ? '🏪' : '🌍';
        const tipoText = notification.tipo === 'pos' ? 'PoS' : 'Web';
        
        return `
            <div class="pos-delivery-modal-item">
                <div class="pos-delivery-toast-title">📍 PEDIDO LISTO PARA RETIRAR ${tipoIcon}</div>
                <div class="pos-delivery-toast-type">${tipoText}: ${notification.order_name}</div>
                <div class="pos-delivery-toast-client">👤 ${notification.cliente}</div>
                <div class="pos-delivery-toast-phone">📞 ${notification.telefono}</div>
                <button class="pos-delivery-toast-btn" onclick="window.posDeliverySystem.markPickupAsDispatched('${notification.id}')">✅ Entregado</button>
            </div>
        `;
    }
    
    async markPickupAsDispatched(orderId) {
        try {
            const response = await fetch('/tu_pedido_v2/mark_delivery_dispatched', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({order_id: orderId})
            });
            
            this.currentPickupNotifications = this.currentPickupNotifications.filter(n => n.id !== orderId);
            this.updatePickupFloatingButton();
            
            if (this.currentPickupNotifications.length === 0) {
                const modal = document.querySelector('.pos-delivery-modal');
                if (modal) modal.remove();
            } else {
                const modal = document.querySelector('.pos-delivery-modal');
                if (modal) {
                    modal.remove();
                    this.showPickupModal();
                }
            }
        } catch (error) {
            console.error('Error marking pickup as dispatched:', error);
        }
    }
}

// Patch del PosStore para inicializar las notificaciones
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        // Inicializar sistema de notificaciones delivery
        setTimeout(() => {
            const system = new PosDeliveryNotifications(this);
            system.currentWebNotifications = [];
            system.currentPickupNotifications = [];
            window.posDeliverySystem = system;
        }, 2000);
    }
});