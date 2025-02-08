"""Basic tests for Valoriste"""
import pytest
from valoriste import User, Gender, UserSizes, UserPreferences
from valoriste.models.user import SizePreference
from valoriste.services.product_finder import ProductFinder
from valoriste.services.price_analyzer import PriceAnalyzer
from valoriste.ebay_api import EbayAPI

def test_user_creation():
    """Test user creation with valid data"""
    user = User(
        id="test_id",
        name="Test User",
        gender=Gender.MEN,
        sizes=UserSizes(
            tops=['M', 'L'],
            bottoms_waist=['32', '33'],
            bottoms_letter=['M', 'L'],
            outerwear=['M', 'L']
        ),
        preferences=UserPreferences(
            brands=['Test Brand'],
            min_roi=30.0,
            max_price=300.0,
            excluded_keywords=['fake', 'replica']
        )
    )
    assert user.id == "test_id"
    assert user.name == "Test User"
    assert user.gender == Gender.MEN

@pytest.mark.asyncio
async def test_product_finder():
    """Test product finder with mock data"""
    from valoriste import ProductFinder
    finder = ProductFinder()
    
    # Test search with minimal criteria
    results = await finder.find_deals_for_user_async(User.create_thai())
    assert isinstance(results, list)

def test_price_analysis():
    """Test price analyzer with mock data"""
    from valoriste import PriceAnalyzer
    analyzer = PriceAnalyzer()
    
    # Test analysis with mock item
    mock_item = {
        'title': 'Test Item',
        'price': {'value': '100.00'},
        'condition': 'New',
    }
    analysis = analyzer.analyze(mock_item)
    assert analysis is None or hasattr(analysis, 'roi')

def test_basic_search():
    """Test basic functionality"""
    try:
        # Initialize API and services
        ebay_api = EbayAPI()
        price_analyzer = PriceAnalyzer(ebay_api)
        product_finder = ProductFinder(ebay_api, price_analyzer)
        
        # Create test user with minimal preferences
        test_user = User(
            id="test_1",
            name="Test User",
            email="test@example.com",
            sizes=SizePreference(
                tops="L",
                bottoms="32",
                outerwear="L"
            ),
            brands=["lululemon"],  # Start with just one brand
            max_price=100.0,
            min_roi=5.0
        )
        
        print("\nTesting eBay API connection...")
        ebay_api.test_credentials()
        
        print("\nTesting basic search...")
        results = ebay_api.search_items("lululemon mens", limit=5)
        if results.get('itemSummaries'):
            print(f"Found {len(results['itemSummaries'])} items")
            print("\nSample item:")
            item = results['itemSummaries'][0]
            print(f"Title: {item['title']}")
            print(f"Price: ${item['price']['value']}")
            print(f"Condition: {item.get('condition', 'unknown')}")
        else:
            print("No items found")
        
        print("\nTesting full product search...")
        products = product_finder.find_products_for_user(test_user)
        print(f"Search complete. Found {len(products)} potential opportunities")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Running basic functionality test...")
    success = test_basic_search()
    print(f"\nTest {'passed' if success else 'failed'}") 