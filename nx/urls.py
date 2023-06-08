from django.contrib import admin
from django.urls import path
from nx import views

urlpatterns = [
    path('', views.home, name='home'),
    path('day1/', views.day1, name='day1'),
    path('<int:yyyymmdd>/', views.day, name='day'),
    path('schedules/', views.schedules, name='schedules'),
    path('schedules/<int:yyyymmdd>/', views.schedule, name='schedule'),
    path('chart-data/<slug:cname>', views.chart_data, name='chartData'),
    path('charts/', views.charts, name='charts'),
    path('events/', views.events, name='events'),
    path('meds/<int:yyyymmdd>', views.meds, name='meds'),
    path("about/", views.about, name='about'),
    path("contact/", views.contact, name='contact'),
    path("admin/", views.admin, name='nx-admin'),
    path('chart.png', views.combo_chart_png, name='combo_chart_png'),
    path('chart.html', views.combo_chart, name='combo_chart'),
]
