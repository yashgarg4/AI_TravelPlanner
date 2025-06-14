try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass # Fallback to system sqlite3 if pysqlite3-binary is not found (e.g., local dev)
import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import litellm
import re
from io import BytesIO
from xhtml2pdf import pisa
import markdown

# Load environment variables from .env file
load_dotenv()

os.environ['LITELLM_LOG'] = 'DEBUG'
litellm.set_verbose=True 

TARGET_GEMINI_MODEL = "gemini-1.5-flash-latest"

litellm.register_model({
    TARGET_GEMINI_MODEL: {
        "model_name": TARGET_GEMINI_MODEL, 
        "litellm_provider": "gemini",       
        "api_key": os.getenv("GEMINI_API_KEY"),
        "api_base": "https://generativelanguage.googleapis.com/v1beta" 
    },
    # Fallback for the problematic "models/" prefix if LiteLLM internally generates it
    f"models/{TARGET_GEMINI_MODEL}": {
        "model_name": TARGET_GEMINI_MODEL,  
        "litellm_provider": "gemini",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "api_base": "https://generativelanguage.googleapis.com/v1beta"
    }
})

st.set_page_config(page_title="AI Travel Planner", layout="wide")

# --- Configure LLM (Google Gemini) ---
gemini_api_key_env = os.getenv("GEMINI_API_KEY")
llm_langchain_init_success = False 
st.title("✈️ Personalized Travel Itinerary Planner")
st.markdown("Let AI craft your next adventure! Tell us your preferences, and we'll generate a personalized itinerary.")

if gemini_api_key_env:
    try:
        ChatGoogleGenerativeAI(model=TARGET_GEMINI_MODEL, google_api_key=gemini_api_key_env)
        llm_langchain_init_success = True
    except Exception as e:
        st.sidebar.error(f"❌ Failed to initialize LLM: {e}")
else:
    st.sidebar.warning("🔴 GEMINI_API_KEY not found in .env file. Please set it.")

# --- Serper API Key Check ---
serper_api_key_set = os.getenv("SERPER_API_KEY") is not None
if not serper_api_key_set:
    st.sidebar.warning("🟡 SERPER_API_KEY environment variable not set. Search quality might be reduced.")

# --- Initialize Tools ---
try:
    if serper_api_key_set:
        search_tool = SerperDevTool()
    else:
        search_tool = WebsiteSearchTool()
        st.warning("⚠️ Serper API key not found, using WebsiteSearchTool (DuckDuckGo) as fallback.")
except Exception as e:
    st.error(f"❌ Failed to initialize search tool: {e}. Please check API keys/internet.")
    search_tool = WebsiteSearchTool() # Fallback

scrape_tool = ScrapeWebsiteTool()

# --- Define Agents Globally ---
# Define the LLM identifier string for CrewAI agents
agent_llm_identifier = f"gemini/{TARGET_GEMINI_MODEL}"

destination_analyst = Agent(
    role='Lead Destination Analyst',
    goal='Gather key facts, cultural insights, must-see general attractions, safety tips, key local emergency contact numbers (e.g., police, ambulance, general emergency), 3-5 basic local phrases (e.g., hello, thank you, goodbye with simple phonetic pronunciations if possible), and 1-2 crucial cultural etiquette tips for {destination}.',
    backstory='You are a seasoned travel writer with an encyclopedic knowledge of global destinations, always ensuring travelers are well-informed with practical cultural nuances.',
    verbose=True,
    allow_delegation=False,
    tools=[search_tool, scrape_tool],
    llm=agent_llm_identifier
)

activity_interest_specialist = Agent(
    role='Activity and Interest Specialist',
    goal='Based on user interests ({interests}) and budget ({budget_level}), find specific activities, attractions, restaurants, and experiences in {destination}.',
    backstory='You have a knack for finding unique and fitting experiences that match individual tastes and budgets, from hidden gems to popular hotspots.',
    verbose=True,
    allow_delegation=False,
    tools=[search_tool, scrape_tool],
    llm=agent_llm_identifier
)

itinerary_synthesizer = Agent(
    role='Master Itinerary Planner',
    goal='Create a balanced, exciting, and practical day-by-day travel itinerary for {duration_of_trip} in {destination}. The itinerary must incorporate user interests ({interests}), consider the {budget_level}, and be logically structured. It should also identify 3-5 key landmarks or points of interest from the itinerary and list them clearly for map plotting. Output in Markdown format.',
    backstory='You are an expert travel planner renowned for crafting memorable and practical itineraries that flow smoothly and maximize enjoyment.',
    verbose=True,
    allow_delegation=False,
    llm=agent_llm_identifier
)

cost_estimator_agent = Agent(
    role='Travel Cost Estimator',
    goal='Provide a rough daily and total trip cost estimation in INR (Indian Rupees) based on the destination ({destination}), trip duration ({duration_of_trip}), user\'s budget level ({budget_level}), and the types of activities planned. Clearly state that these are estimates. Do not look up real-time prices; use general knowledge for estimations.',
    backstory='You are an experienced travel budget advisor who can provide reasonable cost estimates for various travel styles and destinations, helping travelers plan their finances.',
    verbose=True,
    allow_delegation=False,
    llm=agent_llm_identifier
)

