from django.contrib import admin
from django.urls import path
from diet import views

urlpatterns = [
    path('', views.home, name='home'),
    path('foodlabel/<int:pk>', views.foodlabel, name='foodlabel'),
    path('foodsearch/<slug:partial>', views.foodsearch, name='foodsearch'),
    path("about/", views.about, name='about'),
    path("contact/", views.contact, name='contact'),
    path("admin/", views.admin, name='diet-admin'),
]