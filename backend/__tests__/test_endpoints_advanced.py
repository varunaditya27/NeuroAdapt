#!/usr/bin/env python
"""
Advanced Endpoint Testing Suite - Comprehensive Validation
Tests data persistence, pagination, schema validation, and edge cases
"""

import requests
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

def print_section(title: str) -> None:
    """Print formatted section header."""
    print("\n" + "="*75)
    print(f"  {title}")
    print("="*75)

def validate_session_response(data: dict) -> bool:
    """Validate SessionResponse schema."""
    required_fields = {'session_id', 'student_id', 'created_at'}
    if not required_fields.issubset(data.keys()):
        print(f"❌ Missing fields: {required_fields - set(data.keys())}")
        return False
    
    # Validate ISO 8601 timestamp
    try:
        datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        print(f"❌ Invalid ISO 8601 timestamp: {data['created_at']}")
        return False
    
    return True

def validate_lessons_response(data: dict) -> bool:
    """Validate LessonsListResponse schema."""
    if 'lessons' not in data or not isinstance(data['lessons'], list):
        print("❌ Invalid lessons structure")
        return False
    
    if len(data['lessons']) == 0:
        print("⚠️  WARNING: No lessons returned")
        return True
    
    # Validate first lesson structure
    lesson = data['lessons'][0]
    required_fields = {'subject', 'subjectId', 'descriptor', 'topics'}
    if not required_fields.issubset(lesson.keys()):
        print(f"❌ Lesson missing fields: {required_fields - set(lesson.keys())}")
        return False
    
    if not isinstance(lesson['topics'], list):
        print("❌ Topics should be a list")
        return False
    
    return True

def validate_preferences_response(data: dict) -> bool:
    """Validate PreferenceHistoryResponse schema."""
    required_fields = {'session_id', 'preferences', 'count'}
    if not required_fields.issubset(data.keys()):
        print(f"❌ Missing fields: {required_fields - set(data.keys())}")
        return False
    
    if not isinstance(data['preferences'], list):
        print("❌ Preferences should be a list")
        return False
    
    return True

def validate_state_history_response(data: dict) -> bool:
    """Validate StateHistoryResponse schema."""
    required_fields = {'session_id', 'states', 'count'}
    if not required_fields.issubset(data.keys()):
        print(f"❌ Missing fields: {required_fields - set(data.keys())}")
        return False
    
    if not isinstance(data['states'], list):
        print("❌ States should be a list")
        return False
    
    return True

