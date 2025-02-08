from flask import Flask, render_template, g, abort
from .models.user import User
from .services.product_finder import ProductFinder
from .services.price_analyzer import PriceAnalyzer
from .services.user_service import UserService
import asyncio
import nest_asyncio
from cachetools import TTLCache
import os

# Enable nested event loops
nest_asyncio.apply()

# Create Flask app with explicit template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

# Create a TTL cache (5 minutes expiration)
cache = TTLCache(maxsize=100, ttl=300)

# Add custom template filters
@app.template_filter('avg')
def avg_filter(lst):
    """Calculate average of a list"""
    return sum(lst) / len(lst) if lst else 0

@app.template_filter('sum')
def sum_filter(lst):
    """Calculate sum of a list"""
    return sum(lst) if lst else 0

# Create global instances
product_finder = ProductFinder()
price_analyzer = PriceAnalyzer()
user_service = UserService()

@app.before_request
def before_request():
    """Setup for each request"""
    # Store the event loop in g
    if not hasattr(g, 'loop'):
        g.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(g.loop)

@app.teardown_request
def teardown_request(exception):
    """Cleanup after each request"""
    # Close the event loop
    if hasattr(g, 'loop'):
        g.loop.close()
        delattr(g, 'loop')

async def search_and_analyze(user):
    """Combined search and analysis function"""
    try:
        # Reset the session for each search
        if product_finder.ebay_api.session:
            await product_finder.ebay_api.session.close()
            product_finder.ebay_api.session = None
            
        items = await product_finder.find_deals_for_user_async(user)
        if items:
            analyzed_items = await price_analyzer.analyze_batch_async(items)
            return items, analyzed_items
        return [], []
    except Exception as e:
        print(f"Error in search_and_analyze: {e}")
        return [], []

@app.route('/')
def home():
    try:
        return render_template('home.html')
    except Exception as e:
        print(f"Error rendering home template: {e}")
        return str(e), 500

@app.route('/search/<user_id>')
def search(user_id):
    # Get user from service
    user = user_service.get_user(user_id)
    if not user:
        abort(404, description="User not found")
    
    try:
        # Use the request's event loop
        items, analyzed_items = g.loop.run_until_complete(search_and_analyze(user))
        
        # Process deals
        deals = []
        for item, analysis in analyzed_items:
            if analysis:  # Only check if analysis exists
                try:
                    # Calculate shipping cost
                    shipping_cost = 0.0
                    shipping_type = "N/A"
                    shipping_options = item.get('shippingOptions', [])
                    
                    if shipping_options:
                        shipping_info = shipping_options[0]
                        shipping_type = shipping_info.get('shippingCostType', 'N/A')
                        if shipping_type == 'FIXED':
                            shipping_cost = float(shipping_info.get('shippingCost', {}).get('value', 0))
                        elif shipping_type == 'CALCULATED':
                            shipping_cost = 12.99  # Estimated USPS Priority Mail cost
                    
                    # Check if best offer is available
                    best_offer_enabled = 'BEST_OFFER' in item.get('buyingOptions', [])
                    current_price = float(item.get('price', {}).get('value', 0))
                    negotiated_price = current_price * 0.8 if best_offer_enabled else current_price
                    
                    # Calculate total cost including shipping and fees
                    total_cost = current_price + shipping_cost + analysis.ebay_fees
                    
                    # Only include deals with positive ROI
                    if analysis.roi >= 0:
                        deal_data = {
                            'title': item.get('title'),
                            'image_url': item.get('image', {}).get('imageUrl'),
                            'price': current_price,
                            'market_value': analysis.median_price,
                            'roi': analysis.roi,
                            'real_profit': analysis.real_profit,
                            'condition': item.get('condition'),
                            'size': item.get('itemSpecifics', {}).get('Size', 'N/A'),
                            'web_url': item.get('itemWebUrl'),
                            'brand': next((b for b in user.preferences.brands if b.lower() in item.get('title', '').lower()), 'Other'),
                            'total_cost': total_cost
                        }
                        deals.append(deal_data)
                except Exception as e:
                    print(f"Error processing deal: {e}")
                    continue
        
        # Sort deals by ROI
        deals.sort(key=lambda x: x['roi'], reverse=True)
        
        # Group deals by brand
        brands = {}
        for deal in deals:
            brand = deal['brand']
            if brand not in brands:
                brands[brand] = []
            brands[brand].append(deal)
        
        # Prepare template data (with minimal data)
        template_data = {
            'user': user,
            'deals': deals,
            'brands': brands,
            'total_items': len(items),
            'total_deals': len(deals)
        }
        
        # Cache the results
        cache_key = f'deals_{user_id}'
        cache[cache_key] = template_data
        
        return render_template('results.html', **template_data)
                            
    except Exception as e:
        print(f"Error in search route: {e}")
        return f"Error: {str(e)}", 500
    finally:
        # Ensure session cleanup
        g.loop.run_until_complete(cleanup_session())

async def cleanup_session():
    """Cleanup aiohttp session"""
    if product_finder.ebay_api.session:
        await product_finder.ebay_api.session.close()

if __name__ == '__main__':
    # Verify template directory exists
    if not os.path.exists(template_dir):
        print(f"Creating template directory: {template_dir}")
        os.makedirs(template_dir)
    
    print(f"Using template directory: {template_dir}")
    app.run(debug=True) 