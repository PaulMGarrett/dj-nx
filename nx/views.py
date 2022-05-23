import datetime
import io
import math
import traceback

from django.core.paginator import Paginator
from django.forms import formset_factory
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import DetailView, ListView
from PIL import Image, ImageDraw, ImageFont

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


def about(request):
    return render(request, "nx/about.html")


def contact(request):
    return render(request, "nx/contact.html")


def admin(request):
   return HttpResponseRedirect(reverse('nx-admin').replace('nx/admin', 'admin/nx'))


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
            obs.save()

            return HttpResponseRedirect(reverse('day', args=[yyyymmdd]))
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
    already_doses = list([{'tablet': d.tablet, 'slot': d.slot} for d in prev_doses])
    if request.method == 'POST':
        form_set = DoseFormSet(request.POST, initial=already_doses)
        # if form_set.has_changed():
        for f in form_set:
            if f.has_changed():
                f.save()
        for d in models.Dose.objects.filter(slot=''):
            d.delete()

        return HttpResponseRedirect(reverse('schedule', args=[models.fromDate(current)]))
    else:
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
                 lines=None, days=60, smooth=0):
        """
        slug: alphanumeric chart id (goes into variable names)
        title: chart title text
        chart_type: 'bar' or 'line'
        data_labels: text for each dataset plotted
        ob_reader: given an 'Obs' record, return list of values to chart, or None
        stacked: for bar graphs, draw one above the other (second colour white)
        colour: line or bar colour, or array of colours, or None for standard set
        lines: annotation details for extra lines to be drawn
        days: how many (most recent) days to show
        smooth: how many days for rolling average (0 for none)
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
        self.days = int(days)
        self.smooth=smooth

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
        return f"  loadChart(chart_{self.slug}, `/nx/chart-data/{self.slug}?days={self.days}&smooth={self.smooth}`);\n"

    def json_response(self):
        dsets = []
        for i, lbl in enumerate(self.data_labels):
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
             lambda ob: [ob.lbs] if float(ob.lbs) else None,
             colour='#40ff40', days=60),
    ObsChart('kgs', "Weight (kilos)", 'line', ["Weight (kg)"],
             lambda ob: [ob.kgs] if float(ob.kgs) else None,
             colour='#008080', days=60),
    ObsChart('bpam', "Blood Pressure (morning)", 'bar', ["Diastolic", "Systolic"],
             lambda ob: [int(ob.am_lower), int(ob.am_higher) - int(ob.am_lower)] if (
                            ob.am_higher and ob.am_lower and
                            int(ob.am_higher) and int(ob.am_lower) and
                            int(ob.am_higher) > int(ob.am_lower)) else None,
             colour='#ff4040', stacked=True, lines=[100]),
    ObsChart('bppm', "Blood Pressure (afternoon)", 'bar', ["Diastolic", "Systolic"],
             lambda ob: [int(ob.pm_lower), int(ob.pm_higher) - int(ob.pm_lower)] if (
                            ob.pm_higher and ob.pm_lower and
                            int(ob.pm_higher) and int(ob.pm_lower) and
                            int(ob.pm_higher) > int(ob.pm_lower)) else None,
             colour='#4040ff', stacked=True, lines=[80, 100, 120]),
    ObsChart('lbhist', "Weight (smooth)", 'line', ["Weight (lb)"],
             lambda ob: [ob.lbs] if float(ob.lbs) else None,
             colour='#40ff40', days=500, smooth=10),
]

def chart_data(request, cname):
    cobj = list([c for c in AllCharts if c.slug == cname])
    if len(cobj) == 1:
        cobj = cobj[0]
    else:
        return HttpResponseNotFound()
    
    days = int(request.GET.get('days', 60))
    smooth = int(request.GET.get('smooth', 10 if cname == 'lbhist' else 0))
    print(f"days={days} smooth={smooth}")

    resp = cobj.json_response()
    # the response should contain all the options, title text etc. - just add data
    obs = models.Obs.objects.order_by('date0')
    if len(obs) > days:
        obs = obs[len(obs) - days:]
    # prev_row = None
    recent = []
    for ob in obs:
        try:
            row = cobj.ob_reader(ob)
        except:
            traceback.print_exc()
            continue
        if not row:
            continue
    
        if smooth:
            recent.append(row)
            if len(recent) < smooth:
                continue
            while len(recent) > smooth: recent.pop(0)
            for i in range(len(row)):
                row[i] = sum([float(x[i]) for x in recent]) / len(recent)
        for i, v in enumerate(row):
            resp['data']['datasets'][i]['data'].append(v)
        resp['data']['labels'].append(ob.date0.strftime('%b %d'))
        #     prevRow = row
        # elif prev_row:
        #     resp['data']['labels'].append(ob.date0.strftime('%b %d'))
        #     for i, v in enumerate(prev_row):
        #         resp['data']['datasets'][i]['data'].append(v)


    return JsonResponse(resp)

def charts(request):
    context = {
        'cobjs': AllCharts,
    }
    return render(request, 'nx/charts.html', context=context)

class ChartAttrs():
    bg = '#fff'
    margin=15
    bp_margins=5
    bp_width=10
    bp_sep=5
    bp_am='#f22'
    bp_pm='#22f'
    bp_range=(50,130,10)
    bp_height=4
    bp_offset=65
    kilos=True
    wt_range=(105, 109, 1)
    wt_color='#0f0'
    wt_height=50
    wt_offset=450
    wt_target=101
    x_axis_pos=50
    x_axis_font=14
    days = 28
    y_axis_pos = 35
    y_axis_font=16

    @property
    def day_width(self):
        return 1 + self.bp_width * 2 + self.bp_sep + self.bp_margins * 2

    @property
    def width(self):
        return self.day_width * (1 + self.days) + 1 + self.y_axis_pos + 1

    @property
    def height(self):
        def range(r, h, ofs):
            return ofs + h * (r[1] - r[0] + 1)
        return self.x_axis_pos + 1 + max(range(self.wt_range, self.wt_height, self.wt_offset),
                                         range(self.bp_range, self.bp_height, self.bp_offset))


def combo_chart(request):
    """Draw a chart ourselves via PNG image below."""
    chart = ChartAttrs()
    context = {
        'width': chart.width,
        'height': chart.height,
    }
    return render(request, 'nx/chart.html', context=context)

def combo_chart_png(request):
    chart = ChartAttrs()
    img = Image.new("RGB", (chart.width,chart.height), chart.bg)
    draw = ImageDraw.Draw(img)
    obs = models.Obs.objects.order_by('-date0')
    start_day = obs[0].date0
    end_day = start_day - datetime.timedelta(days=chart.days)
    # X axis
    font = ImageFont.truetype("Comic Sans MS.ttf", chart.x_axis_font)
    day_x = {}
    for d in range(1, 1 + chart.days):
        day = end_day + datetime.timedelta(days=d)
        x = d * chart.day_width + chart.y_axis_pos
        day_x[day.strftime('%Y-%m-%d')] = x
        draw.line([(x, chart.height - chart.margin), (x, chart.margin)], fill='#eee')
        day_num = day.day
        lbl = f"{day_num}"
        draw.text((x - chart.day_width / 2, chart.height - chart.x_axis_pos + 2), lbl, fill='#000', anchor='ma', font=font)
        if day_num == 1 or (d == 1 and day_num < 15):
            draw.text((x - chart.day_width / 2, chart.height - chart.x_axis_pos + 2 + chart.x_axis_font * 1.2),
                      day.strftime("%b"), fill='#000', anchor='la', font=font)
        elif (day + datetime.timedelta(days=1)).day == 1 or (d == chart.days + 1 and day_num > 15):
            draw.text((x - chart.day_width / 2, chart.height - chart.x_axis_pos + 2 + chart.x_axis_font * 1.2),
                      day.strftime("%b"), fill='#000', anchor='ra', font=font)

    draw.line([(chart.y_axis_pos, chart.height - chart.x_axis_pos),
               (chart.width - chart.margin, chart.height - chart.x_axis_pos)], fill='#000')

    # Y axis
    def bp_y(bp):
        return chart.height - chart.x_axis_pos - chart.bp_offset - (bp - chart.bp_range[0]) * chart.bp_height
    def wt_y(wt):
        return chart.height - chart.x_axis_pos - chart.wt_offset - (wt - chart.wt_range[0]) * chart.wt_height

    for n in range(chart.bp_range[0], chart.bp_range[1] + 1, chart.bp_range[2]):
        draw.text((chart.y_axis_pos - 2, bp_y(n)), str(n), font=font, fill='#000', anchor='rm')

    for n in range(chart.wt_range[0], chart.wt_range[1] + 1, chart.wt_range[2]):
        draw.text((chart.y_axis_pos - 2, wt_y(n)), str(n), font=font, fill='#080', anchor='rm')
        draw.line([(chart.y_axis_pos, wt_y(n)), (chart.width - chart.margin, wt_y(n))], fill='#ddd')

    draw.line([(chart.y_axis_pos, chart.height - chart.x_axis_pos),
               (chart.y_axis_pos, chart.margin)], fill='#222')
    draw.line([(chart.y_axis_pos, bp_y(80)), (chart.width - chart.margin, bp_y(80))], fill='#777')
    draw.line([(chart.y_axis_pos, bp_y(120)), (chart.width - chart.margin, bp_y(120))], fill='#777')

    weight_line = []
    for ob in obs:
        if ob.date0 <= end_day:
            break
        x = day_x[ob.date1] - chart.day_width / 2
        if ob.am_higher and ob.am_lower:
            draw.rectangle((x - chart.bp_sep / 2 - chart.bp_width, bp_y(ob.am_higher), x - chart.bp_sep / 2, bp_y(ob.am_lower)),
                           outline='#eee', fill=chart.bp_am)
        if ob.pm_higher and ob.pm_lower:
            draw.rectangle((x + chart.bp_sep / 2, bp_y(ob.pm_higher), x + chart.bp_sep / 2 + chart.bp_width, bp_y(ob.pm_lower)),
                           outline='#eee', fill=chart.bp_pm)
        if ob.kilos or ob.pounds:
            weight_line.append((x, wt_y(float(ob.kgs))))

    draw.line(weight_line, fill=chart.wt_color, width=4)

    draw.line([(chart.y_axis_pos, bp_y(100)),
               (chart.width - chart.margin, bp_y(100))], fill='#333', width=2)

    png_buffer = io.BytesIO()
    img.save(png_buffer, "PNG")
    png_buffer.seek(0)
    response = FileResponse(png_buffer)
    return response
