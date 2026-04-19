from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('add/', views.create_transaction, name='add_transaction'),
    path('list/', views.transaction_list, name='transaction_list'),
    path('detail/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('ajax/load-models/', views.load_models, name='ajax_load_models'),
]