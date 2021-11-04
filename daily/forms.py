from django.forms import ModelForm

from daily.models import Incident

class IncidentForm(ModelForm):
    class Meta:
        model = Incident
        fields = ['date0', 'time0', 'description']

