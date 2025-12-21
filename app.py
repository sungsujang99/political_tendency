#!/usr/bin/env python3
"""
Political Tendency Analyzer - Web Server
Scrapes news URLs and determines political tendency based on keywords
"""

import json
import os
import re
import shutil
import sys
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Try to import pyserial for Arduino communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_SUPPORT = True
except ImportError:
    SERIAL_SUPPORT = False
    print("Warning: pyserial not installed. Arduino serial communication disabled.")
    print("Install with: pip install pyserial")

# Try to import openpyxl for Excel support
try:
    from openpyxl import load_workbook
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    print("Warning: openpyxl not installed. Excel file support disabled. Install with: pip install openpyxl")

# Handle PyInstaller bundle path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = sys._MEIPASS
    template_folder = os.path.join(base_path, 'templates')
    # Verify template folder exists
    if not os.path.exists(template_folder):
        print(f"WARNING: Template folder not found at {template_folder}")
        if os.path.exists(base_path):
            try:
                available = os.listdir(base_path)
                print(f"Available in bundle: {available}")
            except:
                pass
        # Try alternative paths
        alt_paths = [
            os.path.join(base_path, 'templates'),
            os.path.join(os.path.dirname(sys.executable), 'templates'),
            os.path.join(os.getcwd(), 'templates')
        ]
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                template_folder = alt_path
                print(f"Found templates at: {template_folder}")
                break
        else:
            print("ERROR: Could not find templates folder!")
    app = Flask(__name__, template_folder=template_folder)
else:
    # Running as script
    app = Flask(__name__)

# Global serial connection
arduino_serial = None
serial_port = None

def init_arduino_serial(port=None, baudrate=9600):
    """Initialize serial connection to Arduino"""
    global arduino_serial, serial_port
    
    if not SERIAL_SUPPORT:
        return False
    
    try:
        # If port not specified, try to auto-detect
        if port is None:
            ports = serial.tools.list_ports.comports()
            # Try to find Arduino ports (works on Windows, Mac, Linux)
            arduino_ports = []
            for p in ports:
                desc_lower = p.description.lower() if p.description else ''
                device_lower = p.device.lower() if p.device else ''
                # Check for Arduino indicators (works across platforms)
                if ('arduino' in desc_lower or 
                    'usb serial' in desc_lower or
                    'ch340' in desc_lower or  # Common Arduino clone chip
                    'cp210' in desc_lower or   # Another common chip
                    'ftdi' in desc_lower):     # FTDI chip
                    arduino_ports.append(p.device)
            
            if arduino_ports:
                port = arduino_ports[0]
                print(f"Auto-detected Arduino port: {port}")
            else:
                # If no Arduino-specific port found, list all available ports
                print("No Arduino-specific port detected. Available ports:")
                for p in ports:
                    print(f"  - {p.device}: {p.description or 'No description'}")
                # On Windows, COM ports are common; on Mac/Linux, /dev/tty* or /dev/cu*
                # User can manually select from the web interface
                return False
        
        # Close existing connection if any
        if arduino_serial and arduino_serial.is_open:
            try:
                arduino_serial.close()
            except:
                pass
        
        arduino_serial = serial.Serial(port, baudrate, timeout=1, write_timeout=1)
        serial_port = port
        # Clear buffers
        arduino_serial.reset_input_buffer()
        arduino_serial.reset_output_buffer()
        print(f"Arduino connected on {port} at {baudrate} baud")
        return True
    except serial.SerialException as e:
        print(f"Serial error connecting to Arduino: {str(e)}")
        arduino_serial = None
        return False
    except Exception as e:
        print(f"Error connecting to Arduino: {str(e)}")
        arduino_serial = None
        return False

