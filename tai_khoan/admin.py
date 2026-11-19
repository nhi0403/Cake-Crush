from django.contrib import admin

from .models import ThongBao


@admin.register(ThongBao)
class ThongBaoAdmin(admin.ModelAdmin):
    """Cấu hình quản trị thông báo người dùng."""

    list_display = ("tieu_de", "nguoi_nhan", "loai", "da_doc", "ngay_tao")
    list_filter = ("loai", "da_doc", "ngay_tao")
    search_fields = ("tieu_de", "noi_dung", "nguoi_nhan__username", "nguoi_nhan__first_name", "nguoi_nhan__last_name")
    ordering = ("-ngay_tao",)
    readonly_fields = ("ngay_tao",)
