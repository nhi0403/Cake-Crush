
"""Xem chi tiết và chỉnh sửa kết quả đánh giá đã lưu."""

from django import forms
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .. import services
from ..models import ChiTietDanhGia, DanhGia, KhenThuongKyLuat, PhanHoi
from ..permissions import QUYEN_DANH_GIA, yeu_cau_quyen


class ChinhSuaDanhGiaForm(forms.Form):
    """Tạo ô sửa điểm và nhận xét theo từng tiêu chí đã lưu."""

    nhanxet_chung = forms.CharField(
        label="Nhận xét chung của quản lý",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 4}
        ),
    )

    def __init__(self, *args, chi_tiet=None, **kwargs):
        super().__init__(*args, **kwargs)

        for ct in chi_tiet or []:
            self.fields[f"diem_{ct.pk}"] = forms.IntegerField(
                label=f"Điểm - {ct.matieuchi.tentieuchi}",
                min_value=0,
                max_value=10,
                widget=forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "min": "0",
                        "max": "10",
                        "step": "1",
                    }
                ),
            )

            self.fields[f"nhanxet_{ct.pk}"] = forms.CharField(
                label="Nhận xét tiêu chí",
                required=False,
                widget=forms.Textarea(
                    attrs={
                        "class": "form-control",
                        "rows": 2,
                        "placeholder": "Nhận xét cho tiêu chí này...",
                    }
                ),
            )


def _lay_chi_tiet(danh_gia):
    return list(
        ChiTietDanhGia.objects.filter(madanhgia=danh_gia)
        .select_related("matieuchi")
        .order_by("matieuchi_id")
    )


@yeu_cau_quyen(QUYEN_DANH_GIA)
def danh_gia_chi_tiet(request, madanhgia):
    dg = get_object_or_404(
        DanhGia.objects.select_related("manv", "maky"),
        pk=madanhgia,
    )

    chi_tiet = _lay_chi_tiet(dg)

    # Chỉ những quyết định gắn với bản đánh giá này.
    ghi_nhan_theo_ky = KhenThuongKyLuat.objects.filter(
        madanhgia=dg
    ).order_by("-ngay", "-maktkl")

    # Quyết định đột xuất của nhân viên, không gắn kỳ.
    ghi_nhan_dot_xuat = KhenThuongKyLuat.objects.filter(
        manv=dg.manv,
        madanhgia__isnull=True,
    ).order_by("-ngay", "-maktkl")

    phan_hoi = PhanHoi.objects.filter(
        madanhgia=dg
    ).order_by("-ngayphanhoi", "-maph")

    return render(
        request,
        "danh_gia/danh_gia_chi_tiet.html",
        {
            "dg": dg,
            "chi_tiet": chi_tiet,
            "ghi_nhan_theo_ky": ghi_nhan_theo_ky,
            "ghi_nhan_dot_xuat": ghi_nhan_dot_xuat,
            "phan_hoi": phan_hoi,
        },
    )


@yeu_cau_quyen(QUYEN_DANH_GIA)
def danh_gia_chinh_sua(request, madanhgia):
    dg = get_object_or_404(
        DanhGia.objects.select_related("manv", "maky"),
        pk=madanhgia,
    )

    chi_tiet = _lay_chi_tiet(dg)

    if not chi_tiet:
        messages.error(
            request,
            "Bản đánh giá chưa có điểm chi tiết để chỉnh sửa."
        )
        return redirect(
            "danh_gia:danh_gia_chi_tiet",
            madanhgia=dg.pk,
        )

    initial = {
        "nhanxet_chung": dg.nhanxet or "",
    }

    for ct in chi_tiet:
        initial[f"diem_{ct.pk}"] = ct.diem
        initial[f"nhanxet_{ct.pk}"] = ct.nhanxet or ""

    form = ChinhSuaDanhGiaForm(
        request.POST or None,
        chi_tiet=chi_tiet,
        initial=initial,
    )

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                # Khóa bản đánh giá khi cập nhật.
                dg = DanhGia.objects.select_for_update().get(
                    pk=madanhgia
                )

                chi_tiet_hien_tai = list(
                    ChiTietDanhGia.objects.select_for_update()
                    .filter(madanhgia=dg)
                )

                if {ct.pk for ct in chi_tiet_hien_tai} != {
                    ct.pk for ct in chi_tiet
                }:
                    raise ValueError(
                        "Danh sách tiêu chí đã thay đổi, hãy tải lại trang."
                    )

                ds_diem = []

                for ct in chi_tiet_hien_tai:
                    diem = form.cleaned_data[f"diem_{ct.pk}"]
                    nhanxet = form.cleaned_data[
                        f"nhanxet_{ct.pk}"
                    ]

                    ct.diem = diem
                    ct.nhanxet = nhanxet or None
                    ct.save(update_fields=["diem", "nhanxet"])

                    ds_diem.append(diem)

                diem_tb = services.tinh_diem_trung_binh(
                    ds_diem
                )

                dg.xeploai = services.xep_loai_tu_diem(
                    diem_tb
                )
                dg.nhanxet = (
                    form.cleaned_data["nhanxet_chung"] or None
                )
                dg.save(update_fields=["xeploai", "nhanxet"])

        except (DatabaseError, ValueError) as exc:
            messages.error(
                request,
                "Không thể cập nhật đánh giá: " + str(exc)
            )
        else:
            messages.success(
                request,
                "Cập nhật kết quả đánh giá thành công!"
            )
            return redirect(
                "danh_gia:danh_gia_chi_tiet",
                madanhgia=dg.pk,
            )

    rows = [
        {
            "ct": ct,
            "diem_field": form[f"diem_{ct.pk}"],
            "nhanxet_field": form[f"nhanxet_{ct.pk}"],
        }
        for ct in chi_tiet
    ]

    return render(
        request,
        "danh_gia/danh_gia_chinh_sua.html",
        {
            "dg": dg,
            "form": form,
            "rows": rows,
        },
    )
