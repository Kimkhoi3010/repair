# Copyright (C) 2021 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    purchase_return_ids = fields.Many2many(
        comodel_name="purchase.return.order",
        compute="_compute_purchase_returns",
        copy=False,
        store=True,
    )
    purchase_return_count = fields.Integer(
        compute="_compute_purchase_returns",
        copy=False,
        default=0,
        store=True,
    )
    purchase_return_notes = fields.Text("Return Purchase Notes")

    @api.depends(
        "move_ids.purchase_return_line_ids",
        "move_ids.purchase_return_line_ids.order_id",
    )
    def _compute_purchase_returns(self):
        for order in self:
            pros = order.mapped("move_ids.purchase_return_line_ids.order_id")
            order.purchase_return_ids = pros
            order.purchase_return_count = len(pros)

    def _prepare_purchase_return_values(self, vendor):
        fp = vendor.with_company(self.company_id).property_account_position_id
        currency = vendor.with_company(self.company_id).property_purchase_currency_id
        vals = {
            "origin": self.name,
            "partner_id": vendor.id,
            "fiscal_position_id": fp and fp.id or False,
            "company_id": self.company_id.id,
            "notes": self.purchase_return_notes,
        }
        if currency:
            vals["currency_id"] = currency.id
        return vals

    @api.model
    def _select_operations_to_return(self, operations):
        return operations.filtered(lambda m: m.repair_line_type == "add")

    def _create_purchase_return(self, vendor):
        pro_line_obj = self.env["purchase.return.order.line"]
        pr_vals = self._prepare_purchase_return_values(vendor)
        pro = (
            self.env["purchase.return.order"]
            .sudo()
            .create(pr_vals)
            .with_user(self.env.uid)
        )
        for move in self._select_operations_to_return(self.move_ids):
            pr_line_vals = move._prepare_purchase_order_line_vals(pro)
            pro_line_obj.create(pr_line_vals)
        return pro

    def action_view_purchase_returns(self):
        purchase_returns = self.mapped("purchase_return_ids")
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_return.purchase_return_form_action"
        )
        if len(purchase_returns) > 1:
            action["domain"] = [("id", "in", purchase_returns.ids)]
        elif len(purchase_returns) == 1:
            form_view = [
                (self.env.ref("purchase_return.purchase_return_order_form").id, "form")
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = purchase_returns.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {
            "default_move_type": "out_invoice",
        }
        if len(self) == 1:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "default_user_id": self.user_id.id,
                }
            )
        action["context"] = context
        return action
