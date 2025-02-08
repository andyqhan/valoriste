"""
Test script for eBay API client
"""
import asyncio
import os
from dotenv import load_dotenv, set_key
from valoriste.api.ebay_client import EbayFindingClient
from valoriste.config import Config

# Load environment variables before running tests
load_dotenv()

def verify_credentials():
    """Verify that required credentials are present"""
    required_vars = ['EBAY_CLIENT_ID']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\nMissing required environment variables:")
        for var in missing:
            print(f"- {var}")
        print("\nPlease add these to your .env file with valid values.")
        print("Example .env file:")
        print("""
EBAY_CLIENT_ID=your_app_id_here
        """)
        return False
    return True

async def test_search():
    """Test basic search functionality"""
    if not verify_credentials():
        return
        
    config = Config()
    client = EbayFindingClient(config)
    
    try:
        print("\nTesting basic search...")
        results = await client.search_items(
            query="lululemon mens",
            category_ids=["57989"],  # Men's Clothing
            min_price=20,
            max_price=200,
            conditions=["NEW", "USED"],
            limit=10
        )
        
        # Print results
        items = results.get('itemSummaries', [])
        print(f"\nFound {len(items)} items")
        
        for item in items:
            print("\n-------------------")
            print(f"Title: {item.get('title')}")
            print(f"Price: ${item.get('price', {}).get('value')}")
            print(f"Condition: {item.get('condition')}")
            if item.get('shippingOptions'):
                shipping = item['shippingOptions'][0]
                print(f"Shipping: {shipping.get('shippingCostType')} - ${shipping.get('shippingCost', {}).get('value', 'N/A')}")
            print(f"URL: {item.get('itemWebUrl')}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

async def test_different_searches():
    """Test various search scenarios"""
    config = Config()
    client = EbayFindingClient(config)
    
    test_cases = [
        {
            "name": "Basic men's clothing search",
            "params": {
                "query": "theory mens shirt",
                "category_ids": ["57989"],
                "conditions": ["NEW"]
            }
        },
        {
            "name": "Price range search",
            "params": {
                "query": "apc jeans",
                "min_price": 50,
                "max_price": 150
            }
        },
        {
            "name": "Multiple categories",
            "params": {
                "query": "norse projects",
                "category_ids": ["57989", "57990"],  # Shirts and Pants
                "limit": 5
            }
        }
    ]
    
    try:
        for test in test_cases:
            print(f"\nRunning test: {test['name']}")
            results = await client.search_items(**test['params'])
            items = results.get('itemSummaries', [])
            print(f"Found {len(items)} items")
            if items:
                print(f"Sample item: {items[0].get('title')} - ${items[0].get('price', {}).get('value')}")
    
    finally:
        await client.close()

async def test_theory_search():
    """Test searching for Theory men's clothing"""
    config = Config()
    client = EbayFindingClient(config)
    
    try:
        print("\nTesting Theory men's clothing search...")
        results = await client.search_items(
            query='Theory',  # Just the brand name
            category_ids=[client.CATEGORIES['mens']['all']],  # Men's category
            min_price=20,  # Add minimum price
            max_price=500,  # Add maximum price
            limit=10
        )
        
        items = results.get('itemSummaries', [])
        if not items:
            print("No items found in results")
            return
            
        print(f"\nFound {len(items)} items")
        
        # Calculate some statistics
        prices = [float(item['price']['value']) for item in items]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            print(f"Price range: ${min_price:.2f} - ${max_price:.2f}")
            print(f"Average price: ${avg_price:.2f}")
            
        # Count conditions
        conditions = {}
        for item in items:
            cond = item.get('condition', 'Unknown')
            conditions[cond] = conditions.get(cond, 0) + 1
            
        print("\nCondition breakdown:")
        for cond, count in conditions.items():
            print(f"- {cond}: {count} items")
            
        # Show sample titles
        print("\nSample items:")
        for item in items[:3]:
            print(f"\n- {item['title']}")
            print(f"  Price: ${float(item['price']['value']):.2f}")
            print(f"  URL: {item['itemWebUrl']}")
            print(f"  Images available: {len(item['images'])}")
            if item['images']:
                print(f"  First image: {item['images'][0]}")
            
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

async def verify_categories():
    """Verify that our category IDs are correct"""
    config = Config()
    client = EbayFindingClient(config)
    
    try:
        print("\nVerifying category IDs...")
        categories = await client.get_category_tree()
        
        # Check our stored categories
        for section, cats in client.CATEGORIES.items():
            print(f"\nChecking {section} categories:")
            for name, cat_id in cats.items():
                if cat_id in categories:
                    print(f"✓ {name}: {cat_id} ({categories[cat_id]})")
                else:
                    print(f"✗ {name}: {cat_id} (NOT FOUND)")
        
    except Exception as e:
        print(f"Error verifying categories: {e}")
    finally:
        await client.close()

async def test_api_format():
    """Test that our API calls match eBay's requirements"""
    config = Config()
    client = EbayFindingClient(config)
    
    # Test cases for different API features
    test_cases = [
        {
            "name": "Basic search",
            "query": "test",
            "expected_xml": '''
                <findItemsAdvancedRequest xmlns="http://www.ebay.com/marketplace/search/v1/services">
                    <keywords>test</keywords>
                    <paginationInput>
                        <entriesPerPage>10</entriesPerPage>
                        <pageNumber>1</pageNumber>
                    </paginationInput>
                </findItemsAdvancedRequest>
            '''
        },
        {
            "name": "Category search",
            "query": "test",
            "category_ids": ["1059"],
            "expected_xml": '''
                <findItemsAdvancedRequest xmlns="http://www.ebay.com/marketplace/search/v1/services">
                    <keywords>test</keywords>
                    <categoryId>1059</categoryId>
                </findItemsAdvancedRequest>
            '''
        }
    ]
    
    try:
        print("\nTesting API format...")
        for test in test_cases:
            print(f"\nTest: {test['name']}")
            
            # Generate payload
            payload = {
                'findItemsAdvanced': {
                    'keywords': test['query'],
                    'paginationInput': {
                        'entriesPerPage': '10',
                        'pageNumber': '1'
                    }
                }
            }
            
            if test.get('category_ids'):
                payload['findItemsAdvanced']['categoryId'] = test['category_ids'][0]
            
            # Convert to XML
            xml = client._dict_to_xml(payload)
            
            # Compare with expected (ignoring whitespace)
            expected = ''.join(test['expected_xml'].split())
            actual = ''.join(xml.split())
            
            if expected in actual:
                print("✓ XML format matches expected")
            else:
                print("✗ XML format mismatch")
                print("Expected:", expected)
                print("Actual:", actual)
                
    except Exception as e:
        print(f"Error testing API format: {e}")
    finally:
        await client.close()

def main():
    """Run the tests"""
    print("Starting eBay API tests...")
    asyncio.run(verify_categories())  # Run this first
    asyncio.run(test_theory_search())

if __name__ == "__main__":
    main() 