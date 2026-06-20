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


def updates(request):
    return render(request, 'tickets/updates.html')


def api_news_feed(request):
    """Returns curated WC2026 news content for the live updates page."""
    topic = request.GET.get('topic', 'latest')
    return JsonResponse({'success': True, 'articles': NEWS_SEED.get(topic, NEWS_SEED['latest'])})


NEWS_SEED = {
    'latest': [
        {"headline": "World Cup 2026 Now Underway — Matchday 9 in Progress", "body": "The 2026 FIFA World Cup is the first edition to feature 48 teams across three host nations: USA, Mexico and Canada. The tournament is now past the first week of group stage action.", "tag": "breaking", "time": "Live"},
        {"headline": "USA Reaches Knockout Phase", "body": "The United States secured their place in the Round of 32 after a 2-0 victory over Australia, improving their record to 2 wins from 2 matches in Group D.", "tag": "result", "time": "Today"},
        {"headline": "Brazil, Morocco and Paraguay Boost Knockout Hopes", "body": "Strong Matchday 9 performances from Brazil, Morocco and Paraguay have strengthened their positions in the race for the Round of 32.", "tag": "result", "time": "Today"},
        {"headline": "Golden Boot Race Heating Up", "body": "Several players have found the net multiple times in the opening matchdays, with the race for the adidas Golden Boot tightening as the group stage progresses.", "tag": "general", "time": "Today"},
        {"headline": "Mexico and Canada Make History", "body": "Mexico became the first co-host nation to clinch a Round of 32 spot, while Canada recorded a landmark 6-0 victory over Qatar — their first ever World Cup win.", "tag": "result", "time": "Recent"},
    ],
    'results': [
        {"headline": "Mexico 1-0 South Korea", "body": "Mexico became the first team to officially clinch a spot in the Round of 32 with a narrow win over South Korea in Group A.", "tag": "result", "time": "Recent"},
        {"headline": "Canada 6-0 Qatar", "body": "Canada recorded their first-ever World Cup victory in dominant fashion, putting six past Qatar in Group B.", "tag": "result", "time": "Recent"},
        {"headline": "USA 2-0 Australia", "body": "The United States moved to 2 wins from 2 in Group D, securing qualification to the knockout stage.", "tag": "result", "time": "Today"},
        {"headline": "South Africa vs Czechia Ends Level", "body": "Teboho Mokoena scored a late penalty to earn South Africa a hard-fought draw against Czechia in their Group A clash.", "tag": "african", "time": "Recent"},
        {"headline": "Argentina vs Algeria — Emotional Scenes", "body": "An emotional Lionel Messi was seen wiping away tears during Argentina's Group J match against Algeria.", "tag": "general", "time": "Recent"},
    ],
    'african': [
        {"headline": "South Africa Battle to Draw with Czechia", "body": "Teboho Mokoena's late penalty rescued a point for South Africa in their opening Group A match — a solid start to their World Cup campaign.", "tag": "african", "time": "Recent"},
        {"headline": "Morocco Boost Knockout Hopes on Matchday 9", "body": "Morocco delivered a strong performance to strengthen their position in Group C, keeping their Round of 32 hopes firmly alive.", "tag": "african", "time": "Today"},
        {"headline": "Cabo Verde Make History in Maiden World Cup Appearance", "body": "Cabo Verde prepare to play their first ever World Cup match, facing title-hunting Spain in Atlanta — a landmark moment for the nation.", "tag": "african", "time": "Recent"},
        {"headline": "Egypt Face Belgium in Group G Opener", "body": "Egypt's tournament debut sees them paired against Belgium in a tough Group G test, with full match previews available.", "tag": "african", "time": "Recent"},
        {"headline": "Ivory Coast, Senegal, Ghana, Tunisia, Algeria All in Action", "body": "All nine African qualifiers are now playing across the group stage, marking the largest-ever African representation at a World Cup.", "tag": "african", "time": "Ongoing"},
    ],
    'standings': [
        {"headline": "Group A Standings", "body": "Mexico lead Group A having already qualified for the Round of 32. South Africa, South Korea and the UEFA play-off side are competing for the remaining spots.", "tag": "general", "time": "Live"},
        {"headline": "Group D Standings", "body": "USA sit top of Group D with 2 wins from 2 matches, having already secured qualification to the knockout stage.", "tag": "general", "time": "Live"},
        {"headline": "Group B Standings", "body": "Canada's emphatic win over Qatar puts them firmly in contention in Group B alongside Switzerland.", "tag": "general", "time": "Live"},
        {"headline": "Full Standings Available on FIFA.com", "body": "For complete, continuously updated standings across all 12 groups, visit the official FIFA World Cup 2026 standings page.", "tag": "general", "time": "Live"},
    ],
    'injuries': [
        {"headline": "Lamine Yamal Fitness Doubt for Spain", "body": "Spain forward Lamine Yamal is reportedly not feeling 100% fit and may not start against Saudi Arabia, according to team sources.", "tag": "injury", "time": "Recent"},
        {"headline": "Brazil Striker Continues to Battle Injury Concerns", "body": "Brazil's record goal-scorer continues to manage fitness issues after being named in the World Cup squad, but is expected to feature against Germany.", "tag": "injury", "time": "Recent"},
        {"headline": "Check Official Team News Before Each Matchday", "body": "Visit FIFA.com match pages for the latest confirmed lineups, injury updates and team news ahead of each fixture.", "tag": "injury", "time": "Ongoing"},
    ],
    'transfers': [
        {"headline": "World Cup Performances Drawing Transfer Interest", "body": "Strong individual displays during the group stage are reportedly drawing interest from major European clubs, as is typical during World Cup tournaments.", "tag": "general", "time": "Ongoing"},
        {"headline": "Golden Boot Contenders Could See Transfer Value Rise", "body": "Players among the leading scorers in the Golden Boot race may see increased transfer interest as the tournament progresses.", "tag": "general", "time": "Ongoing"},
    ],
}
