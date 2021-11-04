import datetime
from django.utils.timezone import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, DetailView

from daily.forms import IncidentForm
from daily.models import Schedule, Incident

def home(request):
    today_meds_schedule = Schedule.objects.order_by('-date0')[0]

    if request.method == 'POST':
        incident_form = IncidentForm(request.POST)
        if incident_form.is_valid():
            incident_form.save()

            return HttpResponseRedirect(reverse('home'))
    else:
        incident_form = IncidentForm(initial=Incident.now_data())

    recent_incidents = Incident.objects.order_by('-date0', '-time0')[:3]
    context = {
        'new_incident_form': incident_form,
        'recent_incidents': recent_incidents,
        'sched': today_meds_schedule,
    }
    return render(request, "daily/home.html", context=context)

def about(request):
    return render(request, "daily/about.html")

def contact(request):
    return render(request, "daily/contact.html")

class SchedListView(ListView):
    """Renders the schedules page, with a list of all schedules."""
    model = Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class SchedDetailView(DetailView):
    """Renders the slots page, with a list of all planned meds for a day."""
    model = Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
