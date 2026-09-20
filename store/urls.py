from django.urls import path

from . import views

app_name = 'store'

urlpatterns = [
    path('', views.pos, name='pos'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),
    path('bill/<int:pk>/', views.bill, name='bill'),

    path('today/', views.today, name='today'),
    path('history/', views.history, name='history'),
    path('history/<int:pk>/void/', views.void_sale, name='void_sale'),

    path('credit/', views.credit_list, name='credit_list'),
    path('credit/add/', views.customer_add, name='customer_add'),
    path('credit/<int:pk>/', views.credit_detail, name='credit_detail'),
    path('credit/<int:pk>/pay/', views.credit_pay, name='credit_pay'),

    path('products/', views.product_list, name='product_list'),
    path('products/save/', views.product_save, name='product_save'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/restock/', views.product_restock, name='product_restock'),

    path('help/', views.help_page, name='help'),
]
