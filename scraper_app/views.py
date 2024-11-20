# scraper_app/views.py
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from bs4 import BeautifulSoup
import html2text
from groq import Groq
import json
import re
import asyncio
import concurrent.futures
from playwright.async_api import async_playwright
import random
from typing import List
import logging
from django.http import HttpResponse
import csv
from dotenv import load_dotenv, dotenv_values
import os
from .powerbi import Pwbi

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
# print(f'Dotenv path is: {dotenv_path}')
load_dotenv(dotenv_path)

env_variables = dotenv_values(dotenv_path)

GROQ_API_KEY = env_variables.get('GROQ_API_KEY')
# print(f'Groq Key is: {GROQ_API_KEY}')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User agents list (truncated for brevity - you can keep the full list from api.py)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
]

class ScraperError(Exception):
    """Custom exception for scraper-related errors"""
    pass

def groq_connection(api_key: str) -> Groq:
    """Initialize Groq client with error handling"""
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Error creating Groq client: {e}")
        raise ScraperError(f"Failed to initialize Groq API: {str(e)}")

async def fetch_and_clean_html(url: str, page_count: int = 1) -> str:
    """Fetch and clean HTML content using Playwright"""
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
            )

            context.set_default_timeout(15000)
            page = await context.new_page()

            # Block unnecessary resources
            await page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
            await page.route("**/*analytics*.js", lambda route: route.abort())
            await page.route("**/*tracking*.js", lambda route: route.abort())
            await page.route("**/*advertisement*.js", lambda route: route.abort())

            all_content = []
            current_page = 1

            while current_page <= page_count:
                logger.info(f"Navigating to page {current_page} of {url}")

                if current_page == 1:
                    await page.goto(url, wait_until='domcontentloaded')

                # Scroll to trigger lazy loading
                for _ in range(30):
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(150)

                try:
                    await page.wait_for_load_state('networkidle', timeout=10000)
                except Exception:
                    pass

                html_content = await page.content()

                # Clean HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                    element.decompose()

                # Convert to markdown/text
                markdown_converter = html2text.HTML2Text()
                markdown_converter.ignore_links = False
                markdown_converter.ignore_images = True
                markdown_converter.ignore_emphasis = False
                markdown_converter.ignore_tables = False
                markdown_converter.body_width = 0

                text_content = markdown_converter.handle(str(soup))
                all_content.append(text_content)

                if current_page < page_count:
                    # Comprehensive list of next button selectors
                    next_button_selectors = [
                        'button[aria-label*="next" i]',
                        'button:has-text("Next")',
                        'button:has-text("next")',
                        'a[rel="next"]',
                        'a[aria-label*="next" i]',
                        'a:has-text("Next")',
                        'a:has-text("next")',
                        'a[class*="next"]',
                        'a.next',
                        '.next a',
                        '[class*="pagination"] [class*="next"]',
                        '[class*="pager"] [class*="next"]',
                        '[class*="paginate"] [class*="next"]',
                        'li.next a',
                        '.pagination-next',
                        '[aria-label="Next page"]',
                        '[aria-label="next page"]',
                        'input[value="Next"]',
                        'input[value="next"]',
                        'span[class*="next"]',
                        'div[class*="next"]'
                    ]

                    # Try each selector
                    next_button = None
                    for selector in next_button_selectors:
                        try:
                            next_button = await page.wait_for_selector(selector, timeout=1000)
                            if next_button:
                                logger.info(f"Found next button with selector: {selector}")
                                break
                        except Exception:
                            continue

                    if not next_button:
                        # Try finding by text content if no button found
                        try:
                            next_button = await page.get_by_text(re.compile(r'next', re.IGNORECASE), exact=False).first
                            if next_button:
                                logger.info("Found next button by text content")
                        except Exception:
                            pass

                    if not next_button:
                        logger.info("No next button found, stopping pagination")
                        break

                    try:
                        # Try multiple click methods
                        try:
                            # First try native click
                            await next_button.click()
                            logger.info("Clicked next button using native click")
                        except Exception:
                            try:
                                # Try JavaScript click
                                await page.evaluate('(element) => element.click()', next_button)
                                logger.info("Clicked next button using JavaScript")
                            except Exception:
                                # Try getting href and navigating
                                href = await next_button.get_attribute('href')
                                if href:
                                    if not href.startswith('http'):
                                        # Handle relative URLs
                                        base_url = '/'.join(url.split('/')[:3])
                                        href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                                    await page.goto(href)
                                    logger.info(f"Navigated to next page using href: {href}")
                                else:
                                    raise Exception("No href attribute found")

                        # Wait for navigation to complete
                        await page.wait_for_timeout(2000)

                        # Verify navigation succeeded by checking URL or content change
                        new_url = page.url
                        if new_url == url and current_page > 1:
                            logger.warning("URL didn't change after clicking next button")
                            break
                        url = new_url

                    except Exception as e:
                        logger.error(f"Error navigating to next page: {e}")
                        break

                current_page += 1

            # Clean combined content
            combined_content = "\n".join(all_content)
            space_pattern = re.compile(r'\s+')
            url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

            cleaned_content = space_pattern.sub(' ', combined_content)
            cleaned_content = url_pattern.sub('', cleaned_content)

            return cleaned_content.strip()

    except Exception as e:
        logger.error(f"Error fetching HTML: {e}")
        raise ScraperError(f"Failed to fetch webpage content: {str(e)}")

