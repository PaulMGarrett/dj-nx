import datetime
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.utils import timezone


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


class Drug(models.Model):
    name = models.CharField(max_length=50)
    purpose = models.CharField("reason to take", max_length=100, blank=True)
    # max_dose_micrograms = models.IntegerField("maximum daily dose")

    def __str__(self):
        """Returns a string representation of a drug."""
        return f"{self.name}"


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


Slots = [
    Slot('A1', 9, "#FFF0FF"),
    Slot('A2', 12, "#F0FFFF"),
    Slot('A3', 14, "#FFFFF0"),
    Slot('B1', 16, "#FFF0F0"),
    Slot('B2', 18.5, "#F0FFF0"),
    Slot('B3', 21.5, "#F0F0FF"),
    ]


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


class Incident(models.Model):
    date0 = models.DateField("date")
    time0 = models.TimeField("time")
    description = models.TextField("What happened")

    @property
    def date1(self):
        return self.date0.strftime("%a %d/%m")

    @property
    def time1(self):
        return self.time0.strftime("%H:%M")

    @property
    def when1(self):
        return self.date1 + ' ' + self.time1

    def __str__(self):
        return f"{self.when0}: {self.description[:20]}"

    @classmethod
    def now_data(cls):
        now = datetime.datetime.now()
        return {'date0': now.date(),
                'time0': now.time(),
                }