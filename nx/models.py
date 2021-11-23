import datetime
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.utils import timezone

# Helpers --------------
K2P_CONV = 2.20462  # how many pounds in one kilo

class Slot():
    def __init__(self, code, alarm, colour, name=None, icon=None):
        self.code = code
        self.alarm_hour = alarm
        self.colour = colour
        self.name = name or code
        self.icon = icon

    def __str__(self):
        h = int(self.alarm_hour)
        m = int(60 * (self.alarm_hour - h))
        return f"{self.code} ~ {h:02d}:{m:02d}"

    def choice(self):
        """ Return 2-element tuple of code and time string. """
        return (self.code, str(self))

# Hard-coded for now
Slots = [
    Slot('A1', 9, "#FFF0FF"),
    Slot('A2', 12, "#F0FFFF"),
    Slot('A3', 14, "#FFFFF0"),
    Slot('B1', 16, "#FFF0F0"),
    Slot('B2', 19, "#F0FFF0"),
    Slot('B3', 21.5, "#F0F0FF"),
    ]

def out_of_ten(value):
    if value < 0 or value > 10:
        raise ValidationError("Must be between 0 and 10")

def ug_to_string(micrograms):
    """Return human-friendly dosage as string."""
    if micrograms % 1000 == 0:
        milligrams = micrograms // 1000
        if milligrams % 1000 == 0:
            grams = milligrams // 1000
            return f"{grams:d}g"
        return f"{milligrams:d}mg"
    elif micrograms % 100 == 0 and micrograms < 100 * 1000:
        return f"{micrograms/1000:.1f}mg"
    else:
        return f"{micrograms:d}ug"

# Models ---------------------


class Drug(models.Model):
    name = models.CharField(max_length=50)
    purpose = models.CharField("reason to take", max_length=100, blank=True)
    # max_dose_micrograms = models.IntegerField("maximum daily dose")

    def __str__(self):
        """Returns a string representation of a drug."""
        return f"{self.name}"


class Tablet(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    tablet_micrograms = models.IntegerField()
    num_tablets = models.FloatField(default=1.0)
    notes = models.CharField(max_length=150, blank=True)

    @property
    def drug_details(self):
        return f"{self.drug}({ug_to_string(self.tablet_micrograms)})"

    def __str__(self):
        x = self.drug_details
        if self.num_tablets > 1:
            x = x + f"x{self.num_tablets}"
        return x


class Schedule(models.Model):
    date0 = models.DateField("when this schedule came into force")
    reason = models.CharField("why it was changed", max_length=150)

    def __str__(self):
        return f"Schedule-from-{self.date0.isoformat()}"


class Dose(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)
    tablet = models.ForeignKey(Tablet, on_delete=models.PROTECT)
    slot = models.CharField(max_length=2, choices = [('', "No slot")] + [s.choice() for s in Slots], blank=True)

    @property
    def colour(self):
        for s in Slots:
            if self.slot == s.code:
                return s.colour
        return 'white'

    @property
    def drug_details(self):
        return self.tablet.drug_details

    def __str__(self):
        return f"{self.drug_details}@{self.slot} ({self.schedule})"


# Daily observations ---------------------

class Obs(models.Model):
    date0 = models.DateField("date measured", primary_key=True)
    pounds = models.FloatField("pounds", default=0)
    kilos = models.FloatField("kilos", default=0)
    am_higher = models.IntegerField("Morning systolic", blank=True, null=True)
    am_lower = models.IntegerField("Morning diastolic", blank=True, null=True)
    # am_heart_rate = models.IntegerField("Morning bpm", null=True)
    pm_higher = models.IntegerField("Afternoon systolic", blank=True, null=True)
    pm_lower = models.IntegerField("Afternoon diastolic", blank=True, null=True)
    # pm_heart_rate = models.IntegerField("Afternoon bpm", null=True)
    exercise = models.CharField("Exercise notes", max_length=100, blank=True, null=True)
    fatigue_score = models.IntegerField("Tiredness (out of 10)", validators=[out_of_ten], null=True)
    oedema = models.CharField("Oedema (swelling)", max_length=50, blank=True, null=True)
    events = models.TextField("Events/Notes", max_length=500, blank=True, null=True)

    @property
    def date1(self):
        return self.date0.strftime("%a %d/%m")

    @property
    def lbs(self):
        w = self.kilos * K2P_CONV if self.pounds == 0 else self.pounds
        return f"{w:.1f}"

    @property
    def kgs(self):
        w = self.pounds / K2P_CONV if self.kilos == 0 else self.kilos
        return f"{w:.1f}"

    @property
    def am_bp(self):
        return f"{self.am_higher}/{self.am_lower}"

    @property
    def pm_bp(self):
        return f"{self.pm_higher}/{self.pm_lower}"

    def __str__(self):
        return f"{self.date1}({self.pounds}lb,{self.am_bp},{self.pm_bp})"

    @classmethod
    def initial_data(cls):
        return {
            'kilos': 0,
            'pounds': 0,
        }

    @property
    def date1(self):
        return self.date0.strftime("%a %d/%m")

    def __str__(self):
        return f"{self.date1}:{self.notes[:40]}"

    @classmethod
    def initial_data(cls):
        now = datetime.datetime.now()
        return {'date0': now.date(),
                'notes': '',
                }

