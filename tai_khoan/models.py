from django.db import models
from django.contrib.auth.models import User


class ThongBao(models.Model):
    """Lưu trữ thông báo gửi đến người dùng trong hệ thống Cake Crush HR."""

    class LoaiThongBao(models.TextChoices):
        CHAM_CONG = "CHAM_CONG", "Chấm công"
        NGHI_PHEP = "NGHI_PHEP", "Nghỉ phép"
        HOP_DONG = "HOP_DONG", "Hợp đồng"
        DAO_TAO = "DAO_TAO", "Đào tạo"
        DANH_GIA = "DANH_GIA", "Đánh giá"
        NHAN_SU = "NHAN_SU", "Nhân sự"
        HE_THONG = "HE_THONG", "Hệ thống"

    nguoi_nhan = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="thong_bao", verbose_name="Người nhận"
    )
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    noi_dung = models.TextField(blank=True, default="", verbose_name="Nội dung")
    loai = models.CharField(
        max_length=30,
        choices=LoaiThongBao.choices,
        default=LoaiThongBao.HE_THONG,
        verbose_name="Loại thông báo",
    )
    duong_dan = models.CharField(
        max_length=500, blank=True, default="", verbose_name="Đường dẫn liên kết"
    )
    da_doc = models.BooleanField(default=False, verbose_name="Đã đọc")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ["-ngay_tao"]
        verbose_name = "Thông báo"
        verbose_name_plural = "Danh sách thông báo"

    def __str__(self):
        return f"[{self.get_loai_display()}] {self.tieu_de} - {self.nguoi_nhan.username}"
