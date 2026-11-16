
from django.urls import path

from . import views
from .views.chi_tiet_danh_gia import (
    danh_gia_chi_tiet,
    danh_gia_chinh_sua,
)

app_name = "danh_gia"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),

    # UC-1.1 / UC-1.2: Kỳ đánh giá và tiêu chí
    path("ky/", views.ky_danh_sach, name="ky_ds"),
    path("ky/tao/", views.ky_tao, name="ky_tao"),
    path(
        "ky/<str:maky>/tieu-chi/",
        views.tieu_chi_thiet_lap,
        name="tieu_chi",
    ),
    path(
        "ky/<str:maky>/ket-qua/",
        views.ky_ket_qua,
        name="ky_ket_qua",
    ),

    # UC-1.3: Chấm điểm và xác nhận
    path(
        "cham-diem/",
        views.danh_gia_tao,
        name="danh_gia_tao",
    ),
    path(
        "cham-diem/xac-nhan/",
        views.danh_gia_xac_nhan,
        name="danh_gia_xac_nhan",
    ),

    # Xem chi tiết và chỉnh sửa đánh giá đã lưu
    path(
        "cham-diem/<str:madanhgia>/chi-tiet/",
        danh_gia_chi_tiet,
        name="danh_gia_chi_tiet",
    ),
    path(
        "cham-diem/<str:madanhgia>/chinh-sua/",
        danh_gia_chinh_sua,
        name="danh_gia_chinh_sua",
    ),

    # UC-2.1 / UC-2.2: Khen thưởng và kỷ luật
    path(
        "khen-thuong/",
        views.khen_thuong,
        name="khen_thuong",
    ),
    path(
        "ky-luat/",
        views.ky_luat,
        name="ky_luat",
    ),

    # UC-2.3 / UC-2.4: Nhân viên
    path(
        "ket-qua/",
        views.ket_qua_cua_toi,
        name="ket_qua",
    ),
    path(
        "ket-qua/<str:madanhgia>/phan-hoi/",
        views.gui_phan_hoi,
        name="phan_hoi",
    ),
]
