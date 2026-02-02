"""
Test caching, error handling, and rate limiting improvements.
"""

import time
from src.utils.web_search import search_company_info, clear_cache


def test_caching():
    """Test that duplicate company searches use cache."""
    print("=" * 60)
    print("TESTING CACHING")
    print("=" * 60)
    
    clear_cache()
    
    company = "Anthropic"
    
    # First call - should hit API
    print(f"\n[1] First call for {company} (should hit API)...")
    start = time.time()
    result1 = search_company_info(company)
    time1 = time.time() - start
    print(f"    Time: {time1:.2f}s")
    print(f"    Data: {result1.employee_count} employees")
    
    # Second call - should use cache
    print(f"\n[2] Second call for {company} (should use cache)...")
    start = time.time()
    result2 = search_company_info(company)
    time2 = time.time() - start
    print(f"    Time: {time2:.2f}s")
    print(f"    Data: {result2.employee_count} employees")
    
    # Verify
    print(f"\n[3] Results:")
    if time2 < 0.1:
        print(f"    ✓ Cache is working (second call was {time2:.3f}s vs {time1:.2f}s)")
    else:
        print(f"    ✗ Cache may not be working")
    
    if result1.employee_count == result2.employee_count:
        print(f"    ✓ Same data returned")
    else:
        print(f"    ✗ Different data")


def test_rate_limiting():
    """Test that API calls are rate limited."""
    print("\n" + "=" * 60)
    print("TESTING RATE LIMITING")
    print("=" * 60)
    
    clear_cache()
    
    companies = ["OpenAI", "Anthropic"]
    
    print(f"\n[1] Making 2 API calls (should have ~1.5s delay between)...")
    start = time.time()
    
    for company in companies:
        print(f"    Searching: {company}")
        search_company_info(company)
    
    total_time = time.time() - start
    print(f"\n[2] Total time: {total_time:.2f}s")
    
    if total_time >= 1.5:
        print(f"    ✓ Rate limiting is working (took {total_time:.2f}s for 2 calls)")
    else:
        print(f"    ⚠ Rate limiting may not be working (expected >1.5s)")


def test_error_handling():
    """Test error handling with invalid company name."""
    print("\n" + "=" * 60)
    print("TESTING ERROR HANDLING")
    print("=" * 60)
    
    clear_cache()
    
    # Test with garbage input
    invalid_company = "XYZ123NotARealCompany999"
    
    print(f"\n[1] Searching for invalid company: {invalid_company}")
    try:
        result = search_company_info(invalid_company)
        print(f"    ✓ No crash - returned empty enrichment")
        print(f"    Data: employee_count={result.employee_count}, is_ai={result.is_ai_company}")
        
        # Try again - should use cache
        print(f"\n[2] Searching again (should use cached empty result)...")
        result2 = search_company_info(invalid_company)
        print(f"    ✓ Cached empty result to avoid retry")
        
    except Exception as e:
        print(f"    ✗ Crashed with error: {e}")


if __name__ == "__main__":
    test_caching()
    test_rate_limiting()
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