# --- Streamlit Input Widgets ---
st.sidebar.header("🌍 Plan Your Trip!")
destination = st.sidebar.text_input("Destination (e.g., Paris, France)")
duration_of_trip = st.sidebar.text_input("Duration of Trip (e.g., 3 days, 1 week)")

interest_options = ["Historical Sites", "Local Cuisine", "Nature & Hiking", "Art & Museums", "Nightlife", "Shopping", "Relaxation", "Adventure Sports"]
selected_interests = st.sidebar.multiselect("Your Interests", interest_options)
interests_string = ", ".join(selected_interests)

budget_level = st.sidebar.selectbox("Budget Level", ["Budget-Friendly", "Mid-Range", "Luxury"], index=1)

if st.sidebar.button("✨ Generate Itinerary"):
    if not gemini_api_key_env: # Check if API key is present
        st.error("🔴 GEMINI_API_KEY not found. Cannot start. Please ensure GEMINI_API_KEY is set in your .env file and is valid.")
    elif not destination or not duration_of_trip or not interests_string:
        st.warning("⚠️ Please fill in all travel details (Destination, Duration, Interests).")
    else:
        st.info(f"🚀 Crafting your personalized itinerary for {destination}...")
        st.info("Please wait, this may take a few minutes (or more for complex trips)...")

        # --- Define Tasks (Inside button click) ---
        destination_analysis_task = Task(
            description='Conduct a comprehensive analysis of {destination}. Gather information on its main attractions, cultural norms, best times to visit, essential travel tips, key local emergency contact numbers (e.g., police, ambulance, general emergency line), 3-5 basic local phrases (like hello, thank you, please, excuse me, goodbye - include simple phonetic pronunciation if available), and 1-2 crucial cultural etiquette tips.',
            expected_output='A summary report on {destination}, including key attractions, cultural notes, travel advice, a list of key local emergency contact numbers, a clearly formatted list of 3-5 basic local phrases with simple pronunciations, and 1-2 important cultural etiquette tips.',
            agent=destination_analyst
        )

        activity_research_task = Task(
            description='Research and identify specific activities, sights, and dining options in {destination} that align with the user\'s interests: {interests} and budget: {budget_level}. Provide a list of at least 5-7 varied suggestions with brief descriptions.',
            expected_output='A curated list of 5-7 activities, sights, and dining options with descriptions, tailored to user preferences and budget.',
            agent=activity_interest_specialist,
            context=[destination_analysis_task]
        )

        cost_estimation_task = Task(
            description='Based on the destination ({destination}), trip duration ({duration_of_trip}), user\'s budget level ({budget_level}), and a general understanding of the types of activities likely to be included (from destination analysis and activity research), provide a rough daily cost estimate and a total trip estimate, both in INR (Indian Rupees). These estimates should cover typical expenses like food, local transport, and minor activities, excluding major international flights and pre-booked accommodation unless specified by the budget level. Clearly label these as "Estimated Daily Cost (INR)" and "Estimated Total Trip Cost (INR, excluding major transit/accommodation)".',
            expected_output='A short section with "Estimated Daily Cost (INR): [Amount Range in INR]" and "Estimated Total Trip Cost (INR, excluding major transit/accommodation): [Amount Range in INR]". For example: "Estimated Daily Cost (INR): ₹3000-₹5000. Estimated Total Trip Cost (INR, excluding major transit/accommodation): ₹15000-₹25000 for 5 days."',
            agent=cost_estimator_agent
        )

        itinerary_generation_task = Task(
            description=(
                'Compile a detailed day-by-day Markdown itinerary for a {duration_of_trip} trip to {destination}, based on destination analysis and activity research. '
                'The itinerary should be engaging, practical (considering travel times between activities if possible), and cater to the user\'s interests: {interests} and budget: {budget_level}. '
                'Also, include the basic local phrases, cultural etiquette tips, and emergency contact numbers obtained from the destination analysis (available in its output) in clearly marked sections (e.g., "Useful Phrases & Etiquette", "Important Contacts") for easy reference. '
                'Incorporate the cost estimation (from the Cost Estimation Task output) into a dedicated "Budget & Cost Estimates" section. '
                'CRITICALLY IMPORTANT: The entire response MUST end with a section starting with the exact, case-sensitive heading: "Key Locations for Map:". '
                'Immediately following this "Key Locations for Map:" heading, list 3-5 prominent landmarks as bullet points. Example of this final section:\n'
                'Key Locations for Map:\n'
                '- Eiffel Tower, Paris\n'
                '- Louvre Museum, Paris\n'
                'Failure to include the "Key Locations for Map:" heading precisely as written, or placing any content after it, will prevent map generation. This section is mandatory and must be the absolute final part of your output. '
                'The main itinerary part should be structured clearly for each day (e.g., Morning, Afternoon, Evening). Format the entire output as a single Markdown string.'
            ),
            expected_output='A complete, day-by-day travel itinerary in Markdown format, detailing suggested activities, sights, and potentially meal spots for each part of the day. The output should also prominently feature: an "Important Contacts" section, a "Useful Phrases & Etiquette" section, a "Budget & Cost Estimates" section, and finally, a "Key Locations for Map:" section with 3-5 listed locations.',
            agent=itinerary_synthesizer,
            context=[destination_analysis_task, activity_research_task, cost_estimation_task]
        )

        travel_crew = Crew(
            agents=[destination_analyst, activity_interest_specialist, cost_estimator_agent, itinerary_synthesizer],
            tasks=[destination_analysis_task, activity_research_task, cost_estimation_task, itinerary_generation_task],
            process=Process.sequential,
            verbose=True
        )

        with st.spinner("🌍 Agents are exploring and planning..."):
            travel_inputs = {
                'destination': destination,
                'duration_of_trip': duration_of_trip,
                'interests': interests_string,
                'budget_level': budget_level
            }
            try:
                result_object = travel_crew.kickoff(inputs=travel_inputs)
                result = result_object.raw # Access the raw string output

                st.success("✅ Your Personalized Itinerary is Ready!")
                st.markdown("---")
                st.session_state.current_itinerary = result # Store the raw string itinerary
                st.session_state.original_inputs = travel_inputs # Store original inputs for refinement

            except Exception as e:
                st.error(f"An error occurred during itinerary generation: {e}")

