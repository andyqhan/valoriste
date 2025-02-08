"""
Test configuration loading
"""
from valoriste.config import Config
import os

def test_env_loading():
    """Test that environment variables are loaded correctly"""
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("ERROR: .env file not found in current directory")
        print(f"Current working directory: {os.getcwd()}")
        return False

    # Try loading config
    try:
        config = Config()
        
        # Check required values
        print("\nChecking eBay configuration:")
        print(f"Client ID: {'✓ Found' if config.EBAY_CLIENT_ID else '✗ Missing'}")
        print(f"Client Secret: {'✓ Found' if config.EBAY_CLIENT_SECRET else '✗ Missing'}")
        print(f"Redirect URI: {'✓ Found' if config.EBAY_REDIRECT_URI else '✗ Missing'}")
        
        # Test token refresh
        from valoriste.api.ebay_client import EbayBuyBrowseClient
        client = EbayBuyBrowseClient(config)
        print("\nTesting token refresh...")
        if client.refresh_access_token():
            print("✓ Successfully obtained access token")
            print(f"Token expires in: {client.token_expiry}")
        else:
            print("✗ Failed to obtain access token")
        
        return True
        
    except Exception as e:
        print(f"\nError loading configuration: {e}")
        return False

if __name__ == "__main__":
    print("Testing configuration loading...")
    success = test_env_loading()
    print(f"\nConfiguration test {'passed' if success else 'failed'}") 