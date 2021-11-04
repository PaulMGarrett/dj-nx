from django.urls import path
from daily import views
from daily.models import Dose, Schedule

scheds_list_view = views.SchedListView.as_view(
    queryset=Schedule.objects.order_by("-date0"),
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
]