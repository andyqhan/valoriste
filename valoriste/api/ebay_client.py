"""
eBay Finding API client
"""
from typing import Dict, List, Optional, Any
import aiohttp
from datetime import datetime, timedelta
import json
import requests
from ..config import Config
import asyncio
import base64
import xml.etree.ElementTree as ET
from cachetools import TTLCache
import hashlib

class EbayFindingClient:
    """Client for eBay's Finding API"""
    
    # eBay category IDs
    CATEGORIES = {
        'mens': {
            'all': '1059',
            'shirts': '57991',
            'pants': '57989',
            'outerwear': '57988',
            'suits': '3001',
            'activewear': '185099'
        }
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.api_endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = datetime.min
        self._request_delay = 0.5
        self.debug = True  # Add debug mode
        
        # Add cache with 1 hour TTL
        self._cache = TTLCache(maxsize=100, ttl=3600)  # Cache for 1 hour

    def _get_cache_key(self, query: str, category_ids: Optional[List[str]], min_price: Optional[float], 
                      max_price: Optional[float], conditions: Optional[List[str]], limit: int) -> str:
        """Generate a unique cache key for the search parameters"""
        key_parts = [
            query,
            str(category_ids),
            str(min_price),
            str(max_price),
            str(conditions),
            str(limit)
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def search_items(
        self,
        query: str,
        category_ids: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        conditions: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search for items using the Finding API with caching"""
        
        # Generate cache key
        cache_key = self._get_cache_key(query, category_ids, min_price, max_price, conditions, limit)
        
        # Check cache first
        if cache_key in self._cache:
            if self.debug:
                print(f"\nReturning cached results for query: {query}")
            return self._cache[cache_key]

        if self.debug:
            print(f"\nCache miss - fetching from API for query: {query}")
            
        if self.debug:
            print(f"\nSearching eBay with:")
            print(f"Query: {query}")
            print(f"Categories: {category_ids}")
            print(f"Price Range: ${min_price or 0} - ${max_price or 'any'}")

        # Build payload with optimized filters
        payload = {
            'findItemsAdvanced': {
                'keywords': f'"{query}" mens',
                'outputSelector': ['PictureURLSuperSize', 'PictureURLLarge', 'GalleryInfo', 'ItemSpecifics'],
                'paginationInput': {
                    'entriesPerPage': str(min(limit, 100)),
                    'pageNumber': '1'
                },
                'itemFilter': [
                    {'name': 'ListingType', 'value': 'FixedPrice'},
                    {'name': 'Currency', 'value': 'USD'},
                    {'name': 'HideVariations', 'value': 'True'}
                ]
            }
        }

        # Add category if provided
        if category_ids:
            payload['findItemsAdvanced']['categoryId'] = category_ids[0]

        # Add price filters if provided
        if min_price is not None:
            payload['findItemsAdvanced']['itemFilter'].append({
                'name': 'MinPrice',
                'value': str(min_price)
            })
        if max_price is not None:
            payload['findItemsAdvanced']['itemFilter'].append({
                'name': 'MaxPrice',
                'value': str(max_price)
            })

        # Add debug output for payload
        if self.debug:
            print("\nRequest payload:")
            print(json.dumps(payload, indent=2))

        headers = {
            'X-EBAY-SOA-SECURITY-APPNAME': self.config.EBAY_CLIENT_ID,
            'X-EBAY-SOA-OPERATION-NAME': 'findItemsAdvanced',
            'X-EBAY-SOA-SERVICE-VERSION': '1.13.0',
            'Content-Type': 'application/xml'
        }

        try:
            xml_payload = self._dict_to_xml(payload)
            if self.debug:
                print("\nSending request to eBay...")
                print("XML Payload:", xml_payload)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint,
                    headers=headers,
                    data=xml_payload
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        print(f"API request failed with status {response.status}")
                        print(f"Response: {response_text}")
                        return {'itemSummaries': []}

                    if self.debug:
                        print("\nResponse:", response_text)

                    results = self._parse_response(response_text)
                    
                    if self.debug:
                        print(f"Found {len(results.get('itemSummaries', []))} items")
                    
            # Cache the results
            self._cache[cache_key] = results
            
            return results

        except Exception as e:
            print(f"Error in search_items: {e}")
            print(f"Exception details: {str(e)}")
            return {'itemSummaries': []}

    def _dict_to_xml(self, d: Dict) -> str:
        """Convert dictionary to XML string"""
        def _to_xml(d, root):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key == 'itemFilter':
                        # Handle itemFilter array
                        for filter_item in value:
                            filter_elem = ET.SubElement(root, 'itemFilter')
                            for k, v in filter_item.items():
                                if isinstance(v, list):
                                    # Handle array values (like multiple conditions)
                                    for val in v:
                                        val_elem = ET.SubElement(filter_elem, k)
                                        val_elem.text = str(val)
                                else:
                                    elem = ET.SubElement(filter_elem, k)
                                    elem.text = str(v)
                    else:
                        child = ET.SubElement(root, key)
                        _to_xml(value, child)
            elif isinstance(d, list):
                for item in d:
                    _to_xml(item, root)
            else:
                root.text = str(d)

        root = ET.Element('findItemsAdvancedRequest', 
                         {'xmlns': 'http://www.ebay.com/marketplace/search/v1/services'})
        _to_xml(d['findItemsAdvanced'], root)
        return ET.tostring(root, encoding='unicode')

    def _enhance_image_url(self, url: str) -> str:
        """Convert eBay image URL to highest quality version"""
        # Only try to get the highest quality version (1600px)
        if 'i.ebayimg.com' in url:
            # Replace any size pattern with the largest size
            for size in ['s-l64', 's-l140', 's-l300', 's-l400', 's-l500', 's-l600']:
                if size in url:
                    return url.replace(size, 's-l1600')
        return url

    def _parse_response(self, xml_str: str) -> Dict:
        """Parse XML response to dictionary"""
        # Register the namespace
        namespaces = {
            'ns': 'http://www.ebay.com/marketplace/search/v1/services'
        }
        
        root = ET.fromstring(xml_str)
        items = []

        # Check for errors first
        error_node = root.find('.//ns:errorMessage', namespaces)
        if error_node is not None:
            error = error_node.find('.//ns:message', namespaces)
            if error is not None:
                print(f"\nAPI Error: {error.text}")
            return {'itemSummaries': []}

        # Get total count
        total_entries = root.find('.//ns:totalEntries', namespaces)
        if total_entries is not None and self.debug:
            print(f"\nTotal items available: {total_entries.text}")

        # Parse each item in searchResult
        search_result = root.find('.//ns:searchResult', namespaces)
        if search_result is None:
            if self.debug:
                print("No searchResult found in response")
                print("Available elements:", [elem.tag for elem in root.iter()])
            return {'itemSummaries': []}

        for item in search_result.findall('.//ns:item', namespaces):
            try:
                # Get basic item info
                title = item.find('ns:title', namespaces)
                price_elem = item.find('.//ns:currentPrice', namespaces)
                condition = item.find('.//ns:conditionDisplayName', namespaces)
                url = item.find('ns:viewItemURL', namespaces)
                
                # Get all available images with enhanced quality
                images = []
                # Try to get the highest quality image first
                supersize_images = item.findall('.//ns:pictureURLSuperSize', namespaces)
                if supersize_images:
                    for img in supersize_images:
                        if img is not None and img.text:
                            images.append(self._enhance_image_url(img.text))
                
                # If no supersize images, try large images
                if not images:
                    large_images = item.findall('.//ns:pictureURLLarge', namespaces)
                    if large_images:
                        for img in large_images:
                            if img is not None and img.text:
                                images.append(self._enhance_image_url(img.text))
                
                # If still no images, use gallery image as fallback
                if not images:
                    gallery = item.find('.//ns:galleryURL', namespaces)
                    if gallery is not None and gallery.text:
                        images.append(self._enhance_image_url(gallery.text))

                # Debug output for first item
                if self.debug and len(items) == 0:
                    print("\nFirst item raw data:")
                    print(f"Title: {title.text if title is not None else 'None'}")
                    print(f"Price: {price_elem.text if price_elem is not None else 'None'}")
                    print(f"Images found: {len(images)}")
                    print(f"Sample image URL: {images[0] if images else 'None'}")

                # Extract values with null checks
                title_text = title.text if title is not None else ''
                price = float(price_elem.text) if price_elem is not None else 0.0
                condition_text = condition.text if condition is not None else ''
                url_text = url.text if url is not None else ''

                # Get item specifics including size
                size = None
                item_specifics = item.findall('.//ns:itemSpecifics/ns:nameValueList', namespaces)
                for specific in item_specifics:
                    name = specific.find('ns:name', namespaces)
                    value = specific.find('ns:value', namespaces)
                    if name is not None and value is not None:
                        if name.text.lower() == 'size':
                            size = value.text
                            break

                # Only include if size matches user preferences
                if title_text and price > 0 and url_text:
                    item_data = {
                        'title': title_text,
                        'itemId': item.find('ns:itemId', namespaces).text if item.find('ns:itemId', namespaces) is not None else '',
                        'price': {'value': str(price)},
                        'condition': condition_text,
                        'itemWebUrl': url_text,
                        'images': images,
                        'size': size  # Add size to item data
                    }
                    items.append(item_data)

            except Exception as e:
                if self.debug:
                    print(f"Error parsing item: {e}")
                    print("Raw item data:", ET.tostring(item, encoding='unicode'))
                continue

        if self.debug:
            print(f"\nSuccessfully parsed {len(items)} items")
            if items:
                print("\nSample items:")
                for item in items[:3]:
                    print(f"\n- {item['title']}")
                    print(f"  Price: ${float(item['price']['value']):.2f}")
                    print(f"  Images: {len(item['images'])}")

        return {
            'itemSummaries': items
        }

    async def close(self) -> None:
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def get_category_tree(self) -> Dict:
        """Get the current eBay category tree"""
        endpoint = "https://api.ebay.com/ws/api.dll"
        
        headers = {
            'X-EBAY-API-SITEID': '0',  # US site
            'X-EBAY-API-COMPATIBILITY-LEVEL': '1155',
            'X-EBAY-API-CALL-NAME': 'GetCategories',
            'X-EBAY-API-APP-NAME': self.config.EBAY_CLIENT_ID,
            'Content-Type': 'text/xml'
        }
        
        # Build XML request
        xml_request = '''
        <?xml version="1.0" encoding="utf-8"?>
        <GetCategoriesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <CategorySiteID>0</CategorySiteID>
            <DetailLevel>ReturnAll</DetailLevel>
            <LevelLimit>4</LevelLimit>
        </GetCategoriesRequest>
        '''
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, data=xml_request) as response:
                    if response.status != 200:
                        print(f"Category API request failed: {response.status}")
                        return {}
                        
                    text = await response.text()
                    root = ET.fromstring(text)
                    
                    categories = {}
                    for category in root.findall('.//Category'):
                        cat_id = category.find('CategoryID').text
                        name = category.find('CategoryName').text
                        categories[cat_id] = name
                    
                    return categories
                    
        except Exception as e:
            print(f"Error getting categories: {e}")
            return {} 