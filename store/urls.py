from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('store/', views.home, name='home'),
    path('checkout/<slug:slug>/', views.checkout, name='checkout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('download/<uuid:token>/', views.download_ebook, name='download_ebook'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('refund/', views.refund_policy, name='refund'),
    path('notes/', views.free_notes, name='free_notes'),
    path('notes/download/<int:note_id>/', views.download_note, name='download_note'),
    path('checkout/pack/<int:pack_id>/', views.pack_checkout, name='pack_checkout'),
]