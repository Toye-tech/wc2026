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
# ARCHIVE PAGE + NEWS API
# ============================================================
def updates(request):
    return render(request, 'tickets/updates.html')


def api_news_feed(request):
    """Returns curated WC2026 archive content for the tournament archive page."""
    topic = request.GET.get('topic', 'final')
    return JsonResponse({'success': True, 'articles': NEWS_SEED.get(topic, NEWS_SEED['final'])})


# ============================================================
# WC2026 ARCHIVE — TOURNAMENT COMPLETE
# ============================================================
# Content finalized July 20, 2026, the day after the final.
# Spain beat Argentina 1-0 (a.e.t.) at MetLife Stadium on July 19, 2026
# to win their second FIFA World Cup title.
NEWS_SEED = {
    'final': [
        {"headline": "Spain Are World Champions", "body": "Spain beat Argentina 1-0 after extra time at MetLife Stadium to win their second FIFA World Cup title. Substitute Ferran Torres scored the only goal in the 106th minute, capping a tournament in which Spain conceded just a single goal in seven matches.", "tag": "breaking", "time": "Jul 19, 2026"},
        {"headline": "Argentina's Title Defense Falls Short", "body": "Argentina were unable to become the first back-to-back champions since Brazil in 1962. Lionel Messi, playing what is widely expected to be his last World Cup, left the field after collecting a runners-up medal.", "tag": "result", "time": "Jul 19, 2026"},
        {"headline": "Rodri Named Golden Ball Winner", "body": "Spain midfielder Rodri was named the tournament's best player, anchoring a Spanish side built around a defensive masterclass through the knockout rounds.", "tag": "general", "time": "Jul 19, 2026"},
        {"headline": "Mbappe Finishes as All-Time World Cup Top Scorer", "body": "France's Kylian Mbappe won the Golden Boot as top scorer and, with two goals in the third-place match, moved to the top of the World Cup's all-time scoring list.", "tag": "general", "time": "Jul 19, 2026"},
        {"headline": "England Take Third Place in Six-Goal Thriller", "body": "England beat France 6-4 in the third-place match, with Bukayo Saka scoring a hat-trick and a Jude Bellingham goal in stoppage time settling an extraordinary contest.", "tag": "result", "time": "Jul 18, 2026"},
    ],
    'knockout': [
        {"headline": "Final: Spain 1-0 Argentina (a.e.t.)", "body": "Ferran Torres scored the only goal in the 106th minute at MetLife Stadium, East Rutherford. Goalkeeper Emiliano Martinez made 11 saves for Argentina but couldn't prevent Spain's second World Cup title.", "tag": "result", "time": "Jul 19"},
        {"headline": "Semi-final: Spain 2-0 France", "body": "Spain controlled the game throughout to reach a second World Cup final, ending France's bid for back-to-back appearances in the showpiece match.", "tag": "result", "time": "Jul 15"},
        {"headline": "Semi-final: Argentina 2-1 England", "body": "Argentina scored twice late to stun England and reach the final as defending champions, keeping alive their hopes of a historic repeat title.", "tag": "result", "time": "Jul 14"},
        {"headline": "Quarter-final: France 2-0 Morocco", "body": "Kylian Mbappe and Ousmane Dembele scored second-half goals in Boston as France ended Morocco's run, denying the Atlas Lions a first-ever World Cup semi-final since their historic 2022 run.", "tag": "result", "time": "Jul 9"},
        {"headline": "Quarter-final: Spain 2-1 Belgium", "body": "Spain edged past Belgium to continue their unbeaten run through the knockout stage on the way to the final.", "tag": "result", "time": "Jul 10"},
        {"headline": "Quarter-final: England 2-1 Norway (a.e.t.)", "body": "England needed extra time to see off Norway and book a semi-final meeting with Argentina.", "tag": "result", "time": "Jul 11"},
        {"headline": "Quarter-final: Argentina 3-1 Switzerland (a.e.t.)", "body": "Argentina came through extra time against Switzerland to reach the semi-finals as they continued their title defense.", "tag": "result", "time": "Jul 11"},
        {"headline": "Round of 16: Co-Hosts All Eliminated", "body": "Canada, Mexico and the USA were each knocked out in the Round of 16 — Canada lost to Morocco, Mexico fell to England, and the USMNT were beaten by Belgium — ending the host nations' campaigns before the quarterfinals.", "tag": "general", "time": "Late Jun / early Jul"},
    ],
    'african': [
        {"headline": "Morocco's Campaign Ends in the Quarterfinals", "body": "Morocco reached the last eight before falling 2-0 to France, a strong follow-up to their historic run to the semi-finals in 2022. They finished as Africa's best-performing side at WC2026.", "tag": "african", "time": "Final result"},
        {"headline": "South Africa Reach a First-Ever Knockout Round", "body": "Bafana Bafana made history by qualifying for the Round of 32 for the first time, before a stoppage-time strike from Canada's Stephen Eustaquio ended their run 1-0.", "tag": "african", "time": "Final result"},
        {"headline": "Ten African Nations, a Record Turnout", "body": "With the expansion to 48 teams, ten African nations reached the finals for the first time in tournament history — Algeria, Cape Verde, DR Congo, Egypt, Ghana, Ivory Coast, Morocco, Senegal, South Africa and Tunisia — Africa's largest-ever World Cup representation.", "tag": "african", "time": "Tournament summary"},
        {"headline": "A Mixed Knockout Round for the Continent", "body": "Beyond Morocco and South Africa's historic runs, the rest of Africa's ten qualifiers were eliminated across the group stage and Round of 32, a reminder of how competitive the expanded 48-team format has become.", "tag": "african", "time": "Tournament summary"},
    ],
    'awards': [
        {"headline": "Golden Ball: Rodri (Spain)", "body": "Rodri was named the tournament's outstanding player after marshalling Spain's midfield through a run that conceded only a single goal across seven matches.", "tag": "general", "time": "Final awards"},
        {"headline": "Golden Boot: Kylian Mbappe (France)", "body": "Mbappe finished as the tournament's top scorer and, with his goals in the third-place match, became the World Cup's all-time leading scorer.", "tag": "general", "time": "Final awards"},
        {"headline": "Spain's Historic Defensive Record", "body": "Spain became the first World Cup champion to win the title while conceding only a single goal across the entire tournament.", "tag": "general", "time": "Tournament stat"},
        {"headline": "A 48-Team World Cup for the Record Books", "body": "The first edition to feature 48 teams delivered a record number of matches and the widest global representation in the tournament's history, including ten African nations.", "tag": "general", "time": "Tournament stat"},
    ],
    'whats_next': [
        {"headline": "Spain Hold Both World Cup Titles", "body": "With the men's title added to Spain's existing women's World Cup crown, Spain became the first nation to hold both titles at the same time.", "tag": "general", "time": "Looking ahead"},
        {"headline": "Messi's World Cup Chapter Likely Closed", "body": "Lionel Messi has indicated the 2026 tournament was his last World Cup appearance, closing out one of the competition's defining individual careers.", "tag": "general", "time": "Looking ahead"},
        {"headline": "Next Stop: 2030 World Cup", "body": "Attention now turns to the 2030 World Cup, set to be jointly hosted across Spain, Portugal and Morocco, with additional matches marking the tournament's centenary in South America.", "tag": "general", "time": "Looking ahead"},
        {"headline": "Ticket Booking for WC2026 Is Now Closed", "body": "With the tournament complete, ticket sales and bookings through this site have closed. Existing ticket holders can still look up bookings and confirmations at any time.", "tag": "general", "time": "Site notice"},
    ],
}


