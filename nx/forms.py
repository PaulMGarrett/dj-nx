from django import forms

from nx import models


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = models.Schedule
        exclude = []


class DoseForm(forms.ModelForm):
    class Meta:
        model = models.Dose
        exclude = []


class DoseEditForm(forms.ModelForm):
    class Meta:
        model = models.Dose
        exclude = ['schedule']


class ObsForm(forms.ModelForm):
    class Meta:
        model = models.Obs
        exclude = ['date0']

    def clean(self):
        pair_errors = []
        lbs = self.cleaned_data['pounds']
        kgs = self.cleaned_data['kilos']
        if lbs and kgs and not (0.99 < (models.K2P_CONV * kgs / lbs ) < 1.01):
            pair_errors.append("Pounds and Kilos are not consistent - try setting one to 0")

        systolic = self.cleaned_data['am_higher']
        diastolic = self.cleaned_data['am_lower']
        if systolic and diastolic and systolic <= diastolic:
            pair_errors.append("Morning BP values are not consistent")

        systolic = self.cleaned_data['pm_higher']
        diastolic = self.cleaned_data['pm_lower']
        if systolic and diastolic and systolic <= diastolic:
            pair_errors.append("Afternoon BP values are not consistent")

        if pair_errors:
            raise forms.ValidationError(pair_errors)
