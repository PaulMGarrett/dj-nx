from django.db import models
from django.utils import timezone


class FoodLabel(models.Model):
    name = models.CharField(max_length=50)
    created = models.DateField()
    calories = models.IntegerField("Kcal")
    # fats = models.DecimalField("Fats", max_digits=3, decimal_places=1, null=True)
    # saturated_fat = models.DecimalField("SatF", max_digits=3, decimal_places=1, null=True)
    # mono_unsaturated_fat = models.DecimalField("MonF", max_digits=3, decimal_places=1, null=True)
    # poly_unsaturated_fat = models.DecimalField("PlyF", max_digits=3, decimal_places=1, null=True)
    carbohydrates = models.DecimalField("Carb", max_digits=4, decimal_places=1)
    # sugars = models.DecimalField("Sugr", max_digits=4, decimal_places=1, null=True)
    # starch = models.DecimalField("Strc", max_digits=3, decimal_places=1, null=True)
    # fibre = models.DecimalField("Fibr", max_digits=3, decimal_places=1, null=True)
    # protein = models.DecimalField("Prot", max_digits=3, decimal_places=1, null=True)
    # salt = models.DecimalField("Salt", max_digits=3, decimal_places=1, null=True)

    def __str__(self):
        """ Returns a string representation of a Food """
        return f"{self.name} ({self.created})"

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()
        return super().save(*args, **kwargs)

