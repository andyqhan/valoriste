from dotenv import load_dotenv
import os
import webbrowser
import time

# Load environment variables from .env file
load_dotenv()

from dev.models.user import User, SizePreference
from dev.services.product_finder import ProductFinder
from dev.services.price_analyzer import PriceAnalyzer
from dev.services.notification_service import NotificationService
from dev.ebay_api import EbayAPI

def get_new_token():
    """Get new OAuth tokens"""
    ebay = EbayAPI()
    auth_url = ebay.get_authorization_url()
    print("\nPlease visit this URL to authorize the application:")
    print(auth_url)
    webbrowser.open(auth_url)
    
    auth_code = input("\nEnter the authorization code from the redirect URL: ")
    tokens = ebay.get_tokens_from_code(auth_code)
    
    # Update .env file with new refresh token
    with open('dev/.env', 'r') as f:
        env_lines = f.readlines()
    
    with open('dev/.env', 'w') as f:
        for line in env_lines:
            if not line.startswith('EBAY_REFRESH_TOKEN='):
                f.write(line)
        f.write(f'EBAY_REFRESH_TOKEN={tokens["refresh_token"]}\n')
    
    return tokens

def main():
    try:
        # Initialize services
        ebay_api = EbayAPI()
        price_analyzer = PriceAnalyzer(ebay_api)
        product_finder = ProductFinder(ebay_api, price_analyzer)
        notification_service = NotificationService()
        
        # Thai's profile
        thai = User(
            id="thai_1",
            name="Thai",
            email="thai@example.com",
            sizes=SizePreference(
                tops="L",  
                bottoms="M/L/33/34",  # Will match any of these sizes
                outerwear="L"  # For jackets
            ),
            brands=[
                "norse projects",
                "apc",
                "lululemon",
                "theory",
                "vince"
            ],
            max_price=200.0,  # Setting a reasonable max price for these brands
            min_roi=10.0
        )
        
        # Find products for Thai
        products = product_finder.find_products_for_user(thai)
        
        # Print results
        notification_service.send_daily_update(thai, products)
        
    except Exception as e:
        if "invalid_grant" in str(e):
            print("\nRefresh token expired. Getting new token...")
            tokens = get_new_token()
            print("\nNew tokens obtained. Please run the script again.")
        else:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 