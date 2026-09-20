"""เทสต์โฟลว์สำคัญของระบบขายหน้าร้าน"""
import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, CreditPayment, Customer, Product, Sale


class PosFlowTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='เครื่องดื่ม', emoji='🥤')
        self.water = Product.objects.create(name='น้ำเปล่า', price=Decimal('7'),
                                            category=cat, stock=10, is_favorite=True)
        self.coke = Product.objects.create(name='โค้ก', price=Decimal('15'),
                                           category=cat, stock=5)
        self.customer = Customer.objects.create(name='ป้าสมศรี')

    def _checkout(self, payload):
        return self.client.post(reverse('store:api_checkout'),
                                data=json.dumps(payload),
                                content_type='application/json')

    def test_cash_sale_computes_total_change_and_stock(self):
        res = self._checkout({
            'items': [{'id': self.water.id, 'qty': 2}, {'id': self.coke.id, 'qty': 1}],
            'paid': 100, 'payment_method': 'cash',
        })
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['total'], 29.0)       # 7*2 + 15
        self.assertEqual(data['change'], 71.0)      # 100 - 29

        self.water.refresh_from_db()
        self.coke.refresh_from_db()
        self.assertEqual(self.water.stock, 8)
        self.assertEqual(self.coke.stock, 4)

    def test_price_comes_from_database_not_from_browser(self):
        """กันกรณีข้อมูลจากหน้าเว็บถูกแก้ ราคาต้องยึดจากฐานข้อมูลเสมอ"""
        res = self._checkout({
            'items': [{'id': self.water.id, 'qty': 1, 'price': 1}],
            'paid': 7, 'payment_method': 'cash',
        })
        self.assertEqual(res.json()['total'], 7.0)

    def test_paid_less_than_total_is_clamped(self):
        res = self._checkout({
            'items': [{'id': self.water.id, 'qty': 1}],
            'paid': 3, 'payment_method': 'cash',
        })
        self.assertEqual(res.json()['change'], 0.0)

    def test_empty_cart_is_rejected(self):
        self.assertEqual(self._checkout({'items': []}).status_code, 400)

    def test_credit_sale_requires_customer(self):
        res = self._checkout({
            'items': [{'id': self.water.id, 'qty': 1}], 'payment_method': 'credit',
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Sale.objects.exists())

    def test_credit_sale_builds_customer_balance(self):
        self._checkout({
            'items': [{'id': self.coke.id, 'qty': 2}],
            'payment_method': 'credit', 'customer_id': self.customer.id,
        })
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('30'))

        self.client.post(reverse('store:credit_pay', args=[self.customer.id]),
                         {'amount': '20'})
        self.assertEqual(self.customer.balance, Decimal('10'))
        self.assertEqual(CreditPayment.objects.count(), 1)

    def test_void_returns_items_to_stock(self):
        self._checkout({
            'items': [{'id': self.water.id, 'qty': 3}], 'paid': 50,
        })
        sale = Sale.objects.get()
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 7)

        self.client.post(reverse('store:void_sale', args=[sale.id]))
        sale.refresh_from_db()
        self.water.refresh_from_db()
        self.assertTrue(sale.is_void)
        self.assertEqual(self.water.stock, 10)

    def test_voided_sale_drops_out_of_today_total(self):
        self._checkout({'items': [{'id': self.water.id, 'qty': 1}], 'paid': 10})
        sale = Sale.objects.get()
        self.client.post(reverse('store:void_sale', args=[sale.id]))
        res = self.client.get(reverse('store:today'))
        self.assertEqual(res.context['total'], Decimal('0'))

    def test_void_twice_does_not_double_restock(self):
        self._checkout({'items': [{'id': self.water.id, 'qty': 2}], 'paid': 20})
        sale = Sale.objects.get()
        self.client.post(reverse('store:void_sale', args=[sale.id]))
        self.client.post(reverse('store:void_sale', args=[sale.id]))
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 10)


class ProductAdminPageTests(TestCase):
    def test_add_and_edit_product(self):
        self.client.post(reverse('store:product_save'), {
            'name': 'ไข่ไก่', 'price': '5', 'emoji': '🥚', 'stock': '30',
            'unit': 'ฟอง', 'is_favorite': 'on',
        })
        p = Product.objects.get(name='ไข่ไก่')
        self.assertEqual(p.price, Decimal('5'))
        self.assertTrue(p.is_favorite)

        self.client.post(reverse('store:product_save'), {
            'id': p.id, 'name': 'ไข่ไก่', 'price': '6', 'emoji': '🥚',
            'stock': '30', 'unit': 'ฟอง',
        })
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal('6'))
        self.assertEqual(Product.objects.count(), 1)

    def test_restock_adds_to_stock(self):
        p = Product.objects.create(name='มาม่า', price=Decimal('7'), stock=2)
        self.client.post(reverse('store:product_restock', args=[p.id]), {'amount': '12'})
        p.refresh_from_db()
        self.assertEqual(p.stock, 14)

    def test_delete_hides_product_but_keeps_history(self):
        p = Product.objects.create(name='ขนม', price=Decimal('20'), stock=5)
        self.client.post(reverse('store:product_delete', args=[p.id]))
        p.refresh_from_db()
        self.assertFalse(p.is_active)
        self.assertTrue(Product.objects.filter(pk=p.pk).exists())
