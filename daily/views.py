import datetime
from django.utils.timezone import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator

from daily import forms, models

def home(request):
    today_meds_schedule = models.Schedule.objects.order_by('-date0')[0]
    recent_incidents = models.Incident.objects.order_by('-date0', '-time0')[:3]

    context = {
        'recent_incidents': recent_incidents,
        'sched': today_meds_schedule,
    }
    return render(request, "daily/home.html", context=context)

def about(request):
    return render(request, "daily/about.html")

def contact(request):
    return render(request, "daily/contact.html")

def incidents(request):
    incidents = models.Incident.objects.order_by('-date0', '-time0')
    paginator=Paginator(incidents, 20)

    if request.method == 'POST':
        incident_form = forms.IncidentForm(request.POST)
        if incident_form.is_valid():
            incident_form.save()

            return HttpResponseRedirect(reverse('incidents'))
    else:
        incident_form = forms.IncidentForm(initial=models.Incident.initial_data())
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

    recent_incidents = models.Incident.objects.order_by('-date0', '-time0')[:3]
    context = {
        'page_obj': page_obj,
        'new_incident_form': incident_form,
    }
    return render(request, "daily/incidents.html", context=context)

def bp(request):
    bps = models.BloodPressure.objects.order_by('-date0', '-time0')
    paginator=Paginator(bps, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        bp_form = forms.BloodPressureForm(request.POST)
        if bp_form.is_valid():
            bp_form.save()

            return HttpResponseRedirect(reverse('bp'))
    else:
        bp_form = forms.BloodPressureForm(initial=models.BloodPressure.initial_data())

    context = {
        'page_obj': page_obj,
        'new_bp_form': bp_form,
    }
    return render(request, "daily/bp.html", context=context)


class SchedListView(ListView):
    """Renders the schedules page, with a list of all schedules."""
    model = models.Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class SchedDetailView(DetailView):
    """Renders the slots page, with a list of all planned meds for a day."""
    model = models.Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
