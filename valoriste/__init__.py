"""
Valoriste - A package for product analysis and price tracking
"""
from importlib.metadata import version

__version__ = version("valoriste")

from .models.user import User, Gender, UserSizes, UserPreferences
from .models.product import Product
from .services.notification_service import NotificationService
from .services.price_analyzer import PriceAnalyzer, PriceAnalysis
from .services.product_finder import ProductFinder
from .ebay_api import EbayAPI

__all__ = [
    'User',
    'Gender',
    'UserSizes',
    'UserPreferences',
    'Product',
    'NotificationService',
    'PriceAnalyzer',
    'PriceAnalysis',
    'ProductFinder',
    'EbayAPI'
] 