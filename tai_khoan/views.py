from datetime import timedelta
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from .models import ThongBao

# ------------------------------------------------------------------------------
# 1. IMPORT AN TOÀN CÁC MODEL THEO TÊN LỚP THỰC TẾ
# ------------------------------------------------------------------------------
try:
    from nhan_su.models import NhanVien, PhongBan as BoPhan, HopDong
except Exception:
    NhanVien = BoPhan = HopDong = None

try:
    from cham_cong.models import ChamCong, DonNghiPhep
except Exception:
    ChamCong = DonNghiPhep = None

try:
    from dao_tao.models import PhanCongDaoTao as Nv_DaoTao, KhoaDaoTao
except Exception:
    Nv_DaoTao = KhoaDaoTao = None


# ------------------------------------------------------------------------------
# 2. XỬ LÝ ĐĂNG NHẬP / ĐĂNG XUẤT / ĐIỀU HƯỚNG VAI TRÒ
# ------------------------------------------------------------------------------
class CakeCrushLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = False

    def get_success_url(self):
        user = self.request.user
        # Cả Admin (superuser) và Quản lý (staff) đều vào Dashboard Quản lý
        if user.is_superuser or user.is_staff:
            return reverse_lazy('trang_quan_ly')
        return reverse_lazy('trang_nhan_vien')


class CakeCrushLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')


def dieu_huong_dashboard(request):
    """Điều hướng người dùng đã đăng nhập tới dashboard tương ứng"""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser or request.user.is_staff:
        return redirect('trang_quan_ly')
    return redirect('trang_nhan_vien')


@login_required
def trang_nhan_vien(request):
    return render(request, 'nhan_vien_home.html')


