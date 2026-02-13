#!/usr/bin/env python3
"""
Zoho OAuth Token Generator - Generate fresh refresh token
Based on test results: Europe (.eu) region works best
"""
import requests
import json
from urllib.parse import urlencode

def generate_auth_url():
    """Generate authorization URL for Europe region"""
    print("🎯 ZOHO OAUTH TOKEN GENERATOR")
    print("="*50)
    
    client_id = input("Enter your Client ID: ").strip()
    
    # Zoho Mail API scopes
    scopes = [
        "ZohoMail.messages.CREATE",
        "ZohoMail.accounts.READ", 
        "ZohoMail.messages.READ",
        "ZohoMail.folders.READ"
    ]
    
    params = {
        'scope': ','.join(scopes),
        'client_id': client_id,
        'response_type': 'code',
        'access_type': 'offline',
        'redirect_uri': 'https://developer.zoho.com/apigw/runner/zoho/v2/oauth/dummy'
    }
    
    # Use Europe region (based on your test showing invalid_code vs invalid_client)
    auth_url = f"https://accounts.zoho.eu/oauth/v2/auth?{urlencode(params)}"
    
    print("\n" + "="*70)
    print("🔗 STEP 1: Visit this URL to authorize your app:")
    print("="*70)
    print(auth_url)
    print("="*70)
    print("\n📋 Instructions:")
    print("1. Copy the URL above and paste it in your browser")
    print("2. Log in to your Zoho account")
    print("3. Grant permissions to your app")
    print("4. You'll be redirected to a dummy page with the authorization code")
    print("5. Copy the 'code' parameter from the redirect URL")
    print("6. Run this script again to generate refresh token")
    
    return client_id

def generate_refresh_token():
    """Generate refresh token from authorization code"""
    print("\n" + "="*50)
    print("🔑 STEP 2: Generate Refresh Token")
    print("="*50)
    
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    auth_code = input("Enter the authorization code from redirect URL: ").strip()
    
    # Use Europe region
    token_url = "https://accounts.zoho.eu/oauth/v2/token"
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'https://developer.zoho.com/apigw/runner/zoho/v2/oauth/dummy',
        'code': auth_code
    }
    
    print(f"\n🔄 Making request to: {token_url}")
    
    try:
        response = requests.post(token_url, data=data)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("\n✅ SUCCESS! Tokens generated!")
            print(json.dumps(token_data, indent=2))
            
            if 'refresh_token' in token_data:
                print(f"\n🔑 UPDATE YOUR .ENV FILE:")
                print("="*50)
                print(f"ZOHO_REFRESH_TOKEN={token_data['refresh_token']}")
                print("="*50)
                
                # Test the new token
                print(f"\n🧪 Testing new refresh token...")
                if test_refresh_token(client_id, client_secret, token_data['refresh_token']):
                    print("🎉 SUCCESS! Your new refresh token works!")
                else:
                    print("⚠️ Warning: Token test failed")
            else:
                print("❌ No refresh_token in response!")
                
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            error_data = response.json()
            print(f"📄 Error: {json.dumps(error_data, indent=2)}")
                
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")

def test_refresh_token(client_id, client_secret, refresh_token):
    """Test the new refresh token"""
    token_url = "https://accounts.zoho.eu/oauth/v2/token"
    
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }
    
    try:
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            if 'access_token' in token_data:
                print("✅ Refresh token works! Access token received.")
                return True
        
        print(f"❌ Test failed: {response.json()}")
        return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main function"""
    print("Choose what you need:")
    print("1. Generate authorization URL (first time)")
    print("2. Generate refresh token (after authorization)")
    print("3. Test existing refresh token")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == '1':
        generate_auth_url()
    elif choice == '2':
        generate_refresh_token()
    elif choice == '3':
        # Test existing token from .env
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        client_id = os.getenv("ZOHO_CLIENT_ID")
        client_secret = os.getenv("ZOHO_CLIENT_SECRET") 
        refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        
        if all([client_id, client_secret, refresh_token]):
            test_refresh_token(client_id, client_secret, refresh_token)
        else:
            print("❌ Missing credentials in .env file")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()