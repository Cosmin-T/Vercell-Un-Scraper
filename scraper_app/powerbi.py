# scraper_app/powerbi.py
import pandas as pd
import pygwalker as pyg
import streamlit.components.v1 as stc
import streamlit as st
import concurrent.futures
from django.core.files.storage import FileSystemStorage
import os
import json

class Pwbi:
    """
    A class for processing and visualizing data files using PowerBI-like interface.
    Supports CSV, Excel, and JSON file formats.
    """
    def __init__(self):
        # Initialize items attribute to store processed data
        self.items = None

    def process_file(self, file):
        """
        Process uploaded files and convert them to pandas DataFrame.

        Args:
            file: File object containing the data to be processed

        Returns:
            pandas.DataFrame: Processed data in DataFrame format

        Raises:
            ValueError: If file format is unsupported or JSON is invalid
        """
        filename = file.name
        ext = os.path.splitext(filename)[1].lower()  # Get file extension in lowercase

        # Handle CSV files
        if ext == '.csv':
            return pd.read_csv(file)

        # Handle Excel files
        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(file)

        # Handle JSON files
        elif ext == '.json':
            with file.open('r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON: {str(e)}")
            return pd.DataFrame(data)

        # Raise error for unsupported file types
        else:
            raise ValueError("Unsupported file format. Please upload CSV or JSON files only.")

    def dashboard(self):
        """
        Generate an interactive dashboard visualization using pygwalker.
        Processes data asynchronously using ThreadPoolExecutor for better performance.

        Returns:
            str: HTML string containing the interactive dashboard

        Raises:
            ValueError: If pygwalker fails to generate HTML output
        """
        # Use ThreadPoolExecutor for concurrent processing
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Convert items to DataFrame asynchronously
            future_items_df = executor.submit(pd.DataFrame, self.items)
            items_df = future_items_df.result()

            # Generate pygwalker visualization asynchronously
            future_pyg_html = executor.submit(pyg.walk(items_df).to_html)
            pyg_html = future_pyg_html.result()

        # Verify and return the HTML output
        if isinstance(pyg_html, str):
            return pyg_html
        else:
            raise ValueError("Error: pyg.walk did not return a string.")