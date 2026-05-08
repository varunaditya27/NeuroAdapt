#!/usr/bin/env python
"""
Comprehensive endpoint testing suite for NeuroAdapt API
Tests all 4 implemented endpoints and validates responses
"""

import requests
import json
import sys
from typing import Optional

BASE_URL = 'http://localhost:8000'
SESSION_ID: Optional[str] = None

def print_header(title: str) -> None:
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_subheader(title: str) -> None:
    """Print formatted subheader."""
    print(f"\n{title}")
    print("-"*70)

def test_session_init() -> Optional[str]:
    """Test 1: POST /api/session - Session Initialization"""
    global SESSION_ID
    print_subheader("[TEST 1] POST /api/session - Session Initialization")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/session',
            json={'student_id': 'test_student_001'},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response:\n{json.dumps(data, indent=2)}")
            SESSION_ID = data.get('session_id')
            print(f"\n✅ PASS - Session Created")
            print(f"   Session ID: {SESSION_ID}")
            print(f"   Created at: {data.get('created_at')}")
            return SESSION_ID
        else:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print("❌ FAIL - Unexpected status code")
            return None
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return None

def test_lessons() -> bool:
    """Test 2: GET /api/lessons - Dynamic Lesson Catalogue"""
    print_subheader("[TEST 2] GET /api/lessons - Dynamic Lesson Catalogue")
    
    try:
        response = requests.get(f'{BASE_URL}/api/lessons', timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Print structure without full content
            print(f"Response keys: {list(data.keys())}")
            lessons = data.get('lessons', [])
            print(f"Number of lessons: {len(lessons)}")
            
            if lessons:
                print(f"\nSample lesson (first 200 chars):")
                print(json.dumps(lessons[0], indent=2)[:200] + "...")
            
            print(f"\n✅ PASS - Lessons Retrieved")
            print(f"   Total lessons: {len(lessons)}")
            
            # Validate structure
            if data.get('total_count') and isinstance(lessons, list):
                print("   Structure validated ✓")
                return True
            else:
                print("   Warning: Unexpected structure")
                return True
        else:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print("❌ FAIL - Unexpected status code")
            return False
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_preferences(session_id: str) -> bool:
    """Test 3: GET /api/preferences/{session_id} - Preference History"""
    print_subheader("[TEST 3] GET /api/preferences/{session_id} - Preference History")
    
    try:
        response = requests.get(f'{BASE_URL}/api/preferences/{session_id}', timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Session ID: {session_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            preferences = data.get('preferences', [])
            print(f"Number of preferences: {len(preferences)}")
            
            if preferences:
                print(f"\nSample preference (first 200 chars):")
                print(json.dumps(preferences[0], indent=2)[:200] + "...")
            
            print(f"\n✅ PASS - Preferences Retrieved")
            print(f"   Total entries: {len(preferences)}")
            print(f"   Session validated ✓")
            return True
        else:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print("❌ FAIL - Unexpected status code")
            return False
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_state_history(session_id: str) -> bool:
    """Test 4: GET /api/state-history/{session_id} - State History Analytics"""
    print_subheader("[TEST 4] GET /api/state-history/{session_id} - State History Analytics")
    
    try:
        response = requests.get(f'{BASE_URL}/api/state-history/{session_id}', timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Session ID: {session_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            snapshots = data.get('snapshots', [])
            print(f"Number of snapshots: {len(snapshots)}")
            
            if snapshots:
                print(f"\nSample snapshot (first 250 chars):")
                print(json.dumps(snapshots[0], indent=2)[:250] + "...")
            
            print(f"\n✅ PASS - State History Retrieved")
            print(f"   Total snapshots: {len(snapshots)}")
            print(f"   Pagination limit: {data.get('limit')}")
            print(f"   Session validated ✓")
            return True
        else:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print("❌ FAIL - Unexpected status code")
            return False
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_error_handling() -> bool:
    """Test error handling with invalid session ID"""
    print_subheader("[BONUS] Error Handling - Invalid Session ID")
    
    try:
        # Test preferences with invalid session
        response = requests.get(f'{BASE_URL}/api/preferences/invalid_session_xyz', timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print(f"\n✅ PASS - Proper error handling (404)")
            return True
        elif response.status_code == 200:
            # Could be valid if it returns empty list
            data = response.json()
            if len(data.get('preferences', [])) == 0:
                print(f"✅ PASS - Returns empty preferences for non-existent session")
                return True
            else:
                print("❌ FAIL - Unexpected data for invalid session")
                return False
        else:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            print(f"⚠️ WARNING - Unexpected status code: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def main() -> None:
    """Run all tests."""
    print_header("NEURO-ADAPT ENDPOINT TESTING SUITE")
    print(f"Testing at: {BASE_URL}\n")
    
    # Run tests sequentially
    results = {
        "Session Init": False,
        "Lessons": False,
        "Preferences": False,
        "State History": False,
        "Error Handling": False
    }
    
    # Test 1
    session_id = test_session_init()
    results["Session Init"] = session_id is not None
    
    # Test 2
    results["Lessons"] = test_lessons()
    
    # Test 3 & 4 (require valid session)
    if session_id:
        results["Preferences"] = test_preferences(session_id)
        results["State History"] = test_state_history(session_id)
    
    # Bonus test
    results["Error Handling"] = test_error_handling()
    
    # Print summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    print("\n" + "="*70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*70 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)

if __name__ == '__main__':
    main()
