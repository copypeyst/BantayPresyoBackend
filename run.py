#!/usr/bin/env python3

import sys
import os

# Add the current directory to the Python path
# This is necessary for importing downloader and main directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import downloader  # Import without auto-executing
import main

if __name__ == "__main__":
    print("\n--- Starting download process ---")
    downloader.download_latest_pdf()

    print("\n--- Starting main processing pipeline ---")
    main.main()
    print("--- Full pipeline complete ---")

