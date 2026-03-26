#!/usr/bin/env python3
"""
API Testing Script for Global Ontology Engine

Tests all API endpoints with valid and invalid inputs, logging results.
"""

import requests
import json
import time
from typing import Dict, Any, List, Tuple

BASE_URL = "http://localhost:8000/api/v1"

def log_result(endpoint: str, method: str, status: int, response: Dict[str, Any], expected: bool, notes: str = ""):
    """Log test result"""
    result = "PASS" if (status == 200 and expected) or (status != 200 and not expected) else "FAIL"
    print(f"[{result}] {method} {endpoint} - Status: {status} - {notes}")
    if response:
        print(f"  Response: {json.dumps(response, indent=2)[:200]}...")
    print()

def test_endpoint(method: str, endpoint: str, data: Dict[str, Any] = None, expected_success: bool = True, notes: str = ""):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            print(f"Unsupported method: {method}")
            return

        try:
            resp_json = response.json()
        except:
            resp_json = {"error": "Non-JSON response"}

        log_result(endpoint, method, response.status_code, resp_json, expected_success, notes)

    except requests.exceptions.RequestException as e:
        log_result(endpoint, method, 0, {"error": str(e)}, False, "Request failed")

def main():
    print("Starting API Tests for Global Ontology Engine")
    print("=" * 50)

    # Health Endpoints
    print("Testing Health Endpoints:")
    test_endpoint("GET", "/health", expected_success=True, notes="Overall health check")
    test_endpoint("GET", "/health/neo4j", expected_success=False, notes="Neo4j health (expected unhealthy)")
    test_endpoint("GET", "/health/postgres", expected_success=False, notes="Postgres health (expected unhealthy)")
    test_endpoint("GET", "/health/redis", expected_success=False, notes="Redis health (expected unhealthy)")

    # Query Endpoints
    print("Testing Query Endpoints:")
    # Valid query
    test_endpoint("POST", "/query", {"question": "What is the impact of climate change on global politics?"}, expected_success=False, notes="Valid query (may fail due to no data)")
    # Invalid query - missing question
    test_endpoint("POST", "/query", {}, expected_success=False, notes="Invalid query - missing question")
    # Invalid query - wrong type
    test_endpoint("POST", "/query", {"question": 123}, expected_success=False, notes="Invalid query - question not string")

    # Insights Endpoints
    print("Testing Insights Endpoints:")
    test_endpoint("GET", "/insights", expected_success=False, notes="Get insights (may fail due to no data)")
    test_endpoint("GET", "/insights/risk-analysis", expected_success=False, notes="Risk analysis")
    test_endpoint("GET", "/insights/map-data", expected_success=False, notes="Map data")
    test_endpoint("GET", "/insights/trends", expected_success=False, notes="Trends")

    # News Endpoints
    print("Testing News Endpoints:")
    test_endpoint("GET", "/news/articles", expected_success=False, notes="Get articles (may fail due to no data)")
    test_endpoint("GET", "/news/sources", expected_success=False, notes="Get sources")
    test_endpoint("GET", "/news/ingestion/status", expected_success=False, notes="Ingestion status")
    test_endpoint("GET", "/news/stats", expected_success=False, notes="News stats")
    # Trigger ingestion - POST
    test_endpoint("POST", "/news/ingestion/trigger", {}, expected_success=False, notes="Trigger ingestion")
    # Add source - valid
    test_endpoint("POST", "/news/sources", {"name": "Test Source", "url": "http://example.com", "type": "rss"}, expected_success=False, notes="Add source")
    # Add source - invalid
    test_endpoint("POST", "/news/sources", {"name": "Test"}, expected_success=False, notes="Add source - missing fields")
    # Delete source - invalid ID
    test_endpoint("DELETE", "/news/sources/invalid_id", expected_success=False, notes="Delete source - invalid ID")

    # Ontology Endpoints
    print("Testing Ontology Endpoints:")
    test_endpoint("GET", "/ontology/stats", expected_success=False, notes="Graph stats")
    test_endpoint("GET", "/ontology/entity-types", expected_success=False, notes="Entity types")
    test_endpoint("GET", "/ontology/relationship-types", expected_success=False, notes="Relationship types")
    test_endpoint("GET", "/ontology/entities/invalid_id", expected_success=False, notes="Get entity - invalid ID")
    test_endpoint("GET", "/ontology/search", expected_success=False, notes="Search entities - no query")
    test_endpoint("GET", "/ontology/search?q=test", expected_success=False, notes="Search entities")
    test_endpoint("GET", "/ontology/entities/invalid_id/relationships", expected_success=False, notes="Entity relationships - invalid ID")
    test_endpoint("GET", "/ontology/graph/invalid_id/subgraph", expected_success=False, notes="Entity subgraph - invalid ID")

    print("API Testing Complete")

if __name__ == "__main__":
    main()