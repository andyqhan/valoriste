"""
Configuration management for Valoriste
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Valoriste"""
    
    # eBay API Configuration
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    EBAY_REDIRECT_URI = os.getenv('EBAY_REDIRECT_URI')
    EBAY_AUTH_TOKEN = os.getenv('EBAY_AUTH_TOKEN')
    EBAY_REFRESH_TOKEN = os.getenv('EBAY_REFRESH_TOKEN')
    
    # Fee Settings
    EBAY_FEE_PERCENTAGE = float(os.getenv('EBAY_FEE_PERCENTAGE', '12.9'))  # Standard eBay fee
    AVERAGE_SHIPPING_COST = float(os.getenv('AVERAGE_SHIPPING_COST', '7.99'))  # Average cost to receive item
    
    # API Endpoints
    EBAY_API_URL = "https://api.ebay.com"
    
    # Notification Settings
    NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # Analysis Settings
    MIN_PRICE_THRESHOLD = float(os.getenv('MIN_PRICE_THRESHOLD', '10.0'))
    MAX_PRICE_THRESHOLD = float(os.getenv('MAX_PRICE_THRESHOLD', '1000.0'))
    DEAL_PERCENTAGE_THRESHOLD = float(os.getenv('DEAL_PERCENTAGE_THRESHOLD', '20.0')) 