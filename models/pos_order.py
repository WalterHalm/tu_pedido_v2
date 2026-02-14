from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'
    

    
    @api.model
    def sync_from_ui(self, orders):
        """Interceptar sync_from_ui para procesar órdenes"""
        result = super().sync_from_ui(orders)
        return result
    

    
    def _pedido_ya_enviado_a_cocina(self, tracking_number):
        """Verificar si el pedido ya fue enviado a cocina usando identificador único"""
        try:
            # Buscar en sale.order por identificador único en notas
            existing_sale_orders = self.env['sale.order'].sudo().search([
                ('nota_cocina', 'ilike', f'[REF:{tracking_number}]'),
                ('estado_rapido', '!=', False)
            ])
            
            if existing_sale_orders:
                print(f"DEBUG: Pedido {tracking_number} ya existe en dashboard")
                return True
            
            return False
            
        except Exception as e:
            print(f"DEBUG: Error verificando duplicados en pos.order: {e}")
            return False
    

    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Llenar dirección cuando cambia el partner solo si es delivery"""
        if self.is_delivery:
            self._llenar_direccion_delivery()
    

    
    def write(self, vals):
        """Interceptar write para detectar cambios importantes"""
        try:
            # Si se está marcando como delivery y no tiene dirección, agregar una
            if vals.get('is_delivery'):
                for record in self:
                    if not record.direccion_delivery and not vals.get('direccion_delivery'):
                        vals['direccion_delivery'] = 'Dirección no especificada'
            
            result = super().write(vals)
            
            # Detectar cuando cambia el estado (sin bloquear)
            for order in self:
                try:
                    # Detectar cancelación de pedido
                    if vals.get('state') == 'cancel':
                        print(f"DEBUG: Pedido {order.name} cancelado en PoS, tracking: {order.tracking_number}")
                        # Actualizar sale.order correspondiente si existe
                        order._marcar_sale_order_cancelado()
                    
                    # Detectar cancelación y marcar sale.order correspondiente
                    pass
                except Exception as e:
                    print(f"DEBUG: Error procesando orden {order.name}: {e}")
            
            return result
        except Exception as e:
            print(f"DEBUG: Error en write: {e}")
            return super().write(vals)
    
    # Campos para integración con tu_pedido (opcionales para evitar errores IndexedDB)
    estado_rapido = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('aceptado', 'Aceptado'),
        ('preparacion', 'En Preparación'),
        ('terminado', 'Terminado'),
        ('despachado', 'Despachado/Retirado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado')
    ], string='Estado Rápido', default='nuevo', required=False)
    
    tipo_pedido = fields.Selection([
        ('mostrador', 'Mostrador'),
        ('mesa', 'Mesa'),
        ('delivery', 'Delivery'),
        ('retiro', 'Retiro')
    ], string='Tipo de Pedido', default='mostrador', required=False)
    
    is_delivery = fields.Boolean(string='Es Delivery', default=False, required=False)
    direccion_delivery = fields.Char(string='Dirección de Envío', required=False)
    telefono_delivery = fields.Char(string='Teléfono de Contacto', required=False)
    
    tiempo_inicio_estado = fields.Datetime(string='Inicio Estado Actual', required=False)
    tiempo_inicio_total = fields.Datetime(string='Inicio Total', required=False)
    sonido_activo = fields.Boolean(string='Sonido Activo', default=True, required=False)
    enviado_a_cocina = fields.Boolean(string='Enviado a Cocina', default=False, required=False)
    
    # Campos computados para tiempos
    tiempo_estado_minutos = fields.Integer(string='Minutos en Estado', compute='_compute_tiempos', store=False)
    tiempo_total_minutos = fields.Integer(string='Minutos Totales', compute='_compute_tiempos', store=False)
    

    

    
    @api.depends('tiempo_inicio_estado', 'tiempo_inicio_total')
    def _compute_tiempos(self):
        for record in self:
            now = fields.Datetime.now()
            if record.tiempo_inicio_estado:
                delta = now - record.tiempo_inicio_estado
                record.tiempo_estado_minutos = int(delta.total_seconds() / 60)
            else:
                record.tiempo_estado_minutos = 0
                
            if record.tiempo_inicio_total:
                delta = now - record.tiempo_inicio_total
                record.tiempo_total_minutos = int(delta.total_seconds() / 60)
            else:
                record.tiempo_total_minutos = 0
    
    def action_enviar_a_cocina(self):
        """Enviar pedido PoS al dashboard de cocina"""
        print(f"DEBUG: === ACTION_ENVIAR_A_COCINA INICIADO ===")
        print(f"DEBUG: Pedido ID: {self.id}, Nombre: {self.name}")
        print(f"DEBUG: Tracking: {self.tracking_number}")
        print(f"DEBUG: Estado actual: {getattr(self, 'estado_rapido', 'NO DEFINIDO')}")
        print(f"DEBUG: Enviado a cocina: {getattr(self, 'enviado_a_cocina', 'NO DEFINIDO')}")
        self.ensure_one()
        
        # Verificar si ya fue enviado
        existing_sale_order = self._buscar_orden_existente(self.tracking_number)
        if existing_sale_order:
            print(f"DEBUG: Pedido {self.tracking_number} ya existe, actualizando")
            self._actualizar_orden_existente(existing_sale_order)
            return True
        
        # Crear orden de venta para el dashboard
        order_vals = {
            'name': self.name,
            'partner_id': self.partner_id.id if self.partner_id else self.env.ref('base.public_partner').id,
            'state': 'draft',
            'estado_rapido': 'nuevo',
            'tiempo_inicio_estado': fields.Datetime.now(),
            'tiempo_inicio_total': fields.Datetime.now(),
            'sonido_activo': True,
            'nota_cocina': self._obtener_notas_cocina_con_ref(),
        }
        
        # Crear la orden
        sale_order = self.env['sale.order'].create(order_vals)
        
        # Crear líneas de productos con atributos y combos
        for line in self.lines:
            # Solo procesar líneas principales (no items de combo)
            if hasattr(line, 'combo_parent_id') and line.combo_parent_id:
                continue  # Saltar items de combo, se procesan con el padre
            
            # Construir nombre completo con atributos
            product_name = self._construir_nombre_con_atributos(line)
            
            line_vals = {
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'price_unit': line.price_unit,
                'name': product_name,
            }
            
            # Crear línea principal
            main_line = self.env['sale.order.line'].create(line_vals)
            
            # Agregar items de combo si existen
            self._crear_items_combo_reales(line, sale_order.id)
        
        # Detectar tipo de pedido antes de marcar como enviado
        self._detectar_tipo_pedido()
        
        # Marcar como enviado y establecer estado
        self.write({
            'enviado_a_cocina': True,
            'estado_rapido': 'nuevo',
            'tiempo_inicio_estado': fields.Datetime.now(),
            'tiempo_inicio_total': fields.Datetime.now(),
            'sonido_activo': True
        })
        
        print(f"DEBUG: === ACTION_ENVIAR_A_COCINA COMPLETADO ===")
        print(f"DEBUG: {self.name} enviado a dashboard exitosamente")
        print(f"DEBUG: Estado final: {self.estado_rapido}")
        print(f"DEBUG: Enviado a cocina final: {self.enviado_a_cocina}")
        return True
    
    def _buscar_orden_existente(self, tracking_number):
        """Buscar orden existente en sale.order"""
        return self.env['sale.order'].sudo().search([
            ('nota_cocina', 'ilike', f'[REF:{tracking_number}]'),
            ('estado_rapido', '!=', False)
        ], limit=1)
    
    def _actualizar_orden_existente(self, sale_order):
        """Actualizar orden existente con cambios de productos"""
        try:
            print(f"DEBUG: Actualizando orden existente {sale_order.name}")
            
            # Verificar si hay cambios en productos
            if self._hay_cambios_productos(sale_order):
                print(f"DEBUG: Detectados cambios en productos")
                
                # Eliminar líneas existentes
                sale_order.order_line.unlink()
                
                # Crear nuevas líneas con productos actuales
                for line in self.lines:
                    product_name = self._construir_nombre_con_atributos(line)
                    
                    line_vals = {
                        'order_id': sale_order.id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'price_unit': line.price_unit,
                        'name': product_name,
                    }
                    
                    main_line = self.env['sale.order.line'].create(line_vals)
                    self._crear_lineas_combo(line, sale_order.id, main_line.id)
                
                # Actualizar notas con nueva información
                sale_order.write({
                    'nota_cocina': self._obtener_notas_cocina_con_ref(),
                    'productos_modificados': True,  # Marcar como modificado
                    'tiempo_inicio_estado': fields.Datetime.now(),  # Reiniciar tiempo
                })
                
                print(f"DEBUG: Orden {sale_order.name} actualizada con cambios")
            else:
                print(f"DEBUG: No hay cambios en productos")
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Error actualizando orden existente: {e}")
            return False
    
    def _hay_cambios_productos(self, sale_order):
        """Verificar si hay cambios en los productos"""
        try:
            print(f"DEBUG: Comparando productos - PoS lines: {len(self.lines)}, Sale lines: {len(sale_order.order_line)}")
            
            # Crear hash simple de productos actuales
            pos_hash = []
            for line in self.lines:
                item = f"{line.product_id.id}|{line.qty}|{self._construir_nombre_con_atributos(line)}"
                pos_hash.append(item)
            pos_hash.sort()
            
            # Crear hash de productos existentes (excluyendo líneas de combo)
            sale_hash = []
            for line in sale_order.order_line:
                if not line.name.startswith('  →'):  # Excluir líneas de combo
                    item = f"{line.product_id.id}|{int(line.product_uom_qty)}|{line.name}"
                    sale_hash.append(item)
            sale_hash.sort()
            
            print(f"DEBUG: PoS hash: {pos_hash}")
            print(f"DEBUG: Sale hash: {sale_hash}")
            
            hay_cambios = pos_hash != sale_hash
            print(f"DEBUG: Hay cambios: {hay_cambios}")
            return hay_cambios
            
        except Exception as e:
            print(f"DEBUG: Error comparando productos: {e}")
            return True
    
    def _obtener_notas_cocina_con_ref(self):
        """Obtener notas para mostrar en cocina con identificador único"""
        notas = []
        
        # Agregar información de mesa si existe
        if self.table_id:
            mesa_info = f"Mesa: {self.table_id.name}"
            if hasattr(self.table_id, 'table_number') and self.table_id.table_number:
                mesa_info += f" N°{self.table_id.table_number}"
            notas.append(mesa_info)
        
        # Agregar notas de líneas de productos
        for line in self.lines:
            if hasattr(line, 'note') and line.note:
                notas.append(f"{line.product_id.name}: {line.note}")
        
        notas_base = ' | '.join(notas) if notas else 'Sin notas especiales'
        # Agregar identificador único
        return f"{notas_base} | [REF:{self.tracking_number}]"
    
    def _construir_nombre_con_atributos(self, line):
        """Construir nombre del producto con atributos y combos"""
        # El full_product_name ya incluye los atributos
        if hasattr(line, 'full_product_name') and line.full_product_name:
            nombre = line.full_product_name
        else:
            nombre = line.product_id.name
        
        # Agregar nota del producto si existe
        if hasattr(line, 'note') and line.note:
            nombre += f" - {line.note}"
        
        return nombre
    
    def _obtener_atributos_linea(self, line):
        """Obtener atributos de la línea PoS usando product.template.attribute.line"""
        atributos = []
        
        try:
            # Obtener atributos desde product.template.attribute.line
            template = line.product_id.product_tmpl_id
            attribute_lines = self.env['product.template.attribute.line'].search([
                ('product_tmpl_id', '=', template.id)
            ])
            
            for attr_line in attribute_lines:
                if attr_line.attribute_id and attr_line.value_ids:
                    # Tomar el primer valor por defecto o todos los valores
                    for value in attr_line.value_ids:
                        atributos.append(f"{attr_line.attribute_id.name}: {value.name}")
                        break  # Solo tomar el primer valor por línea
        
        except Exception as e:
            print(f"DEBUG: Error obteniendo atributos: {e}")
        
        return atributos
    
    def _crear_items_combo_reales(self, pos_line, sale_order_id):
        """Crear líneas para los items reales del combo"""
        try:
            # Buscar items de combo que tienen este como padre
            combo_items = [line for line in self.lines 
                          if hasattr(line, 'combo_parent_id') and 
                          line.combo_parent_id and 
                          line.combo_parent_id.id == pos_line.id]
            
            for combo_item in combo_items:
                item_name = self._construir_nombre_con_atributos(combo_item)
                combo_vals = {
                    'order_id': sale_order_id,
                    'product_id': combo_item.product_id.id,
                    'product_uom_qty': combo_item.qty,
                    'price_unit': combo_item.price_unit,
                    'name': f"  → {item_name}",  # Indentar para mostrar que es parte del combo
                }
                self.env['sale.order.line'].create(combo_vals)
                    
        except Exception as e:
            print(f"DEBUG: Error creando items combo: {e}")
    
    def _es_producto_combo(self, product):
        """Verificar si un producto es tipo combo usando product.combo.item"""
        try:
            # Buscar si existen items de combo para este template
            combo_items = self.env['product.combo.item'].search([
                ('combo_id', '=', product.product_tmpl_id.id)
            ], limit=1)
            return bool(combo_items)
        except:
            return False
    
    def _obtener_items_combo(self, product):
        """Obtener los items del combo desde product.combo.item"""
        items = []
        try:
            # Obtener items del combo desde product.combo.item
            combo_items = self.env['product.combo.item'].search([
                ('combo_id', '=', product.product_tmpl_id.id)
            ])
            
            for combo_item in combo_items:
                if combo_item.product_id:
                    items.append(combo_item.product_id)
                    
        except Exception as e:
            print(f"DEBUG: Error obteniendo items combo: {e}")
        
        return items
    
    def test_enviar_cocina(self):
        """Método de prueba para llamar desde el shell"""
        print(f"DEBUG: test_enviar_cocina para {self.name}")
        return self.action_enviar_a_cocina()
    
    def _detectar_tipo_pedido(self):
        """Detectar tipo de pedido basado en contexto PoS"""
        try:
            print(f"DEBUG: === DETECTANDO TIPO DE PEDIDO ===")
            print(f"DEBUG: Orden: {self.name}")
            print(f"DEBUG: Número de líneas: {len(self.lines)}")
            
            # Mostrar todos los productos
            for line in self.lines:
                print(f"DEBUG: Producto: '{line.product_id.name}'")
            
            # Verificar si tiene producto "envio estandar" para activar delivery
            has_delivery_product = any(
                'envio' in line.product_id.name.lower() or 
                'envío' in line.product_id.name.lower() or
                'delivery' in line.product_id.name.lower() or
                'entrega' in line.product_id.name.lower()
                for line in self.lines
            )
            
            print(f"DEBUG: Tiene producto delivery: {has_delivery_product}")
            
            if has_delivery_product:
                print(f"DEBUG: MARCANDO COMO DELIVERY")
                self.is_delivery = True
                self.tipo_pedido = 'delivery'
                # Llenar dirección automáticamente desde el partner
                self._llenar_direccion_delivery()
            elif self.table_id:
                self.tipo_pedido = 'mesa'
            elif getattr(self, 'takeaway', False):
                self.tipo_pedido = 'retiro'
            else:
                self.tipo_pedido = 'mostrador'
                
            print(f"DEBUG: Tipo final: {self.tipo_pedido}, is_delivery: {self.is_delivery}")
            print(f"DEBUG: === FIN DETECCIÓN ===")
        except Exception as e:
            print(f"DEBUG: Error en _detectar_tipo_pedido: {e}")
            # En caso de error, usar valores por defecto
            self.tipo_pedido = 'mostrador'
    
    def _llenar_direccion_delivery(self):
        """Llenar dirección de delivery desde el partner solo si es delivery"""
        try:
            if self.is_delivery:
                if not self.direccion_delivery:
                    if self.partner_id:
                        direccion_completa = self._obtener_direccion_completa(self.partner_id)
                        self.direccion_delivery = direccion_completa or 'Dirección no especificada'
                    else:
                        self.direccion_delivery = 'Dirección no especificada'
                        
                # Llenar teléfono si no está presente
                if not self.telefono_delivery and self.partner_id:
                    telefono = self.partner_id.phone or self.partner_id.mobile
                    if telefono:
                        self.telefono_delivery = telefono
        except Exception as e:
            print(f"DEBUG: Error en _llenar_direccion_delivery: {e}")
            if self.is_delivery and not self.direccion_delivery:
                self.direccion_delivery = 'Dirección no especificada'
    
    def _obtener_direccion_completa(self, partner):
        """Obtener dirección completa del partner"""
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
            
        return ', '.join(direccion_parts) if direccion_parts else False
    
    def action_cambiar_estado(self, nuevo_estado):
        """Cambiar estado del pedido PoS"""
        self.ensure_one()
        if self.estado_rapido != nuevo_estado:
            vals = {
                'estado_rapido': nuevo_estado,
                'tiempo_inicio_estado': fields.Datetime.now()
            }
            # Desactivar sonido cuando sale del estado "nuevo"
            if self.estado_rapido == "nuevo" and nuevo_estado != "nuevo":
                vals['sonido_activo'] = False
            
            self.write(vals)
        return True
    
    def action_siguiente_estado(self):
        """Avanzar al siguiente estado"""
        estados = ['nuevo', 'aceptado', 'preparacion', 'terminado', 'despachado', 'entregado']
        if self.estado_rapido in estados:
            current_index = estados.index(self.estado_rapido)
            if current_index < len(estados) - 1:
                next_estado = estados[current_index + 1]
                self.action_cambiar_estado(next_estado)
                
                # Notificar si es delivery y está terminado
                if next_estado == 'terminado' and self.is_delivery:
                    self._notificar_delivery_listo()
        return True
    
    def _notificar_delivery_listo(self):
        """Notificar que el pedido delivery está listo para envío"""
        # Crear notificación simple
        message = f"🚚 DELIVERY PoS LISTO: {self.name}\n📍 {self.direccion_delivery or 'Sin dirección'}\n📞 {self.telefono_delivery or 'Sin teléfono'}\n👤 {self.partner_id.name if self.partner_id else 'Cliente PoS'}"
        
        self.env.user.notify_info(message, title="Pedido Delivery PoS Terminado", sticky=True)
        print(f"DEBUG: Notificación delivery PoS enviada para {self.name}")
    
    def action_marcar_despachado(self):
        """Marcar pedido PoS como despachado desde notificación"""
        self.action_cambiar_estado('despachado')
        return {'type': 'ir.actions.act_window_close'}
    
    def action_marcar_entregado(self):
        """Marcar pedido como entregado"""
        self.action_cambiar_estado('entregado')
        return True
    
    def _marcar_sale_order_cancelado(self):
        """Marcar sale.order correspondiente como cancelado"""
        try:
            # Buscar sale.order correspondiente por tracking_number
            sale_order = self.env['sale.order'].sudo().search([
                ('nota_cocina', 'ilike', f'[REF:{self.tracking_number}]'),
                ('estado_rapido', '!=', False)
            ], limit=1)
            
            if sale_order:
                # Agregar marca de cancelado en la nota_cocina
                nota_actual = sale_order.nota_cocina or ''
                if '[CANCELADO]' not in nota_actual:
                    sale_order.write({'nota_cocina': f"[CANCELADO] {nota_actual}"})
                    print(f"DEBUG: Sale order {sale_order.name} marcado como cancelado con nota: {sale_order.nota_cocina}")
                else:
                    print(f"DEBUG: Sale order {sale_order.name} ya estaba marcado como cancelado")
            else:
                print(f"DEBUG: No se encontró sale.order para tracking {self.tracking_number}")
        except Exception as e:
            print(f"DEBUG: Error marcando sale.order como cancelado: {e}")
    
    @api.model
    def enviar_orden_dashboard(self, order_id):
        """Método específico para ser llamado desde JavaScript del PoS"""
        try:
            order = self.browse(order_id)
            if order.exists() and not getattr(order, 'enviado_a_cocina', False):
                print(f"DEBUG: enviar_orden_dashboard llamado para {order.name}")
                return order.action_enviar_a_cocina()
            return True
        except Exception as e:
            print(f"DEBUG: Error en enviar_orden_dashboard: {e}")
            return False

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    
    def write(self, vals):
        result = super().write(vals)
        
        # Detectar cambios en pedidos enviados a cocina
        for record in self:
            if (record.order_id.enviado_a_cocina and 
                record.order_id.estado_rapido not in ['nuevo', 'entregado', 'rechazado']):
                # Marcar como modificado (implementar lógica similar a sale.order)
                pass
        
        return result