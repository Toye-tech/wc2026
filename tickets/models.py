from django.db import models
import uuid


class Venue(models.Model):
    name        = models.CharField(max_length=200)
    city        = models.CharField(max_length=100)
    country     = models.CharField(max_length=50)
    capacity    = models.IntegerField(default=0)
    image_url   = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    timezone    = models.CharField(max_length=50, default='America/New_York')

    class Meta:
        ordering = ['country', 'city']

    def __str__(self):
        return f"{self.name}, {self.city}"


class Match(models.Model):
    STAGE_CHOICES = [
        ('group',     'Group Stage'),
        ('r16',       'Round of 16'),
        ('qf',        'Quarter Final'),
        ('sf',        'Semi Final'),
        ('third',     'Third Place'),
        ('final',     'Final'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold_out',  'Sold Out'),
        ('cancelled', 'Cancelled'),
    ]
    COUNTRY_CHOICES = [
        ('USA',    'United States'),
        ('Mexico', 'Mexico'),
        ('Canada', 'Canada'),
    ]

    team_home   = models.CharField(max_length=100)
    team_away   = models.CharField(max_length=100)
    group_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='group')
    group_name  = models.CharField(max_length=20, blank=True, help_text='e.g. Group A')
    venue       = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    city        = models.CharField(max_length=100)
    country     = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default='USA')
    match_date  = models.DateField()
    match_time  = models.TimeField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    image_url   = models.URLField(max_length=500, blank=True)
    featured    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['match_date', 'match_time']

    def __str__(self):
        return f"{self.team_home} vs {self.team_away} — {self.match_date}"

    def get_stage_display_short(self):
        labels = {
            'group': 'Group Stage',
            'r16':   'Round of 16',
            'qf':    'Quarter Final',
            'sf':    'Semi Final',
            'third': '3rd Place',
            'final': 'Final',
        }
        return labels.get(self.group_stage, self.group_stage)

    def min_price(self):
        cats = self.ticketcategory_set.filter(seats_remaining__gt=0)
        if cats.exists():
            return cats.order_by('price_usd').first().price_usd
        return None


class TicketCategory(models.Model):
    CATEGORY_CHOICES = [
        ('cat1',        'Category 1'),
        ('cat2',        'Category 2'),
        ('cat3',        'Category 3'),
        ('hospitality', 'Hospitality'),
    ]

    match           = models.ForeignKey(Match, on_delete=models.CASCADE)
    name            = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price_usd       = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats     = models.IntegerField(default=100)
    seats_remaining = models.IntegerField(default=100)
    description     = models.TextField(blank=True)
    perks           = models.TextField(blank=True)

    class Meta:
        ordering = ['price_usd']
        verbose_name_plural = 'Ticket Categories'

    def __str__(self):
        return f"{self.get_name_display()} — {self.match}"

    def availability_percent(self):
        if self.total_seats == 0:
            return 0
        return int((self.seats_remaining / self.total_seats) * 100)

    def is_available(self):
        return self.seats_remaining > 0


class Booking(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed',  'Failed'),
    ]

    AFRICAN_COUNTRIES = [
        ('Algeria','Algeria'),('Angola','Angola'),('Benin','Benin'),
        ('Botswana','Botswana'),('Burkina Faso','Burkina Faso'),('Burundi','Burundi'),
        ('Cameroon','Cameroon'),('Cape Verde','Cape Verde'),
        ('Central African Republic','Central African Republic'),('Chad','Chad'),
        ('Comoros','Comoros'),('Congo','Congo'),('DR Congo','DR Congo'),
        ('Djibouti','Djibouti'),('Egypt','Egypt'),
        ('Equatorial Guinea','Equatorial Guinea'),('Eritrea','Eritrea'),
        ('Eswatini','Eswatini'),('Ethiopia','Ethiopia'),('Gabon','Gabon'),
        ('Gambia','Gambia'),('Ghana','Ghana'),('Guinea','Guinea'),
        ('Guinea-Bissau','Guinea-Bissau'),('Ivory Coast','Ivory Coast'),
        ('Kenya','Kenya'),('Lesotho','Lesotho'),('Liberia','Liberia'),
        ('Libya','Libya'),('Madagascar','Madagascar'),('Malawi','Malawi'),
        ('Mali','Mali'),('Mauritania','Mauritania'),('Mauritius','Mauritius'),
        ('Morocco','Morocco'),('Mozambique','Mozambique'),('Namibia','Namibia'),
        ('Niger','Niger'),('Nigeria','Nigeria'),('Rwanda','Rwanda'),
        ('Sao Tome','Sao Tome'),('Senegal','Senegal'),('Sierra Leone','Sierra Leone'),
        ('Somalia','Somalia'),('South Africa','South Africa'),
        ('South Sudan','South Sudan'),('Sudan','Sudan'),('Tanzania','Tanzania'),
        ('Togo','Togo'),('Tunisia','Tunisia'),('Uganda','Uganda'),
        ('Zambia','Zambia'),('Zimbabwe','Zimbabwe'),
    ]

    reference          = models.CharField(max_length=100, unique=True, blank=True)
    match              = models.ForeignKey(Match, on_delete=models.PROTECT)
    ticket_category    = models.ForeignKey(TicketCategory, on_delete=models.PROTECT)
    quantity           = models.IntegerField(default=1)
    total_amount_usd   = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name      = models.CharField(max_length=200)
    customer_email     = models.EmailField()
    customer_phone     = models.CharField(max_length=30)
    customer_country   = models.CharField(max_length=50, choices=AFRICAN_COUNTRIES)
    passport_number    = models.CharField(max_length=50, blank=True)
    special_requirements = models.TextField(blank=True)
    payment_status     = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    paystack_reference = models.CharField(max_length=200, blank=True)
    ticket_code        = models.CharField(max_length=50, unique=True, blank=True)
    booking_date       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date']

    def __str__(self):
        return f"{self.customer_name} — {self.match} x{self.quantity}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"WC26-{uuid.uuid4().hex[:8].upper()}"
        if not self.ticket_code:
            self.ticket_code = f"TKT-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
