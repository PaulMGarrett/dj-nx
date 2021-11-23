import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator

from nx import forms, models


class Link():
    earliest = datetime.date(year=2020, month=1, day=1)
    def __init__(self, datetime, text):
        self.dt = datetime
        self.text = text
    
    def url(self):
        return reverse('day', args=[self.dt.strftime("%Y%m%d")])

    def isValid(self):
        if self.dt < Link.earliest:
            return False
        if self.dt > datetime.date.today():
            return False
        return True


def home(request):
    yyyymmdd = int(datetime.date.today().strftime("%Y%m%d"))
    print(f"TODO replace today's date with earliest unfilled {yyyymmdd}")
    return HttpResponseRedirect(reverse('day', args=[yyyymmdd]))

def day(request, yyyymmdd):
    yyyy = yyyymmdd // 10000
    mmdd = yyyymmdd - 10000 * yyyy
    mm = mmdd // 100
    dd = mmdd - mm * 100
    try:
        current = datetime.date(year=yyyy, month=mm, day=dd)
    except:
        return HttpResponseRedirect(reverse('contact'))     # TODO error page?

    links = [
        Link(current - datetime.timedelta(days=30), "Previous month"),
        Link(current - datetime.timedelta(days=7), "Previous week"),
        Link(current - datetime.timedelta(days=1), "Previous day"),
        Link(current + datetime.timedelta(days=1), "Next day"),
        Link(current + datetime.timedelta(days=7), "Next week"),
        Link(current + datetime.timedelta(days=30), "Next month"),
    ]
    # TODO today, first incomplete, etc.

    med_schedule = None
    for sched in models.Schedule.objects.order_by('-date0'):
        med_schedule = sched
        if sched.date0 < current:
            break

    try:
        obs = models.Obs.objects.get(date0=current)
    except models.Obs.DoesNotExist:
        obs = models.Obs(date0=current)

    if request.method == 'POST':
        obs_form = forms.ObsForm(request.POST, instance=obs)
        if obs_form.is_valid():
            obs.save()

            return HttpResponseRedirect(reverse('day', args=[yyyymmdd]))
    else:
        obs_form = forms.ObsForm(initial=obs.initial_data())

    context = {
        'date1': current.strftime("%A %b %d %Y"),
        'navs': [lnk for lnk in links if lnk.isValid()],
        'sched': med_schedule,
        'new_obs_form': obs_form,
    }
    return render(request, "nx/day.html", context=context)

def about(request):
    return render(request, "nx/about.html")

def contact(request):
    return render(request, "nx/contact.html")

