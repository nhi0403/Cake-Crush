from django.urls import path
from . import views

urlpatterns = [
    path('', views.trang_chao_mung, name='trang_chu'),
    path('welcome/', views.trang_chao_mung, name='welcome'),
    path('login/', views.CakeCrushLoginView.as_view(), name='login'),
    path('logout/', views.CakeCrushLogoutView.as_view(), name='logout'),
    path('dashboard/', views.dieu_huong_dashboard, name='dashboard'),
    path('home/', views.dieu_huong_dashboard, name='home'),
    path('quan-ly/', views.trang_quan_ly, name='trang_quan_ly'),
    path('nhan-vien/', views.trang_nhan_vien, name='trang_nhan_vien'),
    
    # API và trang Thông báo
    path('api/thong-bao/', views.api_danh_sach_thong_bao, name='api_thong_bao'),
    path('api/thong-bao/<int:pk>/doc/', views.api_doc_mot_thong_bao, name='api_doc_mot_thong_bao'),
    path('api/thong-bao/doc-tat-ca/', views.api_doc_tat_ca_thong_bao, name='api_doc_tat_ca_thong_bao'),
    
    # API và trang Tìm kiếm
    path('api/tim-kiem/', views.api_tim_kiem_nhanh, name='api_tim_kiem_nhanh'),
    path('tim-kiem/', views.trang_tim_kiem, name='trang_tim_kiem'),
]
