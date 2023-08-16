from django.contrib.auth.models import User
from django.db import models

from cloudinary.models import CloudinaryField
from cloudinary.utils import cloudinary_url

from django.core.files import File
from autoslug import AutoSlugField
from PIL import Image
from io import BytesIO

class Category(models.Model):
    namn = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='namn', unique=True)
    
    class Meta:
        verbose_name_plural = 'Kategorier'
        ordering = ('namn',)

    def __str__(self):
        return self.namn

class Produkt(models.Model):
    category = models.ForeignKey(Category, related_name='produkt', on_delete=models.CASCADE)
    namn = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='namn', unique=True)
    bredd = models.IntegerField(blank=True, null=True)
    vikt = models.IntegerField(blank=True, null=True)
    blandning = models.CharField(max_length=255)
    kvalitet = models.CharField(max_length=255)
    färg = models.CharField(max_length=255)
    motiv = models.CharField(max_length=255)
    beskrivning = models.TextField(blank=True, null=True)
    inventory = models.IntegerField(default=0, help_text="Mängd tyg kvar")
    is_active = models.BooleanField(default=True, help_text="Är denna produkt i lager?")
    pris = models.IntegerField()
    skapad = models.DateTimeField(auto_now_add=True)
    image = CloudinaryField('image', blank=True, null=True)
    thumbnail = CloudinaryField('image', blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Produkter'
        ordering = ('-skapad',)

    def __str__(self):
        return self.namn

    def get_thumbnail(self):
        if self.image:
            thumbnail_url = cloudinary_url(self.image.public_id, width=300, height=300, crop="fill")[0]
            return thumbnail_url
        else:
            return 'https://via.placeholder.com/240x240x.jpg'


    def get_rating(self):
        reviews_total = 0

        for review in self.reviews.all():
            reviews_total += review.rating

        if reviews_total > 0:
            return reviews_total / self.reviews.count()

        return 0
    
    def save(self, *args, **kwargs):
        if self.inventory <= 0:
            self.is_active = False
        else:
            self.is_active = True
        super(Produkt, self).save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Produkt, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(default=3)
    content = models.TextField()
    created_by = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
