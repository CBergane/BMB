from django.db import models
from django.utils import timezone

class Meddelande(models.Model):
    text = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def check_activity(self):
        """Uppdaterar is_active baserat på start och slutdatum."""
        if self.start_date <= timezone.now() <= self.end_date:
            self.is_active = True
        else:
            self.is_active = False
        self.save()

    def __str__(self):
        return self.text
