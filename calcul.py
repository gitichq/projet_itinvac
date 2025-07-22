import psycopg2
import requests
import json # Pour pretty print la réponse JSON si besoin

# --- Configuration de la base de données ---
DB_CONFIG = {
    "host": "localhost",      # <--- Important !
    "database": "itineraire_db",
    "port": "5433",
    "user": "voyage",
    "password": "secret"
}

# --- Configuration de l'API de Calcul d'Itinéraire ---
# REMPLACEZ 'VOTRE_CLE_API_GOOGLE' PAR VOTRE VRAIE CLÉ API GOOGLE
# Si vous utilisez une autre API, adaptez l'URL et les paramètres
API_KEY = "VOTRE_CLE_API_GOOGLE" 
DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

def connect_db():
    """Établit une connexion à la base de données."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connecté à la base de données.")
        return conn
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        return None

def get_poi_coordinates(conn, poi_name):
    """Récupère la latitude et la longitude d'un POI par son nom."""
    cursor = conn.cursor()
    try:
        sql = "SELECT latitude, longitude FROM point_interet_touristique WHERE nom ILIKE %s;"
        # Utilisez ILIKE pour une recherche insensible à la casse
        cursor.execute(sql, (f'%{poi_name}%',)) # Ajoute des jokers pour une recherche partielle
        result = cursor.fetchone()
        if result:
            return result[0], result[1] # latitude, longitude
        else:
            print(f"POI '{poi_name}' non trouvé dans la base de données.")
            return None, None
    except Exception as e:
        print(f"Erreur lors de la récupération des coordonnées du POI '{poi_name}': {e}")
        return None, None
    finally:
        cursor.close()

def calculate_route(origin_lat, origin_lon, destination_lat, destination_lon, mode="driving"):
    """
    Calcule l'itinéraire entre deux points en utilisant l'API Google Directions.
    """
    origin = f"{origin_lat},{origin_lon}"
    destination = f"{destination_lat},{destination_lon}"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode, # driving, walking, bicycling, transit
        "key": API_KEY,
        "language": "fr" # Pour avoir les instructions en français
    }

    try:
        response = requests.get(DIRECTIONS_API_URL, params=params)
        response.raise_for_status() # Lève une exception pour les codes d'état HTTP d'erreur (4xx ou 5xx)
        route_data = response.json()
        return route_data
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'appel à l'API de calcul d'itinéraire : {e}")
        return None
    except json.JSONDecodeError:
        print("Erreur : La réponse de l'API n'est pas un JSON valide.")
        print(f"Réponse brute: {response.text}")
        return None

def display_route_info(route_data):
    """Affiche les informations clés de l'itinéraire."""
    if not route_data or route_data.get("status") != "OK":
        print("Impossible de calculer l'itinéraire ou l'API a retourné une erreur.")
        if route_data:
            print(f"Statut de l'API : {route_data.get('status')}")
            print(f"Message d'erreur de l'API : {route_data.get('error_message')}")
        return

    routes = route_data.get("routes", [])
    if not routes:
        print("Aucun itinéraire trouvé.")
        return

    # Prendre la première route suggérée
    main_route = routes[0]
    legs = main_route.get("legs", [])

    for leg in legs:
        print(f"\n--- Itinéraire de {leg['start_address']} à {leg['end_address']} ---")
        print(f"Durée : {leg['duration']['text']}")
        print(f"Distance : {leg['distance']['text']}")

        print("\nÉtapes détaillées :")
        for step in leg.get("steps", []):
            # Supprimer les balises HTML des instructions
            html_instructions = step["html_instructions"]
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_instructions, 'html.parser')
            clean_instructions = soup.get_text()
            
            print(f"- {clean_instructions} ({step['distance']['text']})")

    # Si vous voulez l'URL de la carte (pour Google Maps)
    # Maps_url = f"https://www.google.com/maps/dir/{origin_lat},{origin_lon}/{destination_lat},{destination_lon}"
    # print(f"\nVoir sur Google Maps: {Maps_url}")


def main():
    conn = connect_db()
    if not conn:
        return

    try:
        # --- Demande à l'utilisateur les noms des POI ---
        start_poi_name = input("Entrez le nom du POI de départ : ")
        end_poi_name = input("Entrez le nom du POI d'arrivée : ")

        # --- Récupération des coordonnées depuis la base de données ---
        start_lat, start_lon = get_poi_coordinates(conn, start_poi_name)
        end_lat, end_lon = get_poi_coordinates(conn, end_poi_name)

        if start_lat is None or end_lat is None:
            print("Impossible de récupérer les coordonnées pour un ou les deux POI. Fin du programme.")
            return

        # --- Calcul de l'itinéraire ---
        print("\nCalcul de l'itinéraire...")
        route_data = calculate_route(start_lat, start_lon, end_lat, end_lon)

        # --- Affichage des informations ---
        display_route_info(route_data)

    finally:
        conn.close()
        print("Connexion à la base de données fermée.")

if __name__ == "__main__":
    main()