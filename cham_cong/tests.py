from datetime import date, time, timedelta  # Mốc ngày giờ cho kiểm thử.
from decimal import Decimal  # So sánh số giờ chính xác.
from io import BytesIO  # Đọc file Excel trả về.

from django.contrib.auth import get_user_model  # Model tài khoản của dự án.
from django.core.exceptions import ValidationError  # Lỗi nghiệp vụ cần được chặn.
from django.test import TestCase  # Mỗi ca kiểm thử chạy trên database riêng.
from django.utils import timezone  # Mốc "hôm nay" thật mà view dùng.
from django.urls import reverse  # Không ghi cứng URL.

from nhan_su.models import NhanVien, PhongBan  # Hồ sơ nhân viên của phân hệ nhân sự.

from . import services  # Nghiệp vụ cần kiểm tra.
from .models import ChamCong, DonNghiPhep, LoaiPhep  # Các bảng của phân hệ.

HOM_NAY = date(2026, 10, 5)  # Thứ Hai, 05/10/2026 giống mockup.


def luc(gio, phut, ngay=HOM_NAY):  # Tạo thời điểm có múi giờ trong ngày kiểm thử.
    return services.thoi_diem(ngay, time(gio, phut))  # Ghép ngày và giờ.


class ChamCongTests(TestCase):  # Kiểm thử nghiệp vụ chấm công và nghỉ phép.
    @classmethod  # Phương thức của lớp, chạy một lần cho cả nhóm kiểm thử.
    def setUpTestData(cls):  # Tạo dữ liệu dùng chung một lần.
        User = get_user_model()  # Model tài khoản.
        pb = PhongBan.objects.create(maphongban="CH", tenphongban="Cửa hàng")  # Một phòng ban.

        def ho_so(ten_dn, ma, ten, quan_ly=False):  # Tạo tài khoản và hồ sơ.
            user = User.objects.create_user(ten_dn, password="Test!CakeCrush936", is_staff=quan_ly)  # Tài khoản.
            nv = NhanVien.objects.create(  # Hồ sơ nhân viên.
                manv=ma, id_taikhoan=user, maphong=pb, tennv=ten, gioitinh="Nữ", sdt=f"09000000{ma[-2:]}",  # Thông tin.
                email=f"{ten_dn}@test.vn", cccd=f"0000000000{ma[-2:]}", chucvu="Nhân viên bán hàng",  # Thông tin.
                ngayvaolam=date(2026, 1, 1),  # Đã vào làm từ đầu năm.
            )  # Kết thúc tạo hồ sơ.
            return user, nv  # Trả tài khoản và hồ sơ.

        cls.u_nv, cls.nv = ho_so("nv", "NV005", "Trần Thị Hồng Vân")  # Nhân viên.
        cls.u_ql, cls.ql = ho_so("ql", "NV001", "Nguyễn Thị Nhi", quan_ly=True)  # Quản lý.
        cls.phep_nam = LoaiPhep.objects.get(tenloaiphep="Nghỉ phép năm hưởng lương")  # Có từ migration dữ liệu.
        cls.khong_luong = LoaiPhep.objects.get(tenloaiphep="Nghỉ việc riêng không hưởng lương")  # Không trừ phép.

    # ---------- Tính giờ theo số liệu mockup ----------
    def test_tinh_gio_vao_tre_ra_som(self):  # 08:12 → 16:45.
        kq = services.tinh_ket_qua_checkout(time(8, 12), time(16, 45))  # Tính kết quả.
        self.assertEqual(services.tinh_di_tre(time(8, 12)), 12)  # Trễ 12 phút.
        self.assertEqual(kq["sogiolamviec"], Decimal("7.55"))  # 7 giờ 33 phút = 7,55 giờ.
        self.assertEqual(kq["thoigianvesom"], 15)  # Về sớm 15 phút.
        self.assertEqual(kq["sogiolamthem"], Decimal("0.00"))  # Không làm thêm.

    def test_tinh_gio_lam_them(self):  # 08:00 → 18:00.
        kq = services.tinh_ket_qua_checkout(time(8, 0), time(18, 0))  # Tính kết quả.
        self.assertEqual(kq["sogiolamviec"], Decimal("9.00"))  # 10 giờ − 1 giờ nghỉ trưa.
        self.assertEqual(kq["sogiolamthem"], Decimal("1.00"))  # Làm thêm 1 giờ.

    # ---------- Check-in / Check-out ----------
    def test_check_in_hai_lan_bi_chan(self):  # Exception flow 1 của Check-in.
        services.check_in(self.nv, luc(8, 12))  # Lần 1 thành công.
        with self.assertRaisesMessage(ValidationError, "Bạn đã Check-in trong ngày hôm nay"):  # Lần 2 bị chặn.
            services.check_in(self.nv, luc(8, 30))  # Gửi lại yêu cầu.
        bg = ChamCong.objects.get(manv=self.nv)  # Chỉ có một bản ghi.
        self.assertEqual((bg.gio_checkin, bg.thoigianditre), (time(8, 12), 12))  # Không ghi đè giờ cũ.

    def test_check_out_khi_chua_check_in(self):  # Exception flow 1 của Check-out.
        with self.assertRaisesMessage(ValidationError, "Bạn chưa Check-in trong ngày hôm nay"):  # Bị chặn.
            services.check_out(self.nv, luc(17, 0))  # Check-out khi chưa Check-in.

    def test_check_out_thanh_cong_va_lan_hai_bi_chan(self):  # Luồng chính và exception flow 2.
        services.check_in(self.nv, luc(8, 12))  # Check-in.
        bg = services.check_out(self.nv, luc(16, 45))  # Check-out.
        self.assertEqual((bg.sogiolamviec, bg.thoigianvesom), (Decimal("7.55"), 15))  # Lưu đúng kết quả.
        with self.assertRaisesMessage(ValidationError, "Bạn đã Check-out trong ngày hôm nay"):  # Lần 2 bị chặn.
            services.check_out(self.nv, luc(17, 30))  # Gửi lại yêu cầu.

    def test_nut_check_in_tren_giao_dien(self):  # Gửi POST qua view thật.
        self.client.force_login(self.u_nv)  # Đăng nhập nhân viên.
        trang = self.client.post(reverse("cham_cong:check_in"), follow=True)  # Bấm Check-in.
        self.assertContains(trang, "Check-in thành công lúc")  # Có thông báo thành công.
        self.assertTrue(ChamCong.objects.filter(manv=self.nv).exists())  # Đã lưu bản ghi.

    # ---------- Bảng công ----------
    def test_vang_khong_phep_tu_suy_ra(self):  # Ngày làm việc đã qua không có dữ liệu → Vắng.
        dong = services.tao_bang_cong(2026, 9, [self.nv], hom_nay=HOM_NAY)  # Tháng 9 không có dữ liệu.
        self.assertTrue(all(d.trangthai == "VANGKHONGPHEP" for d in dong))  # Toàn bộ là vắng.
        self.assertEqual(len(dong), 30)  # Tiệm bánh làm cả tuần: đủ 30 ngày, kể cả Chủ nhật.

    # ---------- Đơn nghỉ phép ----------
    def test_khong_chon_ngay_qua_khu(self):  # BR2 UC-NP-3.01.
        with self.assertRaises(ValidationError):  # Bị chặn.
            services.tao_don(self.nv, self.phep_nam, date(2026, 10, 1), date(2026, 10, 1), "Việc riêng", HOM_NAY)  # Ngày quá khứ.

    def test_khong_trung_ngay_voi_don_cho_duyet(self):  # BR3 UC-NP-3.01.
        services.tao_don(self.nv, self.phep_nam, date(2026, 10, 8), date(2026, 10, 9), "Việc riêng", HOM_NAY)  # Đơn 1.
        with self.assertRaisesMessage(ValidationError, "trùng"):  # Đơn 2 trùng ngày 09/10.
            services.tao_don(self.nv, self.khong_luong, date(2026, 10, 9), date(2026, 10, 10), "Việc khác", HOM_NAY)  # Đơn 2.

    def test_phep_nam_vuot_quy_bi_chan(self):  # BR1 UC-NP-3.01: quỹ 12 ngày.
        with self.assertRaisesMessage(ValidationError, "không đủ"):  # Bị chặn.
            services.tao_don(self.nv, self.phep_nam, date(2026, 10, 6), date(2026, 10, 18), "Du lịch", HOM_NAY)  # 13 ngày.
        don = services.tao_don(self.nv, self.khong_luong, date(2026, 10, 6), date(2026, 10, 18), "Du lịch", HOM_NAY)  # Không lương thì được.
        self.assertEqual(don.songaynghi, 13)  # Đếm mọi ngày, tính cả hai đầu.

    def test_duyet_don_tru_phep_va_dong_bo_bang_cong(self):  # UC-QLP-3.01 luồng chính.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 10, 8), date(2026, 10, 9), "Việc riêng", HOM_NAY)  # Đơn 2 ngày.
        services.duyet_don(don, self.ql)  # Quản lý duyệt.
        self.assertEqual(services.thong_ke_phep(self.nv, 2026)["con_lai"], 10)  # 12 − 2 = 10.
        self.assertEqual(ChamCong.objects.filter(manv=self.nv, trangthai="NGHIPHEP").count(), 2)  # Đã ghi vào bảng công.
        with self.assertRaises(ValidationError):  # BR3: đơn đã duyệt không được xử lý lại.
            services.tu_choi_don(don, self.ql, "Đổi ý")  # Thử từ chối lại.

    def test_khong_tu_duyet_don_cua_minh(self):  # Quy tắc đã chốt.
        don = services.tao_don(self.ql, self.phep_nam, date(2026, 10, 8), date(2026, 10, 8), "Việc riêng", HOM_NAY)  # Đơn của quản lý.
        with self.assertRaisesMessage(ValidationError, "chính mình"):  # Bị chặn.
            services.duyet_don(don, self.ql)  # Tự duyệt.

    def test_tu_choi_bat_buoc_ly_do(self):  # BR1 UC-QLP-3.01.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 10, 8), date(2026, 10, 8), "Việc riêng", HOM_NAY)  # Đơn 1 ngày.
        with self.assertRaisesMessage(ValidationError, "Vui lòng nhập lý do từ chối"):  # Bị chặn.
            services.tu_choi_don(don, self.ql, "  ")  # Lý do rỗng.
        services.tu_choi_don(don, self.ql, "Thiếu người")  # Có lý do thì được.
        self.assertEqual(services.thong_ke_phep(self.nv, 2026)["con_lai"], 12)  # Quỹ phép giữ nguyên.

    def test_don_qua_hai_nam_chia_theo_tung_nam(self):  # Đơn 30/12/2026 → 02/01/2027.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 12, 30), date(2027, 1, 2), "Về quê", HOM_NAY)  # Đơn 4 ngày.
        services.duyet_don(don, self.ql)  # Quản lý duyệt.
        self.assertEqual(services.thong_ke_phep(self.nv, 2026)["da_dung"], 2)  # 30, 31/12 trừ vào năm 2026.
        self.assertEqual(services.thong_ke_phep(self.nv, 2027)["da_dung"], 2)  # 01, 02/01 trừ vào năm 2027.

    def test_don_qua_nam_kiem_tra_quy_tung_nam(self):  # Năm cũ hết phép thì bị chặn dù năm mới còn đủ.
        services.duyet_don(services.tao_don(  # Dùng hết 11 ngày phép năm 2026.
            self.nv, self.phep_nam, date(2026, 12, 1), date(2026, 12, 11), "Du lịch", HOM_NAY), self.ql)  # Đơn 11 ngày.
        with self.assertRaisesMessage(ValidationError, "năm 2026 còn 1 ngày, đơn cần 2 ngày"):  # Báo đúng năm thiếu.
            services.tao_don(self.nv, self.phep_nam, date(2026, 12, 30), date(2027, 1, 2), "Về quê", HOM_NAY)  # 2 ngày cuối năm.

    def test_hien_thi_phut_doi_sang_gio(self):  # Bộ lọc hiển thị thời gian.
        from .templatetags.cham_cong_tags import gio_phut, phut_gio  # Hai bộ lọc template.
        self.assertEqual([phut_gio(45), phut_gio(60), phut_gio(75)], ["45 phút", "1 giờ", "1 giờ 15 phút"])  # Đủ 60 phút thì đổi giờ.
        self.assertEqual(gio_phut(Decimal("7.55")), "7 giờ 33 phút")  # 7,55 giờ trong database.

    # ---------- Đồng bộ với các phân hệ khác ----------
    def test_duyet_don_khong_ghi_de_ngay_da_check_in(self):  # Đơn duyệt không xóa dữ liệu Check-in thật.
        ChamCong.objects.create(manv=self.nv, ngaychamcong=date(2026, 10, 8), gio_checkin=time(8, 0), trangthai="DILAM")  # Đã đi làm.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 10, 8), date(2026, 10, 9), "Việc riêng", HOM_NAY)  # Đơn 2 ngày.
        don = services.duyet_don(don, self.ql)  # Quản lý duyệt.
        self.assertEqual(don.ngay_bo_qua, [date(2026, 10, 8)])  # Báo lại ngày không ghi được.
        self.assertEqual(ChamCong.objects.get(manv=self.nv, ngaychamcong=date(2026, 10, 8)).trangthai, "DILAM")  # Giữ nguyên.
        self.assertEqual(ChamCong.objects.get(manv=self.nv, ngaychamcong=date(2026, 10, 9)).trangthai, "NGHIPHEP")  # Ngày còn lại đã ghi.

    def test_khong_duyet_don_cua_nhan_vien_da_nghi_viec(self):  # Nghỉ việc sau khi gửi đơn.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 10, 8), date(2026, 10, 8), "Việc riêng", HOM_NAY)  # Đơn 1 ngày.
        NhanVien.objects.filter(pk=self.nv.pk).update(trangthai=False, ngaynghiviec=date(2026, 10, 6))  # Nghỉ việc.
        don = DonNghiPhep.objects.select_related("manv").get(pk=don.pk)  # Đọc lại đơn.
        with self.assertRaisesMessage(ValidationError, "nghỉ việc"):  # Bị chặn duyệt.
            services.duyet_don(don, self.ql)  # Thử duyệt.
        services.tu_choi_don(don, self.ql, "Nhân viên đã nghỉ việc")  # Vẫn từ chối được.

    def test_bang_cong_khong_tinh_sau_ngay_nghi_viec(self):  # Không hiện vắng hay ngày phép sau khi nghỉ.
        ChamCong.objects.create(manv=self.nv, ngaychamcong=date(2026, 10, 8), trangthai="NGHIPHEP")  # Phép sau ngày nghỉ.
        NhanVien.objects.filter(pk=self.nv.pk).update(trangthai=False, ngaynghiviec=date(2026, 10, 6))  # Nghỉ việc.
        nv = NhanVien.objects.get(pk=self.nv.pk)  # Đọc lại hồ sơ.
        dong = services.tao_bang_cong(2026, 10, [nv], hom_nay=date(2026, 10, 12))  # Dựng bảng công.
        self.assertTrue(dong and all(d.ngay <= date(2026, 10, 6) for d in dong))  # Chỉ đến ngày nghỉ việc.

    def test_ho_so_cu_nghi_viec_thieu_ngay_khong_bi_tinh_vang(self):  # trangthai=False, ngaynghiviec=None.
        NhanVien.objects.filter(pk=self.nv.pk).update(trangthai=False, ngaynghiviec=None)  # Hồ sơ cũ.
        nv = NhanVien.objects.get(pk=self.nv.pk)  # Đọc lại hồ sơ.
        dong = services.tao_bang_cong(2026, 9, [nv], hom_nay=HOM_NAY)  # Dựng bảng công.
        self.assertEqual([d for d in dong if d.trangthai == "VANGKHONGPHEP"], [])  # Không suy ra vắng.

    def test_thong_bao_chuyen_dung_duong_dan_co_that(self):  # Link thông báo phải mở được.
        from tai_khoan.models import ThongBao  # Bảng thông báo.
        self.client.force_login(self.u_nv)  # Đăng nhập nhân viên.
        self.client.post(reverse("cham_cong:check_in"))  # Check-in.
        tb = ThongBao.objects.get(nguoi_nhan=self.u_nv, loai="CHAM_CONG")  # Thông báo vừa tạo.
        self.assertEqual(tb.duong_dan, reverse("cham_cong:hom_nay"))  # Đúng route thật.
        self.assertEqual(self.client.get(tb.duong_dan).status_code, 200)  # Mở được.

    def test_tao_don_bao_quan_ly_khong_bao_nguoi_gui(self):  # Quản lý tự gửi đơn không nhận thông báo của chính mình.
        from tai_khoan.models import ThongBao  # Bảng thông báo.
        self.client.force_login(self.u_ql)  # Đăng nhập quản lý.
        self.client.post(reverse("cham_cong:tao_don"), {  # Quản lý gửi đơn.
            "maloaiphep": self.phep_nam.pk, "ngaybatdau": "2099-01-05", "ngayketthuc": "2099-01-05", "lydo": "Việc riêng",
        })  # Kết thúc gửi.
        self.assertFalse(ThongBao.objects.filter(nguoi_nhan=self.u_ql, loai="NGHI_PHEP").exists())  # Không tự nhận.

    def test_trang_quy_phep_tong_hop_bon_the(self):  # Bốn thẻ đầu trang quỹ phép.
        don = services.tao_don(self.nv, self.phep_nam, date(2026, 10, 6), date(2026, 10, 16), "Nghỉ dài", HOM_NAY)  # 11 ngày.
        services.duyet_don(don, self.ql)  # Đã dùng 11 → còn 1 ngày.
        DonNghiPhep.objects.create(  # Đơn chờ 2 ngày, vượt quỹ 1 ngày (tạo trực tiếp vì service chặn).
            manv=self.nv, maloaiphep=self.phep_nam, ngaybatdau=date(2026, 10, 20), ngayketthuc=date(2026, 10, 21),
            songaynghi=2, lydo="Việc riêng",
        )  # Kết thúc tạo đơn.
        hom_nay = timezone.localdate()  # View dùng ngày thật của máy.
        DonNghiPhep.objects.create(  # Quản lý đang nghỉ hôm nay (đã duyệt).
            manv=self.ql, maloaiphep=self.phep_nam, ngaybatdau=hom_nay, ngayketthuc=hom_nay + timedelta(days=1),
            songaynghi=2, lydo="Việc riêng", trangthai="DADUYET",
        )  # Kết thúc tạo đơn.
        DonNghiPhep.objects.create(  # Nhân viên sắp nghỉ sau 3 ngày (đã duyệt).
            manv=self.nv, maloaiphep=self.phep_nam, ngaybatdau=hom_nay + timedelta(days=3), ngayketthuc=hom_nay + timedelta(days=3),
            songaynghi=1, lydo="Việc riêng", trangthai="DADUYET",
        )  # Kết thúc tạo đơn.
        self.client.force_login(self.u_ql)  # Đăng nhập quản lý.
        ctx = self.client.get(reverse("cham_cong:quy_phep"), {"nam": 2026}).context  # Mở trang quỹ phép.
        self.assertEqual(ctx["dang_nghi_hom_nay"], 1)  # Một người đang nghỉ.
        self.assertEqual(ctx["sap_nghi_7_ngay"], 1)  # Một người sắp nghỉ.
        self.assertEqual(ctx["so_don_cho_duyet"], 1)  # Một đơn đang chờ duyệt.
        self.assertEqual(ctx["so_vuot_quy"], 1)  # Một người vượt quỹ.
        self.assertEqual(ctx["so_sap_het"], 1)  # Một người còn ≤ 2 ngày.
        loc = self.client.get(reverse("cham_cong:quy_phep"), {"nam": 2026, "loc": "vuot_quy"}).context  # Bấm thẻ Vượt quỹ.
        self.assertEqual([d["nv"] for d in loc["page_obj"]], [self.nv])  # Bảng chỉ còn người vượt quỹ.
        self.assertEqual(loc["so_vuot_quy"], 1)  # Số trên thẻ không đổi khi đang lọc.
        loc = self.client.get(reverse("cham_cong:quy_phep"), {"nam": 2026, "loc": "sap_het"}).context  # Bấm thẻ Sắp hết phép.
        self.assertEqual([d["nv"] for d in loc["page_obj"]], [self.nv])  # Bảng chỉ còn người sắp hết phép.
        self.assertTrue(self.client.get(reverse("cham_cong:duyet_don_list"), {"tu": "quy_phep"}).context["ve_quy_phep"])  # Bấm thẻ Đơn chờ duyệt: có nút Quay lại.
        self.assertFalse(self.client.get(reverse("cham_cong:duyet_don_list")).context["ve_quy_phep"])  # Mở từ menu: không có.
        ds = self.client.get(reverse("cham_cong:duyet_don_list"), {"trang_thai": "DADUYET", "nghi": "hom_nay"}).context  # Bấm thẻ Nghỉ phép hôm nay.
        self.assertEqual([d.manv for d in ds["page_obj"]], [self.ql])  # Chỉ người đang nghỉ hôm nay.
        ds = self.client.get(reverse("cham_cong:duyet_don_list"), {"trang_thai": "DADUYET", "nghi": "7_ngay"}).context  # Sắp nghỉ.
        self.assertEqual([d.manv for d in ds["page_obj"]], [self.nv])  # Chỉ người sắp nghỉ trong 7 ngày tới.

    # ---------- Phân quyền và xuất file ----------
    def test_nhan_vien_khong_vao_trang_quan_ly(self):  # BR1 UC-QL-3.01.
        self.client.force_login(self.u_nv)  # Đăng nhập nhân viên.
        for ten in ("bang_cham_cong", "xuat_bang_cham_cong", "duyet_don_list", "quy_phep"):  # Các trang quản lý.
            self.assertEqual(self.client.get(reverse(f"cham_cong:{ten}")).status_code, 403)  # Bị từ chối.

    def test_xuat_excel_khop_du_lieu_dang_loc(self):  # BR2 UC-QL-3.02.
        from openpyxl import load_workbook  # Đọc file Excel.
        services.check_in(self.nv, luc(8, 12))  # Một ngày đi làm.
        services.check_out(self.nv, luc(16, 45))  # Check-out.
        self.client.force_login(self.u_ql)  # Đăng nhập quản lý.
        phan_hoi = self.client.get(reverse("cham_cong:xuat_bang_cham_cong"), {"thang": 10, "nam": 2026, "trang_thai": "DILAM"})  # Xuất.
        ws = load_workbook(BytesIO(phan_hoi.content)).active  # Trang tính đầu tiên.
        hang = [list(r) for r in ws.iter_rows(min_row=5, values_only=True)]  # Các hàng dữ liệu.
        self.assertEqual(len(hang), 1)  # Chỉ đúng 1 bản ghi đang lọc.
        self.assertEqual((hang[0][0], hang[0][6], hang[0][7], hang[0][10]), ("NV005", 7.55, 12, "Đi làm"))  # Đúng nội dung.
