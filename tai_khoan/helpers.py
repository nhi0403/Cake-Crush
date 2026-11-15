"""Hàm tiện ích tạo thông báo trong hệ thống Cake Crush HR."""
from django.contrib.auth.models import User
from django.db.models import Q
from .models import ThongBao


def tao_thong_bao(nguoi_nhan, tieu_de, noi_dung="", loai="HE_THONG", duong_dan=""):
    """
    Tạo thông báo cho một hoặc nhiều User.
    nguoi_nhan có thể là User instance, QuerySet[User], hoặc list[User].
    """
    if isinstance(nguoi_nhan, User):
        ds_user = [nguoi_nhan]
    elif hasattr(nguoi_nhan, "__iter__"):
        ds_user = list(nguoi_nhan)
    else:
        return []

    danh_sach = [
        ThongBao(
            nguoi_nhan=u,
            tieu_de=tieu_de,
            noi_dung=noi_dung,
            loai=loai,
            duong_dan=duong_dan,
        )
        for u in ds_user
        if isinstance(u, User)
    ]
    return ThongBao.objects.bulk_create(danh_sach)


def thong_bao_quan_ly(tieu_de, noi_dung="", loai="HE_THONG", duong_dan="", loai_tru_user=None):
    """Gửi thông báo tới toàn bộ tài khoản quản lý và admin."""
    try:
        qs = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True), is_active=True).distinct()
        if loai_tru_user:
            qs = qs.exclude(pk=loai_tru_user.pk)
        return tao_thong_bao(qs, tieu_de, noi_dung, loai, duong_dan)
    except Exception:
        return []


def thong_bao_nhan_vien(nhan_vien, tieu_de, noi_dung="", loai="HE_THONG", duong_dan=""):
    """Gửi thông báo tới tài khoản của nhân viên nếu đã được liên kết."""
    try:
        if not nhan_vien:
            return []
        taikhoan = getattr(nhan_vien, "id_taikhoan", None)
        if taikhoan and isinstance(taikhoan, User) and taikhoan.is_active:
            return tao_thong_bao(taikhoan, tieu_de, noi_dung, loai, duong_dan)
        return []
    except Exception:
        return []
