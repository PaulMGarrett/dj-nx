from django.forms import ModelForm

from daily.models import Incident, BloodPressure

class IncidentForm(ModelForm):
    class Meta:
        model = Incident
        fields = ['date0', 'time0', 'description']

class BloodPressureForm(ModelForm):
    class Meta:
        model = BloodPressure
        fields = ['date0', 'time0', 'higher', 'lower', 'heart_rate']

