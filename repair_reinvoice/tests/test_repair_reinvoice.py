from odoo.fields import Date
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestMrpRepairReinvoice(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "standard_price": 10,
                "list_price": 20,
                "type": "service",
            }
        )
        cls.product.product_tmpl_id.create_repair = True
        cls.partner = cls.env.ref("base.res_partner_address_1")
        cls.location = cls.env["stock.location"].create(
            {
                "name": "Test location",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "test",
                "type": "sale",
                "invoice_reference_type": "invoice",
                "invoice_reference_model": "odoo",
            }
        )

    def test_reinvoice(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": self.product.list_price,
                        },
                    )
                ],
            }
        )

        so.action_confirm()
        self.assertTrue(so.repair_order_ids, "Repair order should be created from SO")

        repair = so.repair_order_ids[0]

        # Initially, no invoices are linked
        self.assertEqual(repair.invoice_count, 0)
        self.assertFalse(repair.invoiced)

        # 2) Create and post an invoice for the SO
        invoice = so._create_invoices()
        invoice.action_post()

        repair._invalidate_cache()

        self.assertEqual(repair.invoice_count, 1)
        self.assertTrue(repair.invoiced)

        # 3) Create a credit note (reversal) for the invoice
        today = Date.context_today(self.env.user)
        refund_invoice_wiz = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "reason": "Please reverse",
                    "journal_id": self.journal.id,
                    "date": today,
                }
            )
        )
        refund_invoice_wiz.reverse_moves(is_modify=True)

        repair._invalidate_cache()

        self.assertEqual(repair.invoice_count, 2)
        self.assertFalse(repair.invoiced)
