from django.db import models
from django.db import transaction
from django.contrib.auth.models import User

from products.models import Produkt, Color


class OrderInventoryError(Exception):
    pass


class OrderStatusTransitionError(Exception):
    pass


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'Mottagen'
        PROCESSING = 'processing', 'Behandlas'
        PACKING = 'packing', 'Packas'
        SHIPPED = 'shipped', 'Skickad'
        COMPLETED = 'completed', 'Slutförd'
        CANCELLED = 'cancelled', 'Avbruten'
        ARCHIVED = 'archived', 'Arkiverad'

    user = models.ForeignKey(User, related_name='orders', blank=True, null=True, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    payment_intent = models.CharField(max_length=255, blank=True, null=True)
    submission_key = models.UUIDField(blank=True, null=True, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    paid = models.BooleanField(default=False)
    paid_amount = models.IntegerField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)

    class Meta:
        ordering = ('-created_at', )

    def get_total_price(self):
        total = sum(item.get_total_price() for item in self.items.all())
        return total

    def mark_as_paid(self):
        with transaction.atomic():
            order = (
                Order.objects
                .select_for_update()
                .get(pk=self.pk)
            )

            if order.paid:
                self.paid = True
                return False

            items = list(
                order.items
                .select_for_update()
                .select_related('produkt')
            )

            if not items:
                raise OrderInventoryError("Ordern saknar orderrader.")

            required_quantities = {}
            for item in items:
                if item.quantity is None or item.quantity <= 0:
                    raise OrderInventoryError("Ogiltigt antal på en orderrad.")

                required_quantities[item.produkt_id] = required_quantities.get(item.produkt_id, 0) + item.quantity

            locked_products = {}
            for produkt_id, required_quantity in required_quantities.items():
                produkt = Produkt.objects.select_for_update().get(pk=produkt_id)

                if not produkt.is_active:
                    raise OrderInventoryError(f"Produkten '{produkt.namn}' är inte aktiv.")

                if produkt.inventory < required_quantity:
                    raise OrderInventoryError(f"Otillräckligt lager för '{produkt.namn}'.")

                locked_products[produkt_id] = produkt

            for produkt_id, required_quantity in required_quantities.items():
                produkt = locked_products[produkt_id]
                produkt.inventory -= required_quantity
                produkt.is_active = produkt.inventory > 0
                produkt.save(update_fields=['inventory', 'is_active'])

            order.paid = True
            order.save(update_fields=['paid'])

            self.paid = True
            return True

    def transition_status(self, new_status, changed_by=None, note=''):
        allowed_statuses = {
            self.Status.RECEIVED: {
                self.Status.PROCESSING: lambda order: order.paid,
                self.Status.CANCELLED: lambda order: not order.paid,
                self.Status.ARCHIVED: lambda order: not order.paid,
            },
            self.Status.PROCESSING: {
                self.Status.PACKING: lambda order: order.paid,
            },
            self.Status.PACKING: {
                self.Status.SHIPPED: lambda order: order.paid,
            },
            self.Status.SHIPPED: {
                self.Status.COMPLETED: lambda order: order.paid,
            },
            self.Status.COMPLETED: {
                self.Status.ARCHIVED: lambda order: True,
            },
            self.Status.CANCELLED: {
                self.Status.ARCHIVED: lambda order: True,
            },
            self.Status.ARCHIVED: {},
        }

        if new_status not in self.Status.values:
            raise OrderStatusTransitionError('Ogiltig orderstatus.')

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            transition = allowed_statuses.get(order.status, {}).get(new_status)

            if transition is None or not transition(order):
                raise OrderStatusTransitionError(
                    f'Ordern kan inte ändras från {order.get_status_display()} '
                    f'till {order.Status(new_status).label}.'
                )

            previous_status = order.status
            order.status = new_status
            order.save(update_fields=['status'])
            OrderStatusHistory.objects.create(
                order=order,
                previous_status=previous_status,
                new_status=new_status,
                changed_by=changed_by,
                note=note,
            )

            self.status = new_status
            return order


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    produkt = models.ForeignKey(Produkt, related_name='items', on_delete=models.PROTECT)
    color = models.ForeignKey(Color, blank=True, null=True, on_delete=models.SET_NULL)
    custom_text = models.CharField(max_length=255, blank=True, null=True)
    price = models.IntegerField()
    quantity = models.IntegerField(default=1)

    def get_total_price(self):
        return self.price


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='status_history',
        on_delete=models.CASCADE,
    )
    previous_status = models.CharField(max_length=20, choices=Order.Status.choices)
    new_status = models.CharField(max_length=20, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='order_status_changes',
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('-created_at', '-pk')
