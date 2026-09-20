import os
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

def generate_mandi_coordinates_cache(data_file, cache_output_file):
    """
    Scans your actual historical database, extracts every unique market in Odisha, 
    and uses Geopy to find and save their real-world latitudes and longitudes.
    """
    print("🌍 Initializing Geopy coordinates locator pipeline...")
    df = pd.read_csv(data_file)
    
    # Get every unique market and its district from your actual database
    unique_markets = df[['market name', 'district name']].drop_duplicates().reset_index(drop=True)
    print(f"📍 Found {len(unique_markets)} real unique Mandis in your processed dataset.")
    
    # Initialize the OpenStreetMap Geocoding client
    geolocator = Nominatim(user_agent="krishibazar_ai_enterprise")
    
    latitudes = []
    longitudes = []
    
    for idx, row in unique_markets.iterrows():
        mandi = row['market name']
        district = row['district name']
        
        # Build a highly precise query string targeting Odisha, India
        query = f"{mandi}, {district}, Odisha, India"
        
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
            else:
                # Fallback to general district town center if specific market address is obscured
                backup_query = f"{district}, Odisha, India"
                fallback_loc = geolocator.geocode(backup_query, timeout=10)
                if fallback_loc:
                    latitudes.append(fallback_loc.latitude)
                    longitudes.append(fallback_loc.longitude)
                else:
                    latitudes.append(20.2961) # Default fallback: Bhubaneswar lat
                    longitudes.append(85.8245) # Default fallback: Bhubaneswar lon
        except Exception as e:
            print(f"⚠️ Network timeout for {mandi}, using default coordinates.")
            latitudes.append(20.2961)
            longitudes.append(85.8245)
            
        # Polite API delay to prevent getting rate-limited by OpenStreetMap servers
        time.sleep(1)
        
    unique_markets['latitude'] = latitudes
    unique_markets['longitude'] = longitudes
    
    os.makedirs(os.path.dirname(cache_output_file), exist_ok=True)
    unique_markets.to_csv(cache_output_file, index=False)
    print(f"💾 Geographic registry safely compiled at: {cache_output_file}\n")

def recommend_best_market_geopy(user_lat, user_lon, predicted_price, cache_file, transport_rate_per_km=6.0):
    """
    Reads the geographic registry, calculates exact geodesic distances to the user's 
    current location, subtracts transit costs, and ranks them by net profit margin.
    """
    if not os.path.exists(cache_file):
        raise FileNotFoundError(f"Coordinate cache missing. Build it first! Path: {cache_file}")
        
    geo_registry = pd.read_csv(cache_file)
    user_coords = (user_lat, user_lon)
    
    recommendations = []
    
    for idx, row in geo_registry.iterrows():
        mandi_name = row['market name']
        district_name = row['district name']
        mandi_coords = (row['latitude'], row['longitude'])
        
        # High-precision ellipsoidal Earth curvature calculation using Geopy's geodesic engine
        direct_distance = geodesic(user_coords, mandi_coords).km
        
        # Multiply by a realistic road-circuit correction coefficient (~1.3x)
        road_distance = direct_distance * 1.3
        
        # Calculate financial logistics parameters
        total_transport_cost = road_distance * transport_rate_per_km
        market_fees = 20.0 # Standard statutory Mandi entry toll
        
        # Calculate Expected Net Yield
        expected_net_price = predicted_price - total_transport_cost - market_fees
        
        recommendations.append({
            "Market": mandi_name,
            "District": district_name,
            "Distance (KM)": round(road_distance, 1),
            "Transport Cost (₹)": round(total_transport_cost, 2),
            "Expected Net Price (₹/q)": round(expected_net_price, 2)
        })
        
    df_rankings = pd.DataFrame(recommendations)
    # Sort from highest net profitability to lowest
    df_rankings = df_rankings.sort_values(by="Expected Net Price (₹/q)", ascending=False).reset_index(drop=True)
    return df_rankings

if __name__ == "__main__":
    RAW_CLEANED_DATA = "data/processed/cleaned_orissa_mandi.csv"
    GEO_CACHE_FILE = "data/processed/mandi_coordinates.csv"
    
    # Phase A: Build your database geographic mapping registry if it doesn't exist yet
    if not os.path.exists(GEO_CACHE_FILE):
        generate_mandi_coordinates_cache(RAW_CLEANED_DATA, GEO_CACHE_FILE)
        
    # Phase B: Test runtime ranking engine calculations
    # Let's mock a farmer using the application from a village outside Cuttack (Lat: 20.4500, Lon: 85.8000)
    # with an ML forecast price threshold evaluated at ₹2,600/quintal
    print("🚚 Evaluating live recommendation rankings with geopy geodesic variables...")
    test_rankings = recommend_best_market_geopy(
        user_lat=20.4500, 
        user_lon=85.8000, 
        predicted_price=2600.0, 
        cache_file=GEO_CACHE_FILE
    )
    
    print("\n🏆 Top 10 Most Profitable Mandis for this Farmer:")
    print(test_rankings.head(10).to_string(index=False))
