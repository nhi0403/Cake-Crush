import os
import sys
import django

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tai_khoan.models import ThongBao


def seed_notifications():
    users = User.objects.all()
    if not users.exists():
        print("Chưa có User nào trong hệ thống.")
        return

    admin_users = users.filter(is_superuser=True)
    staff_users = users.filter(is_staff=True)
    quan_ly_set = (admin_users | staff_users).distinct()

    print(f"Đang tạo thông báo mẫu cho {users.count()} tài khoản...")

    # Thông báo mẫu cho quản lý/admin
    for u in quan_ly_set:
        ThongBao.objects.get_or_create(
            nguoi_nhan=u,
            tieu_de="Đơn xin nghỉ phép mới cần phê duyệt",
            defaults={
                "noi_dung": "Nhân viên Lê Thị Mai Anh vừa gửi đơn xin nghỉ phép 2 ngày.",
                "loai": ThongBao.LoaiThongBao.NGHI_PHEP,
                "duong_dan": "/quan-ly/nghi-phep/",
                "da_doc": False,
            }
        )
        ThongBao.objects.get_or_create(
            nguoi_nhan=u,
            tieu_de="Hợp đồng lao động sắp hết hạn",
            defaults={
                "noi_dung": "Hợp đồng của nhân viên Đỗ Quỳnh Như sắp hết hạn trong 15 ngày tới.",
                "loai": ThongBao.LoaiThongBao.HOP_DONG,
                "duong_dan": "/quan-ly/hop-dong/",
                "da_doc": False,
            }
        )
        ThongBao.objects.get_or_create(
            nguoi_nhan=u,
            tieu_de="Chào mừng đến với hệ thống Cake Crush HR",
            defaults={
                "noi_dung": "Hệ thống quản lý nhân sự Cake Crush đã sẵn sàng phục vụ công việc của bạn.",
                "loai": ThongBao.LoaiThongBao.HE_THONG,
                "duong_dan": "/dashboard/",
                "da_doc": True,
            }
        )

    # Thông báo mẫu cho toàn bộ nhân viên
    for u in users:
        ThongBao.objects.get_or_create(
            nguoi_nhan=u,
            tieu_de="Khóa đào tạo làm bánh lạnh mới",
            defaults={
                "noi_dung": "Khóa học 'Kỹ thuật trang trí bánh lạnh chuyên sâu' đã được bổ sung vào chương trình đào tạo.",
                "loai": ThongBao.LoaiThongBao.DAO_TAO,
                "duong_dan": "/dao-tao-cua-toi/",
                "da_doc": False,
            }
        )
        ThongBao.objects.get_or_create(
            nguoi_nhan=u,
            tieu_de="Nhắc nhở chấm công định kỳ",
            defaults={
                "noi_dung": "Đừng quên Check-in khi bắt đầu ca làm việc và Check-out trước khi ra về nhé!",
                "loai": ThongBao.LoaiThongBao.CHAM_CONG,
                "duong_dan": "/cham-cong/",
                "da_doc": False,
            }
        )

    print("Hoàn tất tạo thông báo mẫu thành công!")


if __name__ == '__main__':
    seed_notifications()
