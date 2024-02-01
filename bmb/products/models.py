from django.contrib.auth.models import User
from django.db import models

from cloudinary.models import CloudinaryField
from cloudinary.utils import cloudinary_url

from django.core.files import File
from autoslug import AutoSlugField
from PIL import Image
from io import BytesIO
from ckeditor.fields import RichTextField

class Category(models.Model):
    namn = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='namn', unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'Kategorier'
        ordering = ('namn',)

    def __str__(self):
        return self.namn

    def is_parent(self):
        return self.children.exists()
    
    def get_children(self):
        return self.children.all()


class WashInstruction(models.Model):
    name = models.CharField(max_length=100)
    icon = CloudinaryField('icon')  # Spara ikoner i media/icons

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=100)
    # Eventuella ytterligare fält, som en HEX-värdet för färgen etc.

    def __str__(self):
        return self.name


class Produkt(models.Model):

    UNIT_CHOICES = [
        ('dm', 'Decimeter'),
        ('st', 'St'),
    ]

    category = models.ForeignKey(Category, related_name='produkt', on_delete=models.CASCADE)
    namn = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='namn', unique=True)
    unit = models.CharField(
        max_length=4,
        choices=UNIT_CHOICES,
        default='st',
        help_text="Enhet för denna produkt"
    )
    is_fabric = models.BooleanField(default=False, help_text="Är denna produkt ett tyg?")
    is_stubbie = models.BooleanField(default=False, help_text="Markera om denna produkt är en stuvbit.")
    bredd = models.IntegerField(blank=True, null=True)
    vikt = models.IntegerField(blank=True, null=True)
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Length of the stubbie product (in decimeters)",)
    blandning = models.CharField(max_length=255, blank=True, null=True)
    kvalitet = models.CharField(max_length=255, blank=True, null=True)
    färg = models.CharField(max_length=255, blank=True, null=True)
    motiv = models.CharField(max_length=255, blank=True, null=True)
    beskrivning = RichTextField(blank=True, null=True)
    wash_instructions = models.ManyToManyField(WashInstruction, blank=True)
    inventory = models.IntegerField(default=0, help_text="Mängd kvar i lager, st eller decimeter")
    is_active = models.BooleanField(default=True, help_text="Är denna produkt i lager?")
    pris = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField(blank=True, null=True, help_text="Rabatt i procent", default=0)
    skapad = models.DateTimeField(auto_now_add=True)
    image = CloudinaryField('image', blank=True, null=True)
    image2 = CloudinaryField('image2', blank=True, null=True, help_text="Valfri: Lägg till en andra bild av produkten.")
    image3 = CloudinaryField('image3', blank=True, null=True, help_text="Valfri: Lägg till en andra bild av produkten.")
    image4 = CloudinaryField('image4', blank=True, null=True, help_text="Valfri: Lägg till en andra bild av produkten.")
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

    def get_thumbnail_image2(self):
        if self.image2:
            thumbnail_url = cloudinary_url(self.image2.public_id, width=300, height=300, crop="fill")[0]
            return thumbnail_url
        else:
            return None

    def get_rating(self):
        reviews_total = 0

        for review in self.reviews.all():
            reviews_total += review.rating

        if reviews_total > 0:
            return reviews_total / self.reviews.count()

        return 0
    
    def save(self, *args, **kwargs):
        if self.is_stubbie and self.length is None:
            raise ValueError("Please specify the length for the stubbie product.")
        
        if self.inventory <= 0:
            self.is_active = False
        else:
            self.is_active = True

        super(Produkt, self).save(*args, **kwargs)

    def get_discounted_price(self):
        """
        Return the price after the discount.
        """
        return self.pris - (self.pris * self.discount_percentage / 100)

    def save(self, *args, **kwargs):
        if self.discount_percentage is None:
            self.discount_percentage = 0
        super(Produkt, self).save(*args, **kwargs)

class ProductVariant(models.Model):
    product = models.ForeignKey(Produkt, related_name='variants', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    allow_custom_text = models.BooleanField(default=False)
    custom_text = models.CharField(max_length=255, blank=True, null=True)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # Eventuellt andra attribut som storlek eller material.

    def __str__(self):
        return f"{self.product.namn} - {self.color.name} - {self.custom_text}"


class Review(models.Model):
    product = models.ForeignKey(Produkt, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(default=3)
    content = models.TextField()
    created_by = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
