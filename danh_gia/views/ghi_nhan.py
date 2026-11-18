
"""Logic chung cho khen thưởng và kỷ luật."""

from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from nhan_su.models import NhanVien

from ..forms import GhiNhanForm
from ..models import DanhGia, KhenThuongKyLuat
from ..permissions import co_quyen


def xu_ly_ghi_nhan(request, loai, cfg):
    if not co_quyen(request.user, cfg["quyen"]):
        messages.error(
            request,
            "Bạn không có quyền thực hiện chức năng này."
        )
        return redirect("danh_gia:trang_chu")

    nhan_vien = NhanVien.objects.all().order_by("pk")

    # Nhận lựa chọn từ URL và từ form khi lưu.
    ma_nv = request.GET.get("nv") or request.POST.get("nv")
    ma_dg = request.GET.get("dg") or request.POST.get("dg")
    ma_dg = (ma_dg or "").strip()

    nv = nhan_vien.filter(pk=ma_nv).first() if ma_nv else None

    ds_dg = DanhGia.objects.none()
    dg = None
    dot_xuat = ma_dg.upper() == "KHAC"

    if nv:
        ds_dg = (
            DanhGia.objects.filter(manv=nv)
            .select_related("maky")
            .order_by("-maky__thoigianbatdau")
        )

        if not dot_xuat:
            if ma_dg:
                dg = ds_dg.filter(pk=ma_dg).first()
            else:
                dg = ds_dg.first()

            if dg is None and ma_dg:
                messages.error(
                    request,
                    "Không tìm thấy kết quả đánh giá tương ứng."
                )

    duoc_ghi_nhan = nv is not None and (
        dot_xuat or dg is not None
    )

    form = (
        GhiNhanForm(request.POST or None, loai=loai)
        if duoc_ghi_nhan
        else None
    )

    if (
        request.method == "POST"
        and form is not None
        and form.is_valid()
    ):
        obj = form.save(commit=False)

        obj.manv = nv
        obj.madanhgia = None if dot_xuat else dg
        obj.loaiphieu = loai

        try:
            with transaction.atomic():
                obj.save()

        except DatabaseError:
            messages.error(request, cfg["loi_csdl"])

        else:
            try:
                from tai_khoan.helpers import (
                    thong_bao_nhan_vien,
                    thong_bao_quan_ly,
                )

                if loai == "KHENTHUONG":
                    tb_nv_tieu_de = "Quyết định khen thưởng"
                    tb_nv_noi_dung = f"Chúc mừng! Bạn đã nhận được quyết định khen thưởng: {obj.hinhthuc} ({obj.lydo})."
                    tb_ql_tieu_de = f"Khen thưởng nhân viên: {nv.tennv}"
                    tb_ql_noi_dung = f"Đã ghi nhận khen thưởng cho nhân viên {nv.tennv} ({nv.manv}): {obj.hinhthuc}."
                    ql_duong_dan = "/danh-gia/khen-thuong/"
                else:
                    tb_nv_tieu_de = "Quyết định kỷ luật"
                    tb_nv_noi_dung = f"Thông báo: Bạn có quyết định kỷ luật về việc: {obj.hinhthuc} ({obj.lydo})."
                    tb_ql_tieu_de = f"Kỷ luật nhân viên: {nv.tennv}"
                    tb_ql_noi_dung = f"Đã ghi nhận hình thức kỷ luật đối với nhân viên {nv.tennv} ({nv.manv}): {obj.hinhthuc}."
                    ql_duong_dan = "/danh-gia/ky-luat/"

                thong_bao_nhan_vien(
                    nhan_vien=nv,
                    tieu_de=tb_nv_tieu_de,
                    noi_dung=tb_nv_noi_dung,
                    loai="DANH_GIA",
                    duong_dan="/danh-gia/ket-qua/",
                )

                thong_bao_quan_ly(
                    tieu_de=tb_ql_tieu_de,
                    noi_dung=tb_ql_noi_dung,
                    loai="DANH_GIA",
                    duong_dan=ql_duong_dan,
                    loai_tru_user=request.user,
                )

            except Exception:
                pass

            messages.success(request, cfg["thanh_cong"])

            # Giữ lại nhân viên và chế độ đột xuất
            # để có thể xem bản ghi vừa tạo.
            return redirect(
                f"{reverse(cfg['url'])}"
                f"?nv={nv.pk}&dg={'KHAC' if dot_xuat else dg.pk}"
            )

    if nv and dot_xuat:
        da_ghi_nhan = KhenThuongKyLuat.objects.filter(
            manv=nv,
            madanhgia__isnull=True,
            loaiphieu=loai,
        ).order_by("-ngay")

    elif nv and dg:
        da_ghi_nhan = KhenThuongKyLuat.objects.filter(
            madanhgia=dg,
            loaiphieu=loai,
        ).order_by("-ngay")

    else:
        da_ghi_nhan = KhenThuongKyLuat.objects.none()

    return render(
        request,
        "danh_gia/ghi_nhan.html",
        {
            "cfg": cfg,
            "nhan_vien": nhan_vien,
            "nv": nv,
            "ds_dg": ds_dg,
            "dg": dg,
            "dot_xuat": dot_xuat,
            "form": form,
            "da_ghi_nhan": da_ghi_nhan,
        },
    )
