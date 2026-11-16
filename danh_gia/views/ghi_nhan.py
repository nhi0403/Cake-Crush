
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
        messages.error(request, "Bạn không có quyền thực hiện chức năng này.")
        return redirect("danh_gia:trang_chu")

    nhan_vien = NhanVien.objects.all().order_by("pk")
    ma_nv, ma_dg = request.GET.get("nv"), request.GET.get("dg")
    nv = nhan_vien.filter(pk=ma_nv).first() if ma_nv else None

    ds_dg = DanhGia.objects.none()
    dg = None
    dot_xuat = ma_dg == "KHAC"

    if nv:
        ds_dg = (
            DanhGia.objects.filter(manv=nv)
            .select_related("maky")
            .order_by("-maky__thoigianbatdau")
        )

        if not dot_xuat:
            dg = ds_dg.filter(pk=ma_dg).first() if ma_dg else ds_dg.first()
            if dg is None:
                messages.error(request, "Không tìm thấy kết quả đánh giá tương ứng.")

    duoc_ghi_nhan = nv is not None and (dg is not None or dot_xuat)
    form = GhiNhanForm(request.POST or None, loai=loai) if duoc_ghi_nhan else None

    if form is not None and request.method == "POST" and form.is_valid():
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
                from tai_khoan.helpers import thong_bao_nhan_vien, thong_bao_quan_ly

                ten_loai = "Khen thưởng" if loai == "KHENTHUONG" else "Kỷ luật"
                thong_bao_nhan_vien(
                    nhan_vien=nv,
                    tieu_de=f"Quyết định {ten_loai.lower()}",
                    noi_dung=f"Bạn có quyết định {ten_loai.lower()} mới: {obj.hinhthuc} ({obj.lydo}).",
                    loai="DANH_GIA",
                    duong_dan="/danh-gia/ket-qua/",
                )
                thong_bao_quan_ly(
                    tieu_de=f"{ten_loai}: {nv.tennv}",
                    noi_dung=f"Đã ghi nhận {ten_loai.lower()} cho nhân viên {nv.tennv}: {obj.hinhthuc}.",
                    loai="DANH_GIA",
                    duong_dan=cfg["url"] if cfg["url"].startswith("/") else reverse(cfg["url"]),
                    loai_tru_user=request.user,
                )
            except Exception:
                pass

            messages.success(request, cfg["thanh_cong"])
            return redirect(cfg["url"])

    if nv:
        da_ghi_nhan = KhenThuongKyLuat.objects.filter(
            loaiphieu=loai
        ).filter(
            madanhgia=dg
        ) if dg else KhenThuongKyLuat.objects.filter(
            manv=nv, madanhgia__isnull=True, loaiphieu=loai
        ) if dot_xuat else KhenThuongKyLuat.objects.none()
    else:
        da_ghi_nhan = KhenThuongKyLuat.objects.none()

    return render(request, "danh_gia/ghi_nhan.html", {
        "cfg": cfg,
        "nhan_vien": nhan_vien,
        "nv": nv,
        "ds_dg": ds_dg,
        "dg": dg,
        "dot_xuat": dot_xuat,
        "form": form,
        "da_ghi_nhan": da_ghi_nhan,
    })
