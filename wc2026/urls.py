from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config

ADMIN_URL = config('ADMIN_URL', default='wc2026-admin/')

admin.site.site_header = 'WC2026 Ticketing Admin'
admin.site.site_title = 'WC2026 Admin'
admin.site.index_title = 'Ticketing Management'

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('', include('tickets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
