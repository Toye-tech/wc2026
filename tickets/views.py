from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Match, TicketCategory, Booking, Venue
import json
import os
import urllib.request


# ============================================================
# HOME
# ============================================================
def home(request):
    featured_matches = Match.objects.filter(status='available', featured=True)[:6]
    all_matches      = Match.objects.filter(status='available')
    venues           = Venue.objects.all()[:6]
    total_matches    = Match.objects.count()
    total_venues     = Venue.objects.count()
    context = {
        'featured_matches': featured_matches,
        'all_matches'     : all_matches,
        'venues'          : venues,
        'total_matches'   : total_matches,
        'total_venues'    : total_venues,
        'paystack_public_key': os.environ.get('PAYSTACK_PUBLIC_KEY', settings.PAYSTACK_PUBLIC_KEY),
    }
    return render(request, 'tickets/home.html', context)


# ============================================================
# MATCHES LIST
# ============================================================
def matches(request):
    qs = Match.objects.all()
    country = request.GET.get('country', '')
    stage   = request.GET.get('stage', '')
    team    = request.GET.get('team', '')
    if country:
        qs = qs.filter(country=country)
    if stage:
        qs = qs.filter(group_stage=stage)
    if team:
        qs = qs.filter(team_home__icontains=team) | qs.filter(team_away__icontains=team)
    context = {
        'matches'        : qs,
        'country_filter' : country,
        'stage_filter'   : stage,
        'team_filter'    : team,
    }
    return render(request, 'tickets/matches.html', context)


# ============================================================
# MATCH DETAIL
# ============================================================
def match_detail(request, match_id):
    match      = get_object_or_404(Match, id=match_id)
    categories = TicketCategory.objects.filter(match=match)
    context = {
        'match'     : match,
        'categories': categories,
    }
    return render(request, 'tickets/match_detail.html', context)


# ============================================================
# BOOKING PAGE
# ============================================================
def booking(request, match_id, category_id):
    match    = get_object_or_404(Match, id=match_id)
    category = get_object_or_404(TicketCategory, id=category_id, match=match)
    context = {
        'match'              : match,
        'category'           : category,
        'paystack_public_key': os.environ.get('PAYSTACK_PUBLIC_KEY', settings.PAYSTACK_PUBLIC_KEY),
        'african_countries'  : Booking.AFRICAN_COUNTRIES,
    }
    return render(request, 'tickets/booking.html', context)


# ============================================================
# PAYMENT VERIFICATION
# ============================================================
def payment_verify(request):
    reference = request.GET.get('reference', '')
    if not reference:
        return render(request, 'tickets/payment_result.html', {
            'success': False,
            'message': 'No payment reference provided.'
        })
    try:
        secret_key = os.environ.get('PAYSTACK_SECRET_KEY', settings.PAYSTACK_SECRET_KEY)
        req = urllib.request.Request(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers={'Authorization': f'Bearer {secret_key}'}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())

        if result['data']['status'] == 'success':
            meta = result['data']['metadata']
            # Update booking
            try:
                b = Booking.objects.get(paystack_reference=reference)
                b.payment_status = 'success'
                b.save()
                # Reduce seats
                cat = b.ticket_category
                cat.seats_remaining = max(0, cat.seats_remaining - b.quantity)
                cat.save()
            except Booking.DoesNotExist:
                pass
            return redirect('confirmation', reference=reference)
        else:
            return render(request, 'tickets/payment_result.html', {
                'success': False,
                'message': 'Payment was not completed successfully. Please try again.'
            })
    except Exception as e:
        return render(request, 'tickets/payment_result.html', {
            'success': False,
            'message': f'Verification error: {str(e)}'
        })


# ============================================================
# BOOKING CONFIRMATION
# ============================================================
def confirmation(request, reference):
    booking = get_object_or_404(Booking, paystack_reference=reference)
    return render(request, 'tickets/confirmation.html', {'booking': booking})


# ============================================================
# BOOKING LOOKUP
# ============================================================
def lookup(request):
    bookings = []
    searched = False
    query    = request.GET.get('q', '').strip()
    if query:
        searched = True
        bookings = Booking.objects.filter(
            customer_email__iexact=query,
            payment_status='success'
        ) | Booking.objects.filter(
            reference__iexact=query,
            payment_status='success'
        )
    return render(request, 'tickets/lookup.html', {
        'bookings': bookings,
        'searched': searched,
        'query'   : query,
    })


# ============================================================
# CREATE BOOKING (API)
# ============================================================
@require_POST
def create_booking(request):
    try:
        data        = json.loads(request.body)
        match       = get_object_or_404(Match, id=data.get('match_id'))
        category    = get_object_or_404(TicketCategory, id=data.get('category_id'))
        quantity    = int(data.get('quantity', 1))

        if category.seats_remaining < quantity:
            return JsonResponse({'success': False, 'error': 'Not enough seats available.'}, status=400)

        total = category.price_usd * quantity

        booking = Booking.objects.create(
            match               = match,
            ticket_category     = category,
            quantity            = quantity,
            total_amount_usd    = total,
            customer_name       = data.get('name', ''),
            customer_email      = data.get('email', ''),
            customer_phone      = data.get('phone', ''),
            customer_country    = data.get('country', ''),
            passport_number     = data.get('passport', ''),
            special_requirements= data.get('special', ''),
            payment_status      = 'pending',
            paystack_reference  = data.get('paystack_ref', ''),
        )
        return JsonResponse({
            'success'  : True,
            'reference': booking.reference,
            'total_usd': float(total),
            'amount_cents': int(float(total) * 100),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================
# PAYMENT SUCCESS (callback from Paystack inline)
# ============================================================
def payment_success(request):
    ref      = request.GET.get('ref', '')
    car_name = request.GET.get('match', '')
    name     = request.GET.get('name', '')

    # Try to find and confirm the booking
    if ref:
        try:
            b = Booking.objects.get(paystack_reference=ref)
            b.payment_status = 'success'
            b.save()
            cat = b.ticket_category
            cat.seats_remaining = max(0, cat.seats_remaining - b.quantity)
            cat.save()
            return redirect('confirmation', reference=ref)
        except Booking.DoesNotExist:
            pass

    return render(request, 'tickets/payment_result.html', {
        'success'      : True,
        'car_name'     : car_name,
        'customer_name': name,
        'amount'       : 'Paid',
        'reference'    : ref,
    })