def send_to_arduino(value):
    """Send value to Arduino via serial with error recovery"""
    global arduino_serial, serial_port
    
    if not SERIAL_SUPPORT:
        return False
    
    # Check if connection is valid
    if arduino_serial is None or not arduino_serial.is_open:
        print("Arduino serial connection not available, attempting to reconnect...")
        # Try to reconnect if we have a port
        if serial_port:
            try:
                arduino_serial = serial.Serial(serial_port, 9600, timeout=1, write_timeout=1)
                arduino_serial.reset_input_buffer()
                arduino_serial.reset_output_buffer()
                print(f"Reconnected to Arduino on {serial_port}")
            except Exception as e:
                print(f"Failed to reconnect to Arduino: {e}")
                arduino_serial = None
                return False
        else:
            return False
    
    try:
        # Clear any pending input
        arduino_serial.reset_input_buffer()
        
        # Send value as integer string with newline (compatible with Serial.parseInt())
        # Format: "750\n" - Arduino's Serial.parseInt() will read this correctly
        message = f"{value}\n"
        arduino_serial.write(message.encode('utf-8'))
        arduino_serial.flush()
        
        # Small delay to ensure data is sent
        import time
        time.sleep(0.01)
        
        print(f"Sent to Arduino: {value} (format: '{message.strip()}')")
        return True
    except serial.SerialException as e:
        print(f"Serial error sending to Arduino: {str(e)}")
        # Close and mark as disconnected
        try:
            arduino_serial.close()
        except:
            pass
        arduino_serial = None
        return False
    except Exception as e:
        print(f"Error sending to Arduino: {str(e)}")
        return False

