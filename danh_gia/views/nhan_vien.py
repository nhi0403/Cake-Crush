"""UC-2.3 (tra cứu kết quả) và UC-2.4 (gửi phản hồi) dành cho nhân viên."""
from django.db.models import Q
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render

from ..forms import PhanHoiForm
from ..models import DanhGia, KyDanhGia, KhenThuongKyLuat
from ..permissions import yeu_cau_nhan_vien
from ..utils import hom_nay


# ======================= UC-2.3: TRA CỨU KẾT QUẢ =======================
@yeu_cau_nhan_vien
def ket_qua_cua_toi(request):
    ds = list(
        DanhGia.objects.filter(manv=request.nhan_vien)
        .select_related("maky")
        .order_by("-maky__thoigianbatdau")
    )
    ma_ky = request.GET.get("ky")
    if ma_ky:
        dg = next((d for d in ds if d.maky_id == ma_ky), None)  # kỳ chưa có kết quả -> None
    else:
        dg = ds[0] if ds else None
    da_co = {d.maky_id for d in ds}
    lich_su_ktkl = (
        KhenThuongKyLuat.objects
        .filter(
            Q(manv=request.nhan_vien) |
            Q(manv__isnull=True, madanhgia__manv=request.nhan_vien)
        )
        .select_related("madanhgia__maky")
        .order_by("-ngay", "-maktkl")
    )
    return render(request, "danh_gia/ket_qua.html", {
        "nhan_vien": request.nhan_vien,
        "ds": ds,
        "dg": dg,
        "ky_dang_xem": KyDanhGia.objects.filter(pk=ma_ky).first() if ma_ky else None,
        "chi_tiet": dg.chitietdanhgia_set.select_related("matieuchi") if dg else [],
        "phan_hoi": dg.phanhoi_set.all() if dg else [],
        "cac_ky": [
            (k, k.pk in da_co)
            for k in KyDanhGia.objects.all()
            if not dg or k.pk != dg.maky_id
        ],
        "lich_su_ktkl": lich_su_ktkl,
    })


# ======================= UC-2.4: GỬI PHẢN HỒI =======================
@yeu_cau_nhan_vien
def gui_phan_hoi(request, madanhgia):
    dg = DanhGia.objects.select_related("maky").filter(pk=madanhgia).first()
    if dg is None or dg.manv_id != request.nhan_vien.pk:
        messages.error(request, "Bạn chỉ được gửi phản hồi đối với kết quả đánh giá của chính mình.")
        return redirect("danh_gia:ket_qua")

    form = PhanHoiForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ph = form.save(commit=False)
        ph.manv = request.nhan_vien
        ph.madanhgia = dg
        ph.ngayphanhoi = hom_nay()
        try:
            with transaction.atomic():
                ph.save()
        except DatabaseError:
            messages.error(request, "Không thể gửi phản hồi, vui lòng thử lại sau")
        else:
            try:
                from tai_khoan.helpers import thong_bao_quan_ly
                thong_bao_quan_ly(
                    tieu_de=f"Phản hồi đánh giá: {request.nhan_vien.tennv}",
                    noi_dung=f"Nhân viên {request.nhan_vien.tennv} đã gửi phản hồi cho kết quả đánh giá kỳ '{dg.maky.tenky}'.",
                    loai="DANH_GIA",
                    duong_dan=f"/danh-gia/ky/{dg.maky_id}/ket-qua/",
                )
            except Exception:
                pass
            messages.success(request, "Gửi phản hồi thành công!")
            return redirect("danh_gia:ket_qua")
    return render(request, "danh_gia/phan_hoi_form.html", {
        "dg": dg, "form": form, "nhan_vien": request.nhan_vien,
    })
