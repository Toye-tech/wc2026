from django.core.management.base import BaseCommand
from tickets.models import Venue, Match, TicketCategory


VENUES = [
    {'name': 'Estadio Azteca', 'city': 'Mexico City', 'country': 'Mexico', 'capacity': 87523, 'timezone': 'America/Mexico_City', 'description': 'Iconic stadium that hosted the 1970 and 1986 World Cup finals. The only venue to host three World Cup opening matches.', 'image_url': 'https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800'},
    {'name': 'Estadio Akron', 'city': 'Guadalajara', 'country': 'Mexico', 'capacity': 49850, 'timezone': 'America/Mexico_City', 'description': 'Modern stadium in Guadalajara, home of Club Deportivo Guadalajara.', 'image_url': 'https://images.unsplash.com/photo-1521731978332-9e9e714bdd20?w=800'},
    {'name': 'Estadio BBVA', 'city': 'Monterrey', 'country': 'Mexico', 'capacity': 53500, 'timezone': 'America/Monterrey', 'description': 'State-of-the-art stadium surrounded by mountains in Monterrey.', 'image_url': 'https://images.unsplash.com/photo-1562077981-4d7eafd44932?w=800'},
    {'name': 'BMO Field', 'city': 'Toronto', 'country': 'Canada', 'capacity': 45736, 'timezone': 'America/Toronto', 'description': 'Canada\'s premier football stadium located on the Toronto waterfront.', 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},
    {'name': 'BC Place', 'city': 'Vancouver', 'country': 'Canada', 'capacity': 54500, 'timezone': 'America/Vancouver', 'description': 'Retractable roof stadium in downtown Vancouver with stunning mountain views.', 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},
    {'name': 'MetLife Stadium', 'city': 'New York', 'country': 'USA', 'capacity': 82500, 'timezone': 'America/New_York', 'description': 'Home of the 2026 World Cup Final. Located in East Rutherford, New Jersey.', 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'name': 'Gillette Stadium', 'city': 'Boston', 'country': 'USA', 'capacity': 65878, 'timezone': 'America/New_York', 'description': 'Home of the New England Patriots, located in Foxborough, Massachusetts.', 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'name': 'AT&T Stadium', 'city': 'Dallas', 'country': 'USA', 'capacity': 80000, 'timezone': 'America/Chicago', 'description': 'America\'s most iconic stadium, hosting the most matches of any venue at 9.', 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},
    {'name': 'NRG Stadium', 'city': 'Houston', 'country': 'USA', 'capacity': 72220, 'timezone': 'America/Chicago', 'description': 'Multi-purpose stadium with a retractable roof in Houston, Texas.', 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'name': 'Arrowhead Stadium', 'city': 'Kansas City', 'country': 'USA', 'capacity': 76416, 'timezone': 'America/Chicago', 'description': 'One of the loudest stadiums in the NFL, home of the Kansas City Chiefs.', 'image_url': 'https://images.unsplash.com/photo-1524398767853-7b7b4cb7cfed?w=800'},
    {'name': 'SoFi Stadium', 'city': 'Los Angeles', 'country': 'USA', 'capacity': 70240, 'timezone': 'America/Los_Angeles', 'description': 'Ultra-modern stadium in Inglewood, California, opened in 2020.', 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'name': 'Hard Rock Stadium', 'city': 'Miami', 'country': 'USA', 'capacity': 65326, 'timezone': 'America/New_York', 'description': 'Home of the Miami Dolphins located in Miami Gardens, Florida.', 'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800'},
    {'name': 'Lincoln Financial Field', 'city': 'Philadelphia', 'country': 'USA', 'capacity': 69796, 'timezone': 'America/New_York', 'description': 'Home of the Philadelphia Eagles, site of key 2026 World Cup matches.', 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},
    {'name': 'Levi\'s Stadium', 'city': 'San Francisco', 'country': 'USA', 'capacity': 68500, 'timezone': 'America/Los_Angeles', 'description': 'Home of the San Francisco 49ers in Santa Clara, California.', 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},
    {'name': 'Lumen Field', 'city': 'Seattle', 'country': 'USA', 'capacity': 68740, 'timezone': 'America/Los_Angeles', 'description': 'Home of the Seattle Seahawks and Seattle Sounders FC.', 'image_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800'},
    {'name': 'Mercedes-Benz Stadium', 'city': 'Atlanta', 'country': 'USA', 'capacity': 71000, 'timezone': 'America/New_York', 'description': 'Retractable roof stadium with a unique oculus design in Atlanta, Georgia.', 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},
]


