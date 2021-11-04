from django.contrib import admin
from daily.models import Drug, Tablet, Schedule, Dose


# Register your models here.

admin.site.register(Drug)
admin.site.register(Tablet)
admin.site.register(Schedule)
admin.site.register(Dose)
