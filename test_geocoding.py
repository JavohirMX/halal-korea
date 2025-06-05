#!/usr/bin/env python3
"""
Test script for Korean address geocoding improvements.
Run this to test the geocoding functions with problematic Korean addresses.
"""

from transform_hp import geocode_address, try_multiple_address_formats

def test_korean_addresses():
    """Test geocoding with various Korean address formats."""
    
    test_addresses = [
        "경기도 안산 단원구 원곡동 936-3번지 2층",
        "서울특별시 강남구 역삼동 123번지",
        "부산광역시 해운대구 우동 456-7번지 1층",
        "인천광역시 남동구 구월동 789번지 (현대빌딩)",
        "경기도 수원시 영통구 매탄동"
    ]
    
    print("Testing Korean Address Geocoding")
    print("=" * 50)
    
    for i, address in enumerate(test_addresses, 1):
        print(f"\n{i}. Testing: {address}")
        print("-" * 40)
        
        # Show address format variations
        formats = try_multiple_address_formats(address)
        print(f"Will try {len(formats)} address formats:")
        for j, fmt in enumerate(formats, 1):
            print(f"   {j}. {fmt}")
        
        # Try geocoding
        result = geocode_address(address)
        if result:
            print(f"✅ SUCCESS: Found coordinates {result.y:.6f}, {result.x:.6f}")
        else:
            print("❌ FAILED: Could not geocode this address")
        
        print()

if __name__ == "__main__":
    test_korean_addresses() 