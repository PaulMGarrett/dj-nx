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
    recent_comments = models.Comment.objects.order_by('-date0', '-time0')[:3]

    context = {
        'recent_comments': recent_comments,
        'sched': today_meds_schedule,
    }
    return render(request, "daily/home.html", context=context)

def about(request):
    return render(request, "daily/about.html")

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


def comments(request):
    comments = models.Comment.objects.order_by('-date0', '-time0')
    paginator=Paginator(comments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        comment_form = forms.CommentForm(request.POST)
        if comment_form.is_valid():
            comment_form.save()

            return HttpResponseRedirect(reverse('comments'))
    else:
        comment_form = forms.CommentForm(initial=models.Comment.initial_data())

    context = {
        'page_obj': page_obj,
        'new_comment_form': comment_form,
    }
    return render(request, "daily/comments.html", context=context)

def contact(request):
    return render(request, "daily/contact.html")

def exercise(request):
    exeercise = models.Exercise.objects.order_by('-date0')
    paginator=Paginator(exeercise, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        exercise_form = forms.ExerciseForm(request.POST)
        if exercise_form.is_valid():
            exercise_form.save()

            return HttpResponseRedirect(reverse('exercise'))
    else:
        exercise_form = forms.ExerciseForm(initial=models.Exercise.initial_data())

    context = {
        'page_obj': page_obj,
        'new_exercise_form': exercise_form,
    }
    return render(request, "daily/exercise.html", context=context)

def oedema(request):
    oedema = models.Oedema.objects.order_by('-date0')
    paginator=Paginator(oedema, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        oedema_form = forms.OedemaForm(request.POST)
        if oedema_form.is_valid():
            oedema_form.save()

            return HttpResponseRedirect(reverse('oedema'))
    else:
        oedema_form = forms.OedemaForm(initial=models.Oedema.initial_data())

    context = {
        'page_obj': page_obj,
        'new_oedema_form': oedema_form,
    }
    return render(request, "daily/oedema.html", context=context)


def weight(request):
    weights = models.Weight.objects.order_by('-date0')
    paginator=Paginator(weights, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        weight_form = forms.WeightForm(request.POST)
        if weight_form.is_valid():
            weight_form.save()

            return HttpResponseRedirect(reverse('weight'))
    else:
        weight_form = forms.WeightForm(initial=models.Weight.initial_data())

    context = {
        'page_obj': page_obj,
        'new_weight_form': weight_form,
    }
    return render(request, "daily/weight.html", context=context)


# View classes ---------------------

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

