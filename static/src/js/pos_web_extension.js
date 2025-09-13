/** @odoo-module **/

import { Chrome } from "@point_of_sale/app/pos_app";
import { Component } from "@odoo/owl";
import { PosWebManager } from "./pos_web_notifications";

// Extender Chrome para incluir nuestro componente
export class ChromeWithWebNotifications extends Chrome {
    static components = {
        ...Chrome.components,
        PosWebManager,
    };
}

ChromeWithWebNotifications.template = "tu_pedido_v2.ChromeWithWebNotifications";