from odoo import models, fields, api
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = "sale.order"

    estado_rapido = fields.Selection([
        ("nuevo", "Nuevo"),
        ("aceptado", "Aceptado"),
        ("preparacion", "En Preparación"),
        ("terminado", "Terminado"),
        ("despachado", "Despachado/Retirado"),
        ("entregado", "Entregado"),
        ("rechazado", "Rechazado"),
    ], string="Estado Pedido")

    nota_cocina = fields.Text(string="Notas Cocina")
    tiempo_inicio_estado = fields.Datetime(default=fields.Datetime.now)
    tiempo_inicio_total = fields.Datetime(default=fields.Datetime.now)
    cliente_confirmo_recepcion = fields.Boolean(string="Cliente confirmó recepción", default=False)
    sonido_activo = fields.Boolean(string="Sonido activo", default=True)
    tiempo_estimado_entrega = fields.Integer(string="Tiempo estimado entrega (min)", default=0)
    motivo_rechazo = fields.Text(string="Motivo del rechazo")
    tiene_reclamo = fields.Boolean(string="Tiene reclamo", default=False)
    descripcion_reclamo = fields.Text(string="Descripción del reclamo")
    productos_modificados = fields.Boolean(string="Productos modificados", default=False)
    productos_snapshot = fields.Text(string="Snapshot de productos")
    es_para_envio = fields.Boolean(string="Es para envío", default=False)
    direccion_entrega_completa = fields.Text(string="Dirección de entrega completa")
    productos_completados = fields.Text(string="Productos completados", help="JSON con IDs de líneas completadas")
    
    # Campos computados para mostrar tiempos
    tiempo_estado_minutos = fields.Integer(string="Minutos en estado actual", compute="_compute_tiempos")
    tiempo_total_minutos = fields.Integer(string="Minutos totales", compute="_compute_tiempos")
    
    @api.depends('tiempo_inicio_estado', 'tiempo_inicio_total')
    def _compute_tiempos(self):
        for record in self:
            ahora = fields.Datetime.now()
            if record.tiempo_inicio_estado:
                delta_estado = ahora - record.tiempo_inicio_estado
                record.tiempo_estado_minutos = int(delta_estado.total_seconds() / 60)
            else:
                record.tiempo_estado_minutos = 0
                
            if record.tiempo_inicio_total:
                delta_total = ahora - record.tiempo_inicio_total
                record.tiempo_total_minutos = int(delta_total.total_seconds() / 60)
            else:
                record.tiempo_total_minutos = 0

    @api.model
    def create(self, vals):
        # Establecer estado "nuevo" solo si no viene del eCommerce
        if not vals.get('website_id'):  # Creado manualmente, no desde website
            vals['estado_rapido'] = 'nuevo'
            vals['tiempo_inicio_estado'] = fields.Datetime.now()
            vals['tiempo_inicio_total'] = fields.Datetime.now()
            vals['sonido_activo'] = True
        
        result = super().create(vals)
        
        # NO activar dashboard para pedidos web en borrador
        # Solo se activará cuando el estado cambie a 'sale' en write() o action_confirm()
        
        # Detectar tipo de entrega si es estado "nuevo"
        if result.estado_rapido == 'nuevo':
            result._detectar_tipo_entrega()
        
        return result
    
    def write(self, vals):
        result = super().write(vals)
        
        # Si el estado cambia a 'sale' (confirmado) y es del eCommerce
        if vals.get('state') == 'sale' and self.website_id:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"🌐 PEDIDO WEB DETECTADO: {self.name} - Estado: {vals.get('state')} - Website: {self.website_id}")
            
            if not self.estado_rapido:
                self.estado_rapido = 'nuevo'
                self.tiempo_inicio_estado = fields.Datetime.now()
                self.tiempo_inicio_total = fields.Datetime.now()
                self.sonido_activo = True
            self._detectar_tipo_entrega()
            # Notificar nuevo pedido web al PoS
            self._notificar_pedido_web_pos()
        
        return result
    
    def action_confirm(self):
        """Override para interceptar confirmación de pedidos web"""
        result = super().action_confirm()
        
        # Si es pedido web Y no tiene estado_rapido, asignarlo y notificar
        if self.website_id and not self.estado_rapido:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"🌐 PEDIDO WEB CONFIRMADO: {self.name} - Website: {self.website_id}")
            
            self.estado_rapido = 'nuevo'
            self.tiempo_inicio_estado = fields.Datetime.now()
            self.tiempo_inicio_total = fields.Datetime.now()
            self.sonido_activo = True
            self._detectar_tipo_entrega()
            self._notificar_pedido_web_pos()
        
        return result

    def action_aceptar_pedido(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Aceptar Pedido',
            'res_model': 'tu_pedido.aceptar_pedido_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    def action_rechazar_pedido(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rechazar Pedido',
            'res_model': 'tu_pedido.rechazar_pedido_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    def action_cambiar_estado(self, nuevo_estado):
        try:
            estado_anterior = self.estado_rapido
            tiempo_anterior = self.tiempo_inicio_estado
            
            # Calcular tiempo en estado anterior
            minutos_en_estado = 0
            if tiempo_anterior and estado_anterior:
                ahora = fields.Datetime.now()
                if ahora > tiempo_anterior:
                    delta = ahora - tiempo_anterior
                    minutos_en_estado = max(0, int(delta.total_seconds() / 60))
            
            # Registrar cambio en historial
            if estado_anterior and estado_anterior != nuevo_estado:
                self.env['tu_pedido.estado.historial'].create({
                    'pedido_id': self.id,
                    'estado_anterior': estado_anterior,
                    'estado_nuevo': nuevo_estado,
                    'fecha_cambio': fields.Datetime.now(),
                    'minutos_en_estado_anterior': minutos_en_estado
                })
            
            self.estado_rapido = nuevo_estado
            self.tiempo_inicio_estado = fields.Datetime.now()
            
            # Desactivar sonido cuando cambia de estado "nuevo"
            if estado_anterior == "nuevo" and nuevo_estado != "nuevo":
                self.sonido_activo = False
            
            # Si llega a "aceptado", crear snapshot de productos
            if nuevo_estado == "aceptado":
                self._crear_snapshot_productos()
                self.productos_modificados = False
                self._detectar_tipo_entrega()
            
            # Si llega a "nuevo", detectar tipo de entrega
            if nuevo_estado == "nuevo":
                self._detectar_tipo_entrega()
            
            # Si llega a "terminado", confirmar la orden de venta y notificar delivery
            if nuevo_estado == "terminado":
                try:
                    if self.state == "draft":
                        self.action_confirm()
                except:
                    pass  # Ignorar errores de confirmación
                
                # Notificar si es delivery
                if self.es_para_envio:
                    self._notificar_delivery_terminado()
            
            return True
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error en action_cambiar_estado: {e}")
            return False
    
    def _crear_pos_order_desde_sale(self):
        """Crear pos.order desde sale.order cuando se acepta en dashboard"""
        try:
            # Extraer tracking_number del nombre
            tracking_number = None
            if 'Pedido-' in self.name:
                tracking_number = self.name.replace('Pedido-', '')
            elif 'Mesa' in self.name:
                # Para nombres como "TerrazaMesa2", usar un número basado en el ID
                tracking_number = str(self.id)
            
            if not tracking_number:
                return
            
            # Verificar si ya existe pos.order
            existing_pos_order = self.env['pos.order'].search([
                ('tracking_number', '=', tracking_number)
            ], limit=1)
            
            if existing_pos_order:
                # Actualizar estado de pos.order existente
                existing_pos_order.write({
                    'state': 'paid',  # Cambiar a estado aceptado
                    'enviado_a_cocina': True
                })
                print(f"DEBUG: pos.order {existing_pos_order.name} actualizado a paid")
            else:
                # Buscar sesión PoS activa
                active_session = self.env['pos.session'].search([
                    ('state', '=', 'opened')
                ], limit=1)
                
                if not active_session:
                    print("DEBUG: No hay sesión PoS activa")
                    return
                
                # Crear pos.order básico
                pos_vals = {
                    'name': f'Orden-{tracking_number}',
                    'tracking_number': tracking_number,
                    'session_id': active_session.id,
                    'partner_id': self.partner_id.id,
                    'state': 'paid',
                    'amount_total': 0.0,
                    'amount_tax': 0.0,
                    'amount_paid': 0.0,
                    'amount_return': 0.0,
                    'pos_reference': f'Order {tracking_number}',
                    'date_order': fields.Datetime.now(),
                    'enviado_a_cocina': True,
                }
                
                pos_order = self.env['pos.order'].create(pos_vals)
                print(f"DEBUG: pos.order {pos_order.name} creado desde dashboard")
                
        except Exception as e:
            print(f"DEBUG: Error creando pos.order: {e}")
    
    def _crear_snapshot_productos(self):
        """Crear snapshot de productos al aceptar pedido"""
        productos_info = []
        for line in self.order_line:
            productos_info.append({
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit
            })
        import json
        self.productos_snapshot = json.dumps(productos_info)
    
    def _detectar_cambios_productos(self):
        """Detectar si hubo cambios en productos después de aceptar"""
        if self.estado_rapido in ['nuevo', 'entregado', 'rechazado']:
            return
        
        # Si no hay snapshot, crearlo ahora (primera vez que se detecta cambio)
        if not self.productos_snapshot:
            # Crear snapshot temporal con productos actuales menos el último cambio
            # Para poder comparar, necesitamos simular el estado anterior
            self.productos_modificados = True
            self.env.cr.commit()
            return
        
        # Si ya está marcado como modificado, no volver a verificar
        if self.productos_modificados:
            return
        
        try:
            import json
            productos_originales = json.loads(self.productos_snapshot)
            productos_actuales = []
            
            for line in self.order_line:
                productos_actuales.append({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit
                })
            
            # Comparar usando JSON strings ordenados
            productos_orig_str = json.dumps(productos_originales, sort_keys=True)
            productos_actual_str = json.dumps(productos_actuales, sort_keys=True)
            
            hay_cambios = productos_orig_str != productos_actual_str
            
            if hay_cambios:
                self.productos_modificados = True
                self.env.cr.commit()
                
        except Exception as e:
            self.productos_modificados = True
            self.env.cr.commit()
    
    def action_detectar_cambios_manual(self):
        """Botón manual para detectar cambios"""
        self._detectar_cambios_productos()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
    
    def action_marcar_productos_revisados(self):
        """Marcar productos modificados como revisados"""
        # Actualizar snapshot con productos actuales ANTES de marcar como no modificado
        self._crear_snapshot_productos()
        self.productos_modificados = False
        return True
    
    def get_detalles_cambios(self):
        """Obtener detalles de los cambios en productos"""
        # Si no hay snapshot, crearlo ahora con los productos actuales como base
        if not self.productos_snapshot:
            self._crear_snapshot_productos()
            return {'agregados': [], 'modificados': [], 'eliminados': []}
        
        try:
            import json
            productos_originales = json.loads(self.productos_snapshot)
            productos_actuales = []
            
            for line in self.order_line:
                productos_actuales.append({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit
                })
            
            # Crear diccionarios para comparación usando product_id como clave
            orig_dict = {p['product_id']: p for p in productos_originales}
            actual_dict = {p['product_id']: p for p in productos_actuales}
            
            agregados = []
            modificados = []
            eliminados = []
            
            # Productos agregados
            for pid, producto in actual_dict.items():
                if pid not in orig_dict:
                    agregados.append({
                        'name': producto['name'],
                        'qty': producto['product_uom_qty'],
                        'tipo': 'agregado'
                    })
            
            # Productos eliminados
            for pid, producto in orig_dict.items():
                if pid not in actual_dict:
                    eliminados.append({
                        'name': producto['name'],
                        'qty': producto['product_uom_qty'],
                        'tipo': 'eliminado'
                    })
            
            # Productos modificados (cantidad o precio)
            for pid, producto_actual in actual_dict.items():
                if pid in orig_dict:
                    producto_orig = orig_dict[pid]
                    if (producto_actual['product_uom_qty'] != producto_orig['product_uom_qty'] or
                        producto_actual['price_unit'] != producto_orig['price_unit']):
                        modificados.append({
                            'name': producto_actual['name'],
                            'qty_original': producto_orig['product_uom_qty'],
                            'qty_nueva': producto_actual['product_uom_qty'],
                            'precio_original': producto_orig['price_unit'],
                            'precio_nuevo': producto_actual['price_unit'],
                            'tipo': 'modificado'
                        })
            
            return {
                'agregados': agregados,
                'modificados': modificados,
                'eliminados': eliminados
            }
        except Exception as e:
            return {'agregados': [], 'modificados': [], 'eliminados': []}
    
    def _detectar_tipo_entrega(self):
        """Detectar si es para envío o retiro en local"""
        # Buscar producto "Envío estándar" o similares
        tiene_envio = any(
            'envío estándar' in line.product_id.name.lower() or
            'envio estandar' in line.product_id.name.lower() or
            'envío' in line.product_id.name.lower() or 
            'envio' in line.product_id.name.lower() or
            'delivery' in line.product_id.name.lower() or
            'shipping' in line.product_id.name.lower() or
            'entrega' in line.product_id.name.lower()
            for line in self.order_line
        )
        
        # Verificar si tiene producto de recolección en tienda
        tiene_recoleccion = any(
            'recolección en tienda' in line.product_id.name.lower() or
            'recoleccion en tienda' in line.product_id.name.lower() or
            'retiro en tienda' in line.product_id.name.lower() or
            'pickup' in line.product_id.name.lower()
            for line in self.order_line
        )
        
        # Si tiene envío = True, si tiene recolección = False, si no tiene ninguno = False (retiro)
        self.es_para_envio = tiene_envio and not tiene_recoleccion
        
        self.es_para_envio = tiene_envio
        
        # Si es para envío, obtener dirección completa
        if tiene_envio:
            partner = self.partner_shipping_id or self.partner_id
            if partner:
                direccion_parts = []
                if partner.street:
                    direccion_parts.append(partner.street)
                if partner.street2:
                    direccion_parts.append(partner.street2)
                if partner.city:
                    direccion_parts.append(partner.city)
                if partner.state_id:
                    direccion_parts.append(partner.state_id.name)
                if partner.zip:
                    direccion_parts.append(partner.zip)
                
                self.direccion_entrega_completa = ', '.join(direccion_parts)
        else:
            self.direccion_entrega_completa = ''
    
    def action_siguiente_estado(self):
        """Avanza al siguiente estado en la secuencia"""
        try:
            estados_orden = ["nuevo", "aceptado", "preparacion", "terminado", "despachado", "entregado"]
            if self.estado_rapido in estados_orden:
                indice_actual = estados_orden.index(self.estado_rapido)
                if indice_actual < len(estados_orden) - 1:
                    nuevo_estado = estados_orden[indice_actual + 1]
                    self.action_cambiar_estado(nuevo_estado)
            return True
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error en action_siguiente_estado: {e}")
            return False
    
    def _notificar_delivery_terminado(self):
        """Notificar que pedido delivery está terminado"""
        try:
            # Solo crear un log simple
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"🚚 DELIVERY LISTO: {self.name} - {self.direccion_entrega_completa or 'Sin dirección'}")
        except Exception as e:
            # Ignorar errores de notificación
            pass
    
    def _notificar_pedido_web_pos(self):
        """Notificar nuevo pedido web al PoS"""
        try:
            # Preparar datos del pedido
            productos_resumen = []
            for line in self.order_line[:3]:  # Primeros 3 productos
                productos_resumen.append({
                    'name': line.name,
                    'qty': line.product_uom_qty
                })
            
            # Enviar notificación a todos los usuarios conectados
            self.env['bus.bus']._sendone(
                (self.env.cr.dbname, 'res.partner', 0),
                'tu_pedido_web_notification',
                {
                    'order_id': self.id,
                    'order_name': self.name,
                    'cliente': self.partner_id.name,
                    'telefono': self.partner_id.phone or self.partner_id.mobile or 'Sin teléfono',
                    'direccion': self.direccion_entrega_completa or 'Retiro en local',
                    'es_para_envio': self.es_para_envio,
                    'productos': productos_resumen,
                    'total_productos': len(self.order_line),
                    'amount_total': self.amount_total,
                    'create_date': self.create_date.isoformat()
                }
            )
            
            # Log para debug
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"🌐 PEDIDO WEB NOTIFICADO: {self.name} - {self.partner_id.name}")
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error notificando pedido web: {e}")
            pass
    
    def action_cliente_confirma_recepcion(self):
        """Acción para cuando el cliente confirma que recibió el pedido"""
        if self.estado_rapido == "despachado":
            self.cliente_confirmo_recepcion = True
            self.action_cambiar_estado("entregado")
        return True
    
    def toggle_producto_completado(self, line_id):
        """Marcar/desmarcar un producto como completado"""
        import json
        try:
            # Obtener lista actual de productos completados
            completados = json.loads(self.productos_completados or '[]')
            
            # Toggle: si está, lo quita; si no está, lo agrega
            if line_id in completados:
                completados.remove(line_id)
                accion = 'desmarcado'
            else:
                completados.append(line_id)
                accion = 'marcado'
            
            # Guardar lista actualizada
            self.productos_completados = json.dumps(completados)
            
            return {
                'success': True,
                'message': f'Producto {accion} como completado',
                'completados': completados
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_productos_completados(self):
        """Obtener lista de productos completados"""
        import json
        try:
            return json.loads(self.productos_completados or '[]')
        except:
            return []
    
    def action_marcar_despachado(self):
        """Marcar pedido como despachado desde notificación"""
        self.action_cambiar_estado('despachado')
        return {'type': 'ir.actions.act_window_close'}
    

    
    @api.model
    def get_pedidos_dashboard(self):
        """Método para obtener datos del dashboard"""
        pedidos = self.search([('estado_rapido', '!=', 'entregado')])
        return pedidos.read([
            'name', 'partner_id', 'estado_rapido', 'nota_cocina', 
            'tiempo_estado_minutos', 'tiempo_total_minutos', 'sonido_activo',
            'order_line'
        ])

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result.order_id and result.order_id.estado_rapido not in ['nuevo', 'entregado', 'rechazado']:
            # Si no hay snapshot, crearlo ANTES de detectar cambios
            if not result.order_id.productos_snapshot:
                # Crear snapshot con productos actuales MENOS la línea recién creada
                productos_anteriores = []
                for line in result.order_id.order_line:
                    if line.id != result.id:  # Excluir la línea recién creada
                        productos_anteriores.append({
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'product_uom_qty': line.product_uom_qty,
                            'price_unit': line.price_unit
                        })
                import json
                result.order_id.productos_snapshot = json.dumps(productos_anteriores)
            
            if not result.order_id.productos_modificados:
                result.order_id._detectar_cambios_productos()
        return result
    
    def write(self, vals):
        # Guardar estado anterior para crear snapshot si es necesario
        orders_to_check = set()
        snapshots_to_create = {}
        
        for record in self:
            if (record.order_id and 
                record.order_id.estado_rapido not in ['nuevo', 'entregado', 'rechazado'] and
                not record.order_id.productos_modificados):
                
                # Si no hay snapshot, crear uno con el estado ANTES del cambio
                if not record.order_id.productos_snapshot:
                    productos_anteriores = []
                    for line in record.order_id.order_line:
                        productos_anteriores.append({
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'product_uom_qty': line.product_uom_qty,
                            'price_unit': line.price_unit
                        })
                    import json
                    snapshots_to_create[record.order_id] = json.dumps(productos_anteriores)
                
                orders_to_check.add(record.order_id)
        
        # Crear snapshots antes de hacer cambios
        for order, snapshot in snapshots_to_create.items():
            order.productos_snapshot = snapshot
        
        result = super().write(vals)
        
        # Detectar cambios después de hacer cambios
        for order in orders_to_check:
            order._detectar_cambios_productos()
        
        return result
    
    def unlink(self):
        # Obtener órdenes y crear snapshots ANTES de eliminar
        orders_to_check = set()
        snapshots_to_create = {}
        
        for record in self:
            if (record.order_id and 
                record.order_id.estado_rapido not in ['nuevo', 'entregado', 'rechazado'] and
                not record.order_id.productos_modificados):
                
                # Si no hay snapshot, crear uno con el estado ANTES de eliminar
                if not record.order_id.productos_snapshot:
                    productos_anteriores = []
                    for line in record.order_id.order_line:
                        productos_anteriores.append({
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'product_uom_qty': line.product_uom_qty,
                            'price_unit': line.price_unit
                        })
                    import json
                    snapshots_to_create[record.order_id] = json.dumps(productos_anteriores)
                
                orders_to_check.add(record.order_id)
        
        # Crear snapshots antes de eliminar
        for order, snapshot in snapshots_to_create.items():
            order.productos_snapshot = snapshot
        
        result = super().unlink()
        
        # Detectar cambios después de eliminar
        for order in orders_to_check:
            order._detectar_cambios_productos()
        
        return result