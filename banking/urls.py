from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<str:account_number>/', views.account_detail, name='account_detail'),
    path('accounts/<str:account_number>/deposit/', views.account_deposit, name='account_deposit'),
    path('accounts/<str:account_number>/withdraw/', views.account_withdraw, name='account_withdraw'),
    path('accounts/<str:account_number>/transfer/', views.account_transfer, name='account_transfer'),
    path('accounts/<str:account_number>/statement/', views.account_statement, name='account_statement'),
    path('transactions/', views.transaction_list, name='transaction_list'),
]
