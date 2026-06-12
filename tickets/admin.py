from django.contrib import admin
from .models import Venue, Match, TicketCategory, Booking


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'capacity']
    list_filter  = ['country']
    search_fields = ['name', 'city']


class TicketCategoryInline(admin.TabularInline):
    model = TicketCategory
    extra = 4


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display  = ['team_home', 'team_away', 'group_stage', 'city', 'country', 'match_date', 'status', 'featured']
    list_filter   = ['country', 'group_stage', 'status', 'featured']
    search_fields = ['team_home', 'team_away', 'city']
    list_editable = ['status', 'featured']
    inlines       = [TicketCategoryInline]


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ['match', 'name', 'price_usd', 'seats_remaining', 'total_seats']
    list_filter  = ['name']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'customer_name', 'match', 'ticket_category', 'quantity', 'total_amount_usd', 'payment_status', 'booking_date']
    list_filter   = ['payment_status', 'customer_country']
    search_fields = ['reference', 'customer_name', 'customer_email', 'paystack_reference']
    readonly_fields = ['reference', 'ticket_code', 'booking_date']
