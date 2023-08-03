from django.db import models

class Category(models.Model):
    namn = models.CharField(max_length=255)
    slug = models.SlugField()
    
    class Meta:
        ordering = ('namn',)

    def __str__(self):
        return self.namn

class Produkt(models.Model):
    category = models.ForeignKey(Category, related_name='produkt', on_delete=models.CASCADE)
    namn = models.CharField(max_length=255)
    slug = models.SlugField()
    bredd = models.IntegerField(blank=True, null=True)
    vikt = models.IntegerField(blank=True, null=True)
    blandning = models.CharField(max_length=255)
    kvalitet = models.CharField(max_length=255)
    färg = models.CharField(max_length=255)
    motiv = models.CharField(max_length=255)
    beskrivning = models.TextField(blank=True, null=True)
    pris = models.IntegerField()
    skapad = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-skapad',)

    def __str__(self):
        return self.namn