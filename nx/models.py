from collections import OrderedDict
import datetime
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
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
    def __init__(self, code, alarm, colour, name, icon):
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
    Slot('A1', 10, "#FFE0FF", "Morning", 'Morning-pic.jpg'),
    Slot('A2', 12, "#E0FFFF", None, None),
    Slot('A3', 14, "#FFFFD0", "Midday", 'Midday-pic.jpg'),
    Slot('B1', 16, "#FFE0E0", None, None),
    Slot('B2', 19, "#E0FFE0", "Evening", 'Evening-pic.jpg'),
    Slot('B3', 21.5, "#E0E0FF", "Bedtime", 'Bedtime-pic.jpg'),
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
    elif micrograms % 10 == 0 and micrograms < 10 * 1000:
        return f"{micrograms/1000:.2f}mg"
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
    num_days = models.IntegerField("stagger doses over", default=1,
                                   validators=[MinValueValidator(1),
                                               MaxValueValidator(7)])
    notes = models.CharField(max_length=150, blank=True)
    second_micrograms = models.IntegerField(null=True)

    @property
    def drug_details(self):
        return f"{self.drug} ({ug_to_string(self.tablet_micrograms, self.second_micrograms)})"

    @property
    def tablet_info(self):
        return str(self)

    def dose_on_day(self, day_num):
        ''' Return the dose for given day '''
        assert day_num > 0
        if self.num_days > 1:
            for scale in range(1,3):
                if scale * self.num_tablets == int(scale * self.num_tablets):
                    by_today = day_num * self.num_tablets * scale // self.num_days
                    by_yesterday = (day_num - 1) * self.num_tablets * scale // self.num_days
                    return (by_today - by_yesterday) / scale
        return self.num_tablets / self.num_days

    def dose_lo_hi(self):
        doses = set()
        for d in range(1, 8):
            doses.add(self.dose_on_day(d))
        if len(doses) == 1:
            return list(doses) * 2
        elif len(doses) == 2:
            return sorted(list(doses))

    @property
    def tablet_doses(self):
        lo_hi = self.dose_lo_hi()
        if lo_hi[0] == lo_hi[1]:
            return str(lo_hi[0])
        else:
            return '/'.join([str(x) for x in lo_hi])

    def __str__(self):
        x = self.drug_details
        if self.num_tablets != 1 or self.num_days != 1:
            x = x + f" x {self.tablet_doses}"
        return x
    

class Schedule(models.Model):
    date0 = models.DateField("when this schedule came into force")
    reason = models.CharField("why it was changed", max_length=150)

    day_names = "Mo Tu We Th Fr Sa Su".split()

    def __str__(self):
        return f"Schedule-from-{self.date0.isoformat()}"

    class SlotTablet():
        """ Wrapper class to let us override tablet_info """
        def __init__(self, tablet, day_offset):
            self.real = tablet
            self.num_repeats = 0
            self.week_pattern = ''
            self.lo, self.hi = self.real.dose_lo_hi()
            if self.lo != self.hi:
                for i, d in enumerate(Schedule.day_names):
                    dose = self.real.dose_on_day(day_offset + i)
                    if dose == self.hi:
                        self.week_pattern += d
            self.num_items = [int(0.99 + self.lo), int(0.99 + self.hi)]

        @property
        def tablet_info(self):
            return self.real.tablet_info

        @property
        def is_reused(self):
            return self.num_repeats
        
        def later_tablet(self, later):
            if (self.real.drug.name == later.real.drug.name and
                    self.real.tablet_micrograms == later.real.tablet_micrograms):
                # same box, so flag it
                self.num_repeats += 1

    class SlotDoses():
        def __init__(self, slot_name, day_offset):
            for s in Slots:
                if slot_name.startswith(s.code):
                    self.slot = s
            self.day_offset = day_offset
            while self.day_offset <= 0:
                self.day_offset += 7 * 6 * 5 * 4 * 3 * 2 * 1
            self.tablets = []
            self.num_items = [0, 0]

        def add(self, tablet):
            st = Schedule.SlotTablet(tablet, self.day_offset)
            for t in self.tablets:
                t.later_tablet(st)
            self.tablets.append(st)
            self.tablets.sort(key=lambda t: (t.real.drug.name, t.real.tablet_micrograms, t.real.num_tablets))
            # count how many "things" are in the pot, so round half tablets up to 1
            self.num_items[0] += st.num_items[0]
            self.num_items[1] += st.num_items[1]

        def later(self, later_sd):
            for t in self.tablets:
                for lt in later_sd.tablets:
                    t.later_tablet(lt)

        @property
        def num_items_min_max(self):
            if self.num_items[0] == self.num_items[1]:
                return str(self.num_items[0])
            return '-'.join([str(self.num_items[0]), str(self.num_items[1])])

    def doses_by_slot(self):
        self.day_offset = 1
        slots = {}
        for dose in Dose.objects.filter(schedule=self):
            if not dose.slot:
                continue
            slots.setdefault(dose.slot, Schedule.SlotDoses(dose.slot, self.day_offset)).add(dose.tablet)
        ret = sorted(slots.values(), key=lambda sd: sd.slot.code)
        for i, sd in enumerate(ret):
            for earlier_sd in ret[:i]:
                earlier_sd.later(sd)
        return ret

    # def doses_in_multiple_slots(self):
    #     tcounts = {}
    #     for dose in Dose.objects.filter(schedule=self):
    #         if not dose.slot:
    #             continue
    #         tcounts[dose.tablet] = tcounts.get(dose.tablet, 0) + 1
    #     return tcounts

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
