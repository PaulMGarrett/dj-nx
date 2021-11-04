import re
from django.utils.timezone import datetime
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView, DetailView

from daily.models import Schedule

def home(request):
    return render(request, "daily/home.html")

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