# ============================================================
# MATCH HIGHLIGHTS — final rounds only, most relevant to the archive
# ============================================================
def api_match_previews(request):
    """Returns recent played-match highlight videos for the archive page."""
    return JsonResponse({'success': True, 'previews': MATCH_PREVIEWS})


MATCH_PREVIEWS = {
    'played': [
        {
            "home": "Spain", "away": "Argentina", "score": "1-0 (a.e.t.)", "group": "Final",
            "venue": "MetLife Stadium, East Rutherford", "date": "July 19, 2026",
            "youtube_id": "dQw4w9WgXcQ",
            "summary": "Ferran Torres scored the only goal of the final in the 106th minute as Spain won their second World Cup title, capping a tournament in which they conceded just once.",
        },
        {
            "home": "England", "away": "France", "score": "6-4", "group": "Third-place match",
            "venue": "Hard Rock Stadium, Miami", "date": "July 18, 2026",
            "youtube_id": "dQw4w9WgXcQ",
            "summary": "A Bukayo Saka hat-trick and a stoppage-time Jude Bellingham goal secured third place for England in one of the highest-scoring games of the tournament.",
        },
        {
            "home": "Spain", "away": "France", "score": "2-0", "group": "Semi-final",
            "venue": "SoFi Stadium, Los Angeles", "date": "July 15, 2026",
            "youtube_id": "dQw4w9WgXcQ",
            "summary": "Spain controlled the semi-final from start to finish to reach their second World Cup final.",
        },
        {
            "home": "Argentina", "away": "England", "score": "2-1", "group": "Semi-final",
            "venue": "AT&T Stadium, Arlington", "date": "July 14, 2026",
            "youtube_id": "dQw4w9WgXcQ",
            "summary": "Argentina scored twice late to overturn England and reach the final as they defended their 2022 title.",
        },
        {
            "home": "France", "away": "Morocco", "score": "2-0", "group": "Quarter-final",
            "venue": "Boston Stadium", "date": "July 9, 2026",
            "youtube_id": "dQw4w9WgXcQ",
            "summary": "Kylian Mbappe and Ousmane Dembele scored in the second half as France ended Morocco's tournament, denying the Atlas Lions a second consecutive World Cup semi-final.",
        },
    ],
    'upcoming': [],  # tournament complete — no upcoming matches to show
}

# NOTE ON YOUTUBE IDS: the placeholder id above (dQw4w9WgXcQ) needs to be
# swapped for the actual FIFA/broadcaster highlight video IDs for each match
# before this goes live — there's no verified source for the real video IDs
# here, so don't ship these as-is.
