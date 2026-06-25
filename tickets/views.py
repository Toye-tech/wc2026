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
# PUBLIC VIEW — visible to all visitors
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
            try:
                b = Booking.objects.get(paystack_reference=reference)
                b.payment_status = 'success'
                b.save()
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


# ============================================================
# LIVE UPDATES PAGE + NEWS API
# ============================================================
def updates(request):
    return render(request, 'tickets/updates.html')


def api_news_feed(request):
    """Returns curated WC2026 news content for the live updates page."""
    topic = request.GET.get('topic', 'latest')
    return JsonResponse({'success': True, 'articles': NEWS_SEED.get(topic, NEWS_SEED['latest'])})


# Content current as of June 25, 2026 — final round of group stage matches underway.
# Morocco and South Africa are the first African nations confirmed for the Round of 32.
NEWS_SEED = {
    'latest': [
        {"headline": "Final Group Stage Matchday Underway", "body": "The 2026 World Cup has reached the final round of group games. Morocco and South Africa have already booked their places in the Round of 32, with seven more African nations still fighting for qualification.", "tag": "breaking", "time": "Live now"},
        {"headline": "Morocco Beat Haiti 4-2 in Six-Goal Thriller", "body": "The Atlas Lions came from behind twice in Atlanta before goals from Hakimi, Saibari, Rahimi and Yassine sealed the win and a Round of 32 spot — Morocco's standout campaign continues unbeaten.", "tag": "african", "time": "Today"},
        {"headline": "South Africa Edge Korea Republic 1-0", "body": "Thapelo Maseko's strike in Monterrey sent Bafana Bafana into the knockout stage for the first time in tournament history, finishing second in Group A behind Mexico.", "tag": "african", "time": "Today"},
        {"headline": "Brazil Thrash Scotland 3-0 in Miami", "body": "A Vinicius Junior brace put Scotland's qualification hopes at the mercy of other results, as Brazil cruised through Group C alongside Morocco.", "tag": "result", "time": "Today"},
        {"headline": "Golden Boot Race Heats Up", "body": "Several players have found the net multiple times through the group stage, with the race for the adidas Golden Boot tightening heading into the knockout rounds.", "tag": "general", "time": "Today"},
    ],
    'results': [
        {"headline": "Morocco 4-2 Haiti", "body": "Morocco came from behind twice to win an entertaining Group C finale in Atlanta, finishing the group stage unbeaten and into the Round of 32.", "tag": "result", "time": "Today"},
        {"headline": "South Africa 1-0 Korea Republic", "body": "Thapelo Maseko's goal secured South Africa's first ever knockout-stage qualification, finishing second in Group A.", "tag": "result", "time": "Today"},
        {"headline": "Brazil 3-0 Scotland", "body": "Vinicius Junior scored twice as Brazil eased through Group C, leaving Scotland needing help from other results to advance.", "tag": "result", "time": "Today"},
        {"headline": "Mexico 3-0 Czechia", "body": "Co-hosts Mexico finished top of Group A with a comfortable win, extending their unbeaten run at their home World Cup.", "tag": "result", "time": "Today"},
        {"headline": "Switzerland 3-1 Canada", "body": "Switzerland topped Group B with victory over co-hosts Canada, who still progress as one of the strongest third-placed teams.", "tag": "result", "time": "Today"},
        {"headline": "Bosnia and Herzegovina 3-1 Qatar", "body": "Bosnia and Herzegovina secured an impressive Group B campaign, eliminating Qatar from the tournament.", "tag": "result", "time": "Today"},
    ],
    'african': [
        {"headline": "Morocco and South Africa Through — Seven Nations Still Fighting", "body": "Morocco and South Africa became the first African teams to secure Round of 32 spots. Cape Verde, Senegal, Egypt, Algeria, DR Congo, Ghana and Ivory Coast all still have realistic qualification hopes heading into the final matchday.", "tag": "african", "time": "Live now"},
        {"headline": "Tunisia's Campaign Ends", "body": "Tunisia have been eliminated from the group stage, the only African nation of the ten qualifiers confirmed out so far as the final round of fixtures plays out.", "tag": "african", "time": "Today"},
        {"headline": "Egypt Face Iran in Group G Decider", "body": "Mohamed Salah's Egypt take on Iran in Seattle with a Round of 32 spot on the line, after results so far in Group G left the picture wide open.", "tag": "african", "time": "Upcoming"},
        {"headline": "Senegal's Tough Group Ends in Heartbreak Bid", "body": "Sadio Mane's Senegal lost both completed Group I fixtures to France and Norway, leaving their fate dependent on the final round of group matches and other results.", "tag": "african", "time": "Today"},
        {"headline": "Record African Representation: 10 Nations at WC2026", "body": "With the expansion to 48 teams, ten African nations qualified for the first time — Algeria, Cape Verde, DR Congo, Egypt, Ghana, Ivory Coast, Morocco, Senegal, South Africa and Tunisia — Africa's strongest ever World Cup showing.", "tag": "african", "time": "Ongoing"},
    ],
    'standings': [
        {"headline": "Group A Final: Mexico 1st, South Africa 2nd", "body": "Mexico finished top of Group A unbeaten, with South Africa securing second place and a historic first knockout-stage berth ahead of Korea Republic and Czechia.", "tag": "general", "time": "Final"},
        {"headline": "Group B Final: Switzerland 1st, Bosnia 2nd", "body": "Switzerland topped Group B with Bosnia and Herzegovina taking second. Co-hosts Canada progress as one of the best third-placed teams. Qatar are eliminated.", "tag": "general", "time": "Final"},
        {"headline": "Group C Final: Morocco 1st, Brazil 2nd", "body": "Morocco finished the group stage unbeaten in top spot, with Brazil securing second. Scotland's fate now depends on other results across the third-place table.", "tag": "general", "time": "Final"},
        {"headline": "Full Standings on FIFA.com", "body": "For complete, continuously updated standings across all 12 groups, including the race for the eight best third-place spots, visit the official FIFA World Cup 2026 standings page.", "tag": "general", "time": "Live"},
    ],
    'injuries': [
        {"headline": "Lamine Yamal Managing Fitness Concern", "body": "Spain forward Lamine Yamal has been managing a minor fitness issue through the group stage but remains available for selection, per team sources.", "tag": "injury", "time": "Recent"},
        {"headline": "Canada's Ismael Kone Sidelined", "body": "Canada midfielder Ismael Kone suffered a serious injury earlier in the tournament after a heavy tackle, with the offending player handed a five-match suspension.", "tag": "injury", "time": "Recent"},
        {"headline": "Check Official Team News Before Each Matchday", "body": "Visit FIFA.com match pages for the latest confirmed lineups, injury updates and team news ahead of the Round of 32 fixtures.", "tag": "injury", "time": "Ongoing"},
    ],
    'transfers': [
        {"headline": "Standout Group Stage Performers Drawing Transfer Interest", "body": "Several breakout performers from the group stage — including players from Morocco, Brazil and Switzerland — are reportedly drawing transfer interest from major European clubs, as is typical during World Cup tournaments.", "tag": "general", "time": "Ongoing"},
        {"headline": "Golden Boot Contenders Could See Transfer Value Rise", "body": "Players among the leading scorers in the Golden Boot race may see increased transfer interest as the tournament moves into the knockout rounds.", "tag": "general", "time": "Ongoing"},
    ],
}


