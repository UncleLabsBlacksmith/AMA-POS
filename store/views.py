import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Category, CreditPayment, Customer, Product, Sale, SaleItem


def _d(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _shop_context():
    return {
        'shop_name': getattr(settings, 'SHOP_NAME', 'ร้านชำ'),
        'shop_phone': getattr(settings, 'SHOP_PHONE', ''),
    }


# ---------------------------------------------------------------- หน้าขาย
@ensure_csrf_cookie
def pos(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.annotate(
        n=Count('products', filter=Q(products__is_active=True))
    ).filter(n__gt=0)

    product_data = [
        {
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'emoji': p.emoji,
            'image': p.image.url if p.image else '',
            'barcode': p.barcode,
            'unit': p.unit,
            'stock': p.stock,
            'track_stock': p.track_stock,
            'category': p.category_id or 0,
            'favorite': p.is_favorite,
        }
        for p in products
    ]

    ctx = _shop_context()
    ctx.update({
        'products': products,
        'categories': categories,
        'products_json': product_data,
        'customers': Customer.objects.filter(is_active=True),
        'today_total': _today_sales().aggregate(s=Sum('total'))['s'] or Decimal('0'),
    })
    return render(request, 'store/pos.html', ctx)


@require_POST
def api_checkout(request):
    """รับตะกร้าจากหน้าขาย แล้วบันทึกเป็นบิล"""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'ข้อมูลไม่ถูกต้อง'}, status=400)

    raw_items = payload.get('items') or []
    if not raw_items:
        return JsonResponse({'ok': False, 'error': 'ยังไม่มีสินค้าในบิล'}, status=400)

    method = payload.get('payment_method') or Sale.PAYMENT_CASH
    if method not in dict(Sale.PAYMENT_CHOICES):
        method = Sale.PAYMENT_CASH

    customer = None
    if method == Sale.PAYMENT_CREDIT:
        customer_id = payload.get('customer_id')
        if not customer_id:
            return JsonResponse(
                {'ok': False, 'error': 'ซื้อเชื่อต้องเลือกชื่อลูกค้าก่อน'}, status=400)
        customer = get_object_or_404(Customer, pk=customer_id)

    with transaction.atomic():
        sale = Sale(payment_method=method, customer=customer,
                    note=(payload.get('note') or '')[:200])
        sale.save()

        total = Decimal('0.00')
        for row in raw_items:
            qty = _d(row.get('qty'), '1')
            if qty <= 0:
                continue
            product = Product.objects.filter(pk=row.get('id'), is_active=True).first()
            if product is None:
                continue
            SaleItem.objects.create(
                sale=sale, product=product, name=product.name, emoji=product.emoji,
                price=product.price, qty=qty,
            )
            total += (product.price * qty)
            if product.track_stock:
                product.stock = product.stock - int(qty)
                product.save(update_fields=['stock'])

        if total <= 0:
            transaction.set_rollback(True)
            return JsonResponse({'ok': False, 'error': 'ยอดเงินเป็นศูนย์'}, status=400)

        total = total.quantize(Decimal('0.01'))
        paid = _d(payload.get('paid'), '0')
        if method == Sale.PAYMENT_CREDIT:
            paid = Decimal('0.00')
        elif method == Sale.PAYMENT_TRANSFER or paid < total:
            paid = total

        sale.total = total
        sale.paid = paid
        sale.change = (paid - total).quantize(Decimal('0.01'))
        sale.save(update_fields=['total', 'paid', 'change'])

    return JsonResponse({
        'ok': True,
        'sale_id': sale.id,
        'bill_no': sale.bill_no,
        'total': float(sale.total),
        'paid': float(sale.paid),
        'change': float(sale.change),
        'bill_url': f'/bill/{sale.id}/',
    })


def bill(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=pk)
    ctx = _shop_context()
    ctx['sale'] = sale
    return render(request, 'store/bill.html', ctx)


# ---------------------------------------------------------------- สรุปยอด
def _today_sales():
    today = timezone.localdate()
    return Sale.objects.filter(created_at__date=today, is_void=False)


