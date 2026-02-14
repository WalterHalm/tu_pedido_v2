from odoo import http
from odoo.http import request
import json
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class PosSimpleController(http.Controller):

    @http.route('/tu_pedido_v2/crear_pedido_simple', type='json', auth='user', csrf=False)
    def crear_pedido_simple(self, **kwargs):
        """Crear pedido simple en el dashboard desde datos del carrito PoS"""
        try:
            tracking_number = kwargs.get('tracking_number')
            table_name = kwargs.get('table_name', 'Mostrador')
            customer_name = kwargs.get('customer_name', 'Cliente PoS')
            products = kwargs.get('products', [])
            general_note = kwargs.get('general_note', '')

            if not tracking_number or not products:
                return {'success': False, 'message': 'Datos incompletos'}
            
            # Verificar si ya fue enviado y manejar modificaciones
            existing_order = self._buscar_orden_existente_simple(tracking_number)
            if existing_order:
                print(f"DEBUG: Pedido {tracking_number} ya existe, verificando cambios")
                actualizado = self._actualizar_orden_desde_boton(existing_order, products, general_note, table_name, tracking_number)
                if actualizado:
                    return {
                        'success': True,
                        'message': f'Pedido {tracking_number} actualizado',
                        'order_id': existing_order.id
                    }
                else:
                    return {
                        'success': True,
                        'message': f'Pedido {tracking_number} sin cambios',
                        'order_id': existing_order.id
                    }

            # Ya no necesitamos sesiones

            # Buscar o crear el partner
            partner = request.env['res.partner'].sudo().search([
                ('name', '=', customer_name)
            ], limit=1)
            
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': customer_name,
                    'is_company': False,
                })

            # Crear nombre correcto con mesa y número
            if table_name and table_name != 'Mostrador' and table_name != 'null' and table_name != 'None':
                order_name = f'{table_name}'
            else:
                order_name = f'Pedido-{tracking_number}'
            
            print(f"DEBUG: Creando pedido - table_name: '{table_name}', order_name: '{order_name}', tracking: {tracking_number}")
            
            # Detectar si es delivery por productos
            is_delivery = any(
                'envio' in product_data.get('name', '').lower() or 
                'envío' in product_data.get('name', '').lower() or
                'delivery' in product_data.get('name', '').lower() or
                'entrega' in product_data.get('name', '').lower() or
                'estandar' in product_data.get('name', '').lower()
                for product_data in products
            )
            
            print(f"DEBUG: Es delivery: {is_delivery}")
            if is_delivery:
                print(f"DEBUG: Productos con delivery: {[p.get('name') for p in products if any(word in p.get('name', '').lower() for word in ['envio', 'envío', 'delivery', 'entrega', 'estandar'])]}")
            
            # Crear registro simple en sale.order para el dashboard
            order_vals = {
                'name': order_name,
                'partner_id': partner.id,
                'state': 'draft',
                'es_para_envio': is_delivery,
                'estado_rapido': 'nuevo',  # IMPORTANTE: Establecer estado inicial
                'tiempo_inicio_estado': datetime.now(),
                'tiempo_inicio_total': datetime.now(),
                'sonido_activo': True,
            }

            # Crear la orden
            order = request.env['sale.order'].sudo().create(order_vals)
            
            # Actualizar con campos personalizados que existen
            try:
                order.write({
                    'nota_cocina': self._build_kitchen_notes(general_note, products, table_name, tracking_number),  # Incluir tracking para identificación
                })
                print(f"DEBUG: Pedido creado con estado_rapido: {order.estado_rapido}")
            except Exception as e:
                print(f"DEBUG: Error actualizando campos: {e}")

            # Crear líneas de productos simples
            for product_data in products:
                # Buscar producto por nombre exacto
                product = request.env['product.product'].sudo().search([
                    ('name', '=', product_data.get('name', ''))
                ], limit=1)
                
                if not product:
                    # Crear producto con nombre exacto (Problema 2)
                    product = request.env['product.product'].sudo().create({
                        'name': product_data.get('name', 'Producto PoS'),
                        'type': 'consu',
                        'list_price': 0.0,
                    })

                # Problema 2: usar el nombre exacto del producto
                product_name = product_data.get('name', '')
                product_note = product_data.get('note', '')
                
                # Construir nombre con combo items si existen
                combo_items = product_data.get('combo_items', [])
                if combo_items:
                    combo_names = [item.get('name', '') for item in combo_items]
                    combo_text = f" ({', '.join(combo_names)})"
                    final_product_name = f"{product_name}{combo_text}"
                else:
                    final_product_name = product_name
                
                # Agregar nota si existe
                if product_note:
                    final_product_name = f"{final_product_name} - {product_note}"
                
                line_vals = {
                    'order_id': order.id,
                    'product_id': product.id,
                    'product_uom_qty': product_data.get('qty', 1),
                    'price_unit': 0.0,
                    'name': final_product_name,
                }
                main_line = request.env['sale.order.line'].sudo().create(line_vals)

            # Commit para que aparezca inmediatamente
            request.env.cr.commit()

            print(f"DEBUG: Pedido final creado - ID: {order.id}, Estado: {order.estado_rapido}, es_para_envio: {order.es_para_envio}")
            
            return {
                'success': True,
                'message': f'Pedido {tracking_number} creado y enviado a cocina',
                'order_id': order.id
            }

        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _pedido_ya_enviado_a_cocina(self, tracking_number, table_name):
        """Verificar si el pedido ya fue enviado a cocina usando pos_reference"""
        try:
            # Buscar pos.order por tracking_number para obtener pos_reference
            pos_order = request.env['pos.order'].sudo().search([
                ('tracking_number', '=', tracking_number)
            ], limit=1)
            
            if not pos_order:
                return False  # No existe pos.order, puede crear
            
            pos_reference = pos_order.pos_reference
            if not pos_reference:
                return False
            
            # Buscar en sale.order si ya existe con este tracking_number
            existing_sale_orders = request.env['sale.order'].sudo().search([
                ('nota_cocina', 'ilike', f'[REF:{tracking_number}]'),  # Buscar identificador único
                ('estado_rapido', '!=', False)
            ])
            
            if existing_sale_orders:
                print(f"DEBUG: Pedido con tracking {tracking_number} ya existe en dashboard")
                return True
            
            return False
            
        except Exception as e:
            print(f"DEBUG: Error verificando duplicados: {e}")
            return False
    
    def _buscar_orden_existente_simple(self, tracking_number):
        """Buscar orden existente por tracking number que permita modificaciones"""
        return request.env['sale.order'].sudo().search([
            ('nota_cocina', 'ilike', f'[REF:{tracking_number}]'),
            ('estado_rapido', 'not in', [False, 'entregado', 'rechazado'])
        ], limit=1)
    
    def _actualizar_orden_desde_boton(self, sale_order, products, general_note, table_name, tracking_number):
        """Actualizar orden existente desde el botón"""
        try:
            # Verificar si hay cambios ANTES de actualizar
            hay_cambios = self._hay_cambios_productos_boton(sale_order, products)
            
            if not hay_cambios:
                return False  # No hay cambios
            
            print(f"DEBUG: Actualizando pedido {tracking_number} con cambios")
            
            # Si el pedido ya fue aceptado o terminado, marcar como modificado
            if sale_order.estado_rapido not in ['nuevo']:
                sale_order.write({'productos_modificados': True})
                request.env.cr.commit()
            
            # Eliminar líneas existentes
            sale_order.order_line.unlink()
            
            # Crear nuevas líneas
            for product_data in products:
                product = request.env['product.product'].sudo().search([
                    ('name', '=', product_data.get('name', ''))
                ], limit=1)
                
                if not product:
                    product = request.env['product.product'].sudo().create({
                        'name': product_data.get('name', 'Producto PoS'),
                        'type': 'consu',
                        'list_price': 0.0,
                    })

                product_name = product_data.get('name', '')
                product_note = product_data.get('note', '')
                
                # Construir nombre con combo items si existen
                combo_items = product_data.get('combo_items', [])
                if combo_items:
                    combo_names = [item.get('name', '') for item in combo_items]
                    combo_text = f" ({', '.join(combo_names)})"
                    final_product_name = f"{product_name}{combo_text}"
                else:
                    final_product_name = product_name
                
                # Agregar nota si existe
                if product_note:
                    final_product_name = f"{final_product_name} - {product_note}"
                
                line_vals = {
                    'order_id': sale_order.id,
                    'product_id': product.id,
                    'product_uom_qty': product_data.get('qty', 1),
                    'price_unit': 0.0,
                    'name': final_product_name,
                }
                main_line = request.env['sale.order.line'].sudo().create(line_vals)
            
            # Actualizar notas
            sale_order.write({
                'nota_cocina': self._build_kitchen_notes(general_note, products, table_name, tracking_number),
                'tiempo_inicio_estado': request.env.cr.now(),
            })
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Error actualizando desde botón: {e}")
            return False
    
    def _hay_cambios_productos_boton(self, sale_order, products):
        """Verificar cambios desde el botón"""
        try:
            # Hash de productos del botón
            button_hash = []
            for product in products:
                name = product.get('name', '')
                note = product.get('note', '')
                full_name = f"{name} - {note}" if note else name
                item = f"{name}|{product.get('qty', 1)}|{full_name}"
                button_hash.append(item)
            button_hash.sort()
            
            # Hash de productos existentes
            sale_hash = []
            for line in sale_order.order_line:
                if not line.name.startswith('  →'):
                    item = f"{line.product_id.name}|{int(line.product_uom_qty)}|{line.name}"
                    sale_hash.append(item)
            sale_hash.sort()
            
            return button_hash != sale_hash
            
        except Exception as e:
            return True
    
    def _build_kitchen_notes(self, general_note, products, table_name, tracking_number):
        """Construir notas de cocina completas con identificador único"""
        notes = []
        
        # Agregar nota general si existe
        if general_note:
            notes.append(general_note)
        
        # Agregar notas de productos sin prefijo
        product_notes = []
        for product in products:
            if product.get('note'):
                product_notes.append(f"{product.get('name')}: {product.get('note')}")
        
        if product_notes:
            notes.extend(product_notes)
        
        # Agregar información de mesa si no hay otras notas
        if not notes:
            notes.append(f"Mesa: {table_name or 'Mostrador'}")
        
        # Agregar identificador único al final (oculto para el usuario)
        notes.append(f"[REF:{tracking_number}]")
        
        return " | ".join(notes)