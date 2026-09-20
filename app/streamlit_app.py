import streamlit as st
import requests
import pandas as pd

# Set up clean professional dashboard styling configuration
st.set_page_config(
    page_title="KrishiBazar AI",
    page_icon="🌾",
    layout="wide"
)

# Set up global bridge link pointing directly to your live FastAPI backend server
BACKEND_API_URL = "http://127.0.0.1:8000/recommend-market"

# Header Panel
st.title("🌾 KrishiBazar AI")
st.subheader("Smart Crop Price Forecasting & Best Market Recommendation System")
st.markdown("---")

# Main Page Split Layout: Inputs on the Left Sidebar, Visual Data Outputs on the Right
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📍 Farmer Inputs")
    
    # 1. Dropdown Selector for MVP Commodities
    selected_crop = st.selectbox(
        "Select your Crop:",
        ["Tomato", "Potato", "Onion", "Wheat", "Maize"]
    )
    
    st.markdown("### Your Current Location Coordinates")
    # 2. Coordinates inputs (Preset to geographic Cuttack area for testing)
    user_lat = st.number_input("Latitude:", value=20.4500, format="%.4f")
    user_lon = st.number_input("Longitude:", value=85.8000, format="%.4f")
    
    st.markdown("---")
    # Action submission trigger button
    submit_button = st.button("🚀 Calculate Best Market", use_container_width=True)

with col2:
    st.header("📊 Market Insights Dashboard")
    
    if submit_button:
        # Wrap up UI inputs into a clean structured dictionary package
        payload = {
            "crop": selected_crop,
            "user_latitude": user_lat,
            "user_longitude": user_lon
        }
        
        with st.spinner("⏳ Querying machine learning models & calculating logistics costs..."):
            try:
                # Fire off the secure network data request package directly to your FastAPI backend
                response = requests.post(BACKEND_API_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 1. Pull core output numbers and render big metrics
                    base_price = data["predicted_base_price_per_q"]
                    st.success(f"🔮 Machine Learning Predicted Price Matrix for {selected_crop}: **₹{base_price:,.2f} per Quintal**")
                    
                    # 2. Extract ranked recommendation lists
                    rec_records = data["recommendations"]
                    df_results = pd.DataFrame(rec_records)
                    
                    # Break out top winning market choices cleanly
                    best_mandi = df_results.iloc[0]
                    
                    st.markdown("### 🏆 Top Recommended Marketplace Choice")
                    metric_cols = st.columns(3)
                    metric_cols[0].metric(label="🏆 Best Market Name", value=str(best_mandi["Market"]))
                    metric_cols[1].metric(label="🚚 Road Proximity", value=f"{best_mandi['Distance (KM)']} KM")
                    metric_cols[2].metric(label="💰 Expected Net Return", value=f"₹{best_mandi['Expected Net Price (₹/q)']:,.2f}")
                    
                    # 3. Render the broader sorted comparison data table
                    st.markdown("### 📋 Nearby Ranked Mandi Breakdown Matrix")
                    st.dataframe(
                        df_results,
                        column_config={
                            "Expected Net Price (₹/q)": st.column_config.NumberColumn(format="₹%.2f"),
                            "Transport Cost (₹)": st.column_config.NumberColumn(format="₹%.2f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                else:
                    st.error(f"❌ Backend System Error: Received status code {response.status_code}")
                    
            except Exception as e:
                st.error(f"⚠️ Connection Failure: Could not communicate with server bridge. Ensure your API is running. Error details: {str(e)}")
    else:
        # Neutral state guidance banner when app boots up
        st.info("💡 Adjust your location parameters on the sidebar and click 'Calculate Best Market' to see optimized economic routing.")