# ------------------------------------------------------------------------------
# 3. DASHBOARD QUẢN LÝ: TRUY VẤN VÀ TỰ ĐỘNG CẬP NHẬT THEO CSDL
# ------------------------------------------------------------------------------
@login_required
def trang_quan_ly(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('trang_nhan_vien')

    today = timezone.localdate()

    # Nhận tiêu chí lọc theo bộ phận
    bo_phan_loc = request.GET.get('bo_phan', '').strip()
    bo_phan_obj = None
    if bo_phan_loc and bo_phan_loc != 'all' and BoPhan:
        bo_phan_obj = BoPhan.objects.filter(
            Q(maphongban=bo_phan_loc) | Q(tenphongban=bo_phan_loc)
        ).first()

    # --- A. Thống kê Nhân viên (NhanVien) ---
    tong_nhan_vien = 0
    dang_lam = 0
    da_nghi = 0
    if NhanVien:
        try:
            fields = [f.name for f in NhanVien._meta.get_fields()]
            qs_nv = NhanVien.objects.all()
            if bo_phan_obj and 'maphong' in fields:
                qs_nv = qs_nv.filter(maphong=bo_phan_obj)

            if 'trangthai' in fields:
                dang_lam = qs_nv.filter(trangthai=True).count()
                da_nghi = qs_nv.filter(trangthai=False).count()
                tong_nhan_vien = dang_lam
            elif 'is_active' in fields:
                dang_lam = qs_nv.filter(is_active=True).count()
                da_nghi = qs_nv.filter(is_active=False).count()
                tong_nhan_vien = dang_lam
            else:
                tong_nhan_vien = qs_nv.count()
                dang_lam = tong_nhan_vien
        except Exception:
            tong_nhan_vien = dang_lam = da_nghi = 0

    # --- B. Thống kê Chấm công trong ngày (ChamCong) ---
    cham_cong_hom_nay = 0
    co_mat = di_muon = vang_mat = 0
    checkin_gan_day = []
    if ChamCong:
        try:
            cc_fields = [f.name for f in ChamCong._meta.get_fields()]
            date_col = 'ngaychamcong' if 'ngaychamcong' in cc_fields else 'ngay'

            qs_cc = ChamCong.objects.filter(**{date_col: today})
            if bo_phan_obj and 'manv' in cc_fields:
                qs_cc = qs_cc.filter(manv__maphong=bo_phan_obj)

            cham_cong_hom_nay = qs_cc.count()

            if 'trangthai' in cc_fields:
                co_mat = qs_cc.filter(trangthai__in=['DILAM', 'co_mat', 'Đi làm']).count()
            elif 'gio_checkin' in cc_fields:
                co_mat = qs_cc.filter(gio_checkin__isnull=False).count()
            else:
                co_mat = cham_cong_hom_nay

            if 'thoigianditre' in cc_fields:
                di_muon = qs_cc.filter(thoigianditre__gt=0).count()
            elif 'di_muon' in cc_fields:
                di_muon = qs_cc.filter(di_muon=True).count()

            vang_mat = max(0, tong_nhan_vien - co_mat)

            # Lấy 3 - 4 lượt check-in gần nhất hôm nay
            if 'gio_checkin' in cc_fields:
                qs_recent = qs_cc.filter(gio_checkin__isnull=False).select_related('manv__maphong').order_by('-gio_checkin')[:4]
                for cc in qs_recent:
                    nv = getattr(cc, 'manv', None)
                    mp = getattr(nv, 'maphong', None)
                    phong_ten = getattr(mp, 'tenphongban', getattr(mp, 'tenphong', str(mp))) if mp else 'Chưa phân phòng'
                    checkin_gan_day.append({
                        'ten': getattr(nv, 'tennv', 'Nhân viên'),
                        'ma': getattr(nv, 'manv', ''),
                        'phong': phong_ten,
                        'gio_checkin': cc.gio_checkin.strftime('%H:%M') if cc.gio_checkin else '--:--',
                        'di_tre': getattr(cc, 'thoigianditre', 0) or 0,
                        'trang_thai_text': f"Trễ {cc.thoigianditre}p" if getattr(cc, 'thoigianditre', 0) and cc.thoigianditre > 0 else "Đúng giờ",
                        'trang_thai_class': "bg-amber-50 text-amber-700 border-amber-200/60" if getattr(cc, 'thoigianditre', 0) and cc.thoigianditre > 0 else "bg-emerald-50 text-emerald-700 border-emerald-200/60",
                    })
        except Exception:
            pass

    # --- C. Thống kê Đơn nghỉ phép (DonNghiPhep) ---
    don_nghi_cho_duyet = 0
    don_nghi_da_duyet = 0
    don_nghi_tu_choi = 0
    if DonNghiPhep:
        try:
            qs_dnp = DonNghiPhep.objects.all()
            if bo_phan_obj:
                qs_dnp = qs_dnp.filter(manv__maphong=bo_phan_obj)
            don_nghi_cho_duyet = qs_dnp.filter(trangthai__in=['CHODUYET', 'cho_duyet', 'Chờ duyệt']).count()
            don_nghi_da_duyet = qs_dnp.filter(trangthai__in=['DADUYET', 'da_duyet', 'Đã duyệt']).count()
            don_nghi_tu_choi = qs_dnp.filter(trangthai__in=['TUCHOI', 'tu_choi', 'Từ chối']).count()
        except Exception:
            pass

    # --- D. Cảnh báo Hợp đồng sắp hết hạn trong 30 ngày (HopDong) ---
    hop_dong_sap_het_han = 0
    danh_sach_hop_dong = []
    if HopDong:
        try:
            hd_fields = [f.name for f in HopDong._meta.get_fields()]
            exp_col = 'ngayhethan' if 'ngayhethan' in hd_fields else 'ngay_het_han'
            ngay_gioi_han = today + timedelta(days=30)

            qs_hd = HopDong.objects.filter(**{
                f"{exp_col}__isnull": False,
                f"{exp_col}__gte": today,
                f"{exp_col}__lte": ngay_gioi_han
            }).order_by(exp_col)
            if bo_phan_obj:
                qs_hd = qs_hd.filter(manv__maphong=bo_phan_obj)
            hop_dong_sap_het_han = qs_hd.count()

            dict_loai_hd = {
                'THU_VIEC': 'Thử việc',
                'XAC_DINH_1_NAM': '1 năm',
                'KHONG_XAC_DINH': 'Không thời hạn'
            }

            for hd in qs_hd[:3]:
                dt_end = getattr(hd, exp_col)
                so_ngay = (dt_end - today).days

                nv_obj = getattr(hd, 'manv', getattr(hd, 'nhan_vien', None))
                ma_nv = getattr(nv_obj, 'manv', getattr(nv_obj, 'ma_nv', f"NV{getattr(hd, 'manv_id', hd.pk)}"))
                ho_ten = getattr(nv_obj, 'tennv', getattr(nv_obj, 'ho_ten', getattr(nv_obj, 'hoten', str(nv_obj))))
                loai_hd_val = getattr(hd, 'loaihd', getattr(hd, 'loai_hop_dong', 'HĐ Lao động'))

                danh_sach_hop_dong.append({
                    'ma_nv': ma_nv,
                    'ho_ten': ho_ten,
                    'loai': dict_loai_hd.get(loai_hd_val, loai_hd_val),
                    'het_han': dt_end.strftime('%d/%m/%Y'),
                    'con_lai': f"{so_ngay} ngày",
                    'canh_bao': 'do' if so_ngay <= 15 else 'vang'
                })
        except Exception:
            pass

    # --- E. Thống kê theo Bộ phận (BoPhan & NhanVien) ---
    bo_phan_list = []
    tong_toan_cty = 0
    if NhanVien:
        try:
            fields = [f.name for f in NhanVien._meta.get_fields()]
            if 'trangthai' in fields:
                tong_toan_cty = NhanVien.objects.filter(trangthai=True).count()
            else:
                tong_toan_cty = NhanVien.objects.count()
        except Exception:
            tong_toan_cty = 0

    if BoPhan and NhanVien:
        try:
            nv_fields = [f.name for f in NhanVien._meta.get_fields()]
            bp_fk = 'maphong' if 'maphong' in nv_fields else 'bo_phan'

            for bp in BoPhan.objects.all().order_by('tenphongban'):
                query = {bp_fk: bp}
                if 'trangthai' in nv_fields:
                    query['trangthai'] = True
                elif 'is_active' in nv_fields:
                    query['is_active'] = True

                count_nv = NhanVien.objects.filter(**query).count()
                pct = int((count_nv / tong_toan_cty) * 100) if tong_toan_cty > 0 else 0
                ten_bp = getattr(bp, 'tenphongban', getattr(bp, 'ten_bo_phan', getattr(bp, 'ten', str(bp))))
                ma_bp = getattr(bp, 'maphongban', getattr(bp, 'pk', str(bp)))

                bo_phan_list.append({
                    'ma': ma_bp,
                    'ten': ten_bp,
                    'so_luong': count_nv,
                    'phan_tram': pct,
                    'is_selected': bool(bo_phan_obj and (bp.pk == bo_phan_obj.pk or ma_bp == bo_phan_loc or ten_bp == bo_phan_loc))
                })
        except Exception:
            pass

    # --- F. Tình trạng Đào tạo (Nv_DaoTao) ---
    dao_tao = {
        'chua_hoc': 0,
        'dang_hoc': 0,
        'da_hoc': 0,
        'dat': 0,
        'chua_dat': 0
    }
    if Nv_DaoTao:
        try:
            fields = [f.name for f in Nv_DaoTao._meta.get_fields()]
            col_status = 'tiendo' if 'tiendo' in fields else 'trangthai'
            qs_dt = Nv_DaoTao.objects.all()
            if bo_phan_obj and 'nhanvien' in fields:
                qs_dt = qs_dt.filter(nhanvien__maphong=bo_phan_obj)

            dao_tao['chua_hoc'] = qs_dt.filter(**{f"{col_status}__in": ['Chưa hoàn thành', 'CHUA_HOAN_THANH', 'CHUA_HOC', 'chua_hoc']}).count()
            dao_tao['dang_hoc'] = qs_dt.filter(**{f"{col_status}__in": ['Đang thực hiện', 'DANG_THUC_HIEN', 'DANG_HOC', 'dang_hoc']}).count()
            dao_tao['da_hoc'] = qs_dt.filter(**{f"{col_status}__in": ['Đã hoàn thành', 'DA_HOAN_THANH', 'DA_HOC', 'da_hoc']}).count()
            dao_tao['dat'] = qs_dt.filter(ketqua__in=['Đạt', 'DAT', 'dat']).count()
            dao_tao['chua_dat'] = qs_dt.filter(ketqua__in=['Chưa đạt', 'CHUA_DAT', 'chua_dat']).count()
        except Exception:
            pass

    context = {
        'tong_nhan_vien': tong_nhan_vien,
        'dang_lam': dang_lam,
        'da_nghi': da_nghi,
        'cham_cong_hom_nay': cham_cong_hom_nay,
        'don_nghi_cho_duyet': don_nghi_cho_duyet,
        'don_nghi_da_duyet': don_nghi_da_duyet,
        'don_nghi_tu_choi': don_nghi_tu_choi,
        'hop_dong_sap_het_han': hop_dong_sap_het_han,
        'diem_danh': {'co_mat': co_mat, 'di_muon': di_muon, 'vang_mat': vang_mat},
        'bo_phan': bo_phan_list,
        'bo_phan_duoc_chon': bo_phan_loc,
        'bo_phan_obj': bo_phan_obj,
        'danh_sach_hop_dong': danh_sach_hop_dong,
        'dao_tao': dao_tao,
        'checkin_gan_day': checkin_gan_day,
    }
    return render(request, 'quan_ly_home.html', context)


# ------------------------------------------------------------------------------
# 4. TRANG CHÀO MỪNG VÀ TRANG CHỦ (LUÔN HIỂN THỊ WELCOME.HTML)
# ------------------------------------------------------------------------------
def trang_chao_mung(request):
    try:
        return render(request, 'welcome.html')
    except Exception:
        return redirect('login')


def trang_chu(request):
    try:
        return render(request, 'welcome.html')
    except Exception:
        return redirect('login')


# ------------------------------------------------------------------------------
# 5. TÍNH NĂNG THÔNG BÁO (NOTIFICATION BELL)
# ------------------------------------------------------------------------------
def _dinh_dang_thoi_gian(dt):
    """Chuyển datetime sang dạng mô tả thân thiện (VD: 5 phút trước, Hôm nay)."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Vừa xong"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} phút trước"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} giờ trước"
    elif seconds < 86400 * 2:
        return "Hôm qua"
    else:
        return dt.strftime("%d/%m/%Y %H:%M")


@login_required
@require_GET
def api_danh_sach_thong_bao(request):
    """API lấy danh sách thông báo và số lượng chưa đọc của người dùng hiện tại."""
    qs = ThongBao.objects.filter(nguoi_nhan=request.user).order_by("-ngay_tao")
    chua_doc_count = qs.filter(da_doc=False).count()
    
    # Lấy 15 thông báo gần nhất
    danh_sach = []
    for tb in qs[:15]:
        danh_sach.append({
            "id": tb.id,
            "tieu_de": tb.tieu_de,
            "noi_dung": tb.noi_dung,
            "loai": tb.loai,
            "loai_hien_thi": tb.get_loai_display(),
            "duong_dan": tb.duong_dan or "#",
            "da_doc": tb.da_doc,
            "thoi_gian": _dinh_dang_thoi_gian(tb.ngay_tao),
        })

    return JsonResponse({
        "status": "success",
        "chua_doc": chua_doc_count,
        "danh_sach": danh_sach,
    })


@login_required
@require_POST
def api_doc_mot_thong_bao(request, pk):
    """Đánh dấu một thông báo là đã đọc."""
    tb = get_object_or_404(ThongBao, pk=pk, nguoi_nhan=request.user)
    if not tb.da_doc:
        tb.da_doc = True
        tb.save(update_fields=["da_doc"])
    
    con_chua_doc = ThongBao.objects.filter(nguoi_nhan=request.user, da_doc=False).count()
    return JsonResponse({
        "status": "success",
        "id": tb.id,
        "duong_dan": tb.duong_dan,
        "con_chua_doc": con_chua_doc,
    })


@login_required
@require_POST
def api_doc_tat_ca_thong_bao(request):
    """Đánh dấu tất cả thông báo của người dùng là đã đọc."""
    ThongBao.objects.filter(nguoi_nhan=request.user, da_doc=False).update(da_doc=True)
    return JsonResponse({
        "status": "success",
        "message": "Đã đánh dấu tất cả là đã đọc",
        "con_chua_doc": 0,
    })


# ------------------------------------------------------------------------------
# 6. TÍNH NĂNG TÌM KIẾM TOÀN DIỆN (GLOBAL SEARCH)
# ------------------------------------------------------------------------------
def _thuc_hien_tim_kiem(query_text, user):
    """Hàm tìm kiếm đa phân hệ theo quyền hạn người dùng."""
    ket_qua = {
        "nhan_vien": [],
        "phong_ban": [],
        "khoa_dao_tao": [],
        "hop_dong": [],
        "nghi_phep": [],
    }
    
    if not query_text:
        return ket_qua

    la_quan_ly = user.is_superuser or user.is_staff
    q = query_text.strip()

    # 1. Tìm Nhân viên
    if NhanVien:
        try:
            qs_nv = NhanVien.objects.filter(
                Q(manv__icontains=q) |
                Q(tennv__icontains=q) |
                Q(email__icontains=q) |
                Q(sdt__icontains=q) |
                Q(chucvu__icontains=q)
            ).select_related("maphong")
            
            for nv in qs_nv[:8]:
                ten_pb = nv.maphong.tenphongban if nv.maphong else "Chưa phân phòng"
                url = reverse("nhan_su:chi_tiet_nhan_vien", args=[nv.manv]) if la_quan_ly else reverse("nhan_su:ho_so_cua_toi")
                ket_qua["nhan_vien"].append({
                    "ma": nv.manv,
                    "tieu_de": nv.tennv,
                    "phu": f"{nv.chucvu} · {ten_pb}",
                    "mo_ta": f"SĐT: {nv.sdt} · Email: {nv.email}",
                    "url": url,
                    "loai": "Nhân viên",
                })
        except Exception:
            pass

    # 2. Tìm Phòng ban
    if BoPhan:
        try:
            qs_pb = BoPhan.objects.filter(
                Q(maphongban__icontains=q) | Q(tenphongban__icontains=q)
            )
            for pb in qs_pb[:5]:
                url = f"{reverse('nhan_su:danh_sach_nhan_vien')}?phong_ban={pb.maphongban}" if la_quan_ly else reverse("trang_nhan_vien")
                ket_qua["phong_ban"].append({
                    "ma": pb.maphongban,
                    "tieu_de": pb.tenphongban,
                    "phu": pb.maphongban,
                    "mo_ta": pb.mota[:100] if pb.mota else "",
                    "url": url,
                    "loai": "Phòng ban",
                })
        except Exception:
            pass

    # 3. Tìm Khóa đào tạo
    if KhoaDaoTao:
        try:
            qs_kdt = KhoaDaoTao.objects.filter(
                Q(makhoa__icontains=q) | Q(tenkhoa__icontains=q)
            )
            for k in qs_kdt[:6]:
                url = reverse("dao_tao:chi_tiet_khoa", args=[k.makhoa]) if la_quan_ly else reverse("dao_tao:chuong_trinh_cua_toi")
                ket_qua["khoa_dao_tao"].append({
                    "ma": k.makhoa,
                    "tieu_de": k.tenkhoa,
                    "phu": f"Trạng thái: {k.trangthai}",
                    "mo_ta": f"Từ {k.ngaybatdau.strftime('%d/%m/%Y') if k.ngaybatdau else '...'} đến {k.ngayketthuc.strftime('%d/%m/%Y') if k.ngayketthuc else '...'}",
                    "url": url,
                    "loai": "Khóa đào tạo",
                })
        except Exception:
            pass

    # 4. Tìm Hợp đồng
    if HopDong:
        try:
            qs_hd = HopDong.objects.filter(
                Q(mahd__icontains=q) | Q(manv__tennv__icontains=q) | Q(manv__manv__icontains=q)
            ).select_related("manv")
            if not la_quan_ly:
                qs_hd = qs_hd.filter(manv__id_taikhoan=user)
                
            for hd in qs_hd[:6]:
                url = reverse("nhan_su:chi_tiet_hop_dong", args=[hd.mahd]) if la_quan_ly else reverse("nhan_su:chi_tiet_hop_dong_cua_toi", args=[hd.mahd])
                ket_qua["hop_dong"].append({
                    "ma": hd.mahd,
                    "tieu_de": f"HĐ {hd.mahd} - {hd.manv.tennv}",
                    "phu": hd.get_loaihd_display() if hasattr(hd, 'get_loaihd_display') else hd.loaihd,
                    "mo_ta": f"Thời hạn: {hd.ngaybatdau.strftime('%d/%m/%Y') if hd.ngaybatdau else ''} - {hd.ngayhethan.strftime('%d/%m/%Y') if hd.ngayhethan else 'Không thời hạn'}",
                    "url": url,
                    "loai": "Hợp đồng",
                })
        except Exception:
            pass

    # 5. Tìm Đơn nghỉ phép
    if DonNghiPhep:
        try:
            qs_dnp = DonNghiPhep.objects.filter(
                Q(manv__tennv__icontains=q) | Q(lydo__icontains=q)
            ).select_related("manv", "maloaiphep")
            if not la_quan_ly:
                qs_dnp = qs_dnp.filter(manv__id_taikhoan=user)

            for d in qs_dnp[:6]:
                url = reverse("cham_cong:chi_tiet_duyet", args=[d.madon]) if la_quan_ly else reverse("cham_cong:chi_tiet_don_cua_toi", args=[d.madon])
                ket_qua["nghi_phep"].append({
                    "ma": f"Đơn #{d.madon}",
                    "tieu_de": f"{d.manv.tennv} - {d.maloaiphep.tenloaiphep if d.maloaiphep else 'Nghỉ phép'}",
                    "phu": f"Trạng thái: {d.get_trangthai_display() if hasattr(d, 'get_trangthai_display') else d.trangthai}",
                    "mo_ta": f"Lý do: {d.lydo[:80]}",
                    "url": url,
                    "loai": "Nghỉ phép",
                })
        except Exception:
            pass

    return ket_qua


@login_required
@require_GET
def api_tim_kiem_nhanh(request):
    """API tìm kiếm nhanh trả về gợi ý JSON khi gõ vào thanh tìm kiếm."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"status": "success", "tong": 0, "ket_qua": []})

    ket_qua_dict = _thuc_hien_tim_kiem(q, request.user)
    
    danh_sach_phang = []
    for nhom, items in ket_qua_dict.items():
        for item in items:
            danh_sach_phang.append(item)

    return JsonResponse({
        "status": "success",
        "tong": len(danh_sach_phang),
        "ket_qua": danh_sach_phang[:12],
    })


@login_required
def trang_tim_kiem(request):
    """Trang hiển thị toàn bộ kết quả tìm kiếm khi ấn Enter."""
    q = request.GET.get("q", "").strip()
    ket_qua = _thuc_hien_tim_kiem(q, request.user)
    
    tong_so = sum(len(items) for items in ket_qua.values())
    
    context = {
        "q": q,
        "tong_so": tong_so,
        "ket_qua": ket_qua,
        "has_results": tong_so > 0,
    }
    return render(request, "tim_kiem_ket_qua.html", context)

