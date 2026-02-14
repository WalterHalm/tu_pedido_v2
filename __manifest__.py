{
    'name': 'Tu Pedido v2',
    'version': '2.3.0',
    'category': 'Sales',
    'summary': 'Sistema completo de gestión de pedidos para restaurantes',
    'description': """
        Sistema de gestión de pedidos con:
        - Dashboard interactivo con Kanban
        - Integración eCommerce y PoS
        - Sistema de notificaciones unificado
        - Seguimiento en tiempo real
        - Control por sesión PoS
    """,
    'author': 'Walter Halm',
    'website': 'https://github.com/WalterHalm/tu_pedido_v2',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'website_sale',
        'portal',
        'point_of_sale',
        'pos_restaurant',
        'pos_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/dashboard_action.xml',
        'views/sale_order_views.xml',
        'views/wizard_views.xml',
        'views/shop_confirmation.xml',
        'views/shop_cart_status.xml',
        'views/shop_closed.xml',
        'views/portal_integration.xml',
        'views/pos_notifications_views.xml',
        'wizards/__init__.py',
    ],
    'assets': {
        'web.assets_backend': [
            'tu_pedido_v2/static/src/css/dashboard.css',
            'tu_pedido_v2/static/src/js/dashboard.js',
        ],
        'point_of_sale._assets_pos': [
            'tu_pedido_v2/static/src/js/pos_kitchen_simple.js',
            'tu_pedido_v2/static/src/xml/pos_kitchen_simple.xml',
            'tu_pedido_v2/static/src/css/pos_kitchen_simple.css',
            'tu_pedido_v2/static/src/js/pos_delivery_notifications_pos.js',
            'tu_pedido_v2/static/src/xml/pos_delivery_notifications_pos.xml',
            'tu_pedido_v2/static/src/css/pos_delivery_notifications_pos.css',
        ],
        'web.assets_frontend': [
            'tu_pedido_v2/static/src/css/shop_confirmation.css',
            'tu_pedido_v2/static/src/js/shop_confirmation.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
