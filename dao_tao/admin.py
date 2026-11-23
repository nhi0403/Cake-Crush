from django.contrib import admin

from .models import KhoaDaoTao, PhanCongDaoTao


class PhanCongDaoTaoInline(admin.TabularInline):
    """Quản lý danh sách nhân viên tham gia ngay trên trang chi tiết khóa đào tạo."""

    model = PhanCongDaoTao
    extra = 0
    fields = ("nhanvien", "tiendo", "ketqua", "ngayhoanthanh", "ngaytao")
    readonly_fields = ("ngaytao",)


@admin.register(KhoaDaoTao)
class KhoaDaoTaoAdmin(admin.ModelAdmin):
    """Cấu hình trang quản trị khóa đào tạo."""

    list_display = ("makhoa", "tenkhoa", "ngaybatdau", "ngayketthuc", "trangthai", "ngaytao")
    list_filter = ("trangthai", "ngaybatdau", "ngayketthuc")
    search_fields = ("makhoa", "tenkhoa", "noidung")
    ordering = ("-ngaybatdau", "-ngaytao")
    inlines = [PhanCongDaoTaoInline]


@admin.register(PhanCongDaoTao)
class PhanCongDaoTaoAdmin(admin.ModelAdmin):
    """Cấu hình trang quản trị phân công đào tạo."""

    list_display = ("khoadaotao", "nhanvien", "tiendo", "ketqua", "ngayhoanthanh", "ngaytao")
    list_filter = ("tiendo", "ketqua", "khoadaotao")
    search_fields = ("nhanvien__manv", "nhanvien__tennv", "khoadaotao__makhoa", "khoadaotao__tenkhoa")
    ordering = ("-ngaytao",)
    readonly_fields = ("ngaytao", "ngaycapnhat")
