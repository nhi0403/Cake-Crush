from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse

from .models import ThongBao
from .helpers import tao_thong_bao, thong_bao_quan_ly, thong_bao_nhan_vien
from .views import CakeCrushLoginView

User = get_user_model()


class ThongBaoTests(TestCase):
    """Kiểm thử mô hình ThongBao và các hàm tiện ích thông báo."""

    def setUp(self):
        self.user_admin = User.objects.create_superuser(
            username="admin_test", password="password123", email="admin@test.com"
        )
        self.user_staff = User.objects.create_user(
            username="staff_test", password="password123", is_staff=True
        )
        self.user_nv = User.objects.create_user(
            username="nv_test", password="password123"
        )

    def test_thong_bao_str(self):
        tb = ThongBao.objects.create(
            nguoi_nhan=self.user_nv,
            tieu_de="Thông báo kiểm tra",
            loai=ThongBao.LoaiThongBao.HE_THONG,
        )
        self.assertIn("Thông báo kiểm tra", str(tb))
        self.assertIn("nv_test", str(tb))
        self.assertFalse(tb.da_doc)

    def test_tao_thong_bao_don_le(self):
        created = tao_thong_bao(
            self.user_nv,
            tieu_de="Khóa học mới",
            noi_dung="Bạn đã được phân công",
            loai=ThongBao.LoaiThongBao.DAO_TAO,
            duong_dan="/dao-tao/",
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].nguoi_nhan, self.user_nv)
        self.assertEqual(created[0].loai, ThongBao.LoaiThongBao.DAO_TAO)

    def test_thong_bao_quan_ly(self):
        created = thong_bao_quan_ly(
            tieu_de="Đơn nghỉ phép mới",
            noi_dung="Có đơn nghỉ phép cần duyệt",
            loai=ThongBao.LoaiThongBao.NGHI_PHEP,
        )
        # Gửi cho cả admin và staff (2 người)
        self.assertEqual(len(created), 2)
        nguoi_nhan_ids = {tb.nguoi_nhan.id for tb in created}
        self.assertIn(self.user_admin.id, nguoi_nhan_ids)
        self.assertIn(self.user_staff.id, nguoi_nhan_ids)

    def test_login_redirect_url(self):
        factory = RequestFactory()

        # Quản lý/Admin vào trang_quan_ly
        request_admin = factory.get("/login/")
        request_admin.user = self.user_admin
        view_admin = CakeCrushLoginView()
        view_admin.request = request_admin
        self.assertEqual(view_admin.get_success_url(), reverse("trang_quan_ly"))

        # Nhân viên thường vào trang_nhan_vien
        request_nv = factory.get("/login/")
        request_nv.user = self.user_nv
        view_nv = CakeCrushLoginView()
        view_nv.request = request_nv
        self.assertEqual(view_nv.get_success_url(), reverse("trang_nhan_vien"))
