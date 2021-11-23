from django.forms import ModelForm, ValidationError

from daily.models import *

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['date0', 'time0', 'description']

class FatigueForm(ModelForm):
    class Meta:
        model = Fatigue
        fields = ['date0', 'time0', 'level']

class OedemaForm(ModelForm):
    class Meta:
        model = Oedema
        fields = ['date0', 'notes']

class ExerciseForm(ModelForm):
    class Meta:
        model = Exercise
        fields = ['date0', 'description']

class WeightForm(ModelForm):
    class Meta:
        model = Weight
        fields = ['date0', 'pounds', 'kilos']

    def clean(self):
        lbs = self.cleaned_data['pounds']
        kgs = self.cleaned_data['kilos']
        if lbs != 0 and kgs != 0:
            if 0.99 < (Weight.CONV * kgs / lbs ) < 1.01:
                return
            raise ValidationError("Pounds and Kilos are different weights - leave one at 0")
        if lbs == 0 and kgs == 0:
            raise ValidationError("Enter weight as either pounds or kilos")
        

class BloodPressureForm(ModelForm):
    class Meta:
        model = BloodPressure
        fields = ['date0', 'time0', 'higher', 'lower', 'heart_rate']

