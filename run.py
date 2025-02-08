"""
Run script for Valoriste web application
"""
from valoriste.web_app import app
from valoriste.services.product_finder import ProductFinder
from valoriste.services.price_analyzer import PriceAnalyzer
from valoriste.services.user_service import UserService
import os
import socket
import asyncio
import argparse

def find_available_port(start_port: int = 5000, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to create a socket with the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

async def test_search_functionality():
    """Test the search and analysis functionality"""
    print("\nTesting search functionality...")
    
    # Initialize services
    product_finder = ProductFinder()
    price_analyzer = PriceAnalyzer()
    user_service = UserService()
    
    # Get test user
    user = user_service.get_user("thai")
    if not user:
        print("Error: Test user 'thai' not found")
        return False
        
    try:
        # Test search
        print(f"\nSearching for {user.name}'s preferences...")
        items = await product_finder.find_deals_for_user_async(user)
        
        if not items:
            print("No items found")
            return False
            
        print(f"Found {len(items)} items")
        
        # Test price analysis
        print("\nAnalyzing prices...")
        analyzed_items = await price_analyzer.analyze_batch_async(items)
        
        if not analyzed_items:
            print("No items could be analyzed")
            return False
            
        # Print sample results
        print("\nSample Results:")
        for item, analysis in analyzed_items[:3]:  # Show first 3 items
            print("\n-------------------")
            print(f"Title: {item.get('title')}")
            print(f"Price: ${item.get('price', {}).get('value')}")
            print(f"ROI: {analysis.roi:.1f}%")
            print(f"Profit: ${analysis.real_profit:.2f}")
            print(f"Confidence: {analysis.confidence:.1%}")
        
        print(f"\nSuccessfully analyzed {len(analyzed_items)} items")
        return True
        
    except Exception as e:
        print(f"Error in test: {e}")
        return False
    finally:
        # Cleanup
        await product_finder.cleanup()

async def verify_api_setup():
    """Verify API configuration and format"""
    from test_ebay import verify_categories, test_api_format
    
    print("\nVerifying eBay API setup...")
    await verify_categories()
    await test_api_format()

def run_cli_tests(verify: bool = False):
    """Run CLI tests"""
    print("Starting Valoriste CLI tests...")
    
    # Create and run event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        if verify:
            loop.run_until_complete(verify_api_setup())
        success = loop.run_until_complete(test_search_functionality())
        if success:
            print("\nAll tests passed successfully!")
        else:
            print("\nSome tests failed.")
    finally:
        loop.close()

def run_web_server(port: int = None):
    """Run the web server"""
    try:
        if not port:
            port = int(os.getenv('PORT', 0))
        
        if port == 0 or port == 5000:
            port = find_available_port(start_port=8000)
            
        print(f"\nStarting Valoriste web application on port {port}")
        print(f"Visit http://localhost:{port} to access the application")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True
        )
        
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Try setting a specific port in .env file: PORT=8000")
        print("2. Check if any other applications are using the ports")
        print("3. On macOS, you might need to disable AirPlay Receiver:")
        print("   System Preferences -> General -> AirDrop & Handoff")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Valoriste in CLI or web mode')
    parser.add_argument('mode', choices=['cli', 'web'], help='Run mode (cli or web)')
    parser.add_argument('--port', type=int, help='Port for web server (web mode only)', default=None)
    parser.add_argument('--verify', action='store_true', help='Verify API setup before running tests')
    
    args = parser.parse_args()
    
    if args.mode == 'cli':
        run_cli_tests(verify=args.verify)
    else:
        if args.verify:
            print("Warning: --verify flag is only used with cli mode")
        run_web_server(args.port) 