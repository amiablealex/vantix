#!/usr/bin/env python3
"""
Automatic patcher for dashboard.js to add multi-league support
This script modifies dashboard.js to use league-specific API URLs
"""

import re
import sys

def patch_dashboard_js(filename='dashboard.js'):
    """Patch dashboard.js for multi-league support"""
    
    print(f"Reading {filename}...")
    with open(filename, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Add league code extraction at the top of the file
    print("1. Adding league code extraction...")
    
    league_code_snippet = """// Extract league code from URL for API calls
const leagueCode = window.location.pathname.split('/')[1] || '';

"""
    
    # Insert after any existing global declarations or at the start
    if 'const leagueCode' not in content:
        # Find a good insertion point (after "use strict" or at the very beginning)
        if "'use strict';" in content:
            content = content.replace("'use strict';", "'use strict';\n\n" + league_code_snippet)
        else:
            content = league_code_snippet + content
    
    # 2. Update all API endpoint calls to include league code
    print("2. Updating API endpoint calls...")
    
    api_endpoints = [
        'cumulative-points',
        'league-positions',
        'recent-transfers',
        'stats',
        'form-chart',
        'points-distribution',
        'team-comparison',
        'biggest-movers',
        'weekly-performance',
        'head-to-head',
        'differentials',
        'podium'
    ]
    
    for endpoint in api_endpoints:
        # Pattern 1: `/api/endpoint?${queryString}`
        old_pattern1 = f"'/api/{endpoint}\\?"
        new_pattern1 = f"'/api/${{leagueCode}}/{endpoint}?"
        content = content.replace(old_pattern1, new_pattern1)
        
        # Pattern 2: `/api/endpoint`
        old_pattern2 = f"'/api/{endpoint}'"
        new_pattern2 = f"'/api/${{leagueCode}}/{endpoint}'"
        content = content.replace(old_pattern2, new_pattern2)
        
        # Pattern 3: `/api/endpoint` with backticks
        old_pattern3 = f"`/api/{endpoint}`"
        new_pattern3 = f"`/api/${{leagueCode}}/{endpoint}`"
        content = content.replace(old_pattern3, new_pattern3)
        
        # Pattern 4: fetch('/api/endpoint')
        old_pattern4 = f"fetch('/api/{endpoint}'"
        new_pattern4 = f"fetch(`/api/${{leagueCode}}/{endpoint}`"
        content = content.replace(old_pattern4, new_pattern4)
        
        # Pattern 5: fetch(`/api/endpoint?
        old_pattern5 = f"fetch(`/api/{endpoint}?"
        new_pattern5 = f"fetch(`/api/${{leagueCode}}/{endpoint}?"
        content = content.replace(old_pattern5, new_pattern5)
    
    # 3. Update refresh button to use league-specific endpoint
    print("3. Updating refresh button...")
    
    content = content.replace(
        "fetch('/api/refresh',",
        "fetch(`/api/${leagueCode}/refresh`,"
    )
    
    content = content.replace(
        'fetch("/api/refresh",',
        'fetch(`/api/${leagueCode}/refresh`,'
    )
    
    # Check if anything changed
    if content == original_content:
        print("\n⚠️  Warning: No changes were made to the file!")
        print("The file may already be patched or the patterns didn't match.")
        return False
    
    # Write the patched content
    print(f"\nWriting patched version to {filename}...")
    with open(filename, 'w') as f:
        f.write(content)
    
    print("\n✅ Successfully patched dashboard.js!")
    
    return True


if __name__ == '__main__':
    import sys
    
    filename = sys.argv[1] if len(sys.argv) > 1 else 'dashboard.js'
    
    print("="*70)
    print("Dashboard.js Multi-League Patcher")
    print("="*70)
    print(f"\nThis will modify {filename} to use league-specific API URLs")
    print("A backup will NOT be created - commit your changes first!")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = patch_dashboard_js(filename)
        sys.exit(0 if success else 1)
    else:
        print("Patching cancelled.")
        sys.exit(0)
