import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os

# --------------------------
# Page Config and CSS
# --------------------------
st.set_page_config(page_title="DRC Congo Positioning", layout="centered")
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1024px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Data Loading with Caching
# --------------------------
@st.cache_data
def load_location_data():
    return pd.read_csv("drc_admin_data.csv")

@st.cache_data
def load_hospital_data():
    return pd.read_csv("drc_health_data.csv")

@st.cache_data
def load_port_data():
    return pd.read_csv("drc_port_data.csv")

@st.cache_data
def load_admin2_geojson():
    # Ensure the GeoJSON file is in the same folder or update the path as needed
    if os.path.exists("drc_admin2.geojson"):
        with open("drc_admin2.geojson", "r") as f:
            return json.load(f)
    else:
        st.warning("Admin2 polygon file not found.")
        return None

try:
    data = load_location_data()
except Exception as e:
    st.error(f"Error reading location CSV file: {e}")
    st.stop()

# --------------------------
# Title and Dropdowns in Columns
# --------------------------

st.markdown(
        "<div style='display: flex; justify-content: center;'>" 
        "<h2>DRC Congo Positioning</h2>"
        "</div>",
        unsafe_allow_html=True,

)

#st.title("DRC Congo Positioning")
st.write("This app allows you to select a location in the Democratic Republic of the Congo and visualize it on a map. You can also overlay additional layers such as health facilities and ports.")

col1, col2, col3 = st.columns(3)

with col1:
    admin1_options = sorted(data['Admin1'].unique())
    selected_admin1 = st.selectbox('Select Admin Level 1 (Province):', admin1_options)

with col2:
    filtered_data_admin1 = data[data['Admin1'] == selected_admin1]
    admin2_options = sorted(filtered_data_admin1['Admin2'].unique())
    selected_admin2 = st.selectbox('Select Admin Level 2 (District):', admin2_options)

with col3:
    filtered_data_admin2 = filtered_data_admin1[filtered_data_admin1['Admin2'] == selected_admin2]
    admin3_options = sorted(filtered_data_admin2['Admin3'].unique())
    selected_admin3 = st.selectbox('Select Admin Level 3 (Town):', admin3_options)

final_data = filtered_data_admin2[filtered_data_admin2['Admin3'] == selected_admin3]

# --------------------------
# Create the Base Map
# --------------------------
if not final_data.empty:
    # Get the coordinates for the selected record (assuming one unique record)
    lat = final_data.iloc[0]['Lat']
    lon = final_data.iloc[0]['Lon']
    st.write(f"Coordinates for {selected_admin3}: Latitude {lat}, Longitude {lon}")

    # Create a Folium map centered at the selected location
    folium_map = folium.Map(location=[lat, lon], zoom_start=10, tiles='OpenStreetMap')

    # Add a marker for each matching record (if more than one exists)
    for idx, row in final_data.iterrows():
        popup_text = f"{row['Admin1']} | {row['Admin2']} | {row['Admin3']}"
        folium.Marker([row['Lat'], row['Lon']], popup=popup_text).add_to(folium_map)
else:
    st.write("No data found for the selected options.")
    folium_map = folium.Map(location=[0, 0], zoom_start=2)

# --------------------------
# Overlay Admin2 Polygon for the Selected Admin2
# --------------------------
admin2_geojson = load_admin2_geojson()
if admin2_geojson:
    # Filter features that match the selected Admin2
    filtered_features = [
        feature for feature in admin2_geojson.get("features", [])
        if feature.get("properties", {}).get("ADM2_FR") == selected_admin2
    ]
    if filtered_features:
        filtered_geojson = {
            "type": "FeatureCollection",
            "features": filtered_features
        }
        # Create a FeatureGroup for the Admin2 polygon overlay
        admin2_layer = folium.FeatureGroup(name="Admin2 Boundary")
        folium.GeoJson(
            filtered_geojson,
            style_function=lambda feature: {
                'fillColor': 'blue',
                'color': 'blue',
                'weight': 2,
                'fillOpacity': 0.2
            }
        ).add_to(admin2_layer)
        admin2_layer.add_to(folium_map)
    else:
        st.info("No polygon found for the selected Admin2.")

# --------------------------
# Flag to Check if Additional Layers Are Added
# --------------------------
layers_added = False

# --------------------------
# Text before the Checkboxes
# --------------------------

st.markdown("<b>Layers</b>", unsafe_allow_html=True)
st.write("Select the layers you want to display on the map. Since the data is loaded from CSV files, it may take a few seconds for the layers to fully load and appear correctly.")

# --------------------------
# Checkbox for Hospital Layer
# --------------------------
if st.checkbox("Show Health Facilities Layer"):
    try:
        hospital_data = load_hospital_data()
    except Exception as e:
        st.error(f"Error reading hospital CSV file: {e}")
    else:
        hospital_layer = folium.FeatureGroup(name="Hospitals")
        for idx, row in hospital_data.iterrows():
            popup_text = f"Hospital: {row['Name']}"
            folium.Marker(
                [row['Lat'], row['Lon']],
                popup=popup_text,
                icon=folium.Icon(color='red', icon='plus-sign')
            ).add_to(hospital_layer)
        hospital_layer.add_to(folium_map)
        layers_added = True

# --------------------------
# Checkbox for Port Layer
# --------------------------
if st.checkbox("Show Ports Layer"):
    try:
        port_data = load_port_data()
    except Exception as e:
        st.error(f"Error reading port CSV file: {e}")
    else:
        port_layer = folium.FeatureGroup(name="Ports")
        for idx, row in port_data.iterrows():
            popup_text = f"Port: {row['Name']}"
            folium.Marker(
                [row['Lat'], row['Lon']],
                popup=popup_text,
                icon=folium.Icon(color='green', icon='plus-sign')
            ).add_to(port_layer)
        port_layer.add_to(folium_map)
        layers_added = True

# Add a single LayerControl if any additional layers have been added
if layers_added or admin2_geojson:
    folium.LayerControl().add_to(folium_map)

# --------------------------
# Render the Map in Streamlit
# --------------------------
st_folium(folium_map, width="100%", height=400)
