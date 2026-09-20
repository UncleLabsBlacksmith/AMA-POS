from decimal import Decimal

from django.db import models
from django.utils import timezone


class Category(models.Model):
    """หมวดสินค้า เช่น เครื่องดื่ม ขนม ของใช้"""

    name = models.CharField('ชื่อหมวด', max_length=60)
    emoji = models.CharField('รูปสัญลักษณ์', max_length=8, default='📦')
    color = models.CharField('สีพื้น', max_length=20, default='#2563eb')
    sort_order = models.IntegerField('ลำดับ', default=0)

    class Meta:
        verbose_name = 'หมวดสินค้า'
        verbose_name_plural = 'หมวดสินค้า'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f'{self.emoji} {self.name}'


class Product(models.Model):
    """สินค้าในร้าน"""

    name = models.CharField('ชื่อสินค้า', max_length=120)
    price = models.DecimalField('ราคาขาย (บาท)', max_digits=10, decimal_places=2)
    cost = models.DecimalField('ราคาทุน (บาท)', max_digits=10, decimal_places=2,
                               default=Decimal('0.00'))
    category = models.ForeignKey(Category, verbose_name='หมวด', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='products')
    emoji = models.CharField('รูปสัญลักษณ์', max_length=8, default='🛒',
                             help_text='ใส่อิโมจิให้อาม่าจำง่าย เช่น 🥤 🍜 🍫')
    image = models.ImageField('รูปสินค้า', upload_to='products/', null=True, blank=True)
    barcode = models.CharField('บาร์โค้ด', max_length=60, blank=True, db_index=True)
    unit = models.CharField('หน่วย', max_length=20, default='ชิ้น')

    stock = models.IntegerField('จำนวนคงเหลือ', default=0)
    track_stock = models.BooleanField('นับสต๊อก', default=True)
    low_stock_alert = models.IntegerField('เตือนเมื่อเหลือน้อยกว่า', default=3)

    is_favorite = models.BooleanField('ปักหมุดหน้าแรก', default=False,
                                      help_text='สินค้าขายบ่อย ให้ขึ้นหน้าแรกตัวใหญ่ๆ')
    sort_order = models.IntegerField('ลำดับ', default=0)
    is_active = models.BooleanField('ยังขายอยู่', default=True)

    class Meta:
        verbose_name = 'สินค้า'
        verbose_name_plural = 'สินค้า'
        ordering = ['-is_favorite', 'sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.track_stock and self.stock <= self.low_stock_alert


class Customer(models.Model):
    """ลูกค้าที่ซื้อเชื่อ (ลงบัญชีไว้ก่อน)"""

    name = models.CharField('ชื่อลูกค้า', max_length=120)
    phone = models.CharField('เบอร์โทร', max_length=30, blank=True)
    note = models.CharField('หมายเหตุ', max_length=200, blank=True)
    is_active = models.BooleanField('ยังใช้งาน', default=True)
    created_at = models.DateTimeField('สร้างเมื่อ', default=timezone.now)

    class Meta:
        verbose_name = 'ลูกหนี้ (ซื้อเชื่อ)'
        verbose_name_plural = 'ลูกหนี้ (ซื้อเชื่อ)'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_charged(self):
        agg = self.sales.filter(is_void=False, payment_method='credit').aggregate(
            s=models.Sum('total'))
        return agg['s'] or Decimal('0.00')

    @property
    def total_paid(self):
        agg = self.payments.aggregate(s=models.Sum('amount'))
        return agg['s'] or Decimal('0.00')

    @property
    def balance(self):
        """ยอดค้างชำระ"""
        return self.total_charged - self.total_paid


class Sale(models.Model):
    """บิลขาย 1 ใบ"""

    PAYMENT_CASH = 'cash'
    PAYMENT_TRANSFER = 'transfer'
    PAYMENT_CREDIT = 'credit'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'เงินสด'),
        (PAYMENT_TRANSFER, 'โอน / สแกนจ่าย'),
        (PAYMENT_CREDIT, 'ลงบัญชี (ซื้อเชื่อ)'),
    ]

    created_at = models.DateTimeField('เวลาขาย', default=timezone.now, db_index=True)
    total = models.DecimalField('ยอดรวม', max_digits=12, decimal_places=2,
                                default=Decimal('0.00'))
    paid = models.DecimalField('รับเงินมา', max_digits=12, decimal_places=2,
                               default=Decimal('0.00'))
    change = models.DecimalField('เงินทอน', max_digits=12, decimal_places=2,
                                 default=Decimal('0.00'))
    payment_method = models.CharField('วิธีจ่าย', max_length=20,
                                      choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    customer = models.ForeignKey(Customer, verbose_name='ลูกค้า', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='sales')
    note = models.CharField('หมายเหตุ', max_length=200, blank=True)
    is_void = models.BooleanField('ยกเลิกบิล', default=False)

    class Meta:
        verbose_name = 'บิลขาย'
        verbose_name_plural = 'บิลขาย'
        ordering = ['-created_at']

    def __str__(self):
        return f'บิล #{self.pk} · {self.total} บาท'

    @property
    def bill_no(self):
        return f'{self.created_at.strftime("%y%m%d")}-{self.pk:04d}'

    @property
    def item_count(self):
        agg = self.items.aggregate(s=models.Sum('qty'))
        return agg['s'] or 0


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField('ชื่อสินค้า', max_length=120)
    emoji = models.CharField(max_length=8, default='🛒')
    price = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2)
    qty = models.DecimalField('จำนวน', max_digits=10, decimal_places=2, default=Decimal('1'))

    class Meta:
        verbose_name = 'รายการในบิล'
        verbose_name_plural = 'รายการในบิล'

    def __str__(self):
        return f'{self.name} x {self.qty}'

    @property
    def subtotal(self):
        return (self.price * self.qty).quantize(Decimal('0.01'))


class CreditPayment(models.Model):
    """ลูกหนี้มาจ่ายเงินคืน"""

    customer = models.ForeignKey(Customer, verbose_name='ลูกค้า', on_delete=models.CASCADE,
                                 related_name='payments')
    amount = models.DecimalField('จำนวนเงินที่จ่าย', max_digits=12, decimal_places=2)
    created_at = models.DateTimeField('เวลา', default=timezone.now)
    note = models.CharField('หมายเหตุ', max_length=200, blank=True)

    class Meta:
        verbose_name = 'การชำระหนี้'
        verbose_name_plural = 'การชำระหนี้'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer.name} จ่าย {self.amount} บาท'
