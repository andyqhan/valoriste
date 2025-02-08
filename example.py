"""
Example usage of Valoriste services
"""
from valoriste import (
    User,
    ProductFinder,
    PriceAnalyzer,
    EbayAPI
)
from valoriste.models.user import SizePreference
from valoriste.services.price_analyzer import PriceAnalysis
from typing import Dict
import argparse
from valoriste.web_app import app

def print_deal(item: Dict, analysis: PriceAnalysis) -> None:
    """Print deal information in a formatted way"""
    try:
        # Get price values safely
        current_price = float(item.get('price', {}).get('value', 0))
        
        # Calculate shipping cost based on item's shipping info
        shipping_options = item.get('shippingOptions', [])
        shipping_cost = 0.0
        shipping_type = "N/A"
        
        if shipping_options:
            shipping_info = shipping_options[0]
            shipping_type = shipping_info.get('shippingCostType', 'N/A')
            if shipping_type == 'FIXED':
                shipping_cost = float(shipping_info.get('shippingCost', {}).get('value', 0))
            elif shipping_type == 'CALCULATED':
                # Use an estimated shipping cost for calculated shipping
                shipping_cost = 12.99  # Estimated USPS Priority Mail cost
            else:
                shipping_cost = 12.99  # Default shipping cost if unknown
        
        total_cost = current_price + shipping_cost
        
        # Check if best offer is available
        buying_options = item.get('buyingOptions', [])
        best_offer_enabled = 'BEST_OFFER' in buying_options
        negotiated_price = current_price * 0.8 if best_offer_enabled else current_price
        negotiated_total = negotiated_price + shipping_cost
        
        print("\n\nDeal Found!")
        print(f"Item: {item.get('title')[:50]}...")
        print(f"Size: {item.get('itemSpecifics', {}).get('Size', 'N/A')}")
        print(f"Condition: {item.get('condition', 'N/A')}")
        
        # Show shipping info
        if shipping_type == 'FIXED':
            if shipping_cost == 0:
                print("Shipping: FREE")
            else:
                print(f"Shipping Cost: ${shipping_cost:.2f} (FIXED)")
        else:
            print(f"Shipping: {shipping_type} (est. ${shipping_cost:.2f})")
        
        # Show original and potential negotiated prices if best offer is available
        print(f"Listed Price: ${current_price:.2f}")
        if best_offer_enabled:
            print(f"Potential Offer Price (-20%): ${negotiated_price:.2f}")
        print(f"+ Shipping to us: ${shipping_cost:.2f}")
        print(f"= Total Cost: ${total_cost:.2f}")
        if best_offer_enabled:
            print(f"= Potential Total Cost with Offer: ${negotiated_total:.2f}")
            
        print(f"\nMarket Value: ${analysis.median_price:.2f}")
        print(f"- eBay Fees: ${analysis.ebay_fees:.2f}")
        
        # Show both original and potential profits
        real_profit = analysis.median_price - total_cost - analysis.ebay_fees
        print(f"= Real Profit: ${real_profit:.2f}")
        roi = (real_profit / total_cost) * 100
        
        if best_offer_enabled:
            negotiated_profit = analysis.median_price - negotiated_total - analysis.ebay_fees
            negotiated_roi = (negotiated_profit / negotiated_total) * 100
            print(f"= Potential Profit with Offer: ${negotiated_profit:.2f}")
            print(f"ROI: {roi:.1f}% (with offer: {negotiated_roi:.1f}%)")
        else:
            print(f"ROI: {roi:.1f}%")
            
        print(f"Confidence: {analysis.confidence:.1%}")
        
        # Add seller info if available
        seller = item.get('seller', {})
        if seller:
            feedback_score = seller.get('feedbackScore', 'N/A')
            feedback_percent = seller.get('feedbackPercentage', 'N/A')
            print(f"\nSeller: {seller.get('username', 'N/A')}")
            print(f"Feedback: {feedback_score} ({feedback_percent}%)")
            
        # Show item location
        location = item.get('itemLocation', {})
        if location:
            country = location.get('country', 'N/A')
            postal = location.get('postalCode', 'N/A')
            print(f"Location: {postal} ({country})")
        
        # Add eBay item URL
        web_url = item.get('itemWebUrl')
        if web_url:
            print(f"\neBay Link: {web_url}")
        else:
            item_id = item.get('itemId', '')
            if item_id:
                try:
                    actual_id = item_id.split('|')[1]
                    print(f"\neBay Link: https://www.ebay.com/itm/{actual_id}")
                except (IndexError, AttributeError):
                    pass
        
        if best_offer_enabled:
            print("\n* Best Offer available - prices shown with potential 20% discount")
            
        print("-" * 50)
    except Exception as e:
        print(f"Error printing deal: {str(e)}")
        print("Raw item data:", item)
        print("Raw analysis data:", analysis)

def main():
    parser = argparse.ArgumentParser(description='Valoriste Deal Finder')
    parser.add_argument('--web', action='store_true', help='Run in web mode')
    args = parser.parse_args()
    
    if args.web:
        # Run web interface
        app.run(debug=True)
    else:
        # Run CLI version
        try:
            ebay = EbayAPI()
            user = User.create_rose()
            
            print(f"\nSearching for deals for {user.name}...")
            print(f"Brands: {', '.join(user.preferences.brands)}")
            print(f"Sizes: Tops {user.sizes.tops}, Bottoms {user.sizes.bottoms_waist} or {user.sizes.bottoms_letter}")
            
            # Find and analyze deals efficiently
            product_finder = ProductFinder()
            price_analyzer = PriceAnalyzer()
            
            items = product_finder.find_deals_for_user(user)
            print(f"\nFound {len(items)} items to analyze...")
            
            analyzed_items = price_analyzer.analyze_batch(items)
            print(f"\nCompleted analysis of {len(analyzed_items)} items")
            
            # Process results
            deals_found = 0
            for item, analysis in analyzed_items:
                try:
                    if analysis and analysis.is_good_deal and analysis.roi >= user.preferences.min_roi:
                        deals_found += 1
                        print_deal(item, analysis)
                except Exception as e:
                    print(f"Error processing deal: {str(e)}")
                    continue
                
            if deals_found == 0:
                print("\nNo profitable deals found matching your preferences.")
            
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main() 