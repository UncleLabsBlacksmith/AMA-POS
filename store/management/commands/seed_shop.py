"""ใส่ข้อมูลตัวอย่างสินค้าร้านชำ เพื่อให้เปิดใช้ได้ทันทีโดยไม่ต้องพิมพ์เอง

    python manage.py seed_shop
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Category, Customer, Product

CATEGORIES = [
    ('เครื่องดื่ม', '🥤', 1),
    ('ขนม', '🍬', 2),
    ('อาหารแห้ง', '🍜', 3),
    ('ของใช้ในบ้าน', '🧼', 4),
    ('บุหรี่ / เบ็ดเตล็ด', '🧺', 5),
]

# (ชื่อ, ราคา, อิโมจิ, หมวด, ปักหมุดหน้าแรก, สต๊อก)
PRODUCTS = [
    ('น้ำเปล่า 600 มล.', '7', '💧', 'เครื่องดื่ม', True, 48),
    ('โค้ก กระป๋อง', '15', '🥤', 'เครื่องดื่ม', True, 24),
    ('นมกล่อง', '13', '🥛', 'เครื่องดื่ม', True, 24),
    ('กาแฟกระป๋อง', '17', '☕', 'เครื่องดื่ม', False, 12),
    ('เบียร์ กระป๋อง', '55', '🍺', 'เครื่องดื่ม', False, 12),
    ('น้ำแข็ง ถุง', '10', '🧊', 'เครื่องดื่ม', True, 20),

    ('ขนมถุง', '20', '🍿', 'ขนม', True, 30),
    ('ช็อกโกแลต', '25', '🍫', 'ขนม', False, 20),
    ('ลูกอม', '5', '🍬', 'ขนม', True, 50),
    ('ไอศกรีม แท่ง', '15', '🍦', 'ขนม', False, 18),
    ('ขนมปัง', '22', '🍞', 'ขนม', False, 10),

    ('มาม่า ซอง', '7', '🍜', 'อาหารแห้ง', True, 60),
    ('ไข่ไก่ ฟอง', '5', '🥚', 'อาหารแห้ง', True, 90),
    ('ข้าวสาร 1 กก.', '45', '🍚', 'อาหารแห้ง', False, 15),
    ('น้ำมันพืช ขวด', '58', '🫗', 'อาหารแห้ง', False, 10),
    ('น้ำปลา ขวด', '30', '🐟', 'อาหารแห้ง', False, 8),
    ('น้ำตาล 1 กก.', '28', '🍯', 'อาหารแห้ง', False, 12),
    ('ปลากระป๋อง', '18', '🥫', 'อาหารแห้ง', True, 24),

    ('ผงซักฟอก ซอง', '12', '🧼', 'ของใช้ในบ้าน', True, 30),
    ('สบู่ก้อน', '15', '🧴', 'ของใช้ในบ้าน', False, 20),
    ('ยาสีฟัน หลอด', '35', '🪥', 'ของใช้ในบ้าน', False, 12),
    ('แชมพู ซอง', '8', '💆', 'ของใช้ในบ้าน', False, 40),
    ('กระดาษทิชชู่', '20', '🧻', 'ของใช้ในบ้าน', True, 18),
    ('ถ่านไฟฉาย แพ็ค', '30', '🔋', 'ของใช้ในบ้าน', False, 10),
    ('ไฟแช็ก', '10', '🔥', 'ของใช้ในบ้าน', True, 25),

    ('ถุงพลาสติก แพ็ค', '15', '🛍', 'บุหรี่ / เบ็ดเตล็ด', False, 20),
    ('ยาดม', '25', '💨', 'บุหรี่ / เบ็ดเตล็ด', False, 10),
    ('ยาแก้ปวด ซอง', '10', '💊', 'บุหรี่ / เบ็ดเตล็ด', False, 20),
]


class Command(BaseCommand):
    help = 'ใส่ข้อมูลตัวอย่างสินค้าร้านชำ'

    def handle(self, *args, **options):
        cats = {}
        for name, emoji, order in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={'emoji': emoji, 'sort_order': order})
            cats[name] = cat

        created = 0
        for name, price, emoji, cat_name, fav, stock in PRODUCTS:
            _, was_new = Product.objects.get_or_create(
                name=name,
                defaults={
                    'price': Decimal(price),
                    'emoji': emoji,
                    'category': cats.get(cat_name),
                    'is_favorite': fav,
                    'stock': stock,
                },
            )
            created += bool(was_new)

        for cust in ['ป้าสมศรี', 'ลุงแดง', 'น้องเอ๋ ร้านตัดผม']:
            Customer.objects.get_or_create(name=cust)

        self.stdout.write(self.style.SUCCESS(
            f'เรียบร้อย: สินค้าใหม่ {created} รายการ, หมวด {len(cats)} หมวด'))
