"""
Product finder service for Valoriste
"""
from typing import List, Dict, Optional
from ..ebay_api import EbayAPI
from ..config import Config
from ..models.user import User, UserSizes
import asyncio

class ProductFinder:
    """Service for finding products on eBay"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.ebay_api = EbayAPI(config=self.config)
    
    def search(self, keywords: str, category_id: Optional[str] = None,
              min_price: Optional[float] = None,
              max_price: Optional[float] = None) -> List[Dict]:
        """
        Search for products matching the given criteria
        
        Args:
            keywords: Search terms
            category_id: Optional eBay category ID
            min_price: Minimum price filter
            max_price: Maximum price filter
            
        Returns:
            List of products matching the search criteria
        """
        return self.ebay_api.search_items(
            keywords=keywords,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price
        )
    
    def find_deals(self, keywords: str, target_price: float) -> List[Dict]:
        """Find potential deals based on keywords and price"""
        # Add more specific keywords to reduce irrelevant results
        search_terms = f"{keywords} -fake -replica -knockoff"
        
        # Set price range to filter out obvious non-deals
        min_price = 5  # Avoid junk listings
        max_price = target_price * 1.2  # Allow slightly above target
        
        items = self.ebay_api.search_items(
            keywords=search_terms,
            min_price=min_price,
            max_price=max_price
        )
        
        # Pre-filter items to reduce analysis load
        filtered_items = []
        for item in items:
            try:
                price = float(item.get('price', {}).get('value', 0))
                if price > 0 and price <= target_price:
                    filtered_items.append(item)
            except (ValueError, TypeError):
                continue
                
        return filtered_items
    
    def find_deals_for_user(self, user: User) -> List[Dict]:
        """Find deals specifically for a user with optimized search"""
        # Prepare size filters with variations
        size_filters = set()
        for size in (user.sizes.tops + user.sizes.bottoms_waist + 
                    user.sizes.bottoms_letter + user.sizes.outerwear):
            size_filters.add(size)
            # Add common variations
            if size.isdigit():
                # Add AU size conversion (approximate)
                au_size = int(size) + 4
                size_filters.add(str(au_size))
            elif size.upper() == 'S':
                size_filters.add('Small')
                size_filters.add('4')
                size_filters.add('6')
            elif size.upper() == 'M':
                size_filters.add('Medium')
                size_filters.add('8')
                size_filters.add('10')
        
        size_filters = list(size_filters)
        print("\nSearching with size filters:", size_filters)
        
        # Get all items in parallel
        items = self.ebay_api.search_items_bulk(
            brands=user.preferences.brands,
            size_filters=size_filters
        )
        
        if not items:
            print("No items found in initial search")
            return []
            
        # Use set operations for faster filtering
        excluded_words = {word.lower() for word in user.preferences.excluded_keywords}
        
        # Filter items efficiently
        filtered_items = []
        price_filtered = 0
        excluded_filtered = 0
        
        for item in items:
            try:
                title = item.get('title', '').lower()
                price = float(item.get('price', {}).get('value', 0))
                
                # Quick checks first
                if price <= 0 or price > user.preferences.max_price:
                    price_filtered += 1
                    continue
                    
                # Check excluded keywords
                if any(word in title for word in excluded_words):
                    excluded_filtered += 1
                    continue
                
                # For women's clothing, check for men's terms
                mens_terms = {'mens', 'men', 'male', 'man', 'boys', 'boy'}
                if any(term in title for term in mens_terms):
                    excluded_filtered += 1
                    continue
                
                filtered_items.append(item)
                
            except Exception as e:
                print(f"Error processing item: {e}")
                continue
        
        print(f"\nFiltering results:")
        print(f"Initial items: {len(items)}")
        print(f"Price filtered: {price_filtered}")
        print(f"Excluded word filtered: {excluded_filtered}")
        print(f"Final items: {len(filtered_items)}")
        
        # Sort by price
        filtered_items.sort(key=lambda x: float(x.get('price', {}).get('value', 0)))
        
        return filtered_items
    
    async def find_deals_for_user_async(self, user: User) -> List[Dict]:
        """Async version of find_deals_for_user"""
        try:
            # Reset eBay API session
            if self.ebay_api.session:
                await self.ebay_api.close_session()
            
            # Get size filters with gender-specific variations
            size_filters = self._get_size_filters(user.sizes, user.gender.value)
            
            print(f"\nSearching for {user.gender.value}'s clothing with sizes:", size_filters)
            
            # Get all items in parallel using async method
            items = await self.ebay_api.search_multiple_brands_async(
                brands=user.preferences.brands,
                size_filters=size_filters,
                gender=user.gender.value
            )
            
            if not items:
                print("No items found in initial search")
                return []
                
            # Use set operations for faster filtering
            excluded_words = {word.lower() for word in user.preferences.excluded_keywords}
            
            # Filter items efficiently
            filtered_items = []
            price_filtered = 0
            excluded_filtered = 0
            
            for item in items:
                try:
                    title = item.get('title', '').lower()
                    price = float(item.get('price', {}).get('value', 0))
                    
                    # Quick checks first
                    if price <= 0 or price > user.preferences.max_price:
                        price_filtered += 1
                        continue
                        
                    # Check excluded keywords
                    if any(word in title for word in excluded_words):
                        excluded_filtered += 1
                        continue
                    
                    # Verify it's a clothing item
                    clothing_keywords = ['dress', 'top', 'skirt', 'pants', 'jacket', 'coat', 'sweater', 'blouse', 'jumpsuit']
                    if not any(keyword in title.lower() for keyword in clothing_keywords):
                        excluded_filtered += 1
                        continue
                    
                    filtered_items.append(item)
                    
                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue
            
            print(f"\nFiltering results:")
            print(f"Initial items: {len(items)}")
            print(f"Price filtered: {price_filtered}")
            print(f"Excluded word filtered: {excluded_filtered}")
            print(f"Final items: {len(filtered_items)}")
            
            # Sort by price
            filtered_items.sort(key=lambda x: float(x.get('price', {}).get('value', 0)))
            
            return filtered_items
        
        except Exception as e:
            print(f"Error in find_deals_for_user_async: {e}")
            return []
        finally:
            # Ensure session cleanup
            if self.ebay_api.session:
                await self.ebay_api.close_session()

    def _get_size_filters(self, sizes: UserSizes, gender: str) -> List[str]:
        """Get size filters with gender-specific variations"""
        # Validate gender
        if not isinstance(gender, str):
            gender = str(gender)
        if gender not in ('men', 'women'):
            raise ValueError(f"Invalid gender value: {gender}")
        
        size_filters = set()
        
        # Process letter sizes with US variations
        for size in (sizes.tops + sizes.bottoms_letter + sizes.outerwear):
            if not size.isdigit():
                size_upper = size.upper()
                # Add basic variations
                if size_upper == 'S':
                    size_filters.update(['Small', 'S'])
                    if gender == 'women':
                        size_filters.add('4')  # US women's size
                elif size_upper == 'M':
                    size_filters.update(['Medium', 'M'])
                    if gender == 'women':
                        size_filters.add('8')  # US women's size
                elif size_upper == 'L':
                    size_filters.update(['Large', 'L'])
                    if gender == 'women':
                        size_filters.add('12')  # US women's size
        
        # Process waist sizes with US variations
        for size in sizes.bottoms_waist:
            if size.isdigit():
                size_filters.add(size)  # Basic numeric size
                if gender == 'men':
                    # Add men's inseam variations
                    size_filters.update([
                        f"{size}R",  # Regular
                        f"{size}L",  # Long
                        f"W{size}"   # Waist prefix
                    ])
        
        print(f"\nGenerated size filters for {gender}:", sorted(size_filters))
        return list(size_filters)

    async def cleanup(self):
        """Cleanup resources"""
        if self.ebay_api and self.ebay_api.session:
            await self.ebay_api.session.close()

    def __del__(self):
        """Ensure cleanup on deletion"""
        if hasattr(self, 'ebay_api') and self.ebay_api:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.cleanup())
            finally:
                loop.close() 