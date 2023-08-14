from django.contrib.auth.models import User
from django.db import models
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
    pris = models.IntegerField()
    skapad = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='uploads/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='uploads/', blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Produkter'
        ordering = ('-skapad',)

    def __str__(self):
        return self.namn

    def get_thumbnail(self):
        if self.thumbnail:
            return self.thumbnail.url
        else:
            if self.image:
                if self.image:
                    self.thumbnail = self.make_thumbnail(self.image)
                    self.save

                    return self.thumbnail.url
                else:
                    return 'https://via.placeholder.com/240x240x.jpg'

    def make_thumbnail(selg, image, size=(300, 300)):
        img = Image.open(image)
        img.convert('RGB')
        img.thumbnail(size)

        thumb_io = BytesIO()
        img.save(thumb_io, 'JPEG', quality=85)

        thumbnail = File(thumb_io, name=image.name)

        return thumbnail

    def get_rating(self):
        reviews_total = 0

        for review in self.reviews.all():
            reviews_total += review.rating

        if reviews_total > 0:
            return reviews_total / self.reviews.count()

        return 0


class Review(models.Model):
    product = models.ForeignKey(Produkt, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(default=3)
    content = models.TextField()
    created_by = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)