# Load keywords from Excel or JSON files
def load_keywords():
    """Load progressive and conservative keywords from Excel or JSON files"""
    # Handle PyInstaller bundle path
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # First check executable directory (where users can place files)
        exe_dir = os.path.dirname(sys.executable)
        bundle_dir = sys._MEIPASS  # Bundled files location
    else:
        # Running as script
        exe_dir = os.path.dirname(__file__)
        bundle_dir = exe_dir
    
    def find_file(filename):
        """Find file in executable directory first, then bundle directory"""
        exe_path = os.path.join(exe_dir, filename)
        if os.path.exists(exe_path):
            return exe_path
        bundle_path = os.path.join(bundle_dir, filename)
        if os.path.exists(bundle_path):
            return bundle_path
        return None
    
    # Excel file paths
    progressive_excel = find_file('progressive.xlsx')
    conservative_excel = find_file('conservative.xlsx')
    keywords_excel = find_file('keywords.xlsx')  # Single file with multiple sheets
    
    # JSON file paths
    progressive_json = find_file('progressive.json')
    conservative_json = find_file('conservative.json')
    
    progressive_keywords = []
    conservative_keywords = []
    
    # Try to load from Excel files first
    if EXCEL_SUPPORT:
        # Check for single Excel file with multiple sheets
        if keywords_excel and os.path.exists(keywords_excel):
            try:
                wb = load_workbook(keywords_excel, read_only=True)
                sheet_names = wb.sheetnames
                
                # Look for progressive sheet (check both English and Korean names)
                progressive_sheet = None
                for sheet_name in sheet_names:
                    if 'progressive' in sheet_name.lower() or '진보' in sheet_name:
                        progressive_sheet = sheet_name
                        break
                
                if progressive_sheet:
                    ws = wb[progressive_sheet]
                    progressive_keywords = []
                    # Read from all columns, not just the first one
                    max_col = ws.max_column
                    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=max_col, values_only=True):
                        for cell_value in row:
                            if cell_value:
                                # Split cell value into multiple keywords if it contains delimiters
                                cell_keywords = split_keywords(cell_value)
                                for kw in cell_keywords:
                                    # Skip header rows (check both English and Korean)
                                    kw_lower = kw.lower()
                                    header_keywords = ['keyword', 'keywords', 'term', 'terms', 'progressive', 
                                                      '키워드', '단어', '용어', '진보', '진보진영']
                                    if kw_lower not in header_keywords and kw not in header_keywords:
                                        progressive_keywords.append(kw)
                    progressive_keywords = [kw for kw in progressive_keywords if kw]
                
                # Look for conservative sheet (check both English and Korean names)
                conservative_sheet = None
                for sheet_name in sheet_names:
                    if 'conservative' in sheet_name.lower() or '보수' in sheet_name:
                        conservative_sheet = sheet_name
                        break
                
                if conservative_sheet:
                    ws = wb[conservative_sheet]
                    conservative_keywords = []
                    # Read from all columns, not just the first one
                    max_col = ws.max_column
                    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=max_col, values_only=True):
                        for cell_value in row:
                            if cell_value:
                                # Split cell value into multiple keywords if it contains delimiters
                                cell_keywords = split_keywords(cell_value)
                                for kw in cell_keywords:
                                    # Skip header rows (check both English and Korean)
                                    kw_lower = kw.lower()
                                    header_keywords = ['keyword', 'keywords', 'term', 'terms', 'conservative',
                                                      '키워드', '단어', '용어', '보수', '보수진영']
                                    if kw_lower not in header_keywords and kw not in header_keywords:
                                        conservative_keywords.append(kw)
                    conservative_keywords = [kw for kw in conservative_keywords if kw]
                
                wb.close()
                
                if progressive_keywords or conservative_keywords:
                    print(f"Loaded keywords from {keywords_excel}")
            except Exception as e:
                print(f"Warning: Error reading {keywords_excel}: {str(e)}")
        
        # Check for separate Excel files
        if not progressive_keywords and progressive_excel and os.path.exists(progressive_excel):
            try:
                wb = load_workbook(progressive_excel, read_only=True)
                ws = wb.active
                progressive_keywords = []
                # Read from all columns, not just the first one
                max_col = ws.max_column
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=max_col, values_only=True):
                    for cell_value in row:
                        if cell_value:
                            # Split cell value into multiple keywords if it contains delimiters
                            cell_keywords = split_keywords(cell_value)
                            for kw in cell_keywords:
                                # Skip header rows (check both English and Korean)
                                kw_lower = kw.lower()
                                header_keywords = ['keyword', 'keywords', 'term', 'terms', 'progressive',
                                                  '키워드', '단어', '용어', '진보', '진보진영']
                                if kw_lower not in header_keywords and kw not in header_keywords:
                                    progressive_keywords.append(kw)
                progressive_keywords = [kw for kw in progressive_keywords if kw]
                wb.close()
                print(f"Loaded {len(progressive_keywords)} progressive keywords from {progressive_excel}")
            except Exception as e:
                print(f"Warning: Error reading {progressive_excel}: {str(e)}")
        
        if not conservative_keywords and conservative_excel and os.path.exists(conservative_excel):
            try:
                wb = load_workbook(conservative_excel, read_only=True)
                ws = wb.active
                conservative_keywords = []
                # Read from all columns, not just the first one
                max_col = ws.max_column
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=max_col, values_only=True):
                    for cell_value in row:
                        if cell_value:
                            # Split cell value into multiple keywords if it contains delimiters
                            cell_keywords = split_keywords(cell_value)
                            for kw in cell_keywords:
                                # Skip header rows (check both English and Korean)
                                kw_lower = kw.lower()
                                header_keywords = ['keyword', 'keywords', 'term', 'terms', 'conservative',
                                                  '키워드', '단어', '용어', '보수', '보수진영']
                                if kw_lower not in header_keywords and kw not in header_keywords:
                                    conservative_keywords.append(kw)
                conservative_keywords = [kw for kw in conservative_keywords if kw]
                wb.close()
                print(f"Loaded {len(conservative_keywords)} conservative keywords from {conservative_excel}")
            except Exception as e:
                print(f"Warning: Error reading {conservative_excel}: {str(e)}")
    
    # Fall back to JSON files if Excel files not found or failed
    if not progressive_keywords and progressive_json and os.path.exists(progressive_json):
        try:
            with open(progressive_json, 'r', encoding='utf-8') as f:
                progressive_keywords = json.load(f)
            print(f"Loaded {len(progressive_keywords)} progressive keywords from {progressive_json}")
        except Exception as e:
            print(f"Warning: Error reading {progressive_json}: {str(e)}")
    
    if not conservative_keywords and conservative_json and os.path.exists(conservative_json):
        try:
            with open(conservative_json, 'r', encoding='utf-8') as f:
                conservative_keywords = json.load(f)
            print(f"Loaded {len(conservative_keywords)} conservative keywords from {conservative_json}")
        except Exception as e:
            print(f"Warning: Error reading {conservative_json}: {str(e)}")
    
    return progressive_keywords, conservative_keywords

