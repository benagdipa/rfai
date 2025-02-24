import pandas as pd
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine
from config.settings import settings
from utils.logger import logger

class DataConnector:
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        raise NotImplementedError

class CsvConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        return pd.read_csv(source_config["file_path"])

class SqlConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        engine = create_engine(source_config["connection_string"])
        return pd.read_sql(source_config["query"], engine)

class GoogleSheetsConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_SHEETS_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(source_config["sheet_id"]).sheet1
        return pd.DataFrame(sheet.get_all_records())

class AirtableConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        url = f"https://api.airtable.com/v0/{source_config['base_id']}/{source_config['table_name']}"
        headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return pd.DataFrame([record["fields"] for record in data["records"]])

class ApiConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        async with aiohttp.ClientSession() as session:
            async with session.get(source_config["url"], params=source_config.get("params", {})) as resp:
                data = await resp.json()
                return pd.json_normalize(data[source_config.get("data_key", "")] if "data_key" in source_config else data)

def get_connector(source_type: str) -> DataConnector:
    connectors = {
        "csv": CsvConnector(),
        "sql": SqlConnector(),
        "google_sheets": GoogleSheetsConnector(),
        "airtable": AirtableConnector(),
        "api": ApiConnector()
    }
    return connectors.get(source_type, None)
