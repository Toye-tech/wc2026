from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.home,            name='home'),
    path('matches/',                            views.matches,         name='matches'),
    path('matches/<int:match_id>/',             views.match_detail,    name='match_detail'),
    path('book/<int:match_id>/<int:category_id>/', views.booking,      name='booking'),
    path('booking/create/',                     views.create_booking,  name='create_booking'),
    path('booking/lookup/',                     views.lookup,          name='lookup'),
    path('booking/confirmation/<str:reference>/', views.confirmation,  name='confirmation'),
    path('payment/verify/',                     views.payment_verify,  name='payment_verify'),
    path('payment/success/',                    views.payment_success, name='payment_success'),
    path('updates/', views.updates, name='updates'),
]
