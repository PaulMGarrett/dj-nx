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
    note = None
    for sched in models.Schedule.objects.order_by('-date0'):
        med_schedule = sched
        if sched.date0 <= current:
            if sched.date0 == current:
                note = sched.reason
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
        'sched_note': note,
        'new_obs_form': obs_form,
    }
    return render(request, "nx/day.html", context=context)

def events(request):
    """ Just days with events noted - not paged yet """
    class TimePoint():
        def __init__(self, ob):
            self.day = ob.date0.strftime("%a %d %b %Y")
            self.notes = ''
            for e in ob.events.splitlines():
                if not e.strip():
                    continue
                if 'dizzy' in e.lower():
                    continue
                if self.notes: self.notes += ' ; '
                self.notes += e.strip()

    events = []
    for ob in models.Obs.objects.order_by('-date0'):
        t = TimePoint(ob)
        if t.notes:
            events.append(t)

    context = {
        'events': events,
    }
    return render(request, 'nx/events.html', context=context)


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


class ObsChart():
    DEFAULT_COLOURS = ['ff4040', '40ff40', '4040ff', '808080']

    def __init__(self, slug, title, chart_type, data_labels, ob_reader,
                 stacked=False, colour=None,
                 xFontSize=14, yFontSize=20,
                 lines=None):
        """
        slug: alphanumeric chart id (goes into variable names)
        title: chart title text
        chart_type: 'bar' or 'line'
        data_labels: text for each dataset plotted
        ob_reader: given an 'Obs' record, return list of values to chart, or None
        stacked: for bar graphs, draw one above the other (second colour white)
        colour: line or bar colour, or array of colours, or None for standard set
        lines: annotation details for extra lines to be drawn
        """
        self.slug = slug
        self.title = title
        self.chart_type = chart_type
        self.data_labels = data_labels
        self.ob_reader = ob_reader
        self.stacked = stacked
        if isinstance(colour, list):
            self.data_colours = colour
        elif isinstance(colour, str) and len(self.data_labels) == 2 and self.stacked:
                self.data_colours = ['#ffffff', colour]
        elif colour is None:
            self.data_colours = ObsChart.DEFAULT_COLOURS[:len(self.data_labels)]
        else:
            self.data_colours = [colour]
        self.xFontSize = xFontSize
        self.yFontSize = yFontSize
        self.ann_lines = lines

    def get_annotations(self):
        ann_list = []
        ann_id = 0
        if self.ann_lines:
            for line in self.ann_lines:
                d = {'type': 'line',
                     'borderColor': '#80ff80',
                     'borderWidth': 2,
                     'mode': 'horizontal',
                     'scaleID': 'y-axis-0',
                }
                if isinstance(line, int):
                    d['value'] = line
                else:
                    d.update(line)
                ann_id += 1
                d.update(id='line%d' % ann_id)
                ann_list.append(d)
        if ann_list:
            return {'annotations': ann_list}
        else:
            return None

    def chart_div(self):
        return f"""
<div class="chart-{self.chart_type}">
  <canvas id="chart_{self.slug}"></canvas>
  <script>
    let ctxt_{self.slug} = document.getElementById("chart_{self.slug}").getContext("2d");
    let chart_{self.slug} = new Chart(ctxt_{self.slug}, {{
      type: "{self.chart_type}"
    }});
  </script>
</div>
"""

    def chart_load(self):
        return f"  loadChart(chart_{self.slug}, `/nx/chart-data/{self.slug}`);\n"

    def json_response(self):
        dsets = []
        for i, lbl in enumerate(self.data_labels):
            print(f"data[{i}] {lbl}")
            dset = {'label': lbl, 'data': []}
            if self.chart_type == 'line':
                dset.update(borderColor=self.data_colours[i],
                            borderWidth=5, fill=False, tension=0)
            elif self.chart_type == 'bar':
                dset.update(backgroundColor=self.data_colours[i],
                            barPercentage=0.6)
            else:
                print(f"Chart type {self.chart_type} not handled")
            dsets.append(dset)
        print(repr(dsets))
        resp = {
            'options': {
                'title': {'text': self.title, 'display': True},
                'type': self.chart_type,
                'scales': {
                    'xAxes': [{
                        'ticks': {
                            'fontSize': self.xFontSize,
                            'maxRotation': 90,
                            'minRotation': 90,
                        },
                    }],
                    'yAxes': [{
                        'stacked': self.stacked,
                        'ticks': {
                            'fontSize': self.yFontSize,
                        },
                    }],
                },
            },
            'data': {
                'labels': [],
                'datasets': dsets,
            },
        }
        
        ann = self.get_annotations()
        if ann:
            resp['options'].setdefault('plugins', {})['annotation'] = ann

        return resp

AllCharts = [
    ObsChart('lbs', "Weight (pounds)", 'line', ["Weight (lb)"],
             lambda ob: [ob.lbs] if ob.lbs else None,
             colour='#40ff40'),
    ObsChart('kgs', "Weight (kilos)", 'line', ["Weight (kg)"],
             lambda ob: [ob.kgs] if ob.kgs else None,
             colour='#008080'),
    ObsChart('bpam', "Blood Pressure (morning)", 'bar', ["Diastolic", "Systolic"],
             lambda ob: [int(ob.am_lower), int(ob.am_higher) - int(ob.am_lower)] if ob.am_higher and ob.am_lower else None,
             colour='#ff4040', stacked=True, lines=[100]),
    ObsChart('bppm', "Blood Pressure (afternoon)", 'bar', ["Diastolic", "Systolic"],
             lambda ob: [int(ob.pm_lower), int(ob.pm_higher) - int(ob.pm_lower)] if ob.pm_higher and ob.pm_lower else None,
             colour='#4040ff', stacked=True, lines=[80, 100, 120]),
]

def chart_data(request, cname, days=90):
    cobj = list([c for c in AllCharts if c.slug == cname])
    if len(cobj) == 1:
        cobj = cobj[0]
    else:
        return HttpResponseNotFound()
    
    resp = cobj.json_response()
    # the response should contain all the options, title text etc. - just add data
    obs = models.Obs.objects.order_by('date0')
    if len(obs) > days:
        obs = obs[-days:]
    for ob in obs:
        row = cobj.ob_reader(ob)
        if row:
            resp['data']['labels'].append(ob.date0.strftime('%b %d'))
            for i, v in enumerate(row):
                resp['data']['datasets'][i]['data'].append(v)

    return JsonResponse(resp)

def charts(request):
    context = {
        'cobjs': AllCharts,
    }
    return render(request, 'nx/charts.html', context=context)


def about(request):
    return render(request, "nx/about.html")

def contact(request):
    return render(request, "nx/contact.html")

def admin(request):
   return HttpResponseRedirect(reverse('nx-admin').replace('nx/admin', 'admin/nx'))

