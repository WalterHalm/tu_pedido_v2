{  
    "name": "Tu Pedido v2 - Sistema Comidas Rápidas",  
    "version": "2.1.0",
    "summary": "Sistema completo de gestión de pedidos con notificaciones en tiempo real",
    "description": """
    Sistema completo de gestión de pedidos para restaurantes de comida rápida.
    
    Características principales:
    - Dashboard interactivo con drag & drop
    - Sistema unificado de notificaciones PoS (web/delivery/pickup)
    - Notificaciones sonoras y visuales automáticas
    - Seguimiento de tiempos de preparación
    - Integración completa eCommerce y PoS
    - Confirmación de entrega por cliente
    - APIs completas para eCommerce
    """,
    "author": "Walter",
    "website": "https://github.com/walter/tu_pedido_v2",
    "maintainer": "Walter",
    "category": "Sales",
    "depends": ["sale", "website_sale", "portal", "point_of_sale", "pos_restaurant"],
    "data": [  
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/dashboard_action.xml",
        "views/pos_notifications_views.xml",
        "views/portal_integration.xml",
        "views/wizard_views.xml",
        "views/analytics_views.xml",
        "views/analytics_menu.xml",
        "views/estado_analytics_views.xml",
        "views/tiempo_diario_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tu_pedido_v2/static/src/js/dashboard.js",
            "tu_pedido_v2/static/src/xml/dashboard_template.xml",
            "tu_pedido_v2/static/src/css/dashboard.css",
        ],
        "point_of_sale._assets_pos": [
            "tu_pedido_v2/static/src/js/pos_delivery_notifications_pos.js",
            "tu_pedido_v2/static/src/css/pos_delivery_notifications_pos.css",
            "tu_pedido_v2/static/src/js/pos_kitchen_simple.js",
            "tu_pedido_v2/static/src/xml/pos_kitchen_simple.xml",
            "tu_pedido_v2/static/src/css/pos_kitchen_simple.css",
            "tu_pedido_v2/static/src/js/pos_web_notifications.js",
            "tu_pedido_v2/static/src/xml/pos_web_templates.xml",
        ],
    },
    "images": ["static/description/icon2.png"],
    "installable": True,  
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
    "price": 0.00,
    "currency": "USD",
}