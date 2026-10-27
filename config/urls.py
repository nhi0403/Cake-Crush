from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tai_khoan.urls'),
    path('danh-gia/', include('danh_gia.urls')),)
]

urlpatterns += staticfiles_urlpatterns()
