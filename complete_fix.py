#!/usr/bin/env python3
"""
Complete fix for multi-league migration issues
Run this to fix everything at once
"""

import os
import sys
import glob
import subprocess

def step(num, desc):
    print(f"\n{'='*70}")
    print(f"Step {num}: {desc}")
    print('='*70)

def main():
    print("="*70)
    print("COMPLETE MULTI-LEAGUE FIX")
    print("="*70)
    print("\nThis will:")
    print("1. Deploy fixed database.py")
    print("2. Delete old databases")
    print("3. Re-patch app.py with improved script")
    print("4. Fix dashboard.html template")
    print("5. Collect fresh data")
    print()
    
    if not os.path.exists('config.py'):
        print("❌ Error: Run from vantix root directory")
        return 1
    
    # Step 1: Deploy fixed database.py
    step(1, "Deploying fixed database.py")
    if os.path.exists('database.py'):
        print("Copying database.py to data/")
        os.system('cp database.py data/')
        print("✓ Deployed")
    else:
        print("⚠️  database.py not found in current directory")
        print("   Make sure you copied it here first")
        return 1
    
    # Step 2: Delete old databases
    step(2, "Cleaning old databases")
    db_files = glob.glob('data/fpl_data_*.db')
    if db_files:
        print(f"Found {len(db_files)} old database files")
        for db_file in db_files:
            print(f"  Removing {db_file}...")
            os.remove(db_file)
        print("✓ Cleaned")
    else:
        print("No old databases found")
    
    # Step 3: Re-patch app.py
    step(3, "Patching app.py")
    if os.path.exists('patch_app_v2.py'):
        print("Running improved patcher...")
        # Run the patcher
        result = subprocess.run([sys.executable, 'patch_app_v2.py', 'app.py'], 
                              input=b'y\n', capture_output=False)
        if result.returncode == 0:
            print("✓ app.py patched")
        else:
            print("⚠️  Patcher may have had issues - check output above")
    else:
        print("⚠️  patch_app_v2.py not found")
        return 1
    
    # Step 4: Verify dashboard_league function exists
    step(4, "Verifying app.py patch")
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    if 'def dashboard_league(league_code):' in app_content:
        print("✓ dashboard_league function found")
    else:
        print("⚠️  dashboard_league function not found")
        print("   app.py may need manual patching")
        return 1
    
    if 'def league_list():' in app_content:
        print("✓ league_list function found")
    else:
        print("⚠️  league_list function not found")
    
    # Step 5: Fix dashboard.html template
    step(5, "Fixing dashboard.html template")
    template_path = 'templates/dashboard.html'
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        original = template_content
        
        # Fix config references
        template_content = template_content.replace('config.LEAGUE_NAME', 'league_name')
        template_content = template_content.replace('config.LEAGUE_ID', 'league_code')
        template_content = template_content.replace('config.FPL_LEAGUE_ID', 'league_code')
        
        if template_content != original:
            with open(template_path, 'w') as f:
                f.write(template_content)
            print("✓ Fixed template references")
        else:
            print("✓ Template already correct")
    else:
        print("⚠️  dashboard.html not found")
    
    # Step 6: Ready to collect data
    step(6, "Ready to collect data")
    print("\nAll fixes applied!")
    print("\nNext steps:")
    print("1. Run: python collect_all_leagues.py")
    print("2. Restart: sudo systemctl restart vantix")
    print("3. Test: Visit http://your-domain.com/")
    print()
    
    response = input("Run data collection now? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        print("\nCollecting data for all leagues...")
        result = subprocess.run([sys.executable, 'collect_all_leagues.py'])
        if result.returncode == 0:
            print("\n✓ Data collection complete!")
            print("\nNow restart Flask: sudo systemctl restart vantix")
        else:
            print("\n⚠️  Data collection had errors - check output above")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
