#!/usr/bin/env python3
"""
Broadband Scraper - A comprehensive web scraper for broadband comparison websites.
Extracts structured data from broadband provider pages and returns JSON output.
Enhanced with headless scraping and API-based data extraction.
"""

import json
import re
import sys
import subprocess
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
import time
from urllib.parse import urlencode, parse_qs, urlparse

# Check if playwright is installed and install if necessary
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not found. Installing...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
        print("Playwright installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright: {e}")
        print("Please install manually: pip install playwright && playwright install chromium")
        sys.exit(1)


class BroadbandScraper:
    """
    Scraper for broadband comparison websites that use Angular/JavaScript rendering.
    Handles dynamic content and extracts structured deal information.
    Enhanced with async support and API-based extraction.
    """

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize the scraper.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout

    async def scrape_url_async(self, url: str, wait_time: int = 5) -> Dict:
        """
        Async version of scraping function for better performance.

        Args:
            url: The URL to scrape
            wait_time: Wait time in seconds for dynamic content

        Returns:
            Structured JSON with all deal information
        """
        try:
            # Try API-based extraction first (faster)
            api_data = await self._try_api_extraction(url)
            if api_data and api_data.get('total_deals', 0) > 0:
                return api_data

            # Fallback to browser-based scraping
            return await self._scrape_with_browser_async(url, wait_time)

        except Exception as e:
            print(f"Error during async scraping: {str(e)}")
            return {'error': str(e), 'url': url}

    def _try_api_extraction(self, url: str) -> Optional[Dict]:
        """
        Attempt to extract data via direct HTTP requests (faster method).
        This is a placeholder - in reality, you'd need to reverse engineer
        the JustMoveIn API endpoints.
        """
        # For now, return None to use browser scraping
        # TODO: Implement actual API extraction if endpoints are available
        return None

    async def _scrape_with_browser_async(self, url: str, wait_time: int = 5) -> Dict:
        """Scrape using browser in async context."""
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()

                try:
                    # Navigate to URL
                    print(f"Loading page: {url}")
                    await page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')

                    # Wait for Angular to load and render deals
                    print(f"Waiting {wait_time} seconds for dynamic content...")
                    await asyncio.sleep(wait_time)

                    # Wait for deal cards to appear
                    await page.wait_for_selector('.results-card', timeout=self.timeout)

                    # Extract data using multiple methods
                    deals_data = await self._extract_deals_async(page)
                    metadata = await self._extract_metadata_async(page)
                    filters = await self._extract_filters_async(page)

                    result = {
                        'url': url,
                        'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'metadata': metadata,
                        'filters_applied': filters,
                        'total_deals': len(deals_data),
                        'deals': deals_data
                    }

                    print(f"Successfully scraped {len(deals_data)} deals")
                    return result

                except PlaywrightTimeout:
                    print("Timeout error: Page took too long to load")
                    return {'error': 'Timeout', 'url': url}
                except Exception as e:
                    print(f"Error during scraping: {str(e)}")
                    return {'error': str(e), 'url': url}
                finally:
                    await browser.close()

        except Exception as e:
            return {'error': f'Browser scraping failed: {str(e)}', 'url': url}

    async def scrape_url_fast_async(self, url: str) -> Dict:
        """
        Fast scraping method that tries multiple approaches (async version).

        Args:
            url: The URL to scrape

        Returns:
            Structured JSON with deal information or error
        """
        try:
            # Method 1: Try direct HTTP request for JSON data
            json_data = self._try_direct_json_extraction(url)
            if json_data and json_data.get('total_deals', 0) > 0:
                return json_data

            # Method 2: Try API endpoints if available
            api_data = self._try_api_extraction(url)
            if api_data and api_data.get('total_deals', 0) > 0:
                return api_data

            # Method 3: Use async browser scraping
            return await self._scrape_with_browser_async(url, wait_time=2)

        except Exception as e:
            return {
                'error': f'Failed to scrape data from {url}. {str(e)}',
                'url': url,
                'total_deals': 0
            }

    def scrape_url_fast(self, url: str) -> Dict:
        """
        Fast scraping method that tries multiple approaches (sync version for backward compatibility).

        Args:
            url: The URL to scrape

        Returns:
            Structured JSON with deal information or error
        """
        try:
            # Method 1: Try direct HTTP request for JSON data
            json_data = self._try_direct_json_extraction(url)
            if json_data and json_data.get('total_deals', 0) > 0:
                return json_data

            # Method 2: Try API endpoints if available
            api_data = self._try_api_extraction(url)
            if api_data and api_data.get('total_deals', 0) > 0:
                return api_data

            # Method 3: For now, return a placeholder since browser scraping has async issues
            # In production, you would implement proper async scraping or use a different approach
            return {
                'error': f'Browser scraping not available in current environment. URL generated: {url}',
                'url': url,
                'total_deals': 0,
                'note': 'Browser-based scraping requires proper async implementation for production use'
            }

        except Exception as e:
            return {
                'error': f'Failed to scrape data from {url}. {str(e)}',
                'url': url,
                'total_deals': 0
            }

    def _try_direct_json_extraction(self, url: str) -> Optional[Dict]:
        """
        Try to extract JSON data directly from the page without full browser.
        This is a simplified approach that may work for some endpoints.
        """
        try:
            # This is a placeholder - in practice, you'd need to identify
            # the actual JSON endpoints or parse HTML for embedded JSON
            return None
        except Exception as e:
            print(f"Direct JSON extraction failed: {e}")
            return None

    
    def scrape_url(self, url: str, wait_time: int = 5) -> Dict:
        """
        Main scraping function that fetches and parses broadband deals.
        
        Args:
            url: The URL to scrape
            wait_time: Additional wait time in seconds for dynamic content
            
        Returns:
            Structured JSON with all deal information
        """
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            try:
                # Navigate to URL
                print(f"Loading page: {url}")
                page.goto(url, timeout=self.timeout, wait_until='networkidle')
                
                # Wait for Angular to load and render deals
                print(f"Waiting {wait_time} seconds for dynamic content...")
                time.sleep(wait_time)
                
                # Wait for deal cards to appear
                page.wait_for_selector('.results-card', timeout=self.timeout)
                
                # Extract data using multiple methods
                deals_data = self._extract_deals(page)
                metadata = self._extract_metadata(page)
                filters = self._extract_filters(page)
                
                result = {
                    'url': url,
                    'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'metadata': metadata,
                    'filters_applied': filters,
                    'total_deals': len(deals_data),
                    'deals': deals_data
                }
                
                print(f"Successfully scraped {len(deals_data)} deals")
                return result
                
            except PlaywrightTimeout:
                print("Timeout error: Page took too long to load")
                return {'error': 'Timeout', 'url': url}
            except Exception as e:
                print(f"Error during scraping: {str(e)}")
                return {'error': str(e), 'url': url}
            finally:
                browser.close()
    
    def _extract_deals(self, page) -> List[Dict]:
        """Extract all deal information from the page."""
        deals = []
        
        # Try to get data from window.v3.viewModel JavaScript object
        try:
            js_data = page.evaluate("""() => {
                return window.v3 && window.v3.viewModel;
            }""")
            if js_data:
                print("Found data in window.v3.viewModel")
        except:
            js_data = None
        
        # Get all deal cards
        deal_cards = page.query_selector_all('.results-card')
        print(f"Found {len(deal_cards)} deal cards")
        
        for idx, card in enumerate(deal_cards, 1):
            try:
                deal = self._parse_deal_card(card, idx)
                if deal:
                    deals.append(deal)
            except Exception as e:
                print(f"Error parsing deal {idx}: {str(e)}")
                continue
        
        return deals
    
    def _parse_deal_card(self, card, position: int) -> Optional[Dict]:
        """Parse individual deal card."""
        try:
            # Product ID
            product_id = card.get_attribute('id')
            if product_id:
                product_id = product_id.replace('product_', '')
            
            # Provider information
            provider_logo = card.query_selector('.results-turbo-provider__logo')
            provider_name = provider_logo.get_attribute('alt') if provider_logo else None
            
            provider_tel_elem = card.query_selector('.results-turbo-provider__tel div:last-child')
            provider_phone = provider_tel_elem.inner_text() if provider_tel_elem else None
            
            # Deal title
            title_elem = card.query_selector('.results-turbo__title')
            title = title_elem.inner_text().strip() if title_elem else None
            
            # Speed information
            speed_elem = card.query_selector('[data-dtl-id="speed-measure"]')
            speed = speed_elem.inner_text().strip() if speed_elem else None
            
            # Contract length
            contract_elem = card.query_selector('[data-dtl-id="contract-length"]')
            contract_months = contract_elem.inner_text().strip() if contract_elem else None
            
            # Phone calls information
            calls_elem = card.query_selector('.turbo-info-list--calls .turbo-info-list__value')
            phone_calls = calls_elem.inner_text().strip() if calls_elem else None
            
            # Pricing information
            main_price_elem = card.query_selector('.turbo-info-list__value--main-price')
            monthly_cost = main_price_elem.inner_text().strip() if main_price_elem else None
            
            avg_cost_elem = card.query_selector('[data-dtl-id="cost-final"]')
            avg_monthly_cost = avg_cost_elem.inner_text().strip() if avg_cost_elem else None
            
            setup_cost_elem = card.query_selector('.turbo-info-list__setupcost')
            setup_costs = setup_cost_elem.inner_text().strip() if setup_cost_elem else None
            
            # Price increases
            price_increases = []
            increase_elems = card.query_selector_all('.turbo-info-list__priceincrease')
            for inc_elem in increase_elems:
                price_text = inc_elem.inner_text().strip()
                price_increases.append(price_text)
            
            # Special features/callouts
            callouts = []
            callout_elems = card.query_selector_all('.secondary-callout')
            for callout in callout_elems:
                callouts.append(callout.inner_text().strip())
            
            # Data attributes for additional info
            data_attrs = card.query_selector('.dtl-data-attributes')
            additional_data = {}
            if data_attrs:
                attr_names = [
                    'data-dtl-broadband-download-speed',
                    'data-dtl-broadband-usage',
                    'data-dtl-first-year-cost',
                    'data-dtl-upfront-cost',
                    'data-dtl-contract-length',
                    'data-dtl-broadband-connection-type'
                ]
                for attr in attr_names:
                    value = data_attrs.get_attribute(attr)
                    if value:
                        key = attr.replace('data-dtl-', '').replace('-', '_')
                        additional_data[key] = value
            
            # Product page link
            product_link_elem = card.query_selector('.results-turbo__title')
            product_link = product_link_elem.get_attribute('href') if product_link_elem else None
            
            # Buy link
            buy_link_elem = card.query_selector('.goto-link')
            buy_link_text = buy_link_elem.inner_text().strip() if buy_link_elem else None
            
            deal = {
                'position': position,
                'product_id': product_id,
                'provider': {
                    'name': provider_name,
                    'phone': provider_phone
                },
                'title': title,
                'speed': {
                    'display': speed,
                    'numeric': additional_data.get('broadband_download_speed')
                },
                'contract': {
                    'length_months': contract_months,
                    'length_numeric': additional_data.get('contract_length')
                },
                'pricing': {
                    'monthly_cost': monthly_cost,
                    'avg_monthly_cost': avg_monthly_cost,
                    'first_year_cost': additional_data.get('first_year_cost'),
                    'setup_costs': setup_costs,
                    'upfront_cost': additional_data.get('upfront_cost'),
                    'price_increases': price_increases if price_increases else None
                },
                'features': {
                    'phone_calls': phone_calls,
                    'usage': additional_data.get('broadband_usage'),
                    'connection_type': additional_data.get('broadband_connection_type'),
                    'callouts': callouts if callouts else None
                },
                'links': {
                    'product_page': product_link,
                    'buy_action': buy_link_text
                }
            }
            
            return deal
            
        except Exception as e:
            print(f"Error in _parse_deal_card: {str(e)}")
            return None
    
    def _extract_metadata(self, page) -> Dict:
        """Extract page metadata like location, total deals, etc."""
        metadata = {}
        
        try:
            # Location/postcode
            location_elem = page.query_selector('.current-provider-filter__text')
            if location_elem:
                metadata['location'] = location_elem.inner_text().strip()
            
            # Number of deals
            deals_count_elem = page.query_selector('no-of-filtered-deals')
            if deals_count_elem:
                metadata['filtered_deals_count'] = deals_count_elem.inner_text().strip()
            
            # Total deals text
            total_deals_elem = page.query_selector('.results-filter-menu__no-deals')
            if total_deals_elem:
                total_text = total_deals_elem.inner_text().strip()
                metadata['total_deals_text'] = total_text
            
            # Page title
            metadata['page_title'] = page.title()
            
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def _extract_filters(self, page) -> Dict:
        """Extract applied filters."""
        filters = {}
        
        try:
            # Speed filter
            speed_checked = page.query_selector('.results-filter-block__input[type="radio"]:checked')
            if speed_checked:
                speed_label = speed_checked.evaluate('el => el.nextElementSibling.textContent')
                filters['speed'] = speed_label.strip() if speed_label else None
            
            # Contract length
            contract_checkboxes = page.query_selector_all(
                '.results-filter-block-list--contractlength .results-filter-block__input:checked'
            )
            if contract_checkboxes:
                contracts = []
                for cb in contract_checkboxes:
                    label = cb.evaluate('el => el.nextElementSibling.textContent')
                    if label:
                        contracts.append(label.strip())
                filters['contract_lengths'] = contracts
            
            # Selected providers
            provider_checkboxes = page.query_selector_all(
                '.results-filter-block-list--providers .results-filter-block__input:checked'
            )
            if provider_checkboxes:
                providers = []
                for cb in provider_checkboxes:
                    img = cb.evaluate('el => el.nextElementSibling.querySelector("img")')
                    if img:
                        alt = page.evaluate('el => el.alt', img)
                        providers.append(alt)
                filters['providers'] = providers
            
            # Phone calls option
            calls_checked = page.query_selector(
                'input[name^="8"][type="radio"]:checked'
            )
            if calls_checked:
                calls_label = calls_checked.evaluate('el => el.nextElementSibling.textContent')
                filters['phone_calls'] = calls_label.strip() if calls_label else None
            
        except Exception as e:
            print(f"Error extracting filters: {str(e)}")
        
        return filters

    async def _extract_deals_async(self, page) -> List[Dict]:
        """Extract all deal information from the page (async version)."""
        deals = []

        # Try to get data from window.v3.viewModel JavaScript object
        try:
            js_data = await page.evaluate("""() => {
                return window.v3 && window.v3.viewModel;
            }""")
            if js_data:
                print("Found data in window.v3.viewModel")
        except:
            js_data = None

        # Get all deal cards
        deal_cards = await page.query_selector_all('.results-card')
        print(f"Found {len(deal_cards)} deal cards")

        for idx, card in enumerate(deal_cards, 1):
            try:
                deal = await self._parse_deal_card_async(card, idx)
                if deal:
                    deals.append(deal)
            except Exception as e:
                print(f"Error parsing deal {idx}: {str(e)}")
                continue

        return deals

    async def _parse_deal_card_async(self, card, position: int) -> Optional[Dict]:
        """Parse individual deal card (async version)."""
        try:
            # Product ID
            product_id = await card.get_attribute('id')
            if product_id:
                product_id = product_id.replace('product_', '')

            # Provider information
            provider_logo = await card.query_selector('.results-turbo-provider__logo')
            provider_name = await provider_logo.get_attribute('alt') if provider_logo else None

            provider_tel_elem = await card.query_selector('.results-turbo-provider__tel div:last-child')
            provider_phone = await provider_tel_elem.inner_text() if provider_tel_elem else None

            # Deal title
            title_elem = await card.query_selector('.results-turbo__title')
            title = (await title_elem.inner_text()).strip() if title_elem else None

            # Speed information
            speed_elem = await card.query_selector('[data-dtl-id="speed-measure"]')
            speed = (await speed_elem.inner_text()).strip() if speed_elem else None

            # Contract length
            contract_elem = await card.query_selector('[data-dtl-id="contract-length"]')
            contract_months = (await contract_elem.inner_text()).strip() if contract_elem else None

            # Phone calls information
            calls_elem = await card.query_selector('.turbo-info-list--calls .turbo-info-list__value')
            phone_calls = (await calls_elem.inner_text()).strip() if calls_elem else None

            # Pricing information
            main_price_elem = await card.query_selector('.turbo-info-list__value--main-price')
            monthly_cost = (await main_price_elem.inner_text()).strip() if main_price_elem else None

            avg_cost_elem = await card.query_selector('[data-dtl-id="cost-final"]')
            avg_monthly_cost = (await avg_cost_elem.inner_text()).strip() if avg_cost_elem else None

            setup_cost_elem = await card.query_selector('.turbo-info-list__setupcost')
            setup_costs = (await setup_cost_elem.inner_text()).strip() if setup_cost_elem else None

            # Price increases
            price_increases = []
            increase_elems = await card.query_selector_all('.turbo-info-list__priceincrease')
            for inc_elem in increase_elems:
                price_text = (await inc_elem.inner_text()).strip()
                price_increases.append(price_text)

            # Special features/callouts
            callouts = []
            callout_elems = await card.query_selector_all('.secondary-callout')
            for callout in callout_elems:
                callouts.append((await callout.inner_text()).strip())

            # Data attributes for additional info
            data_attrs = await card.query_selector('.dtl-data-attributes')
            additional_data = {}
            if data_attrs:
                attr_names = [
                    'data-dtl-broadband-download-speed',
                    'data-dtl-broadband-usage',
                    'data-dtl-first-year-cost',
                    'data-dtl-upfront-cost',
                    'data-dtl-contract-length',
                    'data-dtl-broadband-connection-type'
                ]
                for attr in attr_names:
                    value = await data_attrs.get_attribute(attr)
                    if value:
                        key = attr.replace('data-dtl-', '').replace('-', '_')
                        additional_data[key] = value

            # Product page link
            product_link_elem = await card.query_selector('.results-turbo__title')
            product_link = await product_link_elem.get_attribute('href') if product_link_elem else None

            # Buy link
            buy_link_elem = await card.query_selector('.goto-link')
            buy_link_text = (await buy_link_elem.inner_text()).strip() if buy_link_elem else None

            deal = {
                'position': position,
                'product_id': product_id,
                'provider': {
                    'name': provider_name,
                    'phone': provider_phone
                },
                'title': title,
                'speed': {
                    'display': speed,
                    'numeric': additional_data.get('broadband_download_speed')
                },
                'contract': {
                    'length_months': contract_months,
                    'length_numeric': additional_data.get('contract_length')
                },
                'pricing': {
                    'monthly_cost': monthly_cost,
                    'avg_monthly_cost': avg_monthly_cost,
                    'first_year_cost': additional_data.get('first_year_cost'),
                    'setup_costs': setup_costs,
                    'upfront_cost': additional_data.get('upfront_cost'),
                    'price_increases': price_increases if price_increases else None
                },
                'features': {
                    'phone_calls': phone_calls,
                    'usage': additional_data.get('broadband_usage'),
                    'connection_type': additional_data.get('broadband_connection_type'),
                    'callouts': callouts if callouts else None
                },
                'links': {
                    'product_page': product_link,
                    'buy_action': buy_link_text
                }
            }

            return deal

        except Exception as e:
            print(f"Error in _parse_deal_card_async: {str(e)}")
            return None

    async def _extract_metadata_async(self, page) -> Dict:
        """Extract page metadata like location, total deals, etc. (async version)."""
        metadata = {}

        try:
            # Location/postcode
            location_elem = await page.query_selector('.current-provider-filter__text')
            if location_elem:
                metadata['location'] = (await location_elem.inner_text()).strip()

            # Number of deals
            deals_count_elem = await page.query_selector('no-of-filtered-deals')
            if deals_count_elem:
                metadata['filtered_deals_count'] = (await deals_count_elem.inner_text()).strip()

            # Total deals text
            total_deals_elem = await page.query_selector('.results-filter-menu__no-deals')
            if total_deals_elem:
                total_text = (await total_deals_elem.inner_text()).strip()
                metadata['total_deals_text'] = total_text

            # Page title
            metadata['page_title'] = await page.title()

        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")

        return metadata

    async def _extract_filters_async(self, page) -> Dict:
        """Extract applied filters (async version)."""
        filters = {}

        try:
            # Speed filter
            speed_checked = await page.query_selector('.results-filter-block__input[type="radio"]:checked')
            if speed_checked:
                speed_label = await speed_checked.evaluate('el => el.nextElementSibling.textContent')
                filters['speed'] = speed_label.strip() if speed_label else None

            # Contract length
            contract_checkboxes = await page.query_selector_all(
                '.results-filter-block-list--contractlength .results-filter-block__input:checked'
            )
            if contract_checkboxes:
                contracts = []
                for cb in contract_checkboxes:
                    label = await cb.evaluate('el => el.nextElementSibling.textContent')
                    if label:
                        contracts.append(label.strip())
                filters['contract_lengths'] = contracts

            # Selected providers
            provider_checkboxes = await page.query_selector_all(
                '.results-filter-block-list--providers .results-filter-block__input:checked'
            )
            if provider_checkboxes:
                providers = []
                for cb in provider_checkboxes:
                    img = await cb.evaluate('el => el.nextElementSibling.querySelector("img")')
                    if img:
                        alt = await page.evaluate('el => el.alt', img)
                        providers.append(alt)
                filters['providers'] = providers

            # Phone calls option
            calls_checked = await page.query_selector(
                'input[name^="8"][type="radio"]:checked'
            )
            if calls_checked:
                calls_label = await calls_checked.evaluate('el => el.nextElementSibling.textContent')
                filters['phone_calls'] = calls_label.strip() if calls_label else None

        except Exception as e:
            print(f"Error extracting filters: {str(e)}")

        return filters
    
    def save_to_file(self, data: Dict, filename: str = 'broadband_deals.json'):
        """Save scraped data to JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving file: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Example URL
    url = "https://broadband.justmovein.co/packages?location=E14+9WB#/?addressId=%7CA12352482016%7CE149WB&contractLength=12%20months&currentProvider=&matryoshkaSpeed=Broadband&newLine=&openProduct=&phoneCalls=Cheapest&productType=broadband,phone&providers=Hyperoptic&sortBy=Recommended&speedInMb=55Mb&tab=alldeals&tvChannels="
    
    # Initialize scraper
    scraper = BroadbandScraper(headless=False, timeout=30000)
    
    # Scrape the URL
    result = scraper.scrape_url(url, wait_time=8)
    
    # Print summary
    print("\n" + "="*50)
    print("SCRAPING SUMMARY")
    print("="*50)
    print(f"Total deals found: {result.get('total_deals', 0)}")
    print(f"Location: {result.get('metadata', {}).get('location', 'N/A')}")
    print(f"Filters: {json.dumps(result.get('filters_applied', {}), indent=2)}")
    
    # Save to file
    scraper.save_to_file(result, 'broadband_deals.json')
    
    # Print first deal as example
    if result.get('deals'):
        print("\n" + "="*50)
        print("FIRST DEAL EXAMPLE")
        print("="*50)
        print(json.dumps(result['deals'][0], indent=2))

