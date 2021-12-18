import datetime
import random
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator

from nx import forms, models


class Link():
    MAX_FUTURE_DAYS = 3
    earliest = datetime.date(year=2020, month=9, day=1)
    def __init__(self, datetime, text):
        self.dt = datetime
        self.text = text
    
    def url(self):
        return reverse('day', args=[self.dt.strftime("%Y%m%d")])

    def isValid(self):
        if self.dt < Link.earliest:
            return False
        if self.dt > (datetime.date.today() + datetime.timedelta(days=self.MAX_FUTURE_DAYS)):
            return False
        return True


def home(request):
    try:
        latest = models.Obs.objects.order_by('-date0')[0]
        to_use = latest.date0
        if not (latest.lbs == 0 or latest.am_higher == 0 or latest.am_lower == 0
                or latest.pm_higher == 0 or latest.pm_lower == 0):
            # this day is finished so start with the next one
            to_use += datetime.timedelta(days=1)
    except Exception as e:
        print(f"Exception: {e}")
        to_use = datetime.date.today()

    yyyymmdd = int(to_use.strftime("%Y%m%d"))
    return HttpResponseRedirect(reverse('day', args=[yyyymmdd]))

def day(request, yyyymmdd):
    try:
        current = models.toDate(yyyymmdd)
    except:
        return HttpResponseNotFound(f"Not a valid YYYYMMDD: '{yyyymmdd}'")

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
            print("valid form: " + str(obs_form))
            obs.save()

            return HttpResponseRedirect(reverse('day', args=[yyyymmdd]))
        else:
            print("form not valid: " + str(obs_form.errors))
    else:
        obs_form = forms.ObsForm(instance=obs)

    context = {
        'date1': current.strftime("%A %b %d %Y"),
        'navs': [lnk for lnk in links if lnk.isValid()],
        'sched': med_schedule,
        'new_obs_form': obs_form,
    }
    return render(request, "nx/day.html", context=context)

DoseFormSet = formset_factory(forms.DoseEditForm, extra=1)

def schedule(request, yyyymmdd):
    try:
        current = models.toDate(yyyymmdd)
        sched = models.Schedule.objects.get(date0=current)
    except:
        return HttpResponseNotFound(f"Not a valid YYYYMMDD: '{yyyymmdd}'")

    prev_doses = models.Dose.objects.filter(schedule=sched).order_by('slot', 'tablet')
    print(len(prev_doses), prev_doses[0])
    already_doses = list([{'tablet': d.tablet, 'slot': d.slot} for d in prev_doses])
    print(len(already_doses), already_doses[:4])
    if request.method == 'POST':
        print("handling POST")
        form_set = DoseFormSet(request.POST, initial=already_doses)
        # if form_set.has_changed():
        for f in form_set:
            print(f)
            if f.has_changed():
                print("has changed")
                f.save()
        # print(form_set.cleaned_data)
        for d in models.Dose.objects.filter(slot=''):
            print("removing no-slot doses")
            d.delete()
        # else:
        #     print(form_set.errors)

        print(f"now go back in and fetch again for {models.fromDate(current)}")
        return HttpResponseRedirect(reverse('schedule', args=[models.fromDate(current)]))
    else:
        print("handling GET")
        form_set = DoseFormSet(initial=already_doses)

    context = {
        'sched': sched,
        'doses_form': form_set,
    }
    return render(request, 'nx/schedule.html', context=context)

