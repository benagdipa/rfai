import pandas as pd
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine
from config.settings import settings
from utils.logger import logger
from typing import Dict, Any, Optional
import asyncio
import backoff
from aiohttp import ClientSession
from abc import ABC, abstractmethod

# Base class for data connectors
class DataConnector(ABC):
    @abstractmethod
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from the source and return it as a DataFrame."""
        pass

# CSV Connector
class CsvConnector(DataConnector):
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from a CSV file."""
        file_path = source_config.get("file_path")
        if not file_path:
            logger.error("Missing 'file_path' in source_config for CSV connector")
            raise ValueError("Missing 'file_path' in source_config")
        
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully fetched {len(df)} rows from CSV at {file_path}")
            return df
        except Exception as e:
            logger.error(f"Failed to read CSV from {file_path}: {str(e)}")
            raise

# SQL Connector
class SqlConnector(DataConnector):
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from a SQL database."""
        connection_string = source_config.get("connection_string")
        query = source_config.get("query")
        if not connection_string or not query:
            logger.error("Missing 'connection_string' or 'query' in source_config for SQL connector")
            raise ValueError("Missing 'connection_string' or 'query' in source_config")
        
        try:
            engine = create_engine(connection_string)
            df = pd.read_sql(query, engine)
            logger.info(f"Successfully fetched {len(df)} rows from SQL with query: {query}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data from SQL: {str(e)}")
            raise

# Google Sheets Connector
class GoogleSheetsConnector(DataConnector):
    @backoff.on_exception(backoff.expo, Exception, max_tries=3, on_backoff=lambda details: logger.debug(f"Retrying Google Sheets fetch: attempt {details['tries']}"))
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from Google Sheets with retry logic."""
        sheet_id = source_config.get("sheet_id")
        if not sheet_id:
            logger.error("Missing 'sheet_id' in source_config for Google Sheets connector")
            raise ValueError("Missing 'sheet_id' in source_config")
        
        if not hasattr(settings, "GOOGLE_SHEETS_CREDENTIALS"):
            logger.error("Google Sheets credentials not configured in settings")
            raise ValueError("Google Sheets credentials not configured")

        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_SHEETS_CREDENTIALS, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(sheet_id).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            logger.info(f"Successfully fetched {len(df)} rows from Google Sheet {sheet_id}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data from Google Sheet {sheet_id}: {str(e)}")
            raise

# Airtable Connector
class AirtableConnector(DataConnector):
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3, on_backoff=lambda details: logger.debug(f"Retrying Airtable fetch: attempt {details['tries']}"))
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from Airtable with retry logic."""
        base_id = source_config.get("base_id")
        table_name = source_config.get("table_name")
        if not base_id or not table_name:
            logger.error("Missing 'base_id' or 'table_name' in source_config for Airtable connector")
            raise ValueError("Missing 'base_id' or 'table_name' in source_config")
        
        if not hasattr(settings, "AIRTABLE_API_KEY"):
            logger.error("Airtable API key not configured in settings")
            raise ValueError("Airtable API key not configured")

        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}"}
        
        async with ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    df = pd.DataFrame([record["fields"] for record in data["records"]])
                    logger.info(f"Successfully fetched {len(df)} rows from Airtable {base_id}/{table_name}")
                    return df
            except aiohttp.ClientError as e:
                logger.error(f"Failed to fetch data from Airtable {url}: {str(e)}")
                raise

# API Connector
class ApiConnector(DataConnector):
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3, on_backoff=lambda details: logger.debug(f"Retrying API fetch: attempt {details['tries']}"))
    async def fetch_data(self, source_config: Dict[str, Any]) -> pd.DataFrame:
        """Fetch data from a generic API with retry logic."""
        url = source_config.get("url")
        if not url:
            logger.error("Missing 'url' in source_config for API connector")
            raise ValueError("Missing 'url' in source_config")

        params = source_config.get("params", {})
        data_key = source_config.get("data_key", None)
        
        async with ClientSession() as session:
            try:
                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    df = pd.json_normalize(data[data_key] if data_key and data_key in data else data)
                    logger.info(f"Successfully fetched {len(df)} rows from API {url}")
                    return df
            except aiohttp.ClientError as e:
                logger.error(f"Failed to fetch data from API {url}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Failed to process API response from {url}: {str(e)}")
                raise

# Factory function to get connectors
def get_connector(source_type: str) -> Optional[DataConnector]:
    """
    Retrieve a connector instance based on source type.

    Args:
        source_type (str): Type of data source (e.g., 'csv', 'sql', 'api').

    Returns:
        DataConnector: Instance of the appropriate connector, or None if not found.
    """
    connectors = {
        "csv": CsvConnector(),
        "sql": SqlConnector(),
        "google_sheets": GoogleSheetsConnector(),
        "airtable": AirtableConnector(),
        "api": ApiConnector()
    }
    connector = connectors.get(source_type.lower())
    if not connector:
        logger.warning(f"No connector found for source type: {source_type}")
    return connector

if __name__ == "__main__":
    # Test connectors
    async def test_connectors():
        csv_config = {"file_path": "test.csv"}
        sql_config = {"connection_string": "sqlite:///test.db", "query": "SELECT * FROM test"}
        google_config = {"sheet_id": "your_sheet_id"}
        airtable_config = {"base_id": "app123", "table_name": "Table1"}
        api_config = {"url": "https://api.example.com/data", "data_key": "results"}

        connectors = [
            ("csv", CsvConnector(), csv_config),
            ("sql", SqlConnector(), sql_config),
            ("google_sheets", GoogleSheetsConnector(), google_config),
            ("airtable", AirtableConnector(), airtable_config),
            ("api", ApiConnector(), api_config)
        ]

        for name, connector, config in connectors:
            try:
                df = await connector.fetch_data(config)
                print(f"{name} fetched {len(df)} rows")
            except Exception as e:
                print(f"{name} failed: {str(e)}")

    asyncio.run(test_connectors())