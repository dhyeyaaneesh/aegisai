from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import re
from transformers import pipeline
import sqlite3
from datetime import datetime
import hashlib
import secrets
import assemblyai as aai
from werkzeug.utils import secure_filename
import os
import tempfile

load_dotenv()

app = Flask(__name__)
CORS(app)

# Get API key from .env
GOOGLE_API_KEY = os.getenv('GOOGLE_SAFE_BROWSING_KEY')

print(f"🔑 API Key loaded: {GOOGLE_API_KEY[:20]}..." if GOOGLE_API_KEY else "❌ No API key found!")
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    print(f"🎤 AssemblyAI API Key loaded: {ASSEMBLYAI_API_KEY[:20]}...")
else:
    print("⚠️ No AssemblyAI API key found - voice analysis will be disabled")

# Configure allowed audio file extensions
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm'}

def allowed_audio_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

# Initialize AI sentiment analyzer
try:
    sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    print("✅ AI Model loaded successfully!")
except Exception as e:
    print(f"⚠️ AI Model failed to load: {e}")
    sentiment_analyzer = None


# ============== USER DATABASE SETUP ==============

def init_user_db():
    """Initialize user database"""
    conn = sqlite3.connect('aegisai_users.db')
    c = conn.cursor()
   
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  email TEXT UNIQUE,
                  created_at TEXT,
                  total_xp INTEGER DEFAULT 0,
                  total_scans INTEGER DEFAULT 0,
                  threats_blocked INTEGER DEFAULT 0,
                  quiz_score INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1)''')

    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY,
                  user_id INTEGER,
                  created_at TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
   
    conn.commit()
    conn.close()

init_user_db()


# ============== USER FUNCTIONS ==============

def hash_password(password):
    """Hash password with salt"""
    salt = "aegisai_salt_2025"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def create_user(username, password, email=None):
    """Create new user account"""
    try:
        password_hash = hash_password(password)
        created_at = datetime.now().isoformat()
       
        conn = sqlite3.connect('aegisai_users.db')
        c = conn.cursor()
        c.execute('''INSERT INTO users (username, password_hash, email, created_at)
                     VALUES (?, ?, ?, ?)''', (username, password_hash, email, created_at))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
       
        return {'success': True, 'user_id': user_id, 'username': username}
    except sqlite3.IntegrityError:
        return {'success': False, 'error': 'Username already exists'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def verify_login(username, password):
    """Verify user login credentials"""
    try:
        password_hash = hash_password(password)
       
        conn = sqlite3.connect('aegisai_users.db')
        c = conn.cursor()
        c.execute('''SELECT id, username, total_xp, total_scans, threats_blocked, quiz_score, level
                     FROM users WHERE username = ? AND password_hash = ?''',
                  (username, password_hash))
        user = c.fetchone()
        conn.close()
       
        if user:
            return {
                'success': True,
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'total_xp': user[2],
                    'total_scans': user[3],
                    'threats_blocked': user[4],
                    'quiz_score': user[5],
                    'level': user[6]
                }
            }
        else:
            return {'success': False, 'error': 'Invalid username or password'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_session(user_id):
    """Create session for logged-in user"""
    try:
        session_id = secrets.token_urlsafe(32)
        created_at = datetime.now().isoformat()
       
        conn = sqlite3.connect('aegisai_users.db')
        c = conn.cursor()
        c.execute('INSERT INTO sessions (session_id, user_id, created_at) VALUES (?, ?, ?)',
                  (session_id, user_id, created_at))
        conn.commit()
        conn.close()
       
        return session_id
    except Exception as e:
        print(f"Error creating session: {e}")
        return None


def update_user_stats(user_id, xp_gained=0, scan_increment=0, threat_increment=0, quiz_score_increment=0):
    """Update user statistics"""
    try:
        conn = sqlite3.connect('aegisai_users.db')
        c = conn.cursor()
       
        c.execute('SELECT total_xp, total_scans, threats_blocked, quiz_score FROM users WHERE id = ?', (user_id,))
        current = c.fetchone()
       
        if current:
            new_xp = current[0] + xp_gained
            new_scans = current[1] + scan_increment
            new_threats = current[2] + threat_increment
            new_quiz = current[3] + quiz_score_increment
            new_level = (new_xp // 50) + 1
           
            c.execute('''UPDATE users
                         SET total_xp = ?, total_scans = ?, threats_blocked = ?, quiz_score = ?, level = ?
                         WHERE id = ?''',
                      (new_xp, new_scans, new_threats, new_quiz, new_level, user_id))
            conn.commit()
            conn.close()
            return {'success': True}
        else:
            conn.close()
            return {'success': False, 'error': 'User not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_leaderboard(limit=10):
    """Get top users by XP"""
    try:
        conn = sqlite3.connect('aegisai_users.db')
        c = conn.cursor()
        c.execute('''SELECT username, total_xp, level, total_scans, threats_blocked
                     FROM users
                     ORDER BY total_xp DESC
                     LIMIT ?''', (limit,))
        users = c.fetchall()
        conn.close()
       
        leaderboard = []
        for i, user in enumerate(users, 1):
            leaderboard.append({
                'rank': i,
                'username': user[0],
                'xp': user[1],
                'level': user[2],
                'scans': user[3],
                'threats_blocked': user[4]
            })
        return leaderboard
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return []


# ============== NAME DETECTION FOR PERSONAL SITES ==============

COMMON_FIRST_NAMES = [
    'john', 'james', 'robert', 'michael', 'william', 'david', 'richard', 'joseph', 'thomas', 'charles',
    'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan', 'jessica', 'sarah', 'karen',
    'daniel', 'matthew', 'anthony', 'donald', 'mark', 'paul', 'steven', 'andrew', 'kenneth', 'joshua',
    'emily', 'lisa', 'nancy', 'betty', 'margaret', 'sandra', 'ashley', 'kimberly', 'donna', 'michelle',
    'chris', 'alex', 'sam', 'jordan', 'taylor', 'morgan', 'casey', 'riley', 'avery', 'jamie'
]

COMMON_LAST_NAMES = [
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
    'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin',
    'lee', 'perez', 'thompson', 'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson'
]

# Trusted legitimate domains whitelist
TRUSTED_DOMAINS = [
    'youtube.com', 'google.com', 'facebook.com', 'amazon.com',
    'microsoft.com', 'apple.com', 'netflix.com', 'linkedin.com',
    'twitter.com', 'instagram.com', 'reddit.com', 'wikipedia.org',
    'github.com', 'stackoverflow.com', 'paypal.com', 'ebay.com',
    'gmail.com', 'outlook.com', 'yahoo.com', 'bing.com',
    'dropbox.com', 'spotify.com', 'twitch.tv', 'zoom.us',
    'adobe.com', 'salesforce.com', 'oracle.com', 'ibm.com'
]

def detect_name_pattern(domain):
    """Detect if domain looks like a person's name"""
    domain_lower = domain.lower()
   
    for tld in ['.com', '.net', '.org', '.io', '.dev', '.me', '.co', '.uk', '.us', '.in']:
        if domain_lower.endswith(tld):
            domain_lower = domain_lower[:-len(tld)]
            break
   
    parts = re.split(r'[-.]', domain_lower)
    parts = [p for p in parts if len(p) > 1]
   
    if not parts:
        return False, "unknown"
   
    if len(parts) == 1:
        name = parts[0]
        if name in COMMON_FIRST_NAMES:
            return True, "first_name_only"
        for fname in COMMON_FIRST_NAMES:
            if name.startswith(fname) and len(name) > len(fname):
                remaining = name[len(fname):]
                if remaining in COMMON_LAST_NAMES or len(remaining) > 3:
                    return True, "concatenated_name"
   
    elif len(parts) == 2:
        first, last = parts[0], parts[1]
        if first in COMMON_FIRST_NAMES or last in COMMON_LAST_NAMES:
            return True, "first_last_separated"
        if 3 <= len(first) <= 12 and 3 <= len(last) <= 12:
            if first.isalpha() and last.isalpha():
                return True, "likely_name_pattern"
   
    elif len(parts) == 3:
        if any(p in COMMON_FIRST_NAMES for p in parts) or any(p in COMMON_LAST_NAMES for p in parts):
            return True, "multi_part_name"
   
    return False, "not_a_name"


def is_legitimate_personal_site(domain, path):
    """Determine if this is likely a legitimate personal/portfolio site"""
    domain_lower = domain.lower()
    path_lower = path.lower()
   
    has_name, name_type = detect_name_pattern(domain)
   
    personal_keywords = [
        'portfolio', 'blog', 'resume', 'cv', 'about', 'contact',
        'work', 'projects', 'photography', 'design', 'art', 'music'
    ]
   
    trusted_platforms = [
        'github.io', 'gitlab.io', 'netlify.app', 'vercel.app',
        'herokuapp.com', 'firebase.app', 'pages.dev', 'webflow.io'
    ]
   
    personal_tlds = ['.me', '.dev', '.io', '.art', '.design', '.photo']
   
    confidence_score = 0
   
    if has_name:
        confidence_score += 40
   
    if any(keyword in domain_lower or keyword in path_lower for keyword in personal_keywords):
        confidence_score += 25
   
    if any(platform in domain_lower for platform in trusted_platforms):
        confidence_score += 30
   
    if any(domain_lower.endswith(tld) for tld in personal_tlds):
        confidence_score += 20
   
    if domain.count('.') <= 2:
        confidence_score += 10
   
    return confidence_score >= 50, confidence_score, name_type


# ============== URL CHECKER ==============

def check_url_with_google(url):
    """Check URL against Google Safe Browsing"""
    if not GOOGLE_API_KEY:
        return {'error': 'No API key', 'risk_score': 0}
   
    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_API_KEY}"
   
    payload = {
        "client": {"clientId": "aegisai", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
   
    try:
        response = requests.post(api_url, json=payload, timeout=10)
       
        if response.status_code == 200:
            data = response.json()
            if 'matches' in data and len(data['matches']) > 0:
                return {
                    'threat_found': True,
                    'threat_type': data['matches'][0]['threatType'],
                    'risk_score': 95
                }
        return {'threat_found': False, 'risk_score': 0}
    except Exception as e:
        print(f"Error calling Google API: {e}")
        return {'error': str(e), 'risk_score': 0}


def advanced_url_analysis(url):
    """Enhanced URL analysis with calibrated risk scoring"""
    risk_score = 0
    warnings = []
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        url_lower = url.lower()
        
        # Extract main domain (without subdomains and TLD)
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            main_domain = domain_parts[-2]  # e.g., "paypal" from "www.paypal.com"
        else:
            main_domain = domain
        
        # ============== STEP 1: CHECK TRUSTED WHITELIST FIRST ==============
        base_domain = domain.replace('www.', '')
        if any(trusted in base_domain for trusted in TRUSTED_DOMAINS):
            return {
                'risk_score': 0,
                'warnings': ['✅ Verified legitimate website'],
                'is_personal': False
            }
        
        # ============== STEP 2: PERSONAL SITE DETECTION ==============
        is_personal, personal_confidence, name_type = is_legitimate_personal_site(domain, path)
        
        print(f"[DEBUG] Personal site check: {is_personal}, confidence: {personal_confidence}%, type: {name_type}")
        
        # ============== STEP 3: CRITICAL THREATS (70+ points - HIGH RISK) ==============
        
        # 1. IP ADDRESS - Instant HIGH risk (40 points)
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            risk_score += 40
            warnings.append("🚨 CRITICAL: Uses IP address instead of domain name")
            is_personal = False  # Override - IPs are never personal sites
        
        # 2. @ SYMBOL TRICK - Instant HIGH risk (45 points)
        if '@' in url:
            risk_score += 45
            warnings.append("🚨 CRITICAL: Contains '@' symbol (URL redirect phishing trick)")
            is_personal = False
        
        # 3. TYPOSQUATTING - Brand impersonation (40 points)
        typosquat_brands = {
            'paypal': ['paypa1', 'paypai', 'paypa11', 'paypall', 'paypay', 'paypa-l', 'pay-pal'],
            'amazon': ['amazn', 'amaz0n', 'amazonn', 'arnaz0n', 'arnazon', 'amaz-on', 'ama-zon'],
            'microsoft': ['micros0ft', 'microsooft', 'micosoft', 'microsft', 'micro-soft'],
            'apple': ['app1e', 'appie', 'appl3', 'applle', 'app-le', 'appl-e'],
            'google': ['gooogle', 'goog1e', 'googie', 'gogle', 'goog-le', 'g00gle'],
            'facebook': ['facebo0k', 'faceboook', 'facebok', 'face-book', 'faceb00k'],
            'netflix': ['netflixx', 'netfl1x', 'netfix', 'net-flix', 'netf1ix'],
            'instagram': ['instagrarn', 'instagramm', 'instagran', 'insta-gram', 'instagrm'],
            'bankofamerica': ['bankofamer1ca', 'bank-of-america', 'bankofam3rica'],
        }
        
        for brand, variants in typosquat_brands.items():
            for variant in variants:
                if variant in main_domain or variant in domain:
                    risk_score += 40
                    warnings.append(f"🎭 BRAND IMPERSONATION: Mimicking '{brand.title()}' as '{variant}'")
                    is_personal = False
                    break
        
        # 4. HOMOGRAPH ATTACK - Lookalike characters (35 points)
        suspicious_chars = ['а', 'е', 'о', 'р', 'с', 'у', 'х', 'і', 'ο', 'а']  # Cyrillic
        for char in suspicious_chars:
            if char in url:
                risk_score += 35
                warnings.append("🚨 Homograph attack: Uses lookalike characters to mimic legitimate domains")
                is_personal = False
                break
        
        # ============== STEP 4: HIGH-RISK KEYWORDS (Context-Aware) ==============
        
        # Define phishing keywords with context
        phishing_keywords = {
            'verify': 18,
            'suspended': 22,
            'urgent': 18,
            'security': 15,
            'confirm': 18,
            'locked': 20,
            'update': 12,
            'account': 15,
            'banking': 20,
            'signin': 18,
            'login': 15,
            'password': 20,
            'secure': 12,
            'alert': 15
        }
        
        # Financial brands that shouldn't be in personal URLs
        financial_brands = [
            'paypal', 'amazon', 'bank', 'visa', 'mastercard', 'chase',
            'wellsfargo', 'bofa', 'citi', 'apple', 'microsoft', 'google',
            'netflix', 'ebay', 'walmart', 'target'
        ]
        
        # Count phishing keywords
        keyword_count = 0
        keyword_score = 0
        detected_keywords = []
        
        for keyword, score in phishing_keywords.items():
            if keyword in url_lower:
                keyword_count += 1
                keyword_score += score
                detected_keywords.append(keyword)
        
        # Check for brand mentions
        has_brand = any(brand in url_lower for brand in financial_brands)
        
        # CRITICAL PATTERN: Personal name + Brand + Phishing keywords = SCAM
        if is_personal and has_brand and keyword_count >= 1:
            risk_score += 50
            warnings.append(f"🚨 SCAM PATTERN: Personal name + brand ({has_brand}) + phishing keywords!")
            warnings.append("⚠️ Real personal sites don't combine names with company brands")
            is_personal = False  # Override
        
        # Brand + Multiple phishing keywords = HIGH RISK
        elif has_brand and keyword_count >= 2:
            risk_score += keyword_score
            warnings.append(f"⚠️ Phishing pattern: Brand name + {keyword_count} suspicious keywords ({', '.join(detected_keywords)})")
        
        # Multiple phishing keywords without brand = MEDIUM RISK
        elif keyword_count >= 3:
            risk_score += min(keyword_score, 35)
            warnings.append(f"⚠️ Multiple suspicious keywords detected ({', '.join(detected_keywords)})")
        
        # Single keyword = minor risk
        elif keyword_count == 1:
            risk_score += min(keyword_score, 15)
            warnings.append(f"⚠️ Suspicious keyword: '{detected_keywords[0]}'")
        
        # ============== STEP 5: TECHNICAL INDICATORS ==============
        
        # URL SHORTENERS (25 points - MEDIUM risk)
        shorteners = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly', 'is.gd', 'buff.ly', 'adf.ly', 'short.link']
        for shortener in shorteners:
            if shortener in domain:
                risk_score += 25
                warnings.append(f"⚠️ URL shortener ({shortener}) - hides real destination")
                break
        
        # SUBDOMAIN OVERLOAD (indicates complexity/obfuscation)
        subdomain_count = domain.count('.')
        if subdomain_count > 4:
            risk_score += 25 + ((subdomain_count - 4) * 5)
            warnings.append(f"⚠️ Excessive subdomains: {subdomain_count} levels deep")
            if is_personal:
                is_personal = False  # Personal sites rarely have 5+ subdomains
        elif subdomain_count == 4:
            risk_score += 15
            warnings.append(f"⚠️ Many subdomains: {subdomain_count} levels")
        
        # SUSPICIOUS TLDs (20 points for high-risk TLDs)
        suspicious_tlds = {
            '.xyz': 20, '.top': 20, '.club': 18, '.work': 18, '.click': 22,
            '.link': 20, '.gq': 25, '.ml': 25, '.ga': 25, '.cf': 25, '.tk': 25,
            '.pw': 20, '.ru': 15, '.info': 8
        }
        
        for tld, score in suspicious_tlds.items():
            if domain.endswith(tld):
                # If it's a personal site with suspicious TLD + phishing keywords = HIGH RISK
                if is_personal and keyword_count > 0:
                    risk_score += score + 15
                    warnings.append(f"⚠️ Suspicious TLD ({tld}) combined with phishing indicators")
                else:
                    risk_score += score
                    warnings.append(f"⚠️ Suspicious domain extension: {tld}")
                break
        
        # LONG URL (possible obfuscation)
        if len(url) > 150:
            risk_score += 18
            warnings.append(f"⚠️ Unusually long URL ({len(url)} chars) - possible obfuscation")
        elif len(url) > 120:
            risk_score += 10
            warnings.append(f"⚠️ Long URL ({len(url)} chars)")
        
        # HTTP vs HTTPS (context-aware)
        if url.startswith('http://') and not any(local in domain for local in ['localhost', '127.0.0.1', '192.168']):
            # Check if it's sensitive operations
            if has_brand or any(word in path for word in ['login', 'signin', 'payment', 'checkout', 'verify']):
                risk_score += 22
                warnings.append("🔓 Not using HTTPS for sensitive operations - DANGEROUS")
            elif is_personal:
                risk_score += 5
                warnings.append("🔓 Not using HTTPS (less critical for personal sites)")
            else:
                risk_score += 12
                warnings.append("🔓 Not using HTTPS - connection is not encrypted")
        
        # FREE HOSTING (context-aware)
        free_hosts = {
            '000webhostapp': 25,
            'wixsite.com': 8,
            'weebly.com': 8,
            'blogspot': 6,
            'wordpress.com': 6,
            'github.io': 3,
            'netlify.app': 2,
            'vercel.app': 2,
            'pages.dev': 2
        }
        
        for host, base_score in free_hosts.items():
            if host in domain:
                # Free hosting + brand impersonation = HIGH RISK
                if has_brand or keyword_count >= 2:
                    risk_score += base_score * 2.5
                    warnings.append(f"🚨 Free hosting ({host}) used for brand impersonation!")
                    is_personal = False
                elif is_personal:
                    risk_score += base_score
                    warnings.append(f"ℹ️ Free hosting: {host} (common for personal sites)")
                else:
                    risk_score += base_score * 1.5
                    warnings.append(f"⚠️ Free hosting service: {host}")
                break
        
        # EXCESSIVE HYPHENS (but allow for personal names)
        hyphen_count = domain.count('-')
        if hyphen_count > 3:
            risk_score += 15
            warnings.append(f"⚠️ Many hyphens in domain ({hyphen_count})")
        elif hyphen_count == 3 and not is_personal:
            risk_score += 8
            warnings.append(f"⚠️ Multiple hyphens in domain")
        # 1-2 hyphens are normal for personal sites (first-last.com)
        
        # NUMBERS IN DOMAIN (context-aware)
        domain_without_tld = '.'.join(domain_parts[:-1]) if len(domain_parts) > 1 else domain
        digit_count = sum(c.isdigit() for c in domain_without_tld)
        
        if digit_count > 5:
            risk_score += 18
            warnings.append(f"⚠️ Many numbers in domain ({digit_count}) - often fake sites")
        elif digit_count >= 3:
            # Check if it's a year or version (acceptable)
            if not re.search(r'(19|20)\d{2}|v\d+|\d{4}', domain):
                risk_score += 10
                warnings.append(f"⚠️ Numbers in domain ({digit_count})")
        
        # ============== STEP 6: PERSONAL SITE ADJUSTMENT ==============
        
        # Apply personal site adjustments ONLY if no critical threats
        has_critical_threat = any(
            'CRITICAL' in w or 'SCAM PATTERN' in w or 'BRAND IMPERSONATION' in w or 'SPOOFED' in w
            for w in warnings
        )
        
        if is_personal and personal_confidence >= 70 and not has_critical_threat:
            # High confidence personal site - reduce to LOW risk (10-20%)
            original_score = risk_score
            
            if original_score <= 30:
                # Already low risk, set to 10-15%
                risk_score = min(10 + (original_score // 10), 15)
            else:
                # Had some minor flags, set to 15-20%
                risk_score = min(15 + (original_score // 20), 20)
            
            warnings.clear()
            warnings.append(f"✅ Verified personal/portfolio site (confidence: {personal_confidence}%, pattern: {name_type})")
            print(f"[DEBUG] Personal site adjustment: {original_score}% → {risk_score}% (HIGH confidence)")
        
        elif is_personal and personal_confidence >= 50 and not has_critical_threat:
            # Medium confidence - reduce to MEDIUM-LOW risk (20-35%)
            original_score = risk_score
            
            if original_score <= 40:
                risk_score = min(20 + (original_score // 15), 30)
            else:
                risk_score = min(25 + (original_score // 20), 35)
            
            # Keep some warnings but mark as likely personal
            warnings.insert(0, f"ℹ️ Likely personal site (confidence: {personal_confidence}%, pattern: {name_type})")
            print(f"[DEBUG] Personal site adjustment: {original_score}% → {risk_score}% (MEDIUM confidence)")
        
        # Final clamp
        risk_score = min(max(risk_score, 0), 100)
        
        print(f"[DEBUG] Final risk score: {risk_score}%, Warnings: {len(warnings)}")
        
        return {
            'risk_score': risk_score,
            'warnings': warnings,
            'is_personal': is_personal,
            'personal_confidence': personal_confidence if is_personal else 0,
            'name_type': name_type if is_personal else None
        }
        
    except Exception as e:
        print(f"[ERROR] URL analysis failed: {e}")
        return {'risk_score': 0, 'warnings': ['Error analyzing URL'], 'is_personal': False}

# ============== TEXT ANALYZER ==============

def advanced_text_analysis(text):
    """Analyze text for scam patterns"""
    risk_score = 0
    warnings = []
    text_lower = text.lower()
   
    # Urgent language
    urgent = ['act now', 'urgent', 'immediate', 'expire', 'limited time', 'hurry']
    for phrase in urgent:
        if phrase in text_lower:
            risk_score += 15
            warnings.append(f"🚨 Pressure tactic: '{phrase}'")
            break
   
    # Money promises
    money = ['won', 'winner', 'prize', 'million', 'lottery', 'inheritance', 'jackpot']
    for word in money:
        if word in text_lower:
            risk_score += 25
            warnings.append(f"💰 Too-good-to-be-true: '{word}'")
            break
   
    # Personal info requests
    info = ['verify your', 'confirm your', 'social security', 'bank account', 'credit card', 'password']
    for phrase in info:
        if phrase in text_lower:
            risk_score += 30
            warnings.append(f"🔐 Requests sensitive info: '{phrase}'")
            break
   
    # Threats
    threats = ['suspended', 'locked', 'terminated', 'legal action', 'arrest', 'blocked']
    for word in threats:
        if word in text_lower:
            risk_score += 20
            warnings.append(f"⚡ Threatening: '{word}'")
            break
   
    # Links
    links = re.findall(r'http[s]?://[^\s]+', text)
    if links:
        risk_score += 15
        warnings.append(f"🔗 Contains {len(links)} link(s)")
   
    # Impersonation
    brands = ['microsoft', 'apple', 'amazon', 'paypal', 'bank', 'irs', 'fbi']
    for brand in brands:
        if brand in text_lower:
            risk_score += 15
            warnings.append(f"🎭 May impersonate: '{brand.title()}'")
            break
   
    # Excessive punctuation
    if text.count('!') > 3:
        risk_score += 10
        warnings.append("❗ Excessive punctuation")
   
    return {'risk_score': min(risk_score, 100), 'warnings': warnings}


# ============== STATISTICS ==============

stats = {
    'total_scans': 0,
    'threats_blocked': 0,
    'url_scans': 0,
    'text_scans': 0,
    'email_scans': 0,
    'voice_scans': 0  # ADD THIS LINE
}

def update_stats(scan_type, risk_level):
    """Update statistics"""
    stats['total_scans'] += 1
   
    if scan_type == 'url':
        stats['url_scans'] += 1
    elif scan_type == 'text':
        stats['text_scans'] += 1
    elif scan_type == 'email':
        stats['email_scans'] += 1
    elif scan_type == 'voice':  # ADD THESE 2 LINES
        stats['voice_scans'] += 1
   
    if risk_level == 'HIGH':
        stats['threats_blocked'] += 1


# ============== API ENDPOINTS ==============

# AUTH ENDPOINTS
@app.route('/api/register', methods=['POST'])
def register():
    """User registration"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip() if data.get('email') else None
   
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
   
    if len(username) < 3:
        return jsonify({'success': False, 'error': 'Username must be at least 3 characters'}), 400
   
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
   
    result = create_user(username, password, email)
   
    if result['success']:
        session_id = create_session(result['user_id'])
        return jsonify({
            'success': True,
            'session_id': session_id,
            'username': result['username']
        })
    else:
        return jsonify(result), 400


@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
   
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
   
    result = verify_login(username, password)
   
    if result['success']:
        session_id = create_session(result['user']['id'])
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user': result['user']
        })
    else:
        return jsonify(result), 401


@app.route('/api/update-stats', methods=['POST'])
def update_stats_endpoint():
    """Update user statistics"""
    data = request.json
    user_id = data.get('user_id')
    xp_gained = data.get('xp_gained', 0)
    scan_increment = data.get('scan_increment', 0)
    threat_increment = data.get('threat_increment', 0)
    quiz_score_increment = data.get('quiz_score_increment', 0)
   
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
   
    result = update_user_stats(user_id, xp_gained, scan_increment, threat_increment, quiz_score_increment)
    return jsonify(result)


@app.route('/api/leaderboard', methods=['GET'])
def leaderboard_endpoint():
    """Get leaderboard"""
    limit = request.args.get('limit', 10, type=int)
    leaderboard = get_leaderboard(limit)
    return jsonify(leaderboard)


# SCANNING ENDPOINTS
@app.route('/api/check-url', methods=['POST'])
def check_url():
    """Check URL endpoint"""
    data = request.json
    url = data.get('url', '')
   
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
   
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
   
    print(f"\n🔍 Checking URL: {url}")
   
    # Google check
    google_result = check_url_with_google(url)
   
    # URL analysis
    analysis_result = advanced_url_analysis(url)
   
    # Combine scores
    if google_result.get('threat_found'):
        total_risk = 95
    else:
        total_risk = analysis_result['risk_score']
   
    total_risk = min(total_risk, 100)
   
    # Determine level
    if total_risk >= 70:
        risk_level = "HIGH"
        status = "🔴 DANGEROUS"
    elif total_risk >= 40:
        risk_level = "MEDIUM"
        status = "🟡 SUSPICIOUS"
    else:
        risk_level = "LOW"
        status = "🟢 SAFE"
   
    # Generate explanation
    if google_result.get('threat_found'):
        explanation = f"🚨 **CRITICAL THREAT!** Google Safe Browsing flagged this as: **{google_result.get('threat_type')}**. DO NOT CLICK!"
    elif total_risk >= 70:
        explanation = "⚠️ **HIGH RISK** - Multiple scam indicators detected. Do NOT click or enter information."
    elif total_risk >= 40:
        explanation = "⚠️ **MEDIUM RISK** - Suspicious characteristics detected. Proceed with caution."
    else:
        explanation = "✅ **LOW RISK** - No major threats detected. Always stay vigilant online."
   
    result = {
        'risk_score': total_risk,
        'risk_level': risk_level,
        'status': status,
        'explanation': explanation,
        'warning_signs': analysis_result['warnings'],
        'google_threat': google_result.get('threat_type', None)
    }
   
    update_stats('url', risk_level)
   
    print(f"✅ Result: {risk_level} ({total_risk}%)")
    return jsonify(result)


@app.route('/api/check-text', methods=['POST'])
def check_text():
    """Check text/message"""
    data = request.json
    text = data.get('text', '')
   
    if not text:
        return jsonify({'error': 'No text provided'}), 400
   
    print(f"\n📧 Checking text: {text[:50]}...")
   
    result = advanced_text_analysis(text)
    risk_score = result['risk_score']
   
    # Determine level
    if risk_score >= 70:
        risk_level = "HIGH"
        status = "🔴 SCAM DETECTED"
        explanation = "🚨 **HIGH RISK** - Strong scam indicators! Do NOT respond or share information."
    elif risk_score >= 40:
        risk_level = "MEDIUM"
        status = "🟡 SUSPICIOUS"
        explanation = "⚠️ **MEDIUM RISK** - Suspicious elements detected. Verify through official channels."
    else:
        risk_level = "LOW"
        status = "🟢 APPEARS SAFE"
        explanation = "✅ **LOW RISK** - No major scam indicators. Always verify unexpected requests."
   
    tips = [
        "Never share passwords or PINs",
        "Verify sender through official channels",
        "Be skeptical of urgent requests",
        "Don't click suspicious links"
    ]
   
    response = {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'status': status,
        'explanation': explanation,
        'warning_signs': result['warnings'],
        'safety_tips': tips
    }
   
    update_stats('text', risk_level)
   
    print(f"✅ Result: {risk_level} ({risk_score}%)")
    return jsonify(response)


@app.route('/api/check-email', methods=['POST'])
def check_email():
    """Check email"""
    data = request.json
    email = data.get('email', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
   
    combined_text = f"{email} {subject} {body}"
   
    if not combined_text.strip():
        return jsonify({'error': 'No email content provided'}), 400
   
    print(f"\n📨 Checking email from: {email}")
   
    result = advanced_text_analysis(combined_text)
    risk_score = result['risk_score']
   
    # Email-specific checks
    if email:
        free_domains = ['gmail.com', 'yahoo.com', 'hotmail.com']
        if any(domain in email.lower() for domain in free_domains):
            if any(word in combined_text.lower() for word in ['bank', 'paypal', 'amazon']):
                risk_score += 20
                result['warnings'].append("⚠️ Business using free email - suspicious")
   
    risk_score = min(risk_score, 100)
   
    # Determine level
    if risk_score >= 70:
        risk_level = "HIGH"
        status = "🔴 LIKELY PHISHING"
        explanation = "🚨 **HIGH RISK** - Strong phishing indicators! Do NOT respond or click links."
    elif risk_score >= 40:
        risk_level = "MEDIUM"
        status = "🟡 SUSPICIOUS"
        explanation = "⚠️ **MEDIUM RISK** - Suspicious email. Verify through official channels."
    else:
        risk_level = "LOW"
        status = "🟢 APPEARS LEGITIMATE"
        explanation = "✅ **LOW RISK** - No major phishing indicators. Still verify unexpected requests."
   
    response = {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'status': status,
        'explanation': explanation,
        'warning_signs': result['warnings'],
        'safety_tips': [
            "Verify sender email matches official domain",
            "Call official number to verify",
            "Check for generic greetings",
            "Hover over links to see destination"
        ]
    }
   
    update_stats('email', risk_level)
   
    print(f"✅ Result: {risk_level} ({risk_score}%)")
    return jsonify(response)

@app.route('/api/check-voice', methods=['POST'])
def check_voice():
    """Analyze voice call recording for scam indicators"""
    
    # Check if API key is available
    if not ASSEMBLYAI_API_KEY:
        return jsonify({
            'error': 'Voice analysis not configured',
            'message': 'AssemblyAI API key is missing'
        }), 503
    
    # Check if file is present
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_audio_file(audio_file.filename):
        return jsonify({
            'error': 'Invalid file type',
            'message': f'Allowed formats: {", ".join(ALLOWED_AUDIO_EXTENSIONS)}'
        }), 400
    
    print(f"\n🎤 Analyzing voice call: {audio_file.filename}")
    
    try:
        # Save file temporarily
        filename = secure_filename(audio_file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        audio_file.save(temp_path)
        
        print(f"📁 Saved to: {temp_path}")
        
        # Transcribe using AssemblyAI
        print("🔄 Transcribing audio with AssemblyAI...")
        
        transcriber = aai.Transcriber()
        transcript_result = transcriber.transcribe(temp_path)
        
        # Check if transcription was successful
        if transcript_result.status == aai.TranscriptStatus.error:
            os.remove(temp_path)
            return jsonify({
                'error': 'Transcription failed',
                'message': transcript_result.error
            }), 500
        
        transcript = transcript_result.text
        
        # Clean up temp file
        os.remove(temp_path)
        
        print(f"📝 Transcription: {transcript[:100]}...")
        
        # Analyze transcribed text using existing text analysis
        analysis_result = advanced_text_analysis(transcript)
        risk_score = analysis_result['risk_score']
        
        # Add voice-specific checks
        voice_warnings = []
        
        # Check for common phone scam indicators
        phone_scam_keywords = {
            'social security': 25,
            'irs': 20,
            'arrest warrant': 30,
            'criminal charges': 25,
            'suspended': 20,
            'frozen account': 25,
            'tech support': 20,
            'refund': 15,
            'verify your identity': 20,
            'computer virus': 20,
            'microsoft windows': 15,
            'gift card': 30,
            'bitcoin': 20,
            'wire transfer': 25,
            'send money': 20,
            'act immediately': 20,
            'final notice': 20
        }
        
        transcript_lower = transcript.lower()
        
        for keyword, score in phone_scam_keywords.items():
            if keyword in transcript_lower:
                risk_score += score
                voice_warnings.append(f"🚨 Phone scam indicator: '{keyword}'")
        
        # Check for pressure tactics
        if any(word in transcript_lower for word in ['now', 'immediately', 'urgent', 'today']):
            if any(word in transcript_lower for word in ['payment', 'money', 'pay', 'send']):
                risk_score += 20
                voice_warnings.append("⚡ Pressure tactic: Demanding immediate payment")
        
        # Combine warnings
        all_warnings = analysis_result['warnings'] + voice_warnings
        
        # Cap at 100
        risk_score = min(risk_score, 100)
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "HIGH"
            status = "🔴 SCAM CALL DETECTED"
            explanation = "🚨 **HIGH RISK** - Strong scam indicators detected in this call. Hang up immediately and do NOT provide any information!"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
            status = "🟡 SUSPICIOUS CALL"
            explanation = "⚠️ **MEDIUM RISK** - Suspicious elements detected. Verify caller identity through official channels before proceeding."
        else:
            risk_level = "LOW"
            status = "🟢 APPEARS LEGITIMATE"
            explanation = "✅ **LOW RISK** - No major scam indicators detected. Still verify unexpected requests through official channels."
        
        response = {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'status': status,
            'explanation': explanation,
            'transcript': transcript,
            'warning_signs': all_warnings,
            'safety_tips': [
                "Never provide personal info over unsolicited calls",
                "Hang up and call official number from company website",
                "Government agencies don't threaten arrest over phone",
                "No legitimate company demands gift cards or wire transfers",
                "Don't trust caller ID - it can be spoofed"
            ]
        }
        
        update_stats('voice', risk_level)
        
        print(f"✅ Voice analysis complete: {risk_level} ({risk_score}%)")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error analyzing voice: {e}")
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'error': 'Voice analysis failed',
            'message': str(e)
        }), 500
@app.route('/api/quiz', methods=['GET'])
def quiz():
    """Get quiz questions - randomly select 5 from pool of 25"""
    import random
    
    question_pool = [
        {
            "id": 1,
            "question": "A company emails asking to verify your password. What should you do?",
            "options": [
                "Reply with your password",
                "Click the link and verify",
                "Ignore and contact company directly through official channels",
                "Forward to friends for advice"
            ],
            "correct": 2,
            "explanation": "Legitimate companies NEVER ask for passwords via email. Always contact them through official channels."
        },
        {
            "id": 2,
            "question": "You receive a message saying you won a prize you never entered. This is likely:",
            "options": [
                "A legitimate prize",
                "A phishing scam",
                "A mistake to investigate",
                "Good luck - claim it fast"
            ],
            "correct": 1,
            "explanation": "If you didn't enter, you didn't win. These are designed to steal your information."
        },
        {
            "id": 3,
            "question": "What makes a URL suspicious?",
            "options": [
                "It uses HTTPS (secure connection)",
                "It's from a .com domain",
                "It uses an IP address instead of domain name",
                "It's too short"
            ],
            "correct": 2,
            "explanation": "Legitimate sites use domain names. IP addresses are often used by scammers to hide identity."
        },
        {
            "id": 4,
            "question": "Email says 'URGENT: Account closed in 24 hours!' What is this?",
            "options": [
                "Important security alert",
                "Pressure tactic to make you act without thinking",
                "Standard company procedure",
                "Technical error"
            ],
            "correct": 1,
            "explanation": "Creating urgency is a common scam tactic. Legitimate companies give you time."
        },
        {
            "id": 5,
            "question": "Best way to check if an email is legitimate:",
            "options": [
                "Click links to see where they go",
                "Reply and ask if it's real",
                "Contact company using official info from their website",
                "Check if it has a logo"
            ],
            "correct": 2,
            "explanation": "Always verify through official channels you find yourself, not links in suspicious emails."
        },
        {
            "id": 6,
            "question": "You see 'paypa1.com' (with number 1 instead of letter L). What's wrong?",
            "options": [
                "Nothing, looks secure",
                "Typosquatting - using similar characters to trick you",
                "The domain is too short",
                "Missing 'www' prefix"
            ],
            "correct": 1,
            "explanation": "Typosquatting uses look-alike characters to mimic legitimate domains. Always check carefully!"
        },
        {
            "id": 7,
            "question": "What should you NEVER share via email or text?",
            "options": [
                "Your favorite color",
                "Passwords, Social Security Number, or credit card CVV",
                "Your first name",
                "Your city of residence"
            ],
            "correct": 1,
            "explanation": "Legitimate organizations NEVER ask for passwords, SSN, or CVV via email/text."
        },
        {
            "id": 8,
            "question": "Email from 'support@amazon.gmail.com' wants your info. Red flag?",
            "options": [
                "No, Amazon uses Gmail for support",
                "Yes! Amazon wouldn't use Gmail for official emails",
                "Only if it asks for money",
                "Gmail makes it more secure"
            ],
            "correct": 1,
            "explanation": "Major companies use their own email domains, never free services like Gmail."
        },
        {
            "id": 9,
            "question": "Text says 'Click to track your package' but you didn't order anything. What do you do?",
            "options": [
                "Click to see what it is - might be a gift",
                "Delete it immediately - likely a scam",
                "Reply asking what package it is",
                "Forward to the delivery company"
            ],
            "correct": 1,
            "explanation": "If you didn't order anything, there's no package. These texts contain malicious links."
        },
        {
            "id": 10,
            "question": "Safest way to verify a suspicious email from your 'bank'?",
            "options": [
                "Call the number provided in the email",
                "Click 'unsubscribe' link to stop emails",
                "Call your bank using number on your card or official website",
                "Reply to email asking if it's real"
            ],
            "correct": 2,
            "explanation": "Always use contact information you know is real - on your card or official website."
        },
        {
            "id": 11,
            "question": "Someone calls claiming to be 'Microsoft Tech Support' about viruses. What should you do?",
            "options": [
                "Give them remote access to fix it",
                "Hang up immediately - Microsoft doesn't make unsolicited calls",
                "Pay them to remove the viruses",
                "Download software they recommend"
            ],
            "correct": 1,
            "explanation": "Tech support scams are common. Microsoft NEVER cold-calls users about viruses."
        },
        {
            "id": 12,
            "question": "Text from 'IRS' says you owe taxes, pay now or face arrest. This is:",
            "options": [
                "A legitimate IRS communication",
                "A scam - IRS contacts by mail first, never threatens immediate arrest",
                "Something to handle by clicking the link",
                "Only suspicious if asking for gift cards"
            ],
            "correct": 1,
            "explanation": "IRS always contacts by mail first and NEVER threatens immediate arrest via text."
        },
        {
            "id": 13,
            "question": "What's a red flag in an online romance?",
            "options": [
                "They want to video chat often",
                "They quickly profess love and ask for money",
                "They live in a different city",
                "They have social media profiles"
            ],
            "correct": 1,
            "explanation": "Romance scams involve quick declarations of love and requests for money for 'emergencies.'"
        },
        {
            "id": 14,
            "question": "Job posting: '$5000/week from home, no experience needed'. This is likely:",
            "options": [
                "A great opportunity to apply for",
                "A legitimate entry-level position",
                "A scam or pyramid scheme",
                "Standard pay for remote work"
            ],
            "correct": 2,
            "explanation": "If it sounds too good to be true, it is. Legitimate jobs don't promise high pay for no experience."
        },
        {
            "id": 15,
            "question": "What does 'https://' in a URL mean?",
            "options": [
                "The site is automatically safe and trustworthy",
                "Connection is encrypted, but site could still be malicious",
                "It's a government website",
                "Only banks use this protocol"
            ],
            "correct": 1,
            "explanation": "HTTPS means encrypted connection, but scammers can use HTTPS too. Doesn't guarantee legitimacy."
        },
        {
            "id": 16,
            "question": "Your friend's social media messages you asking for money. What should you do first?",
            "options": [
                "Send money immediately - they need help",
                "Contact friend through different method to verify it's really them",
                "Post about it on social media",
                "Ignore it completely"
            ],
            "correct": 1,
            "explanation": "Accounts get hacked. Always verify through phone, text, or in-person before sending money."
        },
        {
            "id": 17,
            "question": "Email says 'Your Amazon order #4729183 shipped' but you didn't order anything. What do you do?",
            "options": [
                "Click the tracking link to see",
                "Log into Amazon directly (not via email) to check orders",
                "Reply asking what the order is",
                "Call the number in the email"
            ],
            "correct": 1,
            "explanation": "Never click links in unexpected emails. Go directly to website by typing URL yourself."
        },
        {
            "id": 18,
            "question": "Which payment method is MOST requested by scammers?",
            "options": [
                "Credit card",
                "Personal check",
                "Gift cards (iTunes, Amazon, etc.)",
                "PayPal"
            ],
            "correct": 2,
            "explanation": "Gift cards are untraceable and irreversible. No legitimate business demands gift card payment."
        },
        {
            "id": 19,
            "question": "What's 'vishing'?",
            "options": [
                "Voice phishing - scams via phone calls",
                "A type of computer virus",
                "Video game scamming technique",
                "Virtual shopping fraud"
            ],
            "correct": 0,
            "explanation": "Vishing is voice phishing - scammers call pretending to be from banks or government to steal info."
        },
        {
            "id": 20,
            "question": "Selling items online, buyer offers to pay MORE than asking price. This is:",
            "options": [
                "A generous buyer - accept quickly",
                "Likely an overpayment scam",
                "Normal negotiation tactics",
                "Good business practice"
            ],
            "correct": 1,
            "explanation": "Overpayment scams use fake payments. They ask you to refund 'extra,' but payment bounces."
        },
        {
            "id": 21,
            "question": "Pop-up says 'Your computer is infected! Call this number now!' What do you do?",
            "options": [
                "Call the number for help",
                "Close the browser immediately without calling",
                "Download their antivirus software",
                "Enter credit card for the 'fix'"
            ],
            "correct": 1,
            "explanation": "Fake virus warnings (scareware). Close browser, never call, run your real antivirus if concerned."
        },
        {
            "id": 22,
            "question": "What's 'pharming'?",
            "options": [
                "Agricultural fraud schemes",
                "Redirecting you from legitimate websites to fake ones",
                "Fishing for personal data",
                "Pharmacy prescription fraud"
            ],
            "correct": 1,
            "explanation": "Pharming redirects from real sites to fake lookalikes (via DNS poisoning) to steal credentials."
        },
        {
            "id": 23,
            "question": "Stranger offers to 'invest your money' in crypto with guaranteed returns. This is:",
            "options": [
                "A legitimate investment opportunity",
                "Worth trying with small amount",
                "A scam - no investment has guaranteed returns",
                "Legal if they're licensed"
            ],
            "correct": 2,
            "explanation": "Investment scams promise unrealistic 'guaranteed' returns. Real investments have risks."
        },
        {
            "id": 24,
            "question": "Your 'grandson' calls saying he's in jail, needs bail money wired immediately. What do you do?",
            "options": [
                "Wire money immediately - family emergency!",
                "Hang up and call grandson's known number to verify",
                "Ask them to send proof first",
                "Post about it on Facebook"
            ],
            "correct": 1,
            "explanation": "Grandparent scams prey on emotions. Always verify by calling the person at their real number."
        },
        {
            "id": 25,
            "question": "Apartment listing: amazing place, cheap rent, but 'landlord' needs deposit before viewing. Red flag?",
            "options": [
                "No - deposits are normal practice",
                "Yes - never send money before seeing place in person",
                "Only suspicious if asking for cash",
                "Normal for out-of-state landlords"
            ],
            "correct": 1,
            "explanation": "Rental scams use stolen photos. Never send money before viewing in person and verifying landlord."
        }
    ]
    
    # Randomly select 5 questions from pool of 25
    selected = random.sample(question_pool, 5)
    
    # Shuffle answer options for each question to prevent memorization
    for q in selected:
        correct_answer = q['options'][q['correct']]
        random.shuffle(q['options'])
        q['correct'] = q['options'].index(correct_answer)
    
    return jsonify(selected)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    return jsonify(stats)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'message': 'AegisAI API is running',
        'api_key_present': bool(GOOGLE_API_KEY),
        'ai_model_loaded': sentiment_analyzer is not None,
'       voice_analysis_enabled': bool(ASSEMBLYAI_API_KEY)
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🛡️  AEGISAI BACKEND STARTING")
    print("="*50)
    print(f"📡 API running on: http://localhost:5000")
    print(f"🔑 Google API Key: {'✅ Loaded' if GOOGLE_API_KEY else '❌ Missing'}")
    print(f"🤖 AI Model: {'✅ Loaded' if sentiment_analyzer else '❌ Not loaded'}")
    print(f"👥 User System: ✅ Active")
    print(f"👤 Name Detection: ✅ Active")
    print("="*50 + "\n")
    print(f"🎤 Voice Analysis: {'✅ Enabled' if ASSEMBLYAI_API_KEY else '❌ Disabled (add ASSEMBLYAI_API_KEY)'}")
    app.run(debug=True, port=5000)
