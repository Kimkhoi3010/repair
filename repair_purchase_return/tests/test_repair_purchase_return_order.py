from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestRepairPurchaseReturnOrder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "standard_price": 10,
                "list_price": 20,
            }
        )

        cls.service = cls.env["product.product"].create(
            {
                "name": "Test Fee",
                "standard_price": 30,
                "list_price": 50,
            }
        )

        cls.partner = cls.env.ref("base.res_partner_address_1")
        cls.location = cls.env["stock.location"].create(
            {
                "name": "Test location",
            }
        )
        cls.repair = cls.env["repair.order"].create(
            {
                "product_id": cls.product.id,
                "partner_id": cls.partner.id,
                "product_uom": cls.product.uom_id.id,
                "location_id": cls.location.id,
            }
        )

        cls.repair_move = cls.env["stock.move"].create(
            {
                "repair_id": cls.repair.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_uom_qty": 1.0,
                "company_id": cls.env.company.id,
                "repair_line_type": "add",
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

        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Vendor1",
            }
        )

    def test_repair_purchase_return(self):
        pro = self.repair._create_purchase_return(self.vendor)
        pro.action_view_repair_orders()

        # Check that purchase return order is caching the line
        # and using the product cost
        self.assertEqual(len(pro.order_line), 1)
        self.assertEqual(pro.order_line[0].price_unit, 10)
