"""
Price analyzer service for Valoriste
"""
from typing import Dict, List, Optional, Tuple
from statistics import mean, median, stdev
from ..models.product import Product
from ..ebay_api import EbayAPI
from ..config import Config
from concurrent.futures import ThreadPoolExecutor
from functools import partial

class PriceAnalysis:
    """Container for price analysis results"""
    def __init__(self, median_price: float, total_cost: float, 
                 ebay_fees: float, real_profit: float, roi: float,
                 is_good_deal: bool, confidence: float,
                 mean_price: float = 0.0, std_dev: float = 0.0, 
                 sample_size: int = 1):
        self.median_price = median_price
        self.mean_price = mean_price
        self.std_dev = std_dev
        self.sample_size = sample_size
        self.is_good_deal = is_good_deal
        self.confidence = confidence
        self.total_cost = total_cost
        self.ebay_fees = ebay_fees
        self.real_profit = real_profit
        self.roi = roi
    
    def __str__(self) -> str:
        return (
            f"Price Analysis:\n"
            f"Median Price: ${self.median_price:.2f}\n"
            f"Mean Price: ${self.mean_price:.2f}\n"
            f"Standard Deviation: ${self.std_dev:.2f}\n"
            f"Sample Size: {self.sample_size}\n"
            f"Good Deal: {'Yes' if self.is_good_deal else 'No'}\n"
            f"Confidence: {self.confidence:.1%}"
        )

