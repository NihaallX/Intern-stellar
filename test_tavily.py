"""
Test script for Tavily web search integration.
Validates that the API key works and company enrichment is functional.
"""

from src.utils.web_search import search_company_info, get_tavily_client
from src.models import CompanyEnrichment


def test_tavily_connection():
    """Test basic Tavily API connectivity."""
    print("Testing Tavily API connection...")
    try:
        client = get_tavily_client()
        print("✓ Tavily client initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Tavily client: {e}")
        return False


def test_company_enrichment():
    """Test company enrichment with a known AI company."""
    print("\nTesting company enrichment...")
    
    test_companies = ["OpenAI", "Anthropic", "Hugging Face"]
    
    for company_name in test_companies:
        print(f"\n  Searching: {company_name}")
        try:
            enrichment = search_company_info(company_name)
            
            print(f"    Employee count: {enrichment.employee_count or 'Unknown'}")
            print(f"    Funding stage: {enrichment.funding_stage or 'Unknown'}")
            print(f"    Is AI company: {enrichment.is_ai_company}")
            print(f"    Tech stack: {', '.join(enrichment.tech_stack[:5]) if enrichment.tech_stack else 'None found'}")
            print(f"    Recent news: {len(enrichment.recent_news)} items")
            
            if enrichment.is_ai_company:
                print(f"    ✓ Correctly identified as AI company")
            
        except Exception as e:
            print(f"    ✗ Error: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TAVILY WEB SEARCH INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Connection
    if not test_tavily_connection():
        print("\n[FAILED] Cannot connect to Tavily API")
        return
    
    # Test 2: Company enrichment
    test_company_enrichment()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