def scrape_article(url):
    """Scrape article content from a given URL"""
    response = None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # Try to find article content
        article_text = ""
        
        # Common article selectors
        article_selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.article-body',
            '.post-content',
            '.entry-content',
            'main',
            '.content'
        ]
        
        for selector in article_selectors:
            article = soup.select_one(selector)
            if article:
                article_text = article.get_text(separator=' ', strip=True)
                break
        
        # If no article found, get all text from body
        if not article_text:
            body = soup.find('body')
            if body:
                article_text = body.get_text(separator=' ', strip=True)
        
        # Clean up soup to free memory
        del soup
        return article_text, None
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL: {str(e)}"
    except Exception as e:
        return None, f"Error parsing content: {str(e)}"
    finally:
        # Ensure response is closed to free resources
        if response:
            response.close()

def is_korean_text(text):
    """Check if text contains Korean characters"""
    korean_pattern = re.compile(r'[가-힣]')
    return bool(korean_pattern.search(text))

def calculate_arduino_value(progressive_score, conservative_score, total_score):
    """
    Calculate Arduino scale value:
    - Most progressive: 1
    - Neutral: 500
    - Most conservative: 1000
    """
    if total_score == 0:
        return 500  # Neutral when no keywords matched
    
    # Calculate ratio
    progressive_ratio = progressive_score / total_score
    conservative_ratio = conservative_score / total_score
    
    # Map to scale: 1 (progressive) to 1000 (conservative)
    # Progressive: 1-500, Conservative: 500-1000
    if progressive_score > conservative_score:
        # Progressive range: 1 to 500
        # More progressive = closer to 1
        value = 1 + (progressive_ratio * 499)
    elif conservative_score > progressive_score:
        # Conservative range: 500 to 1000
        # More conservative = closer to 1000
        value = 500 + (conservative_ratio * 500)
    else:
        # Equal scores = neutral
        value = 500
    
    return int(round(value))

def split_keywords(cell_value):
    """Split a cell value into multiple keywords if it contains delimiters"""
    if not cell_value:
        return []
    
    text = str(cell_value).strip()
    if not text:
        return []
    
    # Common delimiters: comma, semicolon, pipe, newline, tab, multiple spaces
    # Split by common delimiters
    delimiters = [',', ';', '|', '\n', '\t', '  ']  # double space for multiple spaces
    
    keywords = [text]  # Start with the whole text
    
    # Split by each delimiter
    for delimiter in delimiters:
        new_keywords = []
        for kw in keywords:
            parts = kw.split(delimiter)
            new_keywords.extend([part.strip() for part in parts if part.strip()])
        keywords = new_keywords
    
    # Filter out empty strings and return unique keywords
    return [kw for kw in keywords if kw]