# ============================================================
# MATCH PREVIEWS / HIGHLIGHTS (for Live Updates video section)
# ============================================================
def api_match_previews(request):
    """Returns recent played-match highlight videos and upcoming match previews."""
    return JsonResponse({'success': True, 'previews': MATCH_PREVIEWS})


MATCH_PREVIEWS = {
    'played': [
        {
            "home": "Morocco", "away": "Haiti", "score": "4-2", "group": "Group C",
            "venue": "Atlanta Stadium", "date": "June 24, 2026",
            "youtube_id": "37c0v5fkCLI",
            "summary": "Morocco came from behind twice before goals from Hakimi, Saibari, Rahimi and Yassine secured a thrilling win and an unbeaten path to the Round of 32.",
        },
        {
            "home": "South Africa", "away": "Korea Republic", "score": "1-0", "group": "Group A",
            "venue": "Estadio BBVA, Monterrey", "date": "June 24, 2026",
            "youtube_id": "YIngWQ5JFpg",
            "summary": "Thapelo Maseko's second-half strike sent Bafana Bafana into the World Cup knockout stage for the first time in their history.",
        },
        {
            "home": "Brazil", "away": "Scotland", "score": "3-0", "group": "Group C",
            "venue": "Hard Rock Stadium, Miami", "date": "June 24, 2026",
            "youtube_id": "XNCjlRQvKfI",
            "summary": "A Vinicius Junior brace headlined a dominant Brazil display that secured top spot in Group C alongside Morocco.",
        },
        {
            "home": "Mexico", "away": "Czechia", "score": "3-0", "group": "Group A",
            "venue": "Estadio Azteca, Mexico City", "date": "June 24, 2026",
            "youtube_id": "I8U0u-toRvY",
            "summary": "Co-hosts Mexico finished the group stage unbeaten with a commanding win in front of their home crowd at the Azteca.",
        },
    ],
    'upcoming': [
        {
            "home": "Egypt", "away": "Iran", "group": "Group G",
            "venue": "Lumen Field, Seattle", "date": "June 26, 2026", "time": "23:00 GMT",
            "preview": "Mohamed Salah and Egypt need a result in Seattle to keep their Round of 32 hopes alive in a wide-open Group G picture.",
        },
        {
            "home": "Cape Verde", "away": "Saudi Arabia", "group": "Group H",
            "venue": "NRG Stadium, Houston", "date": "June 26, 2026", "time": "20:00 GMT",
            "preview": "Debutants Cape Verde face Saudi Arabia knowing a win could send the tiny island nation into the knockout rounds in historic fashion.",
        },
        {
            "home": "Norway", "away": "France", "group": "Group I",
            "venue": "Gillette Stadium, Foxborough", "date": "June 26, 2026", "time": "15:00 GMT",
            "preview": "France have already booked their spot, but Norway need a big result here while Senegal watch the outcome closely from the sidelines.",
        },
        {
            "home": "Panama", "away": "England", "group": "Group L",
            "venue": "MetLife Stadium, New Jersey", "date": "June 27, 2026", "time": "TBC",
            "preview": "England look to seal top spot in Group L as Ghana's Croatia clash plays out simultaneously with knockout implications for both African and European sides.",
        },
    ],
}
