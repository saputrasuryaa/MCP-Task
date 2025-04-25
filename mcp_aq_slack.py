
# Import necessary modules
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import os
import json
import aiohttp
from bs4 import BeautifulSoup  # For web scraping
from openai import OpenAI

# Import MCP libraries
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load configuration values from config.json file
with open("config.json", "r") as json_file:
    config = json.load(json_file)

# Extract values from the config dictionary
OPENAI_API_KEY = config["OPENAI_API_KEY"]
SLACK_BOT_TOKEN = config["SLACK_BOT_TOKEN"]
SLACK_TEAM_ID = config["SLACK_TEAM_ID"]
SLACK_CHANNELID = config["SLACK_CHANNELID"]

# --- Air Quality Data Source Configuration ---
AQICN_BASE_URL = "https://aqicn.org/city/indonesia/"
INDONESIAN_CITIES_AQICN = [
    "jakarta", "surabaya", "bandung", "medan", "semarang", "palembang",
    "makassar", "batam", "pekanbaru", "bogor", "malang", "denpasar",
    "tangerang", "bekasi", "depok", "yogyakarta", "surakarta", "padang",
    "balikpapan", "samarinda"
]

class MCPSlackClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-slack"],
            env={"SLACK_BOT_TOKEN": SLACK_BOT_TOKEN, "SLACK_TEAM_ID": SLACK_TEAM_ID},
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def fetch_air_quality(self, city_name_aqicn):
        url = f"{AQICN_BASE_URL}{city_name_aqicn}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        aqi_div = soup.find('div', class_='aqivalue')
                        if aqi_div:
                            aqi = aqi_div.text.strip()
                            return city_name_aqicn.capitalize(), aqi
                        else:
                            print(f"Could not find AQI value for {city_name_aqicn}")
                            return city_name_aqicn.capitalize(), None
                    else:
                        print(f"Error fetching data for {city_name_aqicn}: HTTP status {response.status}")
                        return city_name_aqicn.capitalize(), None
        except aiohttp.ClientError as e:
            print(f"AIOHTTP error fetching data for {city_name_aqicn}: {e}")
            return city_name_aqicn.capitalize(), None
        except Exception as e:
            print(f"An unexpected error occurred for {city_name_aqicn}: {e}")
            return city_name_aqicn.capitalize(), None

    async def get_indonesian_air_quality(self):
        tasks = [self.fetch_air_quality(city) for city in INDONESIAN_CITIES_AQICN]
        results = await asyncio.gather(*tasks)
        city_aqi_data = {city: aqi for city, aqi in results if aqi is not None and aqi.isdigit()}
        return city_aqi_data

    def get_aqi_category(self, aqi):
        try:
            aqi_value = int(aqi)
            if aqi_value <= 50:
                return "Good"
            elif 51 <= aqi_value <= 100:
                return "Moderate"
            elif 101 <= aqi_value <= 150:
                return "Unhealthy for Sensitive Groups"
            elif 151 <= aqi_value <= 200:
                return "Unhealthy"
            elif 201 <= aqi_value <= 300:
                return "Very Unhealthy"
            elif aqi_value > 300:
                return "Hazardous"
            return "Unknown"
        except (ValueError, TypeError):
            return "Unknown"

    async def summarize_air_quality_with_openai(self, city_aqi_data):
        if not city_aqi_data:
            return "No air quality data available for Indonesian cities."

        prompt = f"""Summarize the current air quality index for the following Indonesian cities based on the provided AQI values.
        For each city, include the AQI value and a brief description of what that AQI level means for health.
        Also, provide an overall summary of the air quality situation across these cities.

        Air Quality Data:
        """
        for city, aqi in sorted(city_aqi_data.items()):
            category = self.get_aqi_category(aqi)
            prompt += f"- {city}: AQI = {aqi} ({category})\n"

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"Error during OpenAI summarization: {e}")
            basic_summary = "Air Quality Index Report for Indonesian Cities:\n"
            for city, aqi in sorted(city_aqi_data.items()):
                category = self.get_aqi_category(aqi)
                basic_summary += f"- {city}: AQI = {aqi} ({category})\n"
            return basic_summary

    async def post_air_quality_to_slack(self, summary):
        try:
            await self.session.call_tool("slack_post_message", {
                "channel_id": SLACK_CHANNELID,
                "text": summary
            })
            print("Air quality report posted to Slack successfully.")
        except Exception as e:
            print(f"Error posting air quality report to Slack: {e}")

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPSlackClient()

    try:
        await client.connect_to_server()

        print("Fetching air quality data for Indonesian cities from AQICN...")
        air_quality_data = await client.get_indonesian_air_quality()

        if air_quality_data:
            print("Summarizing air quality data with OpenAI...")
            summary = await client.summarize_air_quality_with_openai(air_quality_data)
            print("\nAir Quality Summary from OpenAI:\n", summary)

            print("Posting summary to Slack...")
            await client.post_air_quality_to_slack(summary)
        else:
            print("Could not retrieve air quality data.")

    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
