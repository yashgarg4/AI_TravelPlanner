# ✈️ AI Personalized Travel Itinerary Planner

Welcome to the AI Travel Planner! This is a web application built with Streamlit and powered by a crew of AI agents using CrewAI and Google's Gemini model. It crafts detailed, personalized travel itineraries based on your preferences.

Tell the AI your destination, trip duration, interests, and budget, and it will generate a day-by-day plan complete with activity suggestions, cultural tips, emergency contacts, cost estimates, and an interactive map of key locations.

## ✨ Features

- **Personalized Itineraries:** Get travel plans tailored to your specific interests (e.g., history, food, nature) and budget (budget-friendly, mid-range, luxury).
- **AI Agent Crew:** Utilizes a team of specialized AI agents for:
    - **Destination Analysis:** Gathers key facts, cultural insights, safety tips, and basic local phrases.
    - **Activity Research:** Finds specific activities, restaurants, and attractions matching your profile.
    - **Cost Estimation:** Provides a rough daily and total trip cost estimate in INR.
    - **Itinerary Synthesis:** Compiles all the information into a coherent, day-by-day plan.
- **Interactive Map:** Visualizes key landmarks from your itinerary on an interactive map using Folium.
- **Download as PDF:** Save your generated itinerary for offline use with a one-click PDF download.
- **Web-Powered:** Uses Serper for real-time, high-quality search results to inform the AI's planning.

## 🛠️ Tech Stack

- **Framework:** [Streamlit]
- **AI Orchestration:** [CrewAI]
- **LLM:** [Google Gemini]
- **Web Search:** [SerperDevTool]
- **Mapping:** [Folium] & [Geopy]
- **PDF Generation:** [xhtml2pdf]
- **Deployment:** Includes `pysqlite3-binary` for compatibility with Streamlit Community Cloud.

## 🚀 Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

- Python 3.8 or higher
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI_TravelPlanner-main.git
cd AI_TravelPlanner-main
```

### 2. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

You need to provide API keys for the services used by the application.

1.  Create a file named `.env` in the root directory of the project.
2.  Add the following lines to the `.env` file, replacing `your_api_key_here` with your actual keys:

    ```env
    GEMINI_API_KEY="your_google_gemini_api_key_here"
    SERPER_API_KEY="your_serper_dev_api_key_here"
    ```

    -   **GEMINI_API_KEY:** Get your key from Google AI Studio.
    -   **SERPER_API_KEY:** Get your key from Serper.dev. The free plan is sufficient for development.

## ▶️ How to Run

Once the setup is complete, run the Streamlit application with the following command:

```bash
streamlit run app.py
```

Your web browser should open a new tab with the application running. Fill in the travel details in the sidebar and click "Generate Itinerary" to start.

