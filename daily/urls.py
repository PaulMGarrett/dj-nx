from django.urls import path
from daily import models, views

scheds_list_view = views.SchedListView.as_view(
    queryset=models.Schedule.objects.order_by("-date0"),
    context_object_name="schedule_list",
    template_name="daily/schedules.html",
)

sched_detail_view = views.SchedDetailView.as_view(
    context_object_name="sched",
    template_name="daily/slots.html",
)

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("schedules/", scheds_list_view, name="schedules"),
    path("schedules/<int:pk>/", sched_detail_view, name="slots"),
    path('comments/', views.comments, name='comments'),
    path('oedema/', views.oedema, name='oedema'),
    path('exercise/', views.exercise, name='exercise'),
    path('bp/', views.bp, name='bp'),
    path('weight/', views.weight, name='weight'),
]
