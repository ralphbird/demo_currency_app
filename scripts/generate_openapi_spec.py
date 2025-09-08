#!/usr/bin/env python3
"""Script to generate OpenAPI specification file from the Currency Conversion API."""

import json
import sys
from pathlib import Path

from currency_app.main import app


def main():
    """Generate OpenAPI specification file."""
    print("🔄 Generating OpenAPI specification file...")

    try:
        # Get the OpenAPI schema from the FastAPI app
        openapi_schema = app.openapi()

        # Create the api_specs directory if it doesn't exist
        api_specs_dir = Path("api_specs")
        api_specs_dir.mkdir(exist_ok=True)

        # Define the output file path
        output_file = api_specs_dir / "openapi.json"

        # Write the OpenAPI schema to the JSON file
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add newline at end to satisfy end-of-file-fixer

        print(f"✅ OpenAPI specification generated successfully: {output_file}")
        print(f"   - Title: {openapi_schema.get('info', {}).get('title', 'N/A')}")
        print(f"   - Version: {openapi_schema.get('info', {}).get('version', 'N/A')}")
        print(f"   - Paths: {len(openapi_schema.get('paths', {}))}")

    except Exception as e:
        print(f"❌ Error generating OpenAPI specification: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
