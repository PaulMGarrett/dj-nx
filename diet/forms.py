from django import forms

from diet import models


class FoodLabelForm(forms.ModelForm):
    class Meta:
        model = models.FoodLabel
        exclude = ['created']

    def clean(self):
        total = 0

        # TODO check fats and carbs breakdowns
        total += self.cleaned_data['fats']
        total += self.cleaned_data['carbohydrates']
        total += self.cleaned_data['fibre']
        total += self.cleaned_data['protein']
        total += self.cleaned_data['salt']
        if total > 100:
            raise forms.ValidationError(f"Total percentages = {total}")

        # fats = models.DecimalField("Fats", max_digits=3, decimal_places=1, null=True)
        # saturated_fat = models.DecimalField("SatF", max_digits=3, decimal_places=1, null=True)
        # mono_unsaturated_fat = models.DecimalField("MonF", max_digits=3, decimal_places=1, null=True)
        # poly_unsaturated_fat = models.DecimalField("PlyF", max_digits=3, decimal_places=1, null=True)
        # carbohydrates = models.DecimalField("Carb", max_digits=4, decimal_places=1)
        # sugars = models.DecimalField("Sugr", max_digits=4, decimal_places=1, null=True)
        # starch = models.DecimalField("Strc", max_digits=3, decimal_places=1, null=True)
        # fibre = models.DecimalField("Fibr", max_digits=3, decimal_places=1, null=True)
        # protein = models.DecimalField("Prot", max_digits=3, decimal_places=1, null=True)
        # salt = models.DecimalField("Salt", max_digits=3, decimal_places=1, null=True)
