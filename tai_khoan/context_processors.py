from .models import ThongBao


def thong_bao_context(request):
    """Cung cấp số lượng thông báo chưa đọc cho mọi template kế thừa base.html."""
    if request.user.is_authenticated:
        try:
            so_chua_doc = ThongBao.objects.filter(
                nguoi_nhan=request.user, da_doc=False
            ).count()
            return {"so_thong_bao_chua_doc": so_chua_doc}
        except Exception:
            return {"so_thong_bao_chua_doc": 0}
    return {"so_thong_bao_chua_doc": 0}
