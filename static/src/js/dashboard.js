/** @odoo-module **/

import { Component, onWillStart, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class PedidoDashboard extends Component {
    setup() {
        this.dashboardRef = useRef("dashboard");
        
        this.state = useState({
            state_columns: [],
            all_columns: [],
            loading: false,
            error: null,
            showAceptarModal: false,
            showRechazarModal: false,
            showCambiosModal: false,
            showCancelacionModal: false,
            filters: {
                fecha: 'hoy',
                cliente: '',
                origen: 'todos',
                estado: 'todos'
            },
            modalData: {
                order_id: null,
                tiempo_estimado: 30,
                direccion_entrega: '',
                retira_en_local: false,
                notas_adicionales: '',
                motivo_rechazo: '',
                es_para_envio: false,
                direccion_entrega_completa: ''
            },
            cambiosData: {
                order_id: null,
                pedido_nombre: '',
                cliente_nombre: '',
                motivo_decision: ''
            },
            cancelacionData: {
                order_id: null,
                pedido_nombre: '',
                cliente_nombre: '',
                notas_adicionales: ''
            }
        });

        this.refreshInterval = null;
        this.soundInterval = null;
        this.audioContext = null;

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.setupDragAndDrop();
            this.startAutoRefresh();
            this.initAudio();
            this.addProductEventListeners();
            this.setupHorizontalScroll();
            this.startRealTimeTimer();
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.soundInterval) {
                clearInterval(this.soundInterval);
            }
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const result = await rpc("/tu_pedido_v2/dashboard_data", {});
            this.state.all_columns = result?.columns || [];
            this.applyFilters();
            this.checkForNewOrders();
            
            setTimeout(() => {
                this.addProductEventListeners();
                this.initializeDragAndDrop();
                this.initializeTimeCounters();
            }, 200);
        } catch (error) {
            this.state.error = "Error cargando datos del dashboard: " + error.message;
            this.state.state_columns = [];
        } finally {
            this.state.loading = false;
        }
    }

    checkForNewOrders() {
        // Verificar si hay pedidos nuevos con sonido activo
        const nuevosConSonido = this.state.state_columns
            .find(col => col.key === 'nuevo')?.orders
            .filter(order => order.sonido_activo) || [];

        if (nuevosConSonido.length > 0) {
            this.startSoundAlert();
        } else {
            this.stopSoundAlert();
        }
    }

    initAudio() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn("Audio no disponible:", e);
        }
    }

    playNotificationSound() {
        if (!this.audioContext) return;

        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, this.audioContext.currentTime);
            oscillator.frequency.setValueAtTime(600, this.audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 0.5);
        } catch (e) {
            console.warn("Error reproduciendo sonido:", e);
        }
    }

    startSoundAlert() {
        if (this.soundInterval) return;
        
        this.soundInterval = setInterval(() => {
            this.playNotificationSound();
        }, 10000); // Cada 10 segundos
        
        // Reproducir inmediatamente
        this.playNotificationSound();
    }

    stopSoundAlert() {
        if (this.soundInterval) {
            clearInterval(this.soundInterval);
            this.soundInterval = null;
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadData();
        }, 30000); // Actualizar cada 30 segundos
    }

    setupDragAndDrop() {
        // Se configurará después del render
        setTimeout(() => {
            this.initializeDragAndDrop();
        }, 100);
    }

    initializeDragAndDrop() {
        const dashboardEl = this.dashboardRef.el;
        if (!dashboardEl) return;
        
        const cards = dashboardEl.querySelectorAll('.pedido-card');
        const columns = dashboardEl.querySelectorAll('.estado-list');

        cards.forEach(card => {
            card.draggable = true;
            // Remover listeners anteriores
            card.removeEventListener('dragstart', this.onDragStart);
            card.removeEventListener('dragend', this.onDragEnd);
            // Agregar nuevos listeners
            card.addEventListener('dragstart', this.onDragStart.bind(this));
            card.addEventListener('dragend', this.onDragEnd.bind(this));
        });

        columns.forEach(column => {
            // Remover listeners anteriores
            column.removeEventListener('dragover', this.onDragOver);
            column.removeEventListener('drop', this.onDrop);
            column.removeEventListener('dragleave', this.onDragLeave);
            // Agregar nuevos listeners
            column.addEventListener('dragover', this.onDragOver.bind(this));
            column.addEventListener('drop', this.onDrop.bind(this));
            column.addEventListener('dragleave', this.onDragLeave.bind(this));
        });
    }

    onDragStart(e) {
        e.dataTransfer.setData('text/plain', e.target.dataset.orderId);
        e.dataTransfer.effectAllowed = 'move';
        e.target.classList.add('dragging');
    }
    
    onDragEnd(e) {
        e.target.classList.remove('dragging');
        // Limpiar todas las clases drag-over
        const dashboardEl = this.dashboardRef.el;
        if (dashboardEl) {
            dashboardEl.querySelectorAll('.drag-over').forEach(el => {
                el.classList.remove('drag-over');
            });
        }
    }

    onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        e.currentTarget.classList.add('drag-over');
    }
    
    onDragLeave(e) {
        // Solo remover si realmente salimos del elemento
        if (!e.currentTarget.contains(e.relatedTarget)) {
            e.currentTarget.classList.remove('drag-over');
        }
    }

    onDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        const orderId = parseInt(e.dataTransfer.getData('text/plain'));
        const newState = e.currentTarget.dataset.state;
        
        if (orderId && newState) {
            this.changeOrderState(orderId, newState);
        }
        
        // Limpiar clases de drag
        const dashboardEl = this.dashboardRef.el;
        if (dashboardEl) {
            dashboardEl.querySelectorAll('.dragging').forEach(el => {
                el.classList.remove('dragging');
            });
        }
    }

    async changeOrderState(orderId, newState) {
        try {
            const result = await rpc("/tu_pedido_v2/cambiar_estado", {
                order_id: orderId,
                nuevo_estado: newState
            });
            
            if (result.success) {
                await this.loadData();
            }
        } catch (error) {
            // Error silencioso
        }
    }

    async aceptarPedido(orderId) {
        const order = this.getOrderById(orderId);
        if (!order) return;
        
        this.state.modalData = {
            order_id: orderId,
            tiempo_estimado: 30,
            direccion_entrega: order.direccion_entrega_completa || '',
            retira_en_local: !order.es_para_envio,
            notas_adicionales: '',
            motivo_rechazo: '',
            es_para_envio: order.es_para_envio,
            direccion_entrega_completa: order.direccion_entrega_completa || ''
        };
        this.state.showAceptarModal = true;
    }
    
    getOrderById(orderId) {
        for (const col of this.state.state_columns) {
            const order = col.orders.find(o => o.id === orderId);
            if (order) return order;
        }
        return null;
    }
    
    confirmarAceptar() {
        rpc("/tu_pedido_v2/aceptar_pedido", {
            order_id: this.state.modalData.order_id
        }).then(result => {
            if (result.success) {
                this.closeModal();
                this.loadData();
            }
        }).catch(() => {});
    }

    async rechazarPedido(orderId) {
        this.state.modalData = {
            order_id: orderId,
            tiempo_estimado: 30,
            direccion_entrega: '',
            retira_en_local: false,
            notas_adicionales: '',
            motivo_rechazo: ''
        };
        this.state.showRechazarModal = true;
    }
    
    confirmarRechazo() {
        if (!this.state.modalData.motivo_rechazo?.trim()) {
            alert('Debe ingresar un motivo para el rechazo');
            return;
        }
        
        rpc("/tu_pedido_v2/rechazar_pedido", {
            order_id: this.state.modalData.order_id,
            motivo: this.state.modalData.motivo_rechazo
        }).then(result => {
            if (result.success) {
                this.closeModal();
                this.loadData();
            }
        }).catch(() => {});
    }
    
    closeModal() {
        this.state.showAceptarModal = false;
        this.state.showRechazarModal = false;
    }
    
    async mostrarCambiosModal(order) {
        this.state.cambiosData = {
            order_id: order.id,
            pedido_nombre: order.name,
            cliente_nombre: order.partner_id[1],
            motivo_decision: '',
            detalles: {agregados: [], modificados: [], eliminados: []}
        };
        
        // Cargar detalles de cambios
        try {
            const result = await rpc("/tu_pedido_v2/get_detalles_cambios", {
                order_id: order.id
            });
            if (result.success) {
                this.state.cambiosData.detalles = result.detalles;
            }
        } catch (error) {
            // Error silencioso
        }
        
        this.state.showCambiosModal = true;
    }
    
    closeCambiosModal() {
        this.state.showCambiosModal = false;
    }
    
    aceptarCambios() {
        rpc("/tu_pedido_v2/aceptar_cambios_productos", {
            order_id: this.state.cambiosData.order_id,
            motivo: this.state.cambiosData.motivo_decision
        }).then(result => {
            if (result.success) {
                this.closeCambiosModal();
                this.loadData();
            }
        }).catch(() => {});
    }
    
    rechazarCambios() {
        if (!this.state.cambiosData.motivo_decision.trim()) {
            alert('Debe ingresar un motivo para rechazar los cambios');
            return;
        }
        
        rpc("/tu_pedido_v2/rechazar_cambios_productos", {
            order_id: this.state.cambiosData.order_id,
            motivo: this.state.cambiosData.motivo_decision
        }).then(result => {
            if (result.success) {
                this.closeCambiosModal();
                this.loadData();
            }
        }).catch(() => {});
    }
    
    mostrarCancelacionModal(order) {
        this.state.cancelacionData = {
            order_id: order.id,
            pedido_nombre: order.name,
            cliente_nombre: order.partner_id[1],
            notas_adicionales: ''
        };
        this.state.showCancelacionModal = true;
    }
    
    closeCancelacionModal() {
        this.state.showCancelacionModal = false;
    }
    
    confirmarCancelacion() {
        rpc("/tu_pedido_v2/confirmar_cancelacion", {
            order_id: this.state.cancelacionData.order_id,
            notas: this.state.cancelacionData.notas_adicionales
        }).then(result => {
            if (result.success) {
                this.closeCancelacionModal();
                this.loadData();
            }
        }).catch(() => {});
    }

    async siguienteEstado(orderId) {
        try {
            const result = await rpc("/tu_pedido_v2/siguiente_estado", {
                order_id: orderId
            });
            
            if (result.success) {
                await this.loadData();
            }
        } catch (error) {
            // Error silencioso
        }
    }
    
    applyFilters() {
        let filteredColumns = JSON.parse(JSON.stringify(this.state.all_columns));
        
        filteredColumns = filteredColumns.map(col => {
            let orders = col.orders;
            
            // Filtro por fecha
            if (this.state.filters.fecha !== 'todos') {
                const now = new Date();
                orders = orders.filter(order => {
                    const orderDate = new Date(order.create_date || order.tiempo_inicio_total);
                    
                    if (this.state.filters.fecha === 'hoy') {
                        return orderDate.toDateString() === now.toDateString();
                    } else if (this.state.filters.fecha === 'ayer') {
                        const yesterday = new Date(now);
                        yesterday.setDate(yesterday.getDate() - 1);
                        return orderDate.toDateString() === yesterday.toDateString();
                    } else if (this.state.filters.fecha === 'ultimos_7') {
                        const weekAgo = new Date(now);
                        weekAgo.setDate(weekAgo.getDate() - 7);
                        return orderDate >= weekAgo;
                    }
                    return true;
                });
            }
            
            // Filtro por cliente
            if (this.state.filters.cliente.trim()) {
                const searchTerm = this.state.filters.cliente.toLowerCase();
                orders = orders.filter(order => 
                    order.partner_id[1].toLowerCase().includes(searchTerm)
                );
            }
            
            // Filtro por origen
            if (this.state.filters.origen !== 'todos') {
                orders = orders.filter(order => {
                    if (this.state.filters.origen === 'web') {
                        return order.tipo_pedido === 'web';
                    } else if (this.state.filters.origen === 'pos') {
                        return order.tipo_pedido !== 'web';
                    }
                    return true;
                });
            }
            
            // Filtro por estado
            if (this.state.filters.estado !== 'todos') {
                orders = orders.filter(order => 
                    order.estado_rapido === this.state.filters.estado
                );
            }
            
            return {
                ...col,
                orders: orders,
                count: orders.length
            };
        });
        
        this.state.state_columns = filteredColumns;
    }
    
    resetFilters() {
        this.state.filters = {
            fecha: 'hoy',
            cliente: '',
            origen: 'todos',
            estado: 'todos'
        };
        this.applyFilters();
    }



    formatTime(minutes) {
        if (minutes < 60) {
            return `${minutes}m`;
        } else {
            const hours = Math.floor(minutes / 60);
            const mins = minutes % 60;
            return `${hours}h ${mins}m`;
        }
    }
    
    setupHorizontalScroll() {
        setTimeout(() => {
            const dashboardEl = this.dashboardRef.el;
            if (!dashboardEl) return;
            
            const columnsContainer = dashboardEl.querySelector('.estado-columns');
            if (!columnsContainer) return;
            
            // Mouse wheel horizontal scroll
            columnsContainer.addEventListener('wheel', (e) => {
                if (e.deltaY !== 0) {
                    e.preventDefault();
                    columnsContainer.scrollLeft += e.deltaY;
                }
            }, { passive: false });
            
            // Scroll configurado
        }, 100);
    }
    
    startRealTimeTimer() {
        // Inicializar contadores al cargar datos
        setTimeout(() => {
            this.initializeTimeCounters();
        }, 500);
        
        this.timerInterval = setInterval(() => {
            this.updateTimeCounters();
        }, 1000);
    }
    
    initializeTimeCounters() {
        // Inicializar tiempo base para cada pedido
        this.state.state_columns.forEach(column => {
            column.orders.forEach(order => {
                if (!order.tiempo_inicial_guardado) {
                    order.tiempo_inicial_guardado = order.tiempo_total || 0;
                    order.tiempo_inicio_contador = Date.now();
                }
            });
        });
    }
    
    updateTimeCounters() {
        document.querySelectorAll('.pedido-card').forEach(card => {
            const tiempoElement = card.querySelector('.tiempo-contador');
            if (!tiempoElement) return;
            
            const orderId = card.dataset.orderId;
            const order = this.findOrderById(orderId);
            if (!order) return;
            
            // Incrementar tiempo_total cada segundo (1/60 de minuto)
            if (!order.tiempo_inicial_guardado) {
                order.tiempo_inicial_guardado = order.tiempo_total || 0;
                order.tiempo_inicio_contador = Date.now();
            }
            
            const segundosTranscurridos = Math.floor((Date.now() - order.tiempo_inicio_contador) / 1000);
            const tiempoTotal = order.tiempo_inicial_guardado + Math.floor(segundosTranscurridos / 60);
            const { clase, texto } = this.getTimeStatus(tiempoTotal);
            
            tiempoElement.textContent = texto;
            tiempoElement.className = `tiempo-contador ${clase}`;
            
            // Actualizar clases de la tarjeta
            card.className = card.className.replace(/tiempo-(normal|advertencia|critico)/g, '');
            card.classList.add(`tiempo-${clase}`);
        });
    }
    
    findOrderById(orderId) {
        for (const column of this.state.state_columns || []) {
            const order = column.orders.find(o => o.id == orderId);
            if (order) return order;
        }
        return null;
    }
    
    calculateRealTime(startTime, now) {
        if (!startTime) return 0;
        const start = new Date(startTime);
        return Math.floor((now - start) / (1000 * 60));
    }
    
    getTimeStatus(minutes) {
        if (minutes >= 60) {
            return {
                clase: 'critico',
                texto: `${Math.floor(minutes / 60)}h ${minutes % 60}m`
            };
        } else if (minutes >= 30) {
            return {
                clase: 'advertencia', 
                texto: `${minutes}m`
            };
        } else {
            return {
                clase: 'normal',
                texto: `${minutes}m`
            };
        }
    }
    
    addProductEventListeners() {
        setTimeout(() => {
            this.initializeProductListeners();
        }, 200);
    }
    
    initializeProductListeners() {
        const dashboardEl = this.dashboardRef.el;
        if (!dashboardEl) return;
        
        // Remover listeners anteriores
        if (this.productClickHandler) {
            dashboardEl.removeEventListener('click', this.productClickHandler);
        }
        
        this.productClickHandler = (e) => {
            const productItem = e.target.closest('.producto-item');
            if (productItem) {
                e.preventDefault();
                e.stopPropagation();
                
                const orderId = productItem.dataset.orderId;
                const lineId = productItem.dataset.lineId;
                
                if (orderId && lineId) {
                    this.toggleProducto(parseInt(orderId), parseInt(lineId), productItem);
                }
            }
        };
        
        dashboardEl.addEventListener('click', this.productClickHandler);
    }
    
    async toggleProducto(orderId, lineId, element) {
        try {
            const result = await rpc('/tu_pedido_v2/toggle_producto', {
                order_id: orderId,
                line_id: lineId
            });
            
            if (result?.success) {
                element.classList.toggle('producto-completado');
                
                if (element.classList.contains('producto-completado')) {
                    element.style.backgroundColor = '#e8f5e8';
                    element.style.color = '#155724';
                    element.style.borderLeft = '2px solid #28a745';
                    element.style.boxShadow = '0 1px 3px rgba(40, 167, 69, 0.2)';
                    element.style.opacity = '0.8';
                } else {
                    element.style.backgroundColor = '';
                    element.style.color = '';
                    element.style.borderLeft = '';
                    element.style.boxShadow = '';
                    element.style.opacity = '';
                }
                
                const productName = element.querySelector('.producto-name');
                if (productName) {
                    if (element.classList.contains('producto-completado')) {
                        if (!productName.textContent.includes('✓')) {
                            productName.textContent += ' ✓';
                        }
                        productName.style.color = '#155724';
                        productName.style.textDecoration = 'line-through';
                        productName.style.fontWeight = '600';
                    } else {
                        productName.textContent = productName.textContent.replace(' ✓', '');
                        productName.style.color = '';
                        productName.style.textDecoration = '';
                    }
                }
            }
        } catch (error) {
            // Error silencioso
        }
    }
}

PedidoDashboard.template = "tu_pedido_v2.Dashboard";

registry.category("actions").add("pedido_dashboard", PedidoDashboard);