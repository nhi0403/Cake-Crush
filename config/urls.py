from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Cấu hình tiêu đề thương hiệu Cake Crush cho Django Admin
admin.site.site_header = "Cake Crush HR — Quản trị hệ thống"
admin.site.site_title = "Cake Crush Admin"
admin.site.index_title = "Trung tâm Quản trị Dữ liệu Cake Crush"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("nhan_su.urls")),  # Bổ sung URL phân hệ nhân sự (Vân)
    path("", include("cham_cong.urls")),
    path("", include("dao_tao.urls")),  # Phân hệ Đào tạo
    path("danh-gia/", include("danh_gia.urls")),  # Phân hệ Đánh giá
    path('', include('tai_khoan.urls')),
]

urlpatterns += staticfiles_urlpatterns()
