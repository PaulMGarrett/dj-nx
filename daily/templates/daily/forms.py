from django.forms import ModelForm

from daily.models import *

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['date0', 'time0', 'comment']

class OedemaForm(ModelForm):
    class Meta:
        model = Oedema
        fields = ['date0', 'comment']

class ExerciseForm(ModelForm):
    class Meta:
        model = Oedema
        fields = ['date0', 'comment']

class BloodPressureForm(ModelForm):
    class Meta:
        model = BloodPressure
        fields = ['date0', 'time0', 'higher', 'lower', 'heart_rate']

