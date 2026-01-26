# Copyright (C) 2021 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        copy=False,
        readonly=True,
        tracking=True,
        domain=[("move_type", "=", "out_invoice")],
        compute="_compute_invoice_ids",
    )

    invoiced = fields.Boolean(compute="_compute_invoiced", store=False)

    invoice_count = fields.Integer(
        compute="_compute_invoice_count",
        string="Bill Count",
        copy=False,
        default=0,
        store=False,
    )

    def _compute_invoice_ids(self):
        Move = self.env["account.move"]
        has_repair_ids = "repair_ids" in Move._fields
        for repair in self:
            moves = Move.browse()
            if repair.id and has_repair_ids:
                moves = Move.search(
                    [
                        ("repair_ids", "in", repair.id),
                        ("move_type", "=", "out_invoice"),
                    ]
                )
            elif repair.sale_order_id:
                moves = repair.sale_order_id.invoice_ids.filtered(
                    lambda m: m.move_type == "out_invoice"
                )
            repair.invoice_ids = moves

    def _compute_invoiced(self):
        for repair in self:
            has_reversed = repair.invoice_ids.filtered(
                lambda move: getattr(move, "payment_state", None) == "reversed"
            )
            if has_reversed:
                repair.invoiced = False
            else:
                repair.invoiced = bool(
                    repair.invoice_ids.filtered(lambda move: move.state != "cancel")
                )

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for repair in self:
            repair.invoice_count = len(repair.invoice_ids)

    def action_created_invoices(self):
        self.ensure_one()
        action = {
            "name": self.env._("Invoices created"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
        }

        if len(self.invoice_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "view_id": self.env.ref("account.view_move_form").id,
                    "target": "current",
                    "res_id": self.invoice_ids.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "res_model": "account.move",
                    "domain": [("id", "in", self.invoice_ids.ids)],
                }
            )

        return action
