from collections import OrderedDict
import datetime
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.urls import reverse
from django.utils import timezone

# Helpers --------------
K2P_CONV = 2.20462  # how many pounds in one kilo

def toDate(yyyymmdd):
    yyyy = yyyymmdd // 10000
    mmdd = yyyymmdd - 10000 * yyyy
    mm = mmdd // 100
    dd = mmdd - mm * 100
    return datetime.date(year=yyyy, month=mm, day=dd)

def fromDate(dt):
    return dt.strftime("%Y%m%d")


class Slot():
    def __init__(self, code, alarm, colour, name=None, icon=None):
        self.code = code
        self.alarm_hour = alarm
        self.colour = colour
        self.name = name or code
        self.icon = icon

    def __str__(self):
        return f"{self.code} ~ {self.time_str}"

    def text(self):
        return str(self)

    def choice(self):
        """ Return 2-element tuple of code and time string. """
        return (self.code, str(self))

    @property
    def time_str(self):
        h = int(self.alarm_hour)
        m = int(60 * (self.alarm_hour - h))
        return f"{h:02d}:{m:02d}"


# Hard-coded for now
Slots = [
    Slot('A1', 9, "#FFE0FF"),
    Slot('A2', 12, "#E0FFFF"),
    Slot('A3', 14, "#FFFFD0"),
    Slot('B1', 16, "#FFE0E0"),
    Slot('B2', 19, "#E0FFE0"),
    Slot('B3', 21.5, "#E0E0FF"),
    ]

def out_of_ten(value):
    if value < 0 or value > 10:
        raise ValidationError("Must be between 0 and 10")

def ug_to_string(micrograms, second_micrograms=None):
    """Return human-friendly dosage as string."""
    if second_micrograms:
        return ug_to_string(micrograms) + '/' + ug_to_string(second_micrograms)
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
    second_micrograms = models.IntegerField(null=True)

    @property
    def drug_details(self):
        return f"{self.drug} ({ug_to_string(self.tablet_micrograms, self.second_micrograms)})"

    @property
    def tablet_info(self):
        return str(self)

    def __str__(self):
        x = self.drug_details
        if self.num_tablets != 1:
            x = x + f" x {self.num_tablets}"
        return x
    

class Schedule(models.Model):
    date0 = models.DateField("when this schedule came into force")
    reason = models.CharField("why it was changed", max_length=150)

    def __str__(self):
        return f"Schedule-from-{self.date0.isoformat()}"

    class SlotDoses():
        def __init__(self, slot_name):
            for s in Slots:
                if slot_name.startswith(s.code):
                    self.slot = s
            self.tablets = []
            self.num_items = 0

        def add(self, tablet):
            self.tablets.append(tablet)
            self.tablets.sort(key=lambda t: (t.drug.name, t.tablet_micrograms, t.num_tablets))
            # count how many "things" are in the pot, so round half tablets up to 1
            self.num_items += int(0.99 + tablet.num_tablets)

    def doses_by_slot(self):
        slots = {}
        for dose in Dose.objects.filter(schedule=self):
            if not dose.slot:
                continue
            slots.setdefault(dose.slot, Schedule.SlotDoses(dose.slot)).add(dose.tablet)
        return sorted(slots.values(), key=lambda sd: sd.slot.code)

    def edit_url(self):
        return reverse('schedule', args=[fromDate(self.date0)])


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

class TirednessLevel(models.Model):
    rating = models.IntegerField("tiredness level", unique=True)
    description = models.CharField("description", max_length=30)

    def __str__(self):
        return f"{self.rating}: {self.description}"


class Obs(models.Model):
    date0 = models.DateField("date observed", primary_key=True)
    pounds = models.FloatField("pounds", default=0)
    kilos = models.FloatField("kilos", default=0)
    am_higher = models.IntegerField("Morning systolic", blank=True, null=True)
    am_lower = models.IntegerField("Morning diastolic", blank=True, null=True)
    am_rate = models.IntegerField("Morning resting heart rate", blank=True, null=True)
    pm_higher = models.IntegerField("Afternoon systolic", blank=True, null=True)
    pm_lower = models.IntegerField("Afternoon diastolic", blank=True, null=True)
    pm_rate = models.IntegerField("Afternoon resting heart rate", blank=True, null=True)
    other_rate = models.IntegerField("Extra resting heart rate", blank=True, null=True)
#    fatigue_score = models.IntegerField("Tiredness (out of 10)", validators=[out_of_ten], null=True)
    oedema = models.CharField("Oedema (swelling)", max_length=50, blank=True, null=True)
    dizzy_spells = models.IntegerField("Dizzy spells", default=0, null=True)
    exercise = models.CharField("Exercise notes", max_length=100, blank=True, null=True)
    tiredness = models.ForeignKey(TirednessLevel, null=True, to_field='rating', default=0, on_delete=models.PROTECT)
    events = models.TextField("Events/Notes", max_length=500, blank=True, null=True)

    @property
    def date1(self):
        return self.date0.strftime("%Y-%m-%d")

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
        return self.date0.strftime('%Y-%m-%d')
