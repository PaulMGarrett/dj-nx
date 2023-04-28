import datetime
import io
import math
import traceback

from diet import models
from django.core.paginator import Paginator
from django.forms import formset_factory
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import DetailView, ListView


def foodlabel(request, pk):
    print(f"foodlabel/{pk} type {type(pk)}")
    food = models.FoodLabel.objects.first()
    context = {'food': food }
    return render(request, "diet/foodlabel.html", context=context)

def foodsearch(request, partial):
    result = ''
    for pk, name in [(1, 'Beef mince 5% fat'),
                     (2, 'Onion, large')]:
        result += f"{pk}###{name}|"
    return result

def home(request):
    return HttpResponseRedirect(reverse('foodlabel', args=[1])) 

def about(request):
    info = [f"{k}: {v}" for k, v in request.headers.items()]
    print(info)
    return render(request, "diet/about.html", context={'info': info})


def contact(request):
    return render(request, "diet/contact.html")


def admin(request):
   return HttpResponseRedirect(reverse('diet-admin').replace('diet/admin', 'admin/diet'))

