# MCP Air Quality Reporter for Indonesian Cities on Slack

This Python script uses the Model Context Protocol (MCP) to connect to a Slack server, fetches air quality data for various Indonesian cities by scraping the AQICN website, uses OpenAI to summarize this data, and then posts the summary to a specified Slack channel.

**Note:** This script relies on web scraping AQICN, which might be less reliable than using a dedicated API. The structure of the AQICN website could change, potentially breaking the scraping functionality.

## Prerequisites

* **Slack Bot Token:** You need to create a Slack bot and obtain its OAuth access token.
* **Slack Team ID:** The ID of your Slack workspace.
* **OpenAI API Key:** You need an API key from OpenAI to use their language models for summarization.
* **`config.json` file:** This file stores your API keys and Slack credentials.

## Installation

1.  **Clone the repository (or download the script files).**
2.  **Install the required Python packages:**
    ```bash
    pip install aiohttp beautifulsoup4 openai mcp
    ```
3.  **Set up the MCP Slack Server:** Follow the instructions for `@modelcontextprotocol/server-slack` to get it running. Ensure it has the necessary permissions to post messages to your Slack workspace.

## Configuration

You need to create a `config.json` file in the same directory as the Python script (`mcp_aq_slack.py`). This file should contain your API keys and Slack credentials:

```json
{
  "OPENAI_API_KEY": "YOUR_OPENAI_API_KEY_HERE",
  "SLACK_BOT_TOKEN": "YOUR_SLACK_BOT_TOKEN_HERE",
  "SLACK_TEAM_ID": "YOUR_SLACK_TEAM_ID_HERE",
  "SLACK_CHANNELID": "YOUR_SLACK_CHANNEL_ID_HERE"
}