def today(request):
    sales = _today_sales().prefetch_related('items')
    agg = sales.aggregate(total=Sum('total'), n=Count('id'))
    by_method = {
        key: sales.filter(payment_method=key).aggregate(s=Sum('total'))['s'] or Decimal('0')
        for key, _label in Sale.PAYMENT_CHOICES
    }
    top = (SaleItem.objects.filter(sale__in=sales)
           .values('name', 'emoji')
           .annotate(qty=Sum('qty'))
           .order_by('-qty')[:10])

    ctx = _shop_context()
    ctx.update({
        'sales': sales[:50],
        'total': agg['total'] or Decimal('0'),
        'count': agg['n'] or 0,
        'by_method': by_method,
        'top_items': top,
        'date': timezone.localdate(),
        'low_stock': Product.objects.filter(is_active=True, track_stock=True)
                     .filter(stock__lte=F('low_stock_alert')).order_by('stock')[:20],
    })
    return render(request, 'store/today.html', ctx)


def history(request):
    sales = Sale.objects.prefetch_related('items').select_related('customer')[:200]
    ctx = _shop_context()
    ctx['sales'] = sales
    return render(request, 'store/history.html', ctx)


@require_POST
def void_sale(request, pk):
    """ยกเลิกบิล แล้วคืนของเข้าสต๊อก"""
    sale = get_object_or_404(Sale, pk=pk)
    if not sale.is_void:
        with transaction.atomic():
            for item in sale.items.select_related('product'):
                if item.product and item.product.track_stock:
                    item.product.stock += int(item.qty)
                    item.product.save(update_fields=['stock'])
            sale.is_void = True
            sale.save(update_fields=['is_void'])
    return redirect('store:history')


# ---------------------------------------------------------------- ลูกหนี้
def credit_list(request):
    customers = Customer.objects.filter(is_active=True)
    rows = [{'c': c, 'balance': c.balance} for c in customers]
    rows.sort(key=lambda r: r['balance'], reverse=True)
    ctx = _shop_context()
    ctx.update({
        'rows': rows,
        'grand_total': sum((r['balance'] for r in rows), Decimal('0')),
    })
    return render(request, 'store/credit_list.html', ctx)


def credit_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    ctx = _shop_context()
    ctx.update({
        'customer': customer,
        'sales': customer.sales.filter(
            is_void=False, payment_method=Sale.PAYMENT_CREDIT).prefetch_related('items')[:100],
        'payments': customer.payments.all()[:100],
        'balance': customer.balance,
    })
    return render(request, 'store/credit_detail.html', ctx)


@require_POST
def credit_pay(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    amount = _d(request.POST.get('amount'), '0')
    if amount > 0:
        CreditPayment.objects.create(customer=customer, amount=amount,
                                     note=request.POST.get('note', '')[:200])
    return redirect('store:credit_detail', pk=customer.pk)


@require_POST
def customer_add(request):
    name = (request.POST.get('name') or '').strip()
    if name:
        Customer.objects.create(name=name, phone=(request.POST.get('phone') or '').strip())
    return redirect('store:credit_list')


# ---------------------------------------------------------------- จัดการสินค้า
def product_list(request):
    ctx = _shop_context()
    ctx.update({
        'products': Product.objects.filter(is_active=True).select_related('category'),
        'categories': Category.objects.all(),
    })
    return render(request, 'store/products.html', ctx)


@require_POST
def product_save(request):
    """เพิ่มสินค้าใหม่ หรือแก้ราคา/สต๊อกสินค้าเดิม"""
    pk = request.POST.get('id')
    product = Product.objects.filter(pk=pk).first() if pk else Product()
    if product is None:
        product = Product()

    name = (request.POST.get('name') or '').strip()
    if not name:
        return redirect('store:product_list')

    product.name = name
    product.price = _d(request.POST.get('price'), '0')
    product.emoji = (request.POST.get('emoji') or '🛒').strip()[:8]
    product.barcode = (request.POST.get('barcode') or '').strip()
    product.unit = (request.POST.get('unit') or 'ชิ้น').strip()
    product.stock = int(_d(request.POST.get('stock'), '0'))
    product.is_favorite = bool(request.POST.get('is_favorite'))
    cat_id = request.POST.get('category')
    product.category = Category.objects.filter(pk=cat_id).first() if cat_id else None
    if request.FILES.get('image'):
        product.image = request.FILES['image']
    product.is_active = True
    product.save()
    return redirect('store:product_list')


@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save(update_fields=['is_active'])
    return redirect('store:product_list')


@require_POST
def product_restock(request, pk):
    """เติมของเข้าสต๊อกเร็วๆ"""
    product = get_object_or_404(Product, pk=pk)
    product.stock += int(_d(request.POST.get('amount'), '0'))
    product.save(update_fields=['stock'])
    return redirect('store:product_list')


def help_page(request):
    return render(request, 'store/help.html', _shop_context())