st.markdown("---")

# --- Display Current Itinerary, Downloads, and Map (if exists in session_state) ---
if 'current_itinerary' in st.session_state and st.session_state.current_itinerary:
    current_itinerary_text = st.session_state.current_itinerary
    original_inputs_for_display = st.session_state.original_inputs

    st.subheader(f"Your Trip to {original_inputs_for_display['destination']} ({original_inputs_for_display['duration_of_trip']})")
    st.markdown(current_itinerary_text, unsafe_allow_html=True)

    # --- Helper function to convert Markdown to PDF ---
    def convert_markdown_to_pdf(md_content):
        html_content = markdown.markdown(md_content)
        styled_html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: sans-serif; }}
                    h1, h2, h3 {{ color: #333; }}
                    p {{ line-height: 1.6; }}
                </style>
            </head>
            <body>{html_content}</body>
        </html>"""
        result = BytesIO()
        pdf = pisa.CreatePDF(BytesIO(styled_html.encode('utf-8')), dest=result)
        if not pdf.err:
            return result.getvalue()
        st.error(f"Error converting to PDF: {pdf.err}")
        return None

    # --- Download Buttons ---
    st.markdown("---")
    file_name_dest = "".join(filter(str.isalnum, original_inputs_for_display['destination'])).lower()
    
    # PDF Download
    pdf_data = convert_markdown_to_pdf(current_itinerary_text)
    if pdf_data:
        st.download_button(
            label="📥 Download Itinerary (PDF)",
            data=pdf_data,
            file_name=f"itinerary_{file_name_dest}_{original_inputs_for_display['duration_of_trip'].replace(' ', '_')}.pdf",
            mime="application/pdf",
        )

    # --- Map Display ---
    st.markdown("---")
    st.subheader("🗺️ Key Locations on Map")
    try:
        key_locations_text = None
        if "Key Locations for Map:" in current_itinerary_text:
            key_locations_text = current_itinerary_text.split("Key Locations for Map:")[1].strip()
            lines_to_parse = key_locations_text.split('\n')
        else:
            result_lines = current_itinerary_text.strip().split('\n')
            lines_to_parse = result_lines[-10:] # Fallback

        if lines_to_parse:
            locations_to_map = []
            for line in lines_to_parse:
                cleaned_line = re.sub(r"^\s*[-*•\s]*", "", line).strip()
                if cleaned_line and len(cleaned_line) > 3: # Basic check for valid location name
                    locations_to_map.append(cleaned_line)
            
            if locations_to_map:
                geolocator = Nominatim(user_agent="travel_planner_app/1.0")
                map_points = []
                for loc_name in locations_to_map:
                    try:
                        location_geo = geolocator.geocode(loc_name, timeout=10)
                        if location_geo:
                            map_points.append({
                                "name": loc_name,
                                "lat": location_geo.latitude,
                                "lon": location_geo.longitude
                            })
                    except (GeocoderTimedOut, GeocoderUnavailable):
                        st.warning(f"Could not geocode '{loc_name}' due to service issues. Skipping.")
                    except Exception as geo_e:
                        st.warning(f"Error geocoding '{loc_name}': {geo_e}. Skipping.")
                
                if map_points:
                    # Center map on the first point or average if preferred
                    m = folium.Map(location=[map_points[0]["lat"], map_points[0]["lon"]], zoom_start=10)
                    for point in map_points:
                        folium.Marker([point["lat"], point["lon"]], popup=point["name"]).add_to(m)
                    st_folium(m, key="main_itinerary_map", width=725, height=500)
                else:
                    st.info("No locations could be geocoded for the map.")
            else:
                st.info("No key locations found in the itinerary for mapping.")
    except Exception as map_e:
        st.error(f"An error occurred during map generation: {map_e}")