def schedules(request):
    scheds = models.Schedule.objects.order_by('-date0')
    paginator=Paginator(scheds, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        sched_form = forms.ScheduleForm(request.POST)
        if sched_form.is_valid():
            sched_form.save()

            added = sched_form.cleaned_data['date0']
            previous = models.Schedule.objects.filter(date0__lte=added).order_by('-date0')
            if len(previous) > 1:
                assert previous[0].date0 == added
                for dose in models.Dose.objects.filter(schedule=previous[1]):
                    dose.pk = None
                    dose._state.adding = True
                    dose.schedule = previous[0]
                    dose.save()
            return HttpResponseRedirect(reverse('schedule', args=[models.fromDate(added)]))
    else:
        sched_form = forms.ScheduleForm()

    context = {
        'page_obj': page_obj,
        'new_schedule_form': sched_form,
    }
    return render(request, "nx/schedules.html", context=context)

def charts(request):
    return render(request, 'nx/charts.html', context={})

def chart_data(request, cname):
    obs = models.Obs.objects.order_by('date0')
    if len(obs) > 90:
        obs = obs[-90:]
    dates = []
    if cname == 'lbs':
        lbs = []
        # wt = 238.1
        # for i in range(60, 0, -1):
        #     wt += 0.1 * random.randrange(-45, +40)
        #     if wt == 237:
        #         continue
        #     lbs.append(wt)
        #     dates.append((datetime.date.today() - datetime.timedelta(days=i)).strftime('%b %d'))
        for ob in obs:
            if ob.lbs:
                dates.append(ob.date0.strftime('%b %d'))
                lbs.append(float(ob.lbs))

        return JsonResponse({
            'options': {
                'title': {'text': f'Weight (pounds)', 'display': True},
                'type': 'line',
                'scales': {
                    'yAxes': [{
                        'ticks': {
                            'fontSize': 28
                        }
                    }]
                },
                },
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Weight (lb)',
                    'borderColor': '#00ff00',
                    'borderWidth': 5,
                    'fill': False,
                    'tension': 0,
                    'data': lbs,
                }]
            },
        })
    if cname == 'kgs':
        kgs = []
        for ob in obs:
            if ob.kgs:
                dates.append(ob.date0.strftime('%b %d'))
                kgs.append(float(ob.kgs))

        return JsonResponse({
            'options': {
                'title': {'text': f'Weight (kilos)', 'display': True},
                'type': 'line',
                'scales': {
                    'yAxes': [{
                        'ticks': {
                            'fontSize': 28
                        }
                    }]
                },
                },
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Weight (Kg)',
                    'borderColor': '#00ff00',
                    'borderWidth': 5,
                    'fill': False,
                    'tension': 0,
                    'data': kgs,
                }]
            },
        })
    if cname.startswith('bp-'):
        am = cname.endswith('am')
        systolic = []
        diastolic = []
        # s = 100
        # d = 75
        # for i in range(60, 0, -1):
        #     s += random.randrange(-8, +8)
        #     while s < 75: s += 5
        #     while s > 120: s -= 3
        #     d += random.randrange(-6, +6)
        #     while s < 53: s += 4
        #     while s > 81: s -= 2
        #     if (s - d) < 5:
        #         continue
        #     dates.append((datetime.date.today() - datetime.timedelta(days=i)).strftime('%b %d'))
        #     systolic.append(s)
        #     diastolic.append(d)
        for ob in obs:
            if am:
                if ob.am_higher and ob.am_lower:
                    dates.append(ob.date0.strftime('%b %d'))
                    systolic.append(int(ob.am_higher))
                    diastolic.append(int(ob.am_lower))
            else:
                if ob.pm_higher and ob.pm_lower:
                    dates.append(ob.date0.strftime('%b %d'))
                    systolic.append(int(ob.pm_higher))
                    diastolic.append(int(ob.pm_lower))
        # adjust for stacked bar chart
        for i in range(len(systolic)):
            systolic[i] -= diastolic[i]

        return JsonResponse({
            
            'options': {
                'title': {'text': f"BP ({'morning' if am else 'afternoon'})", 'display': True},
                'scales': {
                    'yAxes': [{ 'stacked': True,
                        'ticks': { 'fontSize': 28 }
                        }],
                'scales': {
                    'yAxes': [{
                        'ticks': {
                            'fontSize': 28
                        }
                    }]
                },
                    'xAxes': [{
                        'barPercentage': 0.2,
                        'stacked': True,
                        'ticks': { 'maxRotation': 90, 'minRotation': 90 }
                    }],
                }
            },
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Diastolic',
                    'backgroundColor': '#ffffff',
                    'data': diastolic
                },
                {
                    'label': 'Systolic',
                    'backgroundColor': '#ff8080' if am else '#4040ff',
                    'data': systolic
                }]
            },
        })
    if cname == 'bp':
        a_systolic = []
        a_diastolic = []
        p_systolic = []
        p_diastolic = []
        for ob in obs:
            dates.append(ob.date0.strftime('%b %d'))
            if ob.am_higher and ob.am_lower:
                a_systolic.append(int(ob.am_higher))
                a_diastolic.append(int(ob.am_lower))
            else:
                # try and draw a zero-height bar to show no reading taken
                a_systolic.append(100)
                a_diastolic.append(100)
            if ob.pm_higher and ob.pm_lower:
                p_systolic.append(int(ob.pm_higher))
                p_diastolic.append(int(ob.pm_lower))
            else:
                # try and draw a zero-height bar to show no reading taken
                p_systolic.append(100)
                p_diastolic.append(100)
        # adjust for stacked bar chart
        for i in range(len(dates)):
            a_systolic[i] -= a_diastolic[i]
            p_systolic[i] -= p_diastolic[i]

        return JsonResponse({
            
            'options': {
                'title': {'text': f"Blood Pressure", 'display': True},
                'scales': {
                    'yAxes': [{ 'stacked': True,
                        'ticks': { 'fontSize': 28 }
                        }],
                    'xAxes': [{
                        'barPercentage': 0.2,
                        'stacked': True,
                        'ticks': { 'maxRotation': 90, 'minRotation': 90 }
                    }],
                }
            },
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Diastolic',
                    'backgroundColor': '#ffffff',
                    'data': a_diastolic
                },
                {
                    'label': 'Systolic',
                    'backgroundColor': '#ff8080',
                    'data': a_systolic
                }]
            },
        })


def about(request):
    return render(request, "nx/about.html")

def contact(request):
    return render(request, "nx/contact.html")

def admin(request):
   return HttpResponseRedirect(reverse('nx-admin').replace('nx/admin', 'admin/nx'))