class PriceAnalyzer:
    """Service for analyzing product prices"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.ebay_api = EbayAPI(config=self.config)
        self.executor = ThreadPoolExecutor(max_workers=20)
    
    def analyze_batch(self, items: List[Dict]) -> List[Tuple[Dict, PriceAnalysis]]:
        """Analyze multiple items in parallel with chunking"""
        # Process in chunks of 50 for better memory management
        chunk_size = 50
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
        
        all_results = []
        for chunk in chunks:
            analyze_func = partial(self.analyze, print_progress=False)
            results = list(self.executor.map(analyze_func, chunk))
            all_results.extend([
                (item, analysis) 
                for item, analysis in zip(chunk, results) 
                if analysis
            ])
            
        return all_results
    
    def analyze(self, item: Dict, print_progress: bool = True) -> Optional[PriceAnalysis]:
        """Analyze a single item"""
        try:
            title = item.get('title')
            if not title:
                return None
                
            if print_progress:
                print(".", end="", flush=True)
                
            # Get historical prices for similar items
            sold_items = self.ebay_api.search_sold_items(title)
            
            if not sold_items:
                return None
                
            # Extract prices from sold items
            prices = []
            for sold_item in sold_items:
                try:
                    price = float(sold_item.get('price', {}).get('value', 0))
                    if price > 0:
                        prices.append(price)
                except (ValueError, TypeError, AttributeError):
                    continue
            
            if len(prices) < 2:
                return None
                
            # Calculate statistics
            try:
                med_price = median(prices)
                if med_price <= 0:
                    return None
                    
                avg_price = mean(prices)
                if avg_price <= 0:
                    return None
                    
                std_dev = stdev(prices) if len(prices) > 1 else 0
                
            except (ValueError, TypeError, ZeroDivisionError) as e:
                print(f"Error calculating statistics: {e}")
                return None
            
            # Get current item's price
            try:
                current_price = float(item.get('price', {}).get('value', 0))
                if current_price <= 0:
                    return None
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Could not get current price: {e}")
                return None
            
            # Calculate real costs and profits
            try:
                # Add shipping cost to our purchase price
                total_cost = current_price + self.config.AVERAGE_SHIPPING_COST
                
                # Calculate eBay fees on potential sale
                ebay_fee_multiplier = self.config.EBAY_FEE_PERCENTAGE / 100
                potential_sale_price = med_price
                ebay_fees = potential_sale_price * ebay_fee_multiplier
                
                # Calculate real profit after all costs
                real_profit = potential_sale_price - total_cost - ebay_fees
                
                # Adjust ROI calculation to use total cost
                roi = (real_profit / total_cost) * 100
                
                # Only consider it a good deal if profit is still positive after fees
                is_good_deal = real_profit > 0 and roi >= self.config.DEAL_PERCENTAGE_THRESHOLD
                
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Could not calculate costs: {e}")
                return None
            
            # Calculate confidence
            try:
                # Base confidence on number of samples
                sample_confidence = len(prices) / 30 if len(prices) > 0 else 0
                confidence = min(sample_confidence, 1.0)
                
                # Adjust confidence based on price variance if possible
                if std_dev > 0 and med_price > 0:
                    try:
                        variance_ratio = std_dev / med_price
                        if variance_ratio > 0:
                            price_confidence = 1 - min(variance_ratio, 1.0)
                            confidence *= price_confidence
                    except ZeroDivisionError:
                        print("Warning: Could not calculate price confidence")
                
            except ZeroDivisionError:
                print("Warning: Using default confidence due to calculation error")
                confidence = 0.1  # Set a low default confidence
            
            return PriceAnalysis(
                median_price=med_price,
                mean_price=avg_price,
                std_dev=std_dev,
                sample_size=len(prices),
                is_good_deal=is_good_deal,
                confidence=confidence,
                total_cost=total_cost,
                ebay_fees=ebay_fees,
                real_profit=real_profit,
                roi=roi
            )
            
        except Exception as e:
            print(f"\nError analyzing item: {e}")
            return None

    def get_theoretical_price(self, product: Product) -> float:
        """Calculate theoretical price based on historical data"""
        search_term = f"{product.brand} {product.title}"
        new_results = self.ebay_api.analyze_lululemon_item(search_term, condition="new")
        used_results = self.ebay_api.analyze_lululemon_item(search_term, condition="used")
        
        if new_results and used_results:
            return new_results['median_price']
        return 0.0
    
    def analyze_opportunity(self, product: Product) -> Product:
        """Analyze if product presents a good opportunity"""
        try:
            theo_price = self.get_theoretical_price(product)
            if theo_price > 0 and product.price > 0:  # Check both prices are positive
                product.theo_price = theo_price
                product.potential_profit = theo_price - product.price
                try:
                    product.roi = (product.potential_profit / product.price) * 100
                except ZeroDivisionError:
                    print(f"Warning: Cannot calculate ROI (price is zero)")
                    product.roi = 0.0
            else:
                print(f"Warning: Invalid prices for ROI calculation (theo: ${theo_price}, actual: ${product.price})")
                product.theo_price = 0.0
                product.potential_profit = 0.0
                product.roi = 0.0
                
            return product
            
        except Exception as e:
            print(f"Error analyzing opportunity: {e}")
            # Return product with default values if analysis fails
            product.theo_price = 0.0
            product.potential_profit = 0.0
            product.roi = 0.0
            return product

    async def analyze_batch_async(self, items: List[Dict]) -> List[Tuple[Dict, PriceAnalysis]]:
        """Async version of analyze_batch"""
        print(f"\nFound {len(items)} items to analyze...")
        
        analyzed_items = []
        for item in items:
            try:
                analysis = await self.analyze_item_async(item)
                if analysis:
                    analyzed_items.append((item, analysis))
            except Exception as e:
                print(f"Error analyzing item: {e}")
                continue
        
        print(f"\nCompleted analysis of {len(analyzed_items)} items")
        return analyzed_items
    
    async def analyze_item_async(self, item: Dict) -> Optional[PriceAnalysis]:
        """Async version of analyze_item"""
        try:
            # Get current price
            price = float(item.get('price', {}).get('value', 0))
            if price <= 0:
                return None
            
            # Get shipping cost
            shipping_cost = 0.0
            shipping_options = item.get('shippingOptions', [])
            if shipping_options:
                shipping_info = shipping_options[0]
                if shipping_info.get('shippingCostType') == 'FIXED':
                    shipping_cost = float(shipping_info.get('shippingCost', {}).get('value', 0))
                else:
                    shipping_cost = 12.99  # Default shipping estimate
            
            total_cost = price + shipping_cost
            
            # Calculate eBay fees (approximately 12.9% + $0.30)
            ebay_fees = (price * 0.129) + 0.30
            
            # Calculate market value based on item condition
            condition = item.get('condition', '').lower()
            if 'new' in condition:
                markup = 1.5  # 50% markup for new items
            else:
                markup = 1.3  # 30% markup for used items
            
            market_value = price * markup
            
            # Calculate profit
            real_profit = market_value - total_cost - ebay_fees
            
            # Calculate ROI
            roi = (real_profit / total_cost) * 100 if total_cost > 0 else 0
            
            # Determine if it's a good deal
            is_good_deal = roi >= 20  # Lower threshold to 20%
            
            # Set confidence based on price difference and condition
            base_confidence = min(abs(market_value - price) / price, 1.0)
            condition_factor = 1.0 if 'new' in condition else 0.8
            confidence = base_confidence * condition_factor
            
            # Calculate standard deviation (estimated)
            std_dev = market_value * 0.15  # Assume 15% variation
            
            # Print debug info
            print(f"\nAnalyzing item: {item.get('title')[:50]}...")
            print(f"Price: ${price:.2f}")
            print(f"Market Value: ${market_value:.2f}")
            print(f"ROI: {roi:.1f}%")
            print(f"Profit: ${real_profit:.2f}")
            
            return PriceAnalysis(
                median_price=market_value,
                total_cost=total_cost,
                ebay_fees=ebay_fees,
                real_profit=real_profit,
                roi=roi,
                is_good_deal=is_good_deal,
                confidence=confidence,
                mean_price=market_value,  # Using market value as mean
                std_dev=std_dev,
                sample_size=1  # Single sample for now
            )
            
        except Exception as e:
            print(f"Error in price analysis: {e}")
            print(f"Item data: {item}")
            return None 