def clean_json_string(json_str: str) -> str:
    """Clean and validate JSON string"""
    try:
        # Find the start and end of the JSON object
        start = json_str.find('{')
        end = json_str.rfind('}') + 1

        # Check if valid JSON structure is found
        if start >= 0 and end > 0:
            # Extract the JSON object
            json_str = json_str[start:end]

            # Ensure the JSON string ends with ']}' for proper listing format
            if not json_str.endswith(']}'):
                # Remove trailing comma if present and add closing brackets
                json_str = json_str.rstrip(',') + ']}'

            return json_str
    except Exception as e:
        # Log any errors encountered during the cleaning process
        logger.error(f"Failed to clean JSON: {e}")

    # Return an empty listings object if cleaning fails
    return '{"listings": []}'

def process_chunk(client: Groq, sys_message: str, chunk: str, fields: List[str]) -> List[dict]:
    """ Process a chunk of text using Groq API" """
    # List of available LLM models
    llms = [
        'llama-3.2-90b-text-preview',
        'llama-3.2-90b-vision-preview',
        'llama-3.1-70b-versatile',
        'llama3-70b-8192',
        'llama3-groq-70b-8192-tool-use-preview'
    ]

    # Initialize model index and retry counter
    current_model_index = 0
    retry_count = 0
    error_details = None

    # Retry loop with a maximum of 3 attempts
    while retry_count < 3:
        try:
            # Select current LLM model
            llm = llms[current_model_index]
            logger.info(f"Processing chunk with model {llm}")

            # Make API call to Groq
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_message},
                    {"role": "user", "content": (
                        f'Extract these fields from the text: {", ".join(fields)}.\n'
                        f'Return as JSON with format {{"listings": [{{fields}}]}}.\n'
                        f'Content:\n{chunk}'
                    )}
                ],
                model=llm,
                temperature=0.1
            )

            # Extract completion from response
            completion = response.choices[0].message.content
            logger.info(f"Raw LLM Response (truncated): {completion[:200]}...")

            try:
                # Clean and parse JSON response
                cleaned_completion = clean_json_string(completion)
                parsed_chunk = json.loads(cleaned_completion)
                if 'listings' not in parsed_chunk:
                    raise ValueError("Missing 'listings' key")
                return parsed_chunk['listings']
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing response: {e}")
                retry_count += 1
                error_details = {
                    'error_type': 'parsing_error',
                    'message': str(e)
                }
                continue

        except Exception as e:
            error_message = str(e).lower()
            logger.error(f"Error in process_chunk: {e}")

            # Handle different types of Groq API errors
            if "rate_limit" in error_message or "429" in error_message:
                error_details = {
                    'error_type': 'rate_limit',
                    'message': 'Rate limit exceeded. Please try again later or switch to a custom API key.'
                }
                current_model_index = (current_model_index + 1) % len(llms)
                logger.info(f"Rate limit hit, switching to model {llms[current_model_index]}")
            elif "invalid_api_key" in error_message or "authentication" in error_message:
                error_details = {
                    'error_type': 'invalid_api_key',
                    'message': 'Invalid API key. Please check your API key and try again.'
                }
                break  # Don't retry for invalid API key
            elif "insufficient_quota" in error_message:
                error_details = {
                    'error_type': 'quota_exceeded',
                    'message': 'API quota exceeded. Please check your subscription or switch to a different API key.'
                }
                break  # Don't retry for quota issues
            else:
                error_details = {
                    'error_type': 'general_error',
                    'message': f'An error occurred: {str(e)}'
                }
                retry_count += 1

    # If we exit the retry loop without success, raise an exception with error details
    if error_details:
        error_message = json.loads(str(e))
        error_type = error_message.get('error', {}).get('type', '')
        message = error_message.get('error', {}).get('message', '')

        if '429' in str(e) or 'rate_limit' in str(e).lower():
            # Extract wait time if available
            wait_time = re.search(r'try again in (.+?)\.', message)
            wait_msg = f" Please wait {wait_time.group(1)}" if wait_time else ""
            raise ScraperError(f"Rate limit reached.{wait_msg} The API is processing too many requests.")
        elif '503' in str(e):
            raise ScraperError("Groq API is temporarily unavailable. Please try again in a few minutes.")
        else:
            raise ScraperError(f"API Error: {message}")

    return []