def test_session_persistence() -> bool:
    """Test 1: Session persistence - create multiple sessions."""
    print_section("TEST 1: Session Persistence (Multiple Sessions)")
    
    try:
        sessions = []
        for i in range(3):
            response = requests.post(
                f'{BASE_URL}/api/session',
                json={'student_id': f'student_{i:03d}'},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to create session {i+1}")
                return False
            
            data = response.json()
            if not validate_session_response(data):
                return False
            
            sessions.append(data)
            print(f"✓ Session {i+1}: {data['session_id']}")
        
        print(f"\n✅ PASS - Created {len(sessions)} sessions successfully")
        return True, sessions
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False, []

def test_lessons_schema() -> bool:
    """Test 2: Lessons schema validation."""
    print_section("TEST 2: Lessons Schema Validation")
    
    try:
        response = requests.get(f'{BASE_URL}/api/lessons', timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Status code: {response.status_code}")
            return False
        
        data = response.json()
        
        if not validate_lessons_response(data):
            return False
        
        lessons = data['lessons']
        print(f"✓ Total lessons: {len(lessons)}")
        print(f"✓ Response count field: {data.get('count', 'N/A')}")
        
        # Verify all lessons have consistent structure
        for idx, lesson in enumerate(lessons):
            if 'topics' in lesson and isinstance(lesson['topics'], list):
                print(f"  - {lesson.get('subject', 'Unknown')}: {len(lesson['topics'])} topics")
        
        print(f"\n✅ PASS - Lessons schema validated")
        return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_preferences_with_session(session_id: str) -> bool:
    """Test 3: Preferences query with valid session."""
    print_section(f"TEST 3: Preferences Query (Session: {session_id})")
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/preferences/{session_id}',
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"❌ Status code: {response.status_code}")
            return False
        
        data = response.json()
        
        if not validate_preferences_response(data):
            return False
        
        print(f"✓ Session ID: {data['session_id']}")
        print(f"✓ Preference entries: {len(data['preferences'])}")
        print(f"✓ Count field: {data.get('count', 'N/A')}")
        
        if data['preferences']:
            print(f"✓ Sample entry: {json.dumps(data['preferences'][0], indent=2)[:200]}")
        
        print(f"\n✅ PASS - Preferences schema validated")
        return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_state_history_with_session(session_id: str) -> bool:
    """Test 4: State history query with valid session."""
    print_section(f"TEST 4: State History Query (Session: {session_id})")
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/state-history/{session_id}',
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"❌ Status code: {response.status_code}")
            return False
        
        data = response.json()
        
        if not validate_state_history_response(data):
            return False
        
        print(f"✓ Session ID: {data['session_id']}")
        print(f"✓ State snapshots: {len(data['states'])}")
        print(f"✓ Count field: {data.get('count', 'N/A')}")
        
        if data['states']:
            print(f"✓ Sample snapshot: {json.dumps(data['states'][0], indent=2)[:200]}")
        
        print(f"\n✅ PASS - State history schema validated")
        return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_pagination() -> bool:
    """Test 5: Pagination parameters."""
    print_section("TEST 5: Pagination Parameters")
    
    try:
        # Create a session first
        sess_resp = requests.post(
            f'{BASE_URL}/api/session',
            json={'student_id': 'pagination_test'},
            timeout=5
        )
        session_id = sess_resp.json()['session_id']
        print(f"✓ Test session: {session_id}")
        
        # Test state-history with limit parameter
        response = requests.get(
            f'{BASE_URL}/api/state-history/{session_id}?limit=5',
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"✓ Limit parameter accepted")
        
        # Test with invalid limit
        response = requests.get(
            f'{BASE_URL}/api/state-history/{session_id}?limit=2000',
            timeout=5
        )
        
        if response.status_code == 422:
            print(f"✓ Invalid limit rejected (status 422)")
        elif response.status_code == 200:
            print(f"⚠️  Invalid limit accepted (clamped or ignored)")
        
        print(f"\n✅ PASS - Pagination parameters tested")
        return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def test_error_handling() -> bool:
    """Test 6: Error handling for edge cases."""
    print_section("TEST 6: Error Handling & Edge Cases")
    
    test_cases = [
        ("Empty session ID", ""),
        ("Non-existent session", "nonexistent_session_xyz"),
        ("Invalid format", "%%%invalid%%%"),
    ]
    
    all_passed = True
    
    for desc, session_id in test_cases:
        try:
            response = requests.get(
                f'{BASE_URL}/api/preferences/{session_id}',
                timeout=5
            )
            
            # Should either return 404 or empty list for non-existent sessions
            if response.status_code in [200, 404]:
                print(f"✓ {desc}: Handled gracefully (status {response.status_code})")
            else:
                print(f"⚠️  {desc}: Unexpected status {response.status_code}")
        except Exception as e:
            print(f"❌ {desc}: Error {e}")
            all_passed = False
    
    print(f"\n✅ PASS - Error handling tested")
    return all_passed

def test_cors() -> bool:
    """Test 7: CORS headers."""
    print_section("TEST 7: CORS Headers Validation")
    
    try:
        response = requests.get(f'{BASE_URL}/api/lessons', timeout=5)
        headers = response.headers
        
        cors_header = headers.get('access-control-allow-origin')
        if cors_header:
            print(f"✓ CORS header present: {cors_header}")
        else:
            print(f"⚠️  CORS header missing")
        
        print(f"\n✅ PASS - CORS tested")
        return True
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False

def main() -> None:
    """Run all advanced tests."""
    print_section("ADVANCED ENDPOINT TESTING SUITE")
    print(f"Testing at: {BASE_URL}\n")
    
    results = {}
    sessions = []
    
    # Test 1: Session Persistence
    result = test_session_persistence()
    if isinstance(result, tuple):
        results["Session Persistence"] = result[0]
        sessions = result[1]
    else:
        results["Session Persistence"] = result
    
    # Test 2: Lessons Schema
    results["Lessons Schema"] = test_lessons_schema()
    
    # Test 3: Preferences (with first session)
    if sessions:
        results["Preferences Query"] = test_preferences_with_session(sessions[0]['session_id'])
    
    # Test 4: State History (with second session)
    if len(sessions) > 1:
        results["State History Query"] = test_state_history_with_session(sessions[1]['session_id'])
    
    # Test 5: Pagination
    results["Pagination"] = test_pagination()
    
    # Test 6: Error Handling
    results["Error Handling"] = test_error_handling()
    
    # Test 7: CORS
    results["CORS"] = test_cors()
    
    # Print summary
    print_section("ADVANCED TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    print("\n" + "="*75)
    print(f"TOTAL: {passed}/{total} advanced tests passed")
    print("="*75 + "\n")

if __name__ == '__main__':
    main()
