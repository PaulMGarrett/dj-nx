from django.urls import path
from nx import views

urlpatterns = [
    path("", views.home, name="home"),
    path('<int:yyyymmdd>/', views.day, name='day'),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]