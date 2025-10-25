#!/usr/bin/env python3
"""
Fix remaining issues from multi-league migration
1. Recreate databases with correct schema
2. Fix any template references to old config variables
"""

import os
import sys
import sqlite3
import glob

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_databases():
    """Remove old databases and let them be recreated with correct schema"""
    print("1. Cleaning up old database files...")
    
    db_files = glob.glob('data/fpl_data_*.db')
    
    if not db_files:
        print("   No league databases found - they'll be created fresh")
        return
    
    print(f"   Found {len(db_files)} database files")
    
    for db_file in db_files:
        print(f"   Removing {db_file}...")
        try:
            os.remove(db_file)
            print(f"   ✓ Removed {db_file}")
        except Exception as e:
            print(f"   ✗ Error removing {db_file}: {e}")
    
    print("\n   ✓ Database cleanup complete")
    print("   Run collect_all_leagues.py to recreate with correct schema\n")


def fix_template_references():
    """Fix dashboard.html if it references old config variables"""
    print("2. Checking dashboard.html for old config references...")
    
    template_path = 'templates/dashboard.html'
    
    if not os.path.exists(template_path):
        print(f"   Template not found at {template_path}")
        return
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Replace config.LEAGUE_NAME with league_name (passed from app.py)
    if 'config.LEAGUE_NAME' in content:
        content = content.replace('config.LEAGUE_NAME', 'league_name')
        changes_made.append("config.LEAGUE_NAME → league_name")
    
    # Replace config.LEAGUE_ID with league_code (passed from app.py)
    if 'config.LEAGUE_ID' in content:
        content = content.replace('config.LEAGUE_ID', 'league_code')
        changes_made.append("config.LEAGUE_ID → league_code")
    
    # Replace any other old config references
    if 'config.FPL_LEAGUE_ID' in content:
        content = content.replace('config.FPL_LEAGUE_ID', 'league_code')
        changes_made.append("config.FPL_LEAGUE_ID → league_code")
    
    if content != original_content:
        print(f"   Found {len(changes_made)} references to fix:")
        for change in changes_made:
            print(f"      - {change}")
        
        # Write updated template
        with open(template_path, 'w') as f:
            f.write(content)
        
        print(f"   ✓ Updated {template_path}")
    else:
        print("   ✓ No old config references found")


def fix_app_template_context():
    """Check if app.py passes the right variables to template"""
    print("\n3. Checking app.py template context...")
    
    if not os.path.exists('app.py'):
        print("   app.py not found")
        return
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check if dashboard_league function exists and passes variables correctly
    if 'def dashboard_league(league_code):' in content:
        if 'league_code=league_code' in content and 'league_name=' in content:
            print("   ✓ app.py passes league_code and league_name to template")
        else:
            print("   ⚠️  app.py may not be passing correct variables to template")
            print("   Check that dashboard_league() includes:")
            print("      return render_template('dashboard.html',")
            print("          league_code=league_code,")
            print("          league_name=league_config['name']")
    else:
        print("   ⚠️  dashboard_league function not found - app.py may not be patched")


def main():
    print("="*70)
    print("Multi-League Migration Fix Script")
    print("="*70)
    print()
    
    # Check we're in the right directory
    if not os.path.exists('config.py'):
        print("❌ Error: config.py not found")
        print("Please run this script from the vantix root directory")
        return 1
    
    fix_databases()
    fix_template_references()
    fix_app_template_context()
    
    print("\n" + "="*70)
    print("Fix Complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Run: python collect_all_leagues.py")
    print("2. Restart Flask: sudo systemctl restart vantix")
    print("3. Test: Visit http://your-domain.com/")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
