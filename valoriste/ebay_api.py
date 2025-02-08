"""
eBay API integration for Valoriste
"""
import requests
import os
from datetime import datetime, timedelta
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from urllib.parse import parse_qs
import threading
from typing import Dict, List, Optional, Set, Any
from .config import Config
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback"""
    auth_code = None
    
    def do_GET(self):
        """Handle the OAuth callback"""
        try:
            # Parse the URL and extract the code
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                OAuthCallbackHandler.auth_code = query_params['code'][0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                success_message = """
                <html>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to the application.</p>
                </body>
                </html>
                """
                self.wfile.write(success_message.encode())
            else:
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_message = """
                <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>No authorization code received. Please try again.</p>
                </body>
                </html>
                """
                self.wfile.write(error_message.encode())
                
        except Exception as e:
            print(f"Error in callback handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Internal server error")

class EbayAPI:
    """Interface for eBay API operations"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config: Optional[Config] = None):
        if cls._instance is None:
            cls._instance = super(EbayAPI, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[Config] = None):
        # Skip initialization if already done
        if self._initialized:
            return
            
        self.config = config or Config()
        self.oauth_endpoint = "https://api.ebay.com/identity/v1/oauth2/token"
        self.api_endpoint = "https://api.ebay.com"
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.session = None
        self._cache = {}
        self._brand_categories = self._init_brand_categories()
        
        # Load tokens from config
        self.access_token = self.config.EBAY_AUTH_TOKEN
        self.refresh_token = self.config.EBAY_REFRESH_TOKEN
        self.token_expiry = None
        
        # Only verify tokens once at initialization
        if not self.access_token or not self.refresh_token:
            print("No valid tokens found. Starting OAuth flow...")
            self.start_oauth_flow()
        elif not self.validate_token():
            print("Token expired. Attempting to refresh...")
            if not self.refresh_access_token():
                print("Refresh failed. Starting OAuth flow...")
                self.start_oauth_flow()
        
        self._initialized = True
    
    def _init_brand_categories(self) -> Dict[str, Dict[str, Any]]:
        """Initialize brand configurations"""
        return {
            'lululemon': {
                'keywords': {'activewear', 'athletic', 'yoga', 'running', 'training',
                            'pants', 'shorts', 'shirt', 'jacket', 'hoodie', 'sweatshirt',
                            'workout', 'gym', 'fitness'},
                'categories': {
                    'men': ['15687', '57989', '185099'],  # Men's Athletic, Shirts, Pants
                    'women': ['15724', '53159', '63861']  # Women's Athletic, Tops, Bottoms
                }
            },
            'norse projects': {
                'keywords': {'streetwear', 'casual', 'contemporary', 'scandinavian',
                            'shirt', 'jacket', 'pants', 'sweater', 'overshirt', 'tee',
                            'clothing', 'apparel'},
                'categories': {
                    'men': ['57990', '57989', '57988'],
                    'women': ['15724', '53159', '63861']
                }
            },
            'apc': {
                'keywords': {'designer', 'contemporary', 'denim', 'french', 'minimal',
                            'jeans', 'shirt', 'jacket', 'sweater', 'coat', 'tee',
                            'clothing', 'apparel'},
                'categories': {
                    'men': ['57990', '57989', '57988'],
                    'women': ['15724', '53159', '63861']
                }
            },
            'theory': {
                'keywords': {'contemporary', 'business', 'casual', 'minimal', 'modern',
                            'suit', 'blazer', 'shirt', 'pants', 'sweater', 'jacket',
                            'clothing', 'apparel'},
                'categories': {
                    'men': ['57990', '57989', '57988'],
                    'women': ['15724', '53159', '63861']
                }
            },
            'stylenanda': {
                'keywords': {'korean', 'fashion', 'streetwear', 'dress', 'top', 'skirt',
                            'pants', 'jacket', 'coat', 'womens', 'women', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'ader error': {
                'keywords': {'korean', 'streetwear', 'oversized', 'unisex', 'shirt',
                            'sweater', 'hoodie', 'jacket', 'pants', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            '87mm': {
                'keywords': {'korean', 'minimal', 'basic', 'shirt', 'tee', 'sweater',
                            'pants', 'jacket', 'clothing', 'streetwear'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'charm': {
                'keywords': {'korean', 'streetwear', 'casual', 'shirt', 'sweater',
                            'hoodie', 'pants', 'jacket', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'musinsa standard': {
                'keywords': {'korean', 'basic', 'minimal', 'shirt', 'sweater', 'pants',
                            'jacket', 'clothing', 'casual'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'meshki': {
                'keywords': {'dress', 'top', 'skirt', 'pants', 'bodysuit', 'womens',
                            'women', 'clothing', 'party', 'going out'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'revolve': {
                'keywords': {'dress', 'top', 'skirt', 'pants', 'jacket', 'womens',
                            'women', 'clothing', 'designer', 'contemporary'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'house of cb': {
                'keywords': {'dress', 'top', 'skirt', 'bodysuit', 'corset', 'womens',
                            'women', 'clothing', 'party', 'going out'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'oh polly': {
                'keywords': {'dress', 'top', 'skirt', 'bodysuit', 'womens', 'women',
                            'clothing', 'party', 'going out'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'bardot': {
                'keywords': {'dress', 'top', 'skirt', 'pants', 'jacket', 'womens',
                            'women', 'clothing', 'party', 'casual'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'cult gaia': {
                'keywords': {'dress', 'top', 'skirt', 'pants', 'bag', 'shoes', 'womens',
                            'women', 'clothing', 'designer', 'resort'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'matin kim': {
                'keywords': {'minimal', 'contemporary', 'dress', 'top', 'skirt', 'pants',
                            'jacket', 'womens', 'women', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'low classic': {
                'keywords': {'minimal', 'contemporary', 'dress', 'top', 'skirt', 'pants',
                            'jacket', 'womens', 'women', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'recto': {
                'keywords': {'minimal', 'contemporary', 'dress', 'top', 'skirt', 'pants',
                            'jacket', 'womens', 'women', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            },
            'theopen product': {
                'keywords': {'minimal', 'contemporary', 'dress', 'top', 'skirt', 'pants',
                            'jacket', 'womens', 'women', 'clothing'},
                'categories': {
                    'men': [],
                    'women': ['15724', '53159', '63861']
                }
            }
        }
    
    async def _init_session(self):
        """Initialize aiohttp session for async requests"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={'Accept': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close_session(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    @lru_cache(maxsize=1000)
    def get_category_keywords(self, brand: str, gender: str = 'women') -> Set[str]:
        """Get category keywords for a brand"""
        base_keywords = self._brand_categories.get(brand.lower(), {}).get('keywords', set())
        
        # Add gender-specific keywords
        if gender == 'men':
            return {kw for kw in base_keywords if 'women' not in kw and 'dress' not in kw}
        else:
            return {kw for kw in base_keywords if 'men' not in kw}

    async def search_items_async(self, brand: str, size_filters: List[str], gender: str) -> List[Dict]:
        """Async search for items with optimized filtering"""
        await self._init_session()
        
        # Build brand query with variations
        brand_terms = []
        if brand.lower() == 'apc':
            brand_terms = ['APC', 'A.P.C', 'A.P.C.']
        elif brand.lower() == 'theory':
            brand_terms = ['Theory']
        else:
            brand_terms = [brand]
        
        # Build main query
        brand_query = ' OR '.join(f'"{term}"' for term in brand_terms)
        query = f'({brand_query})'
        if gender == 'men':
            query += ' mens -women -womens -female -girls'
        else:
            query += ' womens -mens -men -male -boys'
        
        # Add basic exclusions
        query += ' -fake -replica -wholesale -lot -bulk'
        
        # Get category IDs for the specified gender
        category_ids = self._brand_categories.get(brand.lower(), {}).get('categories', {}).get(gender, [])
        if not category_ids:
            print(f"Warning: No categories found for gender '{gender}' and brand '{brand}'")
            return []
        
        # Basic filters
        filters = [
            'buyingOptions:{FIXED_PRICE}',
            'deliveryCountry:US',
            'price:[5..500]',
            f'categoryIds:{{{"|".join(category_ids)}}}',
        ]
        
        # Add size filter
        size_filter_terms = set()
        for size in size_filters:
            size_filter_terms.add(size)
            if size.isdigit():
                size_filter_terms.add(f"W{size}")
            elif size.upper() in ['S', 'M', 'L']:
                if size.upper() == 'S':
                    size_filter_terms.update(['S', 'Small'])
                elif size.upper() == 'M':
                    size_filter_terms.update(['M', 'Medium'])
                elif size.upper() == 'L':
                    size_filter_terms.update(['L', 'Large'])
        
        if size_filter_terms:
            filters.append(f'aspects.Size:{{{"|".join(size_filter_terms)}}}')
        
        params = {
            'q': query,
            'limit': 50,  # Reduced from 200 to avoid rate limits
            'filter': ','.join(filters),
            'fieldgroups': ['BUYING_OPTIONS', 'PRICE_INFO']
        }
        
        print(f"\nSearching {brand} with query: {query}")
        print(f"Size filters: {sorted(size_filter_terms)}")
        
        try:
            # Add delay between requests
            await asyncio.sleep(1)
            
            async with self.session.get(
                f"{self.api_endpoint}/buy/browse/v1/item_summary/search",
                params=params,
                headers=self._get_headers()
            ) as response:
                if response.status == 429:  # Too Many Requests
                    print(f"Rate limit hit for {brand}, waiting...")
                    await asyncio.sleep(5)  # Wait 5 seconds before retry
                    return []
                
                data = await response.json()
                if 'itemSummaries' not in data:
                    print(f"No items found for {brand}")
                    return []
                
                return data['itemSummaries']
            
        except Exception as e:
            print(f"\nError searching for {brand}: {e}")
            return []

    async def search_multiple_brands_async(self, brands: List[str], size_filters: List[str], gender: str = 'women') -> List[Dict]:
        """Search for multiple brands in parallel"""
        tasks = []
        for brand in brands:
            tasks.append(self.search_items_async(brand, size_filters, gender))
        
        try:
            results = await asyncio.gather(*tasks)
            # Flatten the results
            all_items = [item for brand_items in results for item in brand_items]
            print(f"\nTotal items found across all brands: {len(all_items)}")
            return all_items
        except Exception as e:
            print(f"Error in parallel brand search: {e}")
            return []

    def search_items_bulk(self, brands: List[str], size_filters: List[str]) -> List[Dict]:
        """Bulk search with async processing"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.search_multiple_brands_async(brands, size_filters)
            )
        finally:
            loop.close()

    def validate_token(self) -> bool:
        """Validate the current OAuth token"""
        if not self.access_token:
            self.access_token = self.config.EBAY_AUTH_TOKEN
            if not self.access_token:
                return False
            
        # Try a simple API call to test the token
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            # Use the browse/search API endpoint for validation instead of user endpoint
            response = self.make_request(
                "/buy/browse/v1/item_summary/search",
                params={'q': 'test', 'limit': 1}
            )
            
            if response:
                return True
                
            print(f"Token validation failed: {response}")
            return False
            
        except Exception as e:
            print(f"Token validation failed: {e}")
            if self.refresh_token and not getattr(self, '_tried_refresh', False):
                print("Attempting to refresh token...")
                self._tried_refresh = True  # Prevent infinite loop
                if self.refresh_access_token():
                    # Try validation again with new token
                    return self.validate_token()
            return False
        finally:
            # Reset the refresh flag after attempt
            self._tried_refresh = False
    
    def start_oauth_flow(self):
        """Start the OAuth flow to get a new token"""
        try:
            # Get and display authorization URL
            auth_url = self.get_authorization_url()
            print("\nPlease authorize the application by visiting:")
            print(f"\n{auth_url}\n")
            
            # Open browser
            webbrowser.open(auth_url)
            
            # Get authorization code from user input
            print("After authorizing, paste the full URL or just the code here:")
            user_input = input().strip()
            
            # Extract code from input (whether it's a full URL or just the code)
            auth_code = user_input
            if '?' in user_input:  # If it's a full URL
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(user_input).query)
                auth_code = query_params.get('code', [''])[0]
                # Remove expires_in part if present
                if '&expires_in=' in auth_code:
                    auth_code = auth_code.split('&expires_in=')[0]
            
            if not auth_code:
                print("\nNo valid authorization code provided!")
                return False
            
            # Exchange the code for tokens
            tokens = self.get_tokens_from_code(auth_code)
            
            if tokens and 'access_token' in tokens:
                # Update the .env file with the new token
                self.update_env_file(tokens['access_token'], tokens['refresh_token'])
                self.config.EBAY_AUTH_TOKEN = tokens['access_token']
                print("\nSuccessfully obtained new OAuth token!")
                return True
            else:
                print("\nFailed to obtain OAuth token!")
                return False
                
        except Exception as e:
            print(f"\nError in OAuth flow: {e}")
            return False
    
    def update_env_file(self, access_token: str, refresh_token: str = None):
        """Update the .env file with the new tokens"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        
        if os.path.exists(env_path):
            # Read all lines
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Process lines
            new_lines = []
            access_token_updated = False
            refresh_token_updated = False
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    new_lines.append(line)
                elif line.startswith('EBAY_AUTH_TOKEN='):
                    new_lines.append(f'EBAY_AUTH_TOKEN={access_token}')
                    access_token_updated = True
                elif line.startswith('EBAY_REFRESH_TOKEN='):
                    if refresh_token:
                        new_lines.append(f'EBAY_REFRESH_TOKEN={refresh_token}')
                        refresh_token_updated = True
                else:
                    new_lines.append(line)
            
            # Add tokens if they weren't updated
            if not access_token_updated:
                new_lines.append(f'EBAY_AUTH_TOKEN={access_token}')
            if refresh_token and not refresh_token_updated:
                new_lines.append(f'EBAY_REFRESH_TOKEN={refresh_token}')
            
            # Write back to file
            with open(env_path, 'w') as f:
                f.write('\n'.join(new_lines) + '\n')
        else:
            # Create new file if it doesn't exist
            with open(env_path, 'w') as f:
                f.write(f'EBAY_AUTH_TOKEN={access_token}\n')
                if refresh_token:
                    f.write(f'EBAY_REFRESH_TOKEN={refresh_token}\n')

    def start_local_server(self):
        """Start local server to catch OAuth callback"""
        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server

    def get_access_token(self):
        """Get a new access token using the refresh token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._get_basic_auth()}'
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'scope': ' '.join([
                'https://api.ebay.com/oauth/api_scope',
                'https://api.ebay.com/oauth/api_scope/sell.marketing.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.marketing',
                'https://api.ebay.com/oauth/api_scope/sell.inventory.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.inventory',
                'https://api.ebay.com/oauth/api_scope/sell.account.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.account'
            ])
        }

        response = requests.post(self.oauth_endpoint, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 300)
            return self.access_token
        else:
            raise Exception(f"Failed to refresh access token: {response.text}")

    def _get_basic_auth(self):
        """Create Basic Auth string from client credentials"""
        import base64
        credentials = f"{self.config.EBAY_CLIENT_ID}:{self.config.EBAY_CLIENT_SECRET}"
        return base64.b64encode(credentials.encode()).decode()

    def make_request(self, endpoint: str, method="GET", params=None, data=None):
        """Make an authenticated request to the eBay API"""
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        url = f"{self.api_endpoint}{endpoint}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )

        if response.status_code in (200, 201):
            return response.json()
        else:
            raise Exception(f"API request failed: {response.text}")

    def test_credentials(self):
        """Test if credentials are valid"""
        try:
            self.get_access_token()
            print("Credentials are valid!")
            return True
        except Exception as e:
            print(f"Invalid credentials: {str(e)}")
            return False

    def get_authorization_url(self):
        """Get the eBay authorization URL"""
        scopes = [
                'https://api.ebay.com/oauth/api_scope',
                'https://api.ebay.com/oauth/api_scope/sell.marketing.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.marketing',
                'https://api.ebay.com/oauth/api_scope/sell.inventory.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.inventory',
                'https://api.ebay.com/oauth/api_scope/sell.account.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.account',
                'https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.fulfillment',
                'https://api.ebay.com/oauth/api_scope/sell.analytics.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.finances',
                'https://api.ebay.com/oauth/api_scope/sell.payment.dispute',
                'https://api.ebay.com/oauth/api_scope/commerce.identity.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.reputation',
                'https://api.ebay.com/oauth/api_scope/sell.reputation.readonly',
                'https://api.ebay.com/oauth/api_scope/commerce.notification.subscription',
                'https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly',
                'https://api.ebay.com/oauth/api_scope/sell.stores',
                'https://api.ebay.com/oauth/api_scope/sell.stores.readonly',
                'https://api.ebay.com/oauth/scope/sell.edelivery'
        ]
        
        params = {
            'client_id': self.config.EBAY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.config.EBAY_REDIRECT_URI,
            'scope': ' '.join(scopes)
        }
        
        auth_url = "https://auth.ebay.com/oauth2/authorize"
        return f"{auth_url}?{urllib.parse.urlencode(params)}"

    def get_tokens_from_code(self, auth_code):
        """Exchange authorization code for tokens"""
        # URL decode the authorization code
        decoded_code = urllib.parse.unquote(auth_code)
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._get_basic_auth()}'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': decoded_code,
            'redirect_uri': self.config.EBAY_REDIRECT_URI
        }

        try:
            response = requests.post(
                self.oauth_endpoint,
                headers=headers,
                data=data
            )
            
            if response.status_code != 200:
                print(f"\nError getting tokens: {response.text}")
                return None
            
            token_data = response.json()
            
            # Store both tokens
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 7200)  # Default to 2 hours
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 minutes buffer
            
            # Update the .env file
            self.update_env_file(self.access_token, self.refresh_token)
            
            return token_data
            
        except Exception as e:
            print(f"\nException getting tokens: {e}")
            return None

    def search_items(self, keywords: str, category_id: Optional[str] = None, 
                    min_price: Optional[float] = None, 
                    max_price: Optional[float] = None) -> List[Dict]:
        """Search for items on eBay"""
        endpoint = "/buy/browse/v1/item_summary/search"
        
        # Build comprehensive filter string upfront
        filters = [
            'conditions:{NEW|USED}',
            'deliveryCountry:US',
            'itemLocationCountry:US',
            'buyingOptions:{FIXED_PRICE}',
            f'price:[{min_price or 5}..{max_price or 1000}]'
        ]
        
        if category_id:
            filters.append(f'categoryIds:{{{category_id}}}')
        
        params = {
            'q': keywords,
            'limit': 200,  # Maximum items per request
            'filter': ','.join(filters),
            'sort': 'price',
            'fieldgroups': 'MINIMAL',  # Request only needed fields
        }
            
        try:
            response = self.make_request(endpoint, params=params)
            return response.get('itemSummaries', [])
        except Exception as e:
            print(f"\nError searching items: {e}")
            return []

    @lru_cache(maxsize=1000)
    def search_sold_items(self, keywords: str, days_back: int = 30) -> List[Dict]:
        """Search for sold items on eBay with caching"""
        endpoint = "/buy/browse/v1/item_summary/search"
        
        filters = [
            'soldItems',
            'conditions:{NEW|USED}',
            'deliveryCountry:US',
            'itemLocationCountry:US',
            'buyingOptions:{FIXED_PRICE}',
            'price:[5..1000]'
        ]
        
        params = {
            'q': keywords,
            'limit': 200,
            'filter': ','.join(filters),
            'sort': '-price',
            'fieldgroups': 'MINIMAL'
        }
        
        try:
            response = self.make_request(endpoint, params=params)
            return response.get('itemSummaries', [])
        except Exception:
            return []

    def analyze_lululemon_item(self, item_name, condition="new", days_back=90):
        """Detailed analysis of a specific Lululemon item"""
        search_term = f"lululemon {item_name}" if condition == "all" else f"lululemon {item_name} {condition}"
        
        all_items = []
        offset = 0
        limit = 200
        
        while True:
            params = {
                'q': search_term,
                'limit': limit,
                'offset': offset,
                'filter': (f'soldItems,priceCurrency:USD,price:[1..500],'
                          f'endTimeFrom:{(datetime.now() - timedelta(days=30)).isoformat()}Z')
            }

            endpoint = "/buy/browse/v1/item_summary/search"
            results = self.make_request(f"{endpoint}?{urllib.parse.urlencode(params)}")
            
            items = results.get('itemSummaries', [])
            if not items:
                break
                
            all_items.extend(items)
            total_results = results.get('total', 0)
            
            offset += limit
            if offset >= total_results or offset >= 1000:
                break
        
        if not all_items:
            return None
            
        # Extract prices silently
        sales_data = []
        for item in all_items:
            try:
                price = float(item['price']['value'])
                sales_data.append({
                    'price': price,
                    'condition': item.get('condition', 'unknown')
                })
            except (KeyError, ValueError):
                continue
        
        if not sales_data:
            return None
            
        prices = [item['price'] for item in sales_data]
        return {
            'median_price': sorted(prices)[len(prices)//2],
            'total_sales': len(sales_data),  # Use actual count of items we got
            'price_std': self._calculate_std(prices)
        }

    def _calculate_std(self, values):
        """Calculate standard deviation"""
        mean = sum(values) / len(values)
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        return (squared_diff_sum / len(values)) ** 0.5

    def get_item_details(self, item_id: str) -> Dict:
        """
        Get detailed information about a specific item
        
        Args:
            item_id: eBay item ID
            
        Returns:
            Dictionary containing item details
        """
        # Implementation for getting specific item details
        # This would use the Trading API and require authentication
        raise NotImplementedError("Item details retrieval not yet implemented")

    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            print("No refresh token available")
            return False

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._get_basic_auth()}'
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }

        try:
            print("\nRefreshing access token...")
            response = requests.post(
                'https://api.ebay.com/identity/v1/oauth2/token',
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                print("Successfully refreshed access token")
                
                # Update the token in memory and file
                self.config.EBAY_AUTH_TOKEN = self.access_token
                self.update_env_file(self.access_token)
                
                return True
            else:
                print(f"Failed to refresh token: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return False

    def verify_configuration(self) -> bool:
        """
        Verify all API configurations are working
        Returns: bool indicating if all configurations are valid
        """
        print("\nVerifying eBay API Configuration...")
        
        # 1. Check if all required credentials exist
        required_credentials = [
            ('Client ID', self.config.EBAY_CLIENT_ID),
            ('Client Secret', self.config.EBAY_CLIENT_SECRET),
            ('Redirect URI', self.config.EBAY_REDIRECT_URI)
        ]
        
        for name, value in required_credentials:
            if not value:
                print(f"❌ Missing {name}")
                return False
            print(f"✓ Found {name}")
        
        # 2. Test OAuth token
        print("\nTesting OAuth token...")
        if not self.validate_token():
            print("\nWould you like to start a new OAuth flow? (y/n)")
            if input().lower().strip() == 'y':
                if self.start_oauth_flow():
                    print("✓ New OAuth token obtained successfully")
                    return True
            return False
        
        print("✓ OAuth token is valid")
        return True

def main():
    """Example usage"""
    try:
        ebay = EbayAPI()
        print("Analyzing Lululemon items for resale opportunities...")
        
        items_to_analyze = [
            "align"
        ]
        
        results = {}
        opportunities = []
        
        for item in items_to_analyze:
            all_results = ebay.analyze_lululemon_item(item, condition="all")
            if all_results:
                new_results = ebay.analyze_lululemon_item(item, condition="new")
                used_results = ebay.analyze_lululemon_item(item, condition="used")
                
                if new_results and used_results:
                    new_price = new_results['median_price']
                    used_price = used_results['median_price']
                    price_diff = new_price - used_price
                    roi = (price_diff / used_price) * 100
                    
                    if roi > 3 and price_diff > 5:
                        opportunities.append({
                            'item': item,
                            'new_price': new_price,
                            'used_price': used_price,
                            'profit': price_diff,
                            'roi': roi,
                            'monthly_sales': new_results['total_sales'],
                            'std_dev': new_results['price_std']
                        })
        
        if not opportunities:
            print("\nNo profitable opportunities found.")
            return
            
        opportunities.sort(key=lambda x: x['roi'], reverse=True)
        
        print("\n" + "="*50)
        print("PROFITABLE RESALE OPPORTUNITIES")
        print("="*50)
        
        for opp in opportunities:
            print(f"\n{opp['item'].title()}:")
            print(f"Buy used @ ${opp['used_price']:.2f} → Sell new @ ${opp['new_price']:.2f}")
            print(f"Profit: ${opp['profit']:.2f} (ROI: {opp['roi']:.1f}%)")
            print(f"Monthly sales: {opp['monthly_sales']} | Risk: {'HIGH' if opp['std_dev'] > 20 else 'MEDIUM' if opp['std_dev'] > 10 else 'LOW'}")
            print(f"Potential monthly profit: ${(opp['profit'] * opp['monthly_sales'] / 3):.2f}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