def handle_file_upload(request):
    """Handle file upload for visualization"""
    try:
        if 'file' not in request.FILES:
            raise ValueError("No file uploaded")

        uploaded_file = request.FILES['file']
        pwbi = Pwbi()
        df = pwbi.process_file(uploaded_file)
        pwbi.items = df.to_dict('records')
        visualization_html = pwbi.dashboard()

        return JsonResponse({
            'status': 'success',
            'html': visualization_html
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

def parse_price_fields(data):
    """Parse and convert price fields in the data"""
    rows = data.get('rows', [])
    if not rows:
        return data

    # Find price fields in the data
    price_fields = [field for field in rows[0].keys() if 'price' in field.lower()]

    # Compile a regex to match all known currencies
    currency_regex = re.compile(r'(\$|€|£|¥|₹|₽|₺|₩|₪|₫|฿|₦|₴|؋|Ar|R|Br|лв|៛|₡|₲|₵|Kč|kr|£|Q|Ft|Rp|﷼|J\$|₭|ден|₮|MT|₦|C\$|P|S/|₨|₱|zł|lei|руб|RSD|₸|₭|DB|Bs|TSh|₸|₾|USD|EUR|GBP|JPY|AUD|CAD|CNY|INR|RUB|TRY|KRW|ILS|VND|THB|NGN|BRL|ZAR|HKD|SGD|MYR|MXN|PHP|PLN|IDR|SAR|EGP|CHF|NOK|SEK|NZD|DKK|AED|KWD|ARS|COP|PEN|CLP|UAH|GHS|AOA|BHD|BWP|GIP|LKR|MVR|MUR|NAD|PGK|TOP|UYU|WST|YER|AFN|ALL|DZD|AOA|XCD|AMD|AWG|AZN|BSD|BHD|BDT|BBD|BYN|BZD|BMD|BOB|BAM|BWP|BND|BGN|BIF|CVE|KHR|XAF|XPF|KYD|KMF|XAF|CLF|KPW|CRC|CUP|DOP|DJF|XCD|ERN|SZL|ETB|FJD|GMD|XAU|XAG|XPT|XPD|GYD|HTG|HUF|IRR|IQD|ISK|JOD|KZT|KGS|LAK|LBP|LSL|LRD|LYD|MGA|MKD|MMK|MNT|MAD|MZN|NIO|OMR|PKR|PYG|QAR|RON|RWF|STD|SCR|SLL|SBD|SOS|SSP|SDG|SRD|SYP|TJS|TMT|TND|UGX|UZS|VEF|VUV|XOF|ZMW|ZWL)', re.IGNORECASE)

    # Parse and convert price fields
    for row in rows:
        for field in price_fields:
            price_value = row[field]

            # Check if a currency is present
            match = currency_regex.search(price_value)
            if match:
                currency_symbol = match.group()
            else:
                currency_symbol = 'Unknown'

            # Remove non-numeric characters except for commas and periods
            cleaned_price = re.sub(r'[^0-9,\.]', '', price_value)

            # Replace comma (European decimal) with period
            cleaned_price = cleaned_price.replace(',', '.')

            # Remove thousands separator (period)
            cleaned_price = cleaned_price.replace('.', '', cleaned_price.count('.') - 1)

            # Convert cleaned price to float
            try:
                new_price = float(cleaned_price)
            except ValueError:
                new_price = price_value  # Fallback to the original value if it fails

            # Remove the original price field and replace it with a new one
            row.pop(field)
            row[f'Price ({currency_symbol})'] = new_price

    return data


@csrf_protect
@never_cache
async def scrape_website(request):
    """Main view function for website scraping"""

    # Initialize context dictionary for template rendering:
    context = {
        'rows': None, # Holds the scraped data (None until data is processed)
        'error': None, # Stores error messages (None if no errors)
        'show_results': False, # Boolean flag to control results display in template
        'default_api_key': GROQ_API_KEY # Default Groq API key from environment variables
    }

    if request.method == 'POST':
        try:
            # Extract and validate inputs
            url = request.POST.get('url')
            groq_api_key = request.POST.get('groq_api_key')
            fields = [field.strip() for field in request.POST.get('fields', '').split(',') if field.strip()]
            page_count = int(request.POST.get('page_count', 1))

            # Validate URL
            url_validator = URLValidator()
            try:
                url_validator(url)
            except ValidationError:
                raise ScraperError("Please provide a valid URL starting with http:// or https://")

            # Validate fields
            if not fields:
                raise ScraperError("Please specify at least one field to extract")

            # Validate page count
            if page_count < 1 or page_count > 10:
                raise ScraperError("Page count must be between 1 and 10")

            # Initialize Groq client
            client = groq_connection(groq_api_key)

            # Fetch and process content with pagination
            content = await fetch_and_clean_html(url, page_count)
            chunk_size = 10000
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

            sys_message = """
                You are a data extraction expert. Extract structured information from the given text.
                Return ONLY a valid JSON object containing the requested fields.
                The response MUST be in this exact format, with no additional text:
                {"listings": [{"field1": "value1", "field2": "value2"}, ...]}
                Each listing must include all requested fields. Use an empty string if a field is not found.
                Ensure all quotes are double quotes and there are no trailing commas.
                """

            # Process chunks concurrently
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                tasks = [
                    loop.run_in_executor(pool, process_chunk, client, sys_message, chunk, fields)
                    for chunk in chunks
                ]
                try:
                    results = await asyncio.gather(*tasks)
                except ScraperError as e:
                    error_details = json.loads(str(e))
                    raise ScraperError(error_details['message'])

            # Combine results
            all_listings = []
            for result in results:
                if isinstance(result, list):
                    all_listings.extend(result)

            if not all_listings:
                raise ScraperError("Could not extract any data with the specified fields")

            context.update({
                'rows': parse_price_fields({'rows': all_listings})['rows'],
                'show_results': True
            })

        except ScraperError as e:
            # Make the error message more user-friendly
            error_msg = str(e)
            if "Rate limit reached" in error_msg:
                context['error'] = error_msg
            elif "Service Unavailable" in error_msg:
                context['error'] = "Groq API servers are currently overwhelmed. Please try again later."
            else:
                context['error'] = error_msg
            logger.error(f"Scraping error: {e}")
        except Exception as e:
            context['error'] = f"An unexpected error occurred: {str(e)}"
            logger.error(f"Unexpected error: {e}", exc_info=True)

    return render(request, 'index.html', context)

@csrf_protect
@never_cache
def download_csv(request):
    """
    Handle CSV download requests for scraped data.
    """
    if request.method == 'POST':
        try:
            # Parse the JSON data from the request body
            data = parse_price_fields(json.loads(request.body))
            rows = data.get('rows', [])

            # Set up the HTTP response for CSV download
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="scraping_results.csv"'

            if rows:
                # Create a CSV writer and write the data
                writer = csv.DictWriter(response, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            return response
        except Exception as e:
            # Return error response if an exception occurs
            return JsonResponse({'error': str(e)}, status=400)
    # Return error for non-POST requests
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_protect
@never_cache
def download_json(request):
    """
    Handle JSON download requests for scraped data.
    """
    if request.method == 'POST':
        try:
            # Parse the JSON data from the request body
            data = parse_price_fields(json.loads(request.body))
            rows = data.get('rows', [])

            # Set up the HTTP response for JSON download
            response = HttpResponse(content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="scraping_results.json"'

            # Write the JSON data to the response
            json.dump(rows, response, indent=2)

            return response
        except Exception as e:
            # Return error response if an exception occurs
            return JsonResponse({'error': str(e)}, status=400)
    # Return error for non-POST requests
    return JsonResponse({'error': 'Invalid request'}, status=400)