def analyze_political_tendency(text, progressive_keywords, conservative_keywords):
    """Analyze text and determine political tendency"""
    if not text:
        return {
            'tendency': 'Unknown',
            'progressive_score': 0,
            'conservative_score': 0,
            'confidence': 0.0,
            'matched_keywords': {
                'progressive': [],
                'conservative': []
            }
        }
    
    # Check if text contains Korean characters
    is_korean = is_korean_text(text)
    
    # For Korean text, don't convert to lowercase (Korean doesn't have case)
    # For non-Korean text, use lowercase
    if is_korean:
        text_normalized = text
    else:
        text_normalized = text.lower()
    
    # Count keyword matches
    progressive_matches = []
    conservative_matches = []
    
    for keyword in progressive_keywords:
        if not keyword or not keyword.strip():
            continue
            
        keyword_normalized = keyword if is_korean_text(keyword) else keyword.lower()
        
        # For Korean text, use simple substring matching (no word boundaries)
        # For non-Korean text, use word boundaries
        if is_korean_text(keyword) or is_korean:
            # Simple substring matching for Korean
            count = text_normalized.count(keyword_normalized)
            if count > 0:
                progressive_matches.extend([keyword] * count)
        else:
            # Word boundary matching for English
            pattern = r'\b' + re.escape(keyword_normalized) + r'\b'
            matches = re.findall(pattern, text_normalized)
            if matches:
                progressive_matches.extend([keyword] * len(matches))
    
    for keyword in conservative_keywords:
        if not keyword or not keyword.strip():
            continue
            
        keyword_normalized = keyword if is_korean_text(keyword) else keyword.lower()
        
        # For Korean text, use simple substring matching (no word boundaries)
        # For non-Korean text, use word boundaries
        if is_korean_text(keyword) or is_korean:
            # Simple substring matching for Korean
            count = text_normalized.count(keyword_normalized)
            if count > 0:
                conservative_matches.extend([keyword] * count)
        else:
            # Word boundary matching for English
            pattern = r'\b' + re.escape(keyword_normalized) + r'\b'
            matches = re.findall(pattern, text_normalized)
            if matches:
                conservative_matches.extend([keyword] * len(matches))
    
    progressive_score = len(progressive_matches)
    conservative_score = len(conservative_matches)
    total_score = progressive_score + conservative_score
    
    # Determine tendency
    if total_score == 0:
        tendency = 'Neutral'
        confidence = 0.0
    elif progressive_score > conservative_score:
        tendency = 'Progressive'
        confidence = progressive_score / total_score if total_score > 0 else 0.0
    elif conservative_score > progressive_score:
        tendency = 'Conservative'
        confidence = conservative_score / total_score if total_score > 0 else 0.0
    else:
        tendency = 'Mixed'
        confidence = 0.5
    
    # Calculate Arduino scale value (1 = most progressive, 500 = neutral, 1000 = most conservative)
    arduino_value = calculate_arduino_value(progressive_score, conservative_score, total_score)
    
    return {
        'tendency': tendency,
        'progressive_score': progressive_score,
        'conservative_score': conservative_score,
        'confidence': round(confidence * 100, 2),
        'arduino_value': arduino_value,
        'matched_keywords': {
            'progressive': list(set(progressive_matches)),
            'conservative': list(set(conservative_matches))
        }
    }

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a news URL or pasted text"""
    data = request.get_json()
    url = data.get('url', '').strip()
    text = data.get('text', '').strip()
    
    # Load keywords
    progressive_keywords, conservative_keywords = load_keywords()
    
    article_text = None
    source = None
    
    # Check if text is provided (paste mode)
    if text:
        article_text = text
        source = 'pasted_text'
    # Otherwise, try to scrape from URL
    elif url:
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return jsonify({'error': 'Invalid URL format'}), 400
        except Exception:
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Scrape article
        article_text, error = scrape_article(url)
        if error:
            return jsonify({'error': error}), 500
        source = url
    else:
        return jsonify({'error': 'Either URL or text content is required'}), 400
    
    # Analyze political tendency
    result = analyze_political_tendency(article_text, progressive_keywords, conservative_keywords)
    result['source'] = source
    result['article_length'] = len(article_text) if article_text else 0
    result['article_text'] = article_text if article_text else ''
    
    # Send Arduino value via serial (with error handling)
    if SERIAL_SUPPORT:
        try:
            send_to_arduino(result['arduino_value'])
        except Exception as e:
            print(f"Warning: Failed to send to Arduino: {e}")
            # Continue even if Arduino send fails
    
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/keywords/count', methods=['GET'])
def get_keyword_counts():
    """Get current keyword counts"""
    progressive_keywords, conservative_keywords = load_keywords()
    return jsonify({
        'progressive_count': len(progressive_keywords),
        'conservative_count': len(conservative_keywords)
    })

@app.route('/keywords/upload', methods=['POST'])
def upload_keywords():
    """Upload keywords file (Excel or JSON)"""
    try:
        # Debug: Check what's in the request
        print(f"DEBUG: Request files: {list(request.files.keys())}")
        print(f"DEBUG: Request form: {dict(request.form)}")
        
        if 'file' not in request.files:
            print("DEBUG: No 'file' key in request.files")
            return jsonify({'error': 'No file provided in request'}), 400
        
        file = request.files['file']
        keyword_type = request.form.get('type', '').strip()
        
        print(f"DEBUG: File object: {file}")
        print(f"DEBUG: File filename: {file.filename if file else 'None'}")
        print(f"DEBUG: Keyword type: '{keyword_type}'")
        
        if not file:
            return jsonify({'error': 'File object is None'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not keyword_type:
            return jsonify({'error': 'Keyword type not provided'}), 400
        
        if keyword_type not in ['progressive', 'conservative']:
            return jsonify({'error': f'Invalid keyword type: {keyword_type}. Must be "progressive" or "conservative"'}), 400
        
        # Get original filename before secure_filename
        original_filename = file.filename
        print(f"DEBUG: Original filename: {original_filename}")
        
        # Extract extension from original filename first
        if '.' in original_filename:
            file_ext = original_filename.rsplit('.', 1)[1].lower()
        else:
            file_ext = ''
        
        print(f"DEBUG: Detected file extension: '{file_ext}'")
        
        if not file_ext:
            return jsonify({'error': f'File has no extension. Original filename: {original_filename}'}), 400
        
        if file_ext not in ['xlsx', 'json']:
            return jsonify({'error': f'Invalid file type: .{file_ext}. Only .xlsx and .json files are supported.'}), 400
        
        # For Korean filenames, preserve the original filename better
        # secure_filename might strip Korean characters, so we'll use a safer approach
        if is_korean_text(original_filename):
            # Keep original filename but sanitize path separators
            filename = original_filename.replace('/', '_').replace('\\', '_')
        else:
            filename = secure_filename(file.filename)
        print(f"DEBUG: Secure filename: {filename}")
        
        # Process the file - save to executable directory when running as executable
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(__file__)
        keywords = []
        
        if file_ext == 'json':
            # Handle JSON file
            keywords_raw = json.load(file)
            if not isinstance(keywords_raw, list):
                return jsonify({'error': 'JSON file must contain an array of keywords'}), 400
            
            # Split keywords if they contain delimiters
            keywords = []
            for item in keywords_raw:
                if isinstance(item, str):
                    # Split if it contains multiple keywords
                    split_kws = split_keywords(item)
                    keywords.extend(split_kws)
                else:
                    keywords.append(str(item))
            
            keywords = [kw for kw in keywords if kw]
            
            # Save JSON file
            json_path = os.path.join(base_dir, f'{keyword_type}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)
            
        elif file_ext == 'xlsx':
            # Handle Excel file
            if not EXCEL_SUPPORT:
                return jsonify({'error': 'Excel support not available. Install openpyxl.'}), 500
            
            # Save uploaded file temporarily (handle Korean filenames)
            temp_path = os.path.join(base_dir, f'temp_{keyword_type}.xlsx')
            # Ensure the file is saved with proper encoding
            file.save(temp_path)
            
            # Read Excel file
            wb = load_workbook(temp_path, read_only=True)
            ws = wb.active
            
            keywords = []
            # Read from all columns, not just the first one
            max_col = ws.max_column
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=max_col, values_only=True):
                for cell_value in row:
                    if cell_value:
                        # Split cell value into multiple keywords if it contains delimiters
                        cell_keywords = split_keywords(cell_value)
                        for kw in cell_keywords:
                            # Skip header rows (check both English and Korean)
                            kw_lower = kw.lower()
                            header_keywords = ['keyword', 'keywords', 'term', 'terms', keyword_type, 
                                              '키워드', '단어', '용어', '진보', '보수', '진보진영', '보수진영']
                            if kw_lower not in header_keywords and kw not in header_keywords:
                                keywords.append(kw)
            
            keywords = [kw for kw in keywords if kw]
            wb.close()
            
            # Save as JSON (also keep Excel if user wants)
            excel_path = os.path.join(base_dir, f'{keyword_type}.xlsx')
            shutil.move(temp_path, excel_path)
            
            # Also save as JSON for compatibility
            json_path = os.path.join(base_dir, f'{keyword_type}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'count': len(keywords),
            'message': f'Successfully uploaded {len(keywords)} {keyword_type} keywords'
        })
        
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error: {str(e)}")
        return jsonify({'error': f'Invalid JSON file format: {str(e)}'}), 400
    except Exception as e:
        print(f"DEBUG: Exception in upload_keywords: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/keywords/download/<keyword_type>', methods=['GET'])
def download_keywords(keyword_type):
    """Download keywords as JSON"""
    if keyword_type not in ['progressive', 'conservative']:
        return jsonify({'error': 'Invalid keyword type'}), 400
    
    progressive_keywords, conservative_keywords = load_keywords()
    
    keywords = progressive_keywords if keyword_type == 'progressive' else conservative_keywords
    
    return jsonify({'keywords': keywords})

@app.route('/arduino/connect', methods=['POST'])
def connect_arduino():
    """Manually connect to Arduino via serial"""
    data = request.get_json() or {}
    port = data.get('port', '').strip()
    baudrate = data.get('baudrate', 9600)
    
    if not SERIAL_SUPPORT:
        return jsonify({'error': 'pyserial not installed'}), 500
    
    if init_arduino_serial(port if port else None, baudrate):
        return jsonify({
            'success': True,
            'port': serial_port,
            'message': f'Arduino connected on {serial_port}'
        })
    else:
        return jsonify({'error': 'Failed to connect to Arduino'}), 500

@app.route('/arduino/disconnect', methods=['POST'])
def disconnect_arduino():
    """Disconnect Arduino serial connection"""
    global arduino_serial, serial_port
    
    if arduino_serial and arduino_serial.is_open:
        arduino_serial.close()
        arduino_serial = None
        port = serial_port
        serial_port = None
        return jsonify({'success': True, 'message': f'Disconnected from {port}'})
    else:
        return jsonify({'error': 'No active connection'}), 400

@app.route('/arduino/status', methods=['GET'])
def arduino_status():
    """Get Arduino connection status"""
    global arduino_serial, serial_port
    
    if not SERIAL_SUPPORT:
        return jsonify({
            'connected': False,
            'message': 'pyserial not installed',
            'available_ports': []
        })
    
    if arduino_serial and arduino_serial.is_open:
        return jsonify({
            'connected': True,
            'port': serial_port,
            'message': f'Connected on {serial_port}'
        })
    else:
        # List available ports
        ports = []
        if SERIAL_SUPPORT:
            try:
                available_ports = serial.tools.list_ports.comports()
                ports = [{'device': p.device, 'description': p.description} for p in available_ports]
            except:
                pass
        
        return jsonify({
            'connected': False,
            'message': 'Not connected',
            'available_ports': ports
        })

@app.route('/arduino/value', methods=['GET'])
def get_arduino_value():
    """
    Get Arduino scale value for the last analyzed article.
    Returns a simple integer value:
    - 1 = Most progressive
    - 500 = Neutral
    - 1000 = Most conservative
    """
    # For simplicity, return a default neutral value
    # In a real implementation, you might want to store the last analysis result
    return str(500)

@app.route('/arduino/analyze', methods=['POST'])
def analyze_for_arduino():
    """
    Analyze article and return Arduino value directly.
    Accepts URL or text, returns just the numeric value for Arduino.
    """
    data = request.get_json()
    url = data.get('url', '').strip()
    text = data.get('text', '').strip()
    
    # Load keywords
    progressive_keywords, conservative_keywords = load_keywords()
    
    article_text = None
    
    # Check if text is provided (paste mode)
    if text:
        article_text = text
    # Otherwise, try to scrape from URL
    elif url:
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return jsonify({'error': 'Invalid URL format'}), 400
        except Exception:
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Scrape article
        article_text, error = scrape_article(url)
        if error:
            return jsonify({'error': error}), 500
    else:
        return jsonify({'error': 'Either URL or text content is required'}), 400
    
    # Analyze political tendency
    result = analyze_political_tendency(article_text, progressive_keywords, conservative_keywords)
    
    # Return just the Arduino value as plain text (easier for Arduino to parse)
    return str(result['arduino_value']), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    import socket
    
    # Load keywords on startup to validate files
    try:
        progressive_keywords, conservative_keywords = load_keywords()
        print(f"Loaded {len(progressive_keywords)} progressive keywords")
        print(f"Loaded {len(conservative_keywords)} conservative keywords")
        
        if len(progressive_keywords) == 0 and len(conservative_keywords) == 0:
            print("\nWARNING: No keywords loaded!")
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                print(f"  Executable directory: {exe_dir}")
                print(f"  Bundle directory: {sys._MEIPASS}")
                print("  Please ensure keyword files (progressive.json/xlsx, conservative.json/xlsx) exist")
                print("  in the same directory as the executable.")
    except Exception as e:
        print(f"ERROR loading keywords: {e}")
        import traceback
        traceback.print_exc()
        progressive_keywords, conservative_keywords = [], []
    
    # Get local IP address
    def get_local_ip():
        """Get the local IP address"""
        try:
            # Method 1: Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                # Method 2: Get hostname and resolve
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                # Filter out localhost
                if ip != "127.0.0.1":
                    return ip
            except Exception:
                pass
            return None
    
    def get_all_ips():
        """Get all network IP addresses"""
        ips = []
        try:
            hostname = socket.gethostname()
            # Get all IP addresses
            for addr_info in socket.getaddrinfo(hostname, None):
                ip = addr_info[4][0]
                if ip not in ['127.0.0.1', '::1'] and ip not in ips:
                    # Filter IPv4 addresses
                    if '.' in ip:
                        ips.append(ip)
        except Exception:
            pass
        return ips
    
    local_ip = get_local_ip()
    all_ips = get_all_ips()
    port = 5000
    
    print("\n" + "="*50)
    print("Political Tendency Analyzer Server")
    print("="*50)
    print(f"Server starting on:")
    print(f"  Local:   http://127.0.0.1:{port}")
    
    if local_ip:
        print(f"  Network: http://{local_ip}:{port}")
    else:
        print("  Network: Could not detect IP automatically")
    
    if all_ips:
        print("\n  Detected IP addresses:")
        for ip in all_ips:
            print(f"    - http://{ip}:{port}")
    
    print("\nTo access from other devices on the same network:")
    if local_ip:
        print(f"  Open browser and go to: http://{local_ip}:{port}")
    elif all_ips:
        print(f"  Try one of these IPs: {', '.join([f'http://{ip}:{port}' for ip in all_ips])}")
    else:
        print("  Find your IP address manually:")
        print("    Windows: ipconfig (look for IPv4 Address)")
        print("    Mac/Linux: ifconfig or ip addr")
    
    print("\nTroubleshooting:")
    print("  1. Make sure Windows Firewall allows Python through")
    print("  2. Ensure both devices are on the same Wi-Fi/network")
    print("  3. Try accessing from the server machine first: http://127.0.0.1:5000")
    print("="*50 + "\n")
    
    try:
        print(f"\nStarting server on 0.0.0.0:{port}...")
        print("Server is running. Press Ctrl+C to stop.\n")
        # Use 0.0.0.0 to bind to all network interfaces (not just localhost)
        # This allows access from other devices on the network
        app.run(debug=False, host='0.0.0.0', port=port, threaded=True, use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e) or "10048" in str(e):
            print(f"\nERROR: Port {port} is already in use!")
            print("Please close the application using port 5000 or change the port number.")
            print("\nTrying to start on port 5001 instead...")
            try:
                app.run(debug=False, host='0.0.0.0', port=5001, threaded=True, use_reloader=False)
            except Exception as e2:
                print(f"ERROR: Could not start on port 5001 either: {e2}")
        else:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()