MATCHES = [
    # GROUP A
    {'home': 'Mexico', 'away': 'South Africa', 'date': '2026-06-11', 'time': '15:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Mexico City', 'country': 'Mexico', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800'},
    {'home': 'South Korea', 'away': 'UEFA Play-off D', 'date': '2026-06-11', 'time': '21:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Guadalajara', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1521731978332-9e9e714bdd20?w=800'},
    {'home': 'UEFA Play-off D', 'away': 'South Africa', 'date': '2026-06-18', 'time': '12:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Atlanta', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},
    {'home': 'Mexico', 'away': 'South Korea', 'date': '2026-06-18', 'time': '21:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Guadalajara', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1521731978332-9e9e714bdd20?w=800'},
    {'home': 'UEFA Play-off D', 'away': 'Mexico', 'date': '2026-06-24', 'time': '21:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Mexico City', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800'},
    {'home': 'South Africa', 'away': 'South Korea', 'date': '2026-06-24', 'time': '21:00', 'group': 'group', 'group_name': 'Group A', 'city': 'Monterrey', 'country': 'Mexico', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1562077981-4d7eafd44932?w=800'},

    # GROUP B
    {'home': 'Canada', 'away': 'UEFA Play-off A', 'date': '2026-06-12', 'time': '15:00', 'group': 'group', 'group_name': 'Group B', 'city': 'Toronto', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},
    {'home': 'Qatar', 'away': 'Switzerland', 'date': '2026-06-13', 'time': '15:00', 'group': 'group', 'group_name': 'Group B', 'city': 'San Francisco', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},
    {'home': 'Switzerland', 'away': 'UEFA Play-off A', 'date': '2026-06-18', 'time': '15:00', 'group': 'group', 'group_name': 'Group B', 'city': 'Los Angeles', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'home': 'Canada', 'away': 'Qatar', 'date': '2026-06-18', 'time': '21:00', 'group': 'group', 'group_name': 'Group B', 'city': 'Vancouver', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},
    {'home': 'Switzerland', 'away': 'Canada', 'date': '2026-06-24', 'time': '21:00', 'group': 'group', 'group_name': 'Group B', 'city': 'Vancouver', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},
    {'home': 'UEFA Play-off A', 'away': 'Qatar', 'date': '2026-06-24', 'time': '15:00', 'group': 'group', 'group_name': 'Group B', 'city': 'Seattle', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800'},

    # GROUP C
    {'home': 'Brazil', 'away': 'Morocco', 'date': '2026-06-13', 'time': '18:00', 'group': 'group', 'group_name': 'Group C', 'city': 'New York', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'home': 'Haiti', 'away': 'Scotland', 'date': '2026-06-13', 'time': '21:00', 'group': 'group', 'group_name': 'Group C', 'city': 'Boston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'home': 'Scotland', 'away': 'Morocco', 'date': '2026-06-19', 'time': '18:00', 'group': 'group', 'group_name': 'Group C', 'city': 'Boston', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'home': 'Brazil', 'away': 'Haiti', 'date': '2026-06-19', 'time': '21:00', 'group': 'group', 'group_name': 'Group C', 'city': 'Philadelphia', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},
    {'home': 'Scotland', 'away': 'Brazil', 'date': '2026-06-24', 'time': '18:00', 'group': 'group', 'group_name': 'Group C', 'city': 'Miami', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800'},
    {'home': 'Morocco', 'away': 'Haiti', 'date': '2026-06-24', 'time': '18:00', 'group': 'group', 'group_name': 'Group C', 'city': 'Atlanta', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},

    # GROUP D
    {'home': 'USA', 'away': 'Paraguay', 'date': '2026-06-12', 'time': '21:00', 'group': 'group', 'group_name': 'Group D', 'city': 'Los Angeles', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'home': 'Australia', 'away': 'UEFA Play-off C', 'date': '2026-06-13', 'time': '00:00', 'group': 'group', 'group_name': 'Group D', 'city': 'Vancouver', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},
    {'home': 'USA', 'away': 'Australia', 'date': '2026-06-19', 'time': '15:00', 'group': 'group', 'group_name': 'Group D', 'city': 'Seattle', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800'},
    {'home': 'UEFA Play-off C', 'away': 'Paraguay', 'date': '2026-06-19', 'time': '21:00', 'group': 'group', 'group_name': 'Group D', 'city': 'San Francisco', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},
    {'home': 'UEFA Play-off C', 'away': 'USA', 'date': '2026-06-25', 'time': '22:00', 'group': 'group', 'group_name': 'Group D', 'city': 'Los Angeles', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'home': 'Paraguay', 'away': 'Australia', 'date': '2026-06-25', 'time': '22:00', 'group': 'group', 'group_name': 'Group D', 'city': 'San Francisco', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},

    # GROUP E
    {'home': 'Germany', 'away': 'Curaçao', 'date': '2026-06-14', 'time': '13:00', 'group': 'group', 'group_name': 'Group E', 'city': 'Houston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'home': 'Ivory Coast', 'away': 'Ecuador', 'date': '2026-06-14', 'time': '19:00', 'group': 'group', 'group_name': 'Group E', 'city': 'Philadelphia', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},
    {'home': 'Germany', 'away': 'Ivory Coast', 'date': '2026-06-20', 'time': '16:00', 'group': 'group', 'group_name': 'Group E', 'city': 'Toronto', 'country': 'Canada', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},
    {'home': 'Ecuador', 'away': 'Curaçao', 'date': '2026-06-20', 'time': '20:00', 'group': 'group', 'group_name': 'Group E', 'city': 'Kansas City', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1524398767853-7b7b4cb7cfed?w=800'},
    {'home': 'Ecuador', 'away': 'Germany', 'date': '2026-06-25', 'time': '16:00', 'group': 'group', 'group_name': 'Group E', 'city': 'New York', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'home': 'Curaçao', 'away': 'Ivory Coast', 'date': '2026-06-25', 'time': '16:00', 'group': 'group', 'group_name': 'Group E', 'city': 'Philadelphia', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},

    # GROUP F
    {'home': 'Netherlands', 'away': 'Japan', 'date': '2026-06-14', 'time': '16:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Dallas', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},
    {'home': 'UEFA Play-off B', 'away': 'Tunisia', 'date': '2026-06-14', 'time': '21:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Monterrey', 'country': 'Mexico', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1562077981-4d7eafd44932?w=800'},
    {'home': 'Netherlands', 'away': 'UEFA Play-off B', 'date': '2026-06-20', 'time': '13:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Houston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'home': 'Tunisia', 'away': 'Japan', 'date': '2026-06-21', 'time': '00:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Monterrey', 'country': 'Mexico', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1562077981-4d7eafd44932?w=800'},
    {'home': 'Japan', 'away': 'UEFA Play-off B', 'date': '2026-06-25', 'time': '19:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Dallas', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},
    {'home': 'Tunisia', 'away': 'Netherlands', 'date': '2026-06-25', 'time': '19:00', 'group': 'group', 'group_name': 'Group F', 'city': 'Kansas City', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1524398767853-7b7b4cb7cfed?w=800'},

    # GROUP G
    {'home': 'Belgium', 'away': 'Egypt', 'date': '2026-06-15', 'time': '15:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Seattle', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800'},
    {'home': 'Iran', 'away': 'New Zealand', 'date': '2026-06-15', 'time': '21:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Los Angeles', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'home': 'Belgium', 'away': 'Iran', 'date': '2026-06-21', 'time': '15:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Los Angeles', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800'},
    {'home': 'New Zealand', 'away': 'Egypt', 'date': '2026-06-21', 'time': '21:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Vancouver', 'country': 'Canada', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},
    {'home': 'Egypt', 'away': 'Iran', 'date': '2026-06-26', 'time': '23:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Seattle', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800'},
    {'home': 'New Zealand', 'away': 'Belgium', 'date': '2026-06-26', 'time': '23:00', 'group': 'group', 'group_name': 'Group G', 'city': 'Vancouver', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1600679472829-3044539ce405?w=800'},

    # GROUP H
    {'home': 'Spain', 'away': 'Cape Verde', 'date': '2026-06-15', 'time': '12:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Atlanta', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},
    {'home': 'Saudi Arabia', 'away': 'Uruguay', 'date': '2026-06-15', 'time': '18:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Miami', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800'},
    {'home': 'Spain', 'away': 'Saudi Arabia', 'date': '2026-06-21', 'time': '12:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Atlanta', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},
    {'home': 'Uruguay', 'away': 'Cape Verde', 'date': '2026-06-21', 'time': '18:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Miami', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800'},
    {'home': 'Cape Verde', 'away': 'Saudi Arabia', 'date': '2026-06-26', 'time': '20:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Houston', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'home': 'Uruguay', 'away': 'Spain', 'date': '2026-06-26', 'time': '20:00', 'group': 'group', 'group_name': 'Group H', 'city': 'Guadalajara', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1521731978332-9e9e714bdd20?w=800'},

    # GROUP I
    {'home': 'France', 'away': 'Senegal', 'date': '2026-06-16', 'time': '15:00', 'group': 'group', 'group_name': 'Group I', 'city': 'New York', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'home': 'FIFA Play-off 2', 'away': 'Norway', 'date': '2026-06-16', 'time': '18:00', 'group': 'group', 'group_name': 'Group I', 'city': 'Boston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'home': 'France', 'away': 'FIFA Play-off 2', 'date': '2026-06-22', 'time': '17:00', 'group': 'group', 'group_name': 'Group I', 'city': 'Philadelphia', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},
    {'home': 'Norway', 'away': 'Senegal', 'date': '2026-06-22', 'time': '20:00', 'group': 'group', 'group_name': 'Group I', 'city': 'New York', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'home': 'Norway', 'away': 'France', 'date': '2026-06-26', 'time': '15:00', 'group': 'group', 'group_name': 'Group I', 'city': 'Boston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'home': 'Senegal', 'away': 'FIFA Play-off 2', 'date': '2026-06-26', 'time': '15:00', 'group': 'group', 'group_name': 'Group I', 'city': 'Toronto', 'country': 'Canada', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},

    # GROUP J
    {'home': 'Argentina', 'away': 'Algeria', 'date': '2026-06-16', 'time': '21:00', 'group': 'group', 'group_name': 'Group J', 'city': 'Kansas City', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1524398767853-7b7b4cb7cfed?w=800'},
    {'home': 'Austria', 'away': 'Jordan', 'date': '2026-06-17', 'time': '00:00', 'group': 'group', 'group_name': 'Group J', 'city': 'San Francisco', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},
    {'home': 'Argentina', 'away': 'Austria', 'date': '2026-06-22', 'time': '13:00', 'group': 'group', 'group_name': 'Group J', 'city': 'Dallas', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},
    {'home': 'Jordan', 'away': 'Algeria', 'date': '2026-06-22', 'time': '23:00', 'group': 'group', 'group_name': 'Group J', 'city': 'San Francisco', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1540747913346-19212a4f3ee9?w=800'},
    {'home': 'Algeria', 'away': 'Austria', 'date': '2026-06-27', 'time': '22:00', 'group': 'group', 'group_name': 'Group J', 'city': 'Kansas City', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1524398767853-7b7b4cb7cfed?w=800'},
    {'home': 'Jordan', 'away': 'Argentina', 'date': '2026-06-27', 'time': '22:00', 'group': 'group', 'group_name': 'Group J', 'city': 'Dallas', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},

    # GROUP K
    {'home': 'Portugal', 'away': 'FIFA Play-off 1', 'date': '2026-06-17', 'time': '13:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Houston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'home': 'Uzbekistan', 'away': 'Colombia', 'date': '2026-06-17', 'time': '22:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Mexico City', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800'},
    {'home': 'Portugal', 'away': 'Uzbekistan', 'date': '2026-06-23', 'time': '13:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Houston', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?w=800'},
    {'home': 'Colombia', 'away': 'FIFA Play-off 1', 'date': '2026-06-23', 'time': '22:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Guadalajara', 'country': 'Mexico', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1521731978332-9e9e714bdd20?w=800'},
    {'home': 'Colombia', 'away': 'Portugal', 'date': '2026-06-27', 'time': '19:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Miami', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800'},
    {'home': 'FIFA Play-off 1', 'away': 'Uzbekistan', 'date': '2026-06-27', 'time': '19:00', 'group': 'group', 'group_name': 'Group K', 'city': 'Atlanta', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1556056504-5c7696c4c28d?w=800'},

    # GROUP L
    {'home': 'England', 'away': 'Croatia', 'date': '2026-06-17', 'time': '16:00', 'group': 'group', 'group_name': 'Group L', 'city': 'Dallas', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800'},
    {'home': 'Ghana', 'away': 'Panama', 'date': '2026-06-17', 'time': '19:00', 'group': 'group', 'group_name': 'Group L', 'city': 'Toronto', 'country': 'Canada', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},
    {'home': 'England', 'away': 'Ghana', 'date': '2026-06-23', 'time': '16:00', 'group': 'group', 'group_name': 'Group L', 'city': 'Boston', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=800'},
    {'home': 'Panama', 'away': 'Croatia', 'date': '2026-06-23', 'time': '19:00', 'group': 'group', 'group_name': 'Group L', 'city': 'Toronto', 'country': 'Canada', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800'},
    {'home': 'Panama', 'away': 'England', 'date': '2026-06-27', 'time': '17:00', 'group': 'group', 'group_name': 'Group L', 'city': 'New York', 'country': 'USA', 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1567521464027-f127ff144326?w=800'},
    {'home': 'Croatia', 'away': 'Ghana', 'date': '2026-06-27', 'time': '17:00', 'group': 'group', 'group_name': 'Group L', 'city': 'Philadelphia', 'country': 'USA', 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800'},
]

TICKET_CATEGORIES = [
    {'name': 'cat3', 'price_usd': 75, 'total_seats': 2000, 'description': 'Affordable seating with full match experience. Upper tier with panoramic stadium views.', 'perks': 'Match programme,Stadium access'},
    {'name': 'cat2', 'price_usd': 100, 'total_seats': 1000, 'description': 'Great atmosphere in the mid-tier sections. Excellent sightlines to the pitch.', 'perks': 'Match programme,Priority entry,Stadium access'},
    {'name': 'cat1', 'price_usd': 150, 'total_seats': 500, 'description': 'Premium lower-tier seating closest to the action. Best views in the stadium.', 'perks': 'Match programme,Priority entry,Premium lounge access,Dedicated concierge'},
    {'name': 'hospitality', 'price_usd': 500, 'total_seats': 100, 'description': 'Full VIP hospitality package with exclusive lounge access and gourmet dining.', 'perks': 'VIP lounge access,Gourmet dining,Open bar,Match programme,Priority entry,Dedicated concierge,Exclusive gifts'},
]


class Command(BaseCommand):
    help = 'Load all FIFA World Cup 2026 matches, venues and ticket categories'

    def handle(self, *args, **kwargs):
        self.stdout.write('🏟️  Loading venues...')
        venue_map = {}
        for v in VENUES:
            venue, created = Venue.objects.get_or_create(
                name=v['name'],
                defaults={
                    'city': v['city'],
                    'country': v['country'],
                    'capacity': v['capacity'],
                    'timezone': v['timezone'],
                    'description': v['description'],
                    'image_url': v['image_url'],
                }
            )
            venue_map[v['city']] = venue
            status = '✅ Created' if created else '⏭️  Exists'
            self.stdout.write(f'  {status}: {v["name"]}, {v["city"]}')

        self.stdout.write(f'\n⚽ Loading {len(MATCHES)} matches...')
        for m in MATCHES:
            from datetime import date, time as dtime
            match_date = date.fromisoformat(m['date'])
            h, mi = map(int, m['time'].split(':'))
            match_time = dtime(h, mi)

            match, created = Match.objects.get_or_create(
                team_home=m['home'],
                team_away=m['away'],
                match_date=match_date,
                defaults={
                    'match_time': match_time,
                    'group_stage': m['group'],
                    'group_name': m['group_name'],
                    'city': m['city'],
                    'country': m['country'],
                    'featured': m['featured'],
                    'status': 'available',
                    'image_url': m['image_url'],
                    'venue': venue_map.get(m['city']),
                }
            )

            if created:
                # Add ticket categories
                for cat in TICKET_CATEGORIES:
                    TicketCategory.objects.create(
                        match=match,
                        name=cat['name'],
                        price_usd=cat['price_usd'],
                        total_seats=cat['total_seats'],
                        seats_remaining=cat['total_seats'],
                        description=cat['description'],
                        perks=cat['perks'],
                    )
                self.stdout.write(f'  ✅ {m["home"]} vs {m["away"]} — {m["city"]} ({m["group_name"]})')
            else:
                self.stdout.write(f'  ⏭️  Exists: {m["home"]} vs {m["away"]}')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Done! {Match.objects.count()} matches, {Venue.objects.count()} venues loaded.'))