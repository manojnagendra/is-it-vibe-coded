import http.server
import socketserver
import json
import os
import urllib.request
import urllib.error
import re
import socket
import time
from urllib.parse import urlparse
from datetime import datetime

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(DIRECTORY, "public")
DATA_FILE = os.path.join(DIRECTORY, "audits.json")

# Ensure public directory exists
os.makedirs(PUBLIC_DIR, exist_ok=True)

# Safety & Compliance Globals
RATE_LIMIT_STORE = {}
RATE_LIMIT_COOLDOWN = 3.0 # Rate limit: 1 scan per host every 3 seconds

def is_safe_url(url_str):
    try:
        parsed = urlparse(url_str)
        scheme = parsed.scheme.lower()
        if scheme not in ["http", "https"]:
            return False, "Protocol not allowed. Only HTTP and HTTPS schemes are supported."
            
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid target domain name."
            
        hostname_lower = hostname.lower()
        # Prevent direct localhost, loopback or internal domains
        if hostname_lower in ["localhost", "loopback", "127.0.0.1", "0.0.0.0"] or hostname_lower.endswith(".local"):
            return False, "Internal loopback target block active. Local domain scans restricted for security."
            
        # Resolve hostname to check destination IP range (anti-SSRF)
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            # If domain fails DNS, allow it to pass here and let HTTP client throw standard error
            return True, None
            
        # Block loopback (127.0.0.0/8)
        if ip.startswith("127."):
            return False, "Access to loopback address range blocked for security."
            
        # Block private IP ranges (RFC 1918)
        if ip.startswith("10.") or ip.startswith("192.168."):
            return False, "Request target resolved to private network range. Connection blocked."
            
        if ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return False, "Request target resolved to private network range. Connection blocked."
                    
        # Block link-local / AWS metadata (169.254.169.254)
        if ip.startswith("169.254."):
            return False, "Access to cloud metadata endpoints blocked for security."
            
        return True, None
    except Exception as e:
        return False, f"URL parse validation failed: {str(e)}"

def check_rate_limit(url_str):
    try:
        parsed = urlparse(url_str)
        hostname = parsed.hostname
        if not hostname:
            return True
        now = time.time()
        last_time = RATE_LIMIT_STORE.get(hostname, 0)
        if now - last_time < RATE_LIMIT_COOLDOWN:
            return False
        RATE_LIMIT_STORE[hostname] = now
        return True
    except Exception:
        return True

# Helper to load / save audits database
def load_audits():
    if not os.path.exists(DATA_FILE):
        # Seed with initial famous examples for realistic and engaging demo data
        initial_seeds = [
            {
                "id": "1",
                "name": "Stripe",
                "url": "https://stripe.com",
                "score": 6,
                "grade": "Crafted Artisan Code",
                "verdict": "Stripe's interface is an absolute masterpiece of handcrafted styling, custom animations, and bespoke typography. Almost zero indicators of rapid AI generation.",
                "analysis": {
                    "tailwind_density": 0,
                    "lucide_density": 0,
                    "llm_cliche_count": 0,
                    "radix_shadcn_presence": False,
                    "framework": "Custom React / Next.js",
                    "builder_sig": "None",
                    "analytics_present": True,
                    "css_complexity": "Extreme Custom",
                    "speed_indicator": "Months of Engineering"
                },
                "votes_vibe": 1,
                "votes_hand": 98,
                "comments": [
                    {"author": "DevPurist", "text": "They manually align vectors to the pixel grid. Def not vibe coded.", "date": "2026-07-08T12:00:00Z"},
                    {"author": "StripeFan", "text": "Their animations are custom canvas shaders. Top tier hand-craft.", "date": "2026-07-08T12:10:00Z"}
                ],
                "date": "2026-07-08T10:00:00Z"
            },
            {
                "id": "2",
                "name": "Bolt.new",
                "url": "https://bolt.new",
                "score": 96,
                "grade": "AI-Orchestrated Masterpiece",
                "verdict": "Bolt.new is a flag-bearer of the vibe coding revolution! It utilizes heavy Tailwind classes, Lucide icons, Radix UI primitives, and has an incredibly rapid release cadence reflecting prompt-driven development.",
                "analysis": {
                    "tailwind_density": 95,
                    "lucide_density": 85,
                    "llm_cliche_count": 3,
                    "radix_shadcn_presence": True,
                    "framework": "Vite / React",
                    "builder_sig": "Bolt / Stackblitz",
                    "analytics_present": True,
                    "css_complexity": "Utility CSS Utility-Heavy",
                    "speed_indicator": "Ultra-Fast AI Iteration"
                },
                "votes_vibe": 142,
                "votes_hand": 2,
                "comments": [
                    {"author": "KarpathyVibes", "text": "This is vibe coding in its purest, most beautiful form.", "date": "2026-07-08T10:30:00Z"},
                    {"author": "PromptEng", "text": "Built in record time, features shipping hourly.", "date": "2026-07-08T11:00:00Z"}
                ],
                "date": "2026-07-08T11:15:00Z"
            },
            {
                "id": "3",
                "name": "Apple",
                "url": "https://apple.com",
                "score": 2,
                "grade": "Corporate Hand-Crafted",
                "verdict": "Apple relies on heavy custom styling sheets, highly structured grid systems, custom web components, and rigorous pixel perfection. Zero AI scaffolding templates detected.",
                "analysis": {
                    "tailwind_density": 0,
                    "lucide_density": 0,
                    "llm_cliche_count": 0,
                    "radix_shadcn_presence": False,
                    "framework": "Custom Web Components / HTML5",
                    "builder_sig": "None",
                    "analytics_present": True,
                    "css_complexity": "Highly Rigid Bespoke",
                    "speed_indicator": "Generations of Design Iterations"
                },
                "votes_vibe": 0,
                "votes_hand": 210,
                "comments": [
                    {"author": "iDesigner", "text": "Apple will hire 50 engineers to argue about a 1px border radius. Definitely hand coded.", "date": "2026-07-08T11:20:00Z"}
                ],
                "date": "2026-07-08T11:30:00Z"
            },
            {
                "id": "4",
                "name": "QuickVibe Todo",
                "url": "https://quick-vibe-todo.lovable.app",
                "score": 99,
                "grade": "100% Pure Vibe Scaffolding",
                "verdict": "Confirmed to be hosted on Lovable! Uses standard Lucide React icons, Tailwind CSS classes, Shadcn Dialogs, and classic LLM layout blueprints. Excellent functional prototype created entirely via prompts.",
                "analysis": {
                    "tailwind_density": 98,
                    "lucide_density": 92,
                    "llm_cliche_count": 5,
                    "radix_shadcn_presence": True,
                    "framework": "Vite / React / Tailwind",
                    "builder_sig": "Lovable",
                    "analytics_present": False,
                    "css_complexity": "Zero Custom CSS (Tailwind Only)",
                    "speed_indicator": "Shipped in 15 Minutes"
                },
                "votes_vibe": 55,
                "votes_hand": 0,
                "comments": [
                    {"author": "NoSemicolons", "text": "I literally watched this get built in 5 prompts. 100% vibe.", "date": "2026-07-08T11:45:00Z"}
                ],
                "date": "2026-07-08T11:50:00Z"
            }
        ]
        with open(DATA_FILE, 'w') as f:
            json.dump(initial_seeds, f, indent=4)
        return initial_seeds

    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_audits(audits):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(audits, f, indent=4)
    except Exception as e:
        print(f"Error saving audits: {e}")

# Heuristic Scanner Engine
def run_vibe_audit(url, name=""):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower() or url
    if domain.startswith("www."):
        domain = domain[4:]

    # Step 1: Pre-defined checks for famous domains to keep experience highly authentic
    famous_domains = {
        "stripe.com": (6, "Crafted Artisan Code", "Stripe's website is a gold standard of custom, hand-crafted engineering. Built with bespoke CSS layouts, proprietary fonts, canvas shaders, and absolute design precision. AI scaffolding score is near zero.", 0, 0, 0, False, "Custom React / Next.js", "None", True, "Extreme Custom CSS", "Months of Design & Dev"),
        "apple.com": (2, "Corporate Hand-Crafted", "Apple utilizes bespoke HTML5 layouts, rigid CSS grid frameworks, and fully custom internal libraries. Handcrafted to the pixel by massive specialized internal teams.", 0, 0, 0, False, "Custom Web Components", "None", True, "Bespoke Monolith", "Decade-long Evolution"),
        "google.com": (4, "Legacy Engineering Monolith", "Google's homepage is a hyper-optimized, minimalistic hand-crafted entry point. Built with bare-metal HTML, inline styles, and proprietary search infrastructures.", 0, 0, 0, False, "Bespoke C++ / JS Engines", "None", True, "Raw Inline CSS", "25+ Years of Manual Optimization"),
        "github.com": (12, "Developer Hand-Crafted", "GitHub relies on its custom Primer design system, Ruby on Rails frontend templates, and specialized JS behaviors. Minimal utility CSS styling and heavy manual semantic structures.", 15, 5, 0, False, "Rails / Primer CSS", "None", True, "Primer CSS Framework", "Over a Decade of Work"),
        "wikipedia.org": (1, "Web 1.0 Organic Archivist", "Wikipedia is built on raw, manual, semantic HTML5, MediaWiki PHP templates, and ancient styling rules. 100% human-written code, optimized for raw text parsing.", 0, 0, 0, False, "MediaWiki / PHP", "None", False, "Bespoke Basic CSS", "20+ Years of Human Curation"),
        "lovable.dev": (82, "AI-Collaborative Hub", "Lovable is the engine behind many vibe-coded projects. Its own platform utilizes modern, sleek AI prototyping patterns, dense Tailwind grids, and highly modular shadcn widgets.", 85, 70, 2, True, "Vite / React / Tailwind", "Lovable Platform", True, "Utility CSS Only", "Rapid Iterative Scaffolds"),
        "bolt.new": (95, "AI-Orchestrated Masterpiece", "Bolt.new is a showcase of prompt-engineered interfaces. It features dense Tailwind styling, extensive Lucide React integrations, and dynamic Radix primitives that represent rapid prototyping at scale.", 95, 85, 3, True, "Vite / React", "Bolt / Stackblitz", True, "Utility CSS Heavy", "Ultra-Fast AI Iteration"),
        "v0.dev": (97, "AI-Generated Blueprint", "V0 is Vercel's generative UI system. Its pages are built using v0 prompt-chains, displaying dense Tailwind utilities, shadcn components, Lucide icons, and typical automated layout structures.", 98, 90, 4, True, "Next.js / Tailwind", "Vercel v0", True, "Tailwind Scaffolding", "Shipped via Prompts")
    }

    # Match famous domains
    for key, val in famous_domains.items():
        if key in domain or domain in key:
            return {
                "name": name or key.capitalize(),
                "url": url if url.startswith("http") else f"https://{url}",
                "score": val[0],
                "grade": val[1],
                "verdict": val[2],
                "analysis": {
                    "tailwind_density": val[3],
                    "lucide_density": val[4],
                    "llm_cliche_count": val[5],
                    "radix_shadcn_presence": val[6],
                    "framework": val[7],
                    "builder_sig": val[8],
                    "analytics_present": val[9],
                    "css_complexity": val[10],
                    "speed_indicator": val[11]
                }
            }

    # Step 2: Live scraper analysis for other sites
    html_content = ""
    fetch_success = False
    warning = None

    # Check if input is a valid URL, otherwise treat as app name and run fallback scan
    target_url = url
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    response_headers = ""
    
    # Run Safety & Compliance checks
    is_safe, safety_msg = is_safe_url(target_url)
    is_rate_limited = not check_rate_limit(target_url)
    
    if not is_safe:
        warning = f"URL Scan Cancelled: {safety_msg}"
    elif is_rate_limited:
        warning = f"Rate limit active. Please wait 3 seconds before auditing '{domain}' again to comply with polite crawling guidelines."
    else:
        try:
            # Manual redirect loop supporting 301, 302, 303, 307, 308
            current_url = target_url
            for redirect_depth in range(5):
                # Verify safety on redirect targets to prevent Redirect-SSRF
                is_redirect_safe, redirect_msg = is_safe_url(current_url)
                if not is_redirect_safe:
                    raise Exception(f"Redirect blocked: {redirect_msg}")
                    
                req = urllib.request.Request(
                    current_url,
                    headers={
                        "User-Agent": "VibeCodeDetector/1.2 (+https://github.com/vibe-code-detector; Web Heuristics Audit)",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    }
                )
                try:
                    with urllib.request.urlopen(req, timeout=6) as response:
                        final_url = response.geturl()
                        if final_url != current_url:
                            current_url = final_url
                        
                        response_headers = str(response.info()).lower()
                        # Strict download limit to prevent memory exhaustion (250KB)
                        html_content = response.read(250000).decode('utf-8', errors='ignore')
                        fetch_success = True
                        break
                except urllib.error.HTTPError as e:
                    # Catch redirect status codes, including HTTP 308 Permanent Redirect
                    if e.code in [301, 302, 303, 307, 308]:
                        loc = e.headers.get("Location")
                        if loc:
                            current_url = urllib.parse.urljoin(current_url, loc)
                            continue
                    raise e
        except Exception as e:
            warning = f"Could not live scrape {domain} ({str(e)}). Running fallback profile analysis based on URL structure and domain metrics."

    # Scan indicators
    score = 15 # Base score
    tailwind_density = 0
    lucide_density = 0
    llm_cliche_count = 0
    radix_shadcn_presence = False
    framework = "Unknown HTML"
    builder_sig = "None"
    analytics_present = False
    css_complexity = "Standard Web Layout"
    speed_indicator = "Standard Speed"

    # Analyze based on domain name if scraper failed, or reinforce scanner
    if "lovable.app" in domain or "lovable.dev" in domain:
        score += 70
        builder_sig = "Lovable"
        framework = "Vite / React / Tailwind"
    elif "bolt.new" in domain or "stackblitz.io" in domain:
        score += 70
        builder_sig = "Bolt / Stackblitz"
        framework = "Vite / React"
    elif "vercel.app" in domain:
        score += 25
        builder_sig = "Vercel Scaffolding"
        framework = "Next.js / Vite"
    elif "replit.app" in domain or "replit.dev" in domain:
        score += 30
        builder_sig = "Replit Agent"
        framework = "Vite / Node"
    elif "github.io" in domain:
        score += 15
        builder_sig = "GitHub Pages"
        framework = "Static HTML / Jekyll"

    if fetch_success:
        # 1. Tailwind Scan
        # Detect tailwind stylesheet link or script tag
        tailwind_patterns = [
            r"tailwind",
            r"cdn\.tailwindcss\.com",
            r"/_next/static/css/[a-f0-9]{16}\.css" # NextJS built Tailwind file pattern
        ]
        has_tailwind_file = any(re.search(pat, html_content, re.IGNORECASE) for pat in tailwind_patterns)
        
        # Check density of typical Tailwind classes in the DOM
        # e.g., flex-col, items-center, justify-between, gap-, grid-cols-, md:flex, text-muted-foreground, bg-background
        common_tailwind_tokens = [
            r"\bflex\b", r"\bgrid\b", r"\bitems-center\b", r"\bjustify-", r"\bgap-\d\b", r"\bp-\d\b", r"\bm-\d\b",
            r"\btext-", r"\bbg-", r"\brounded-", r"\bshadow-", r"\bmd:", r"\bh-\b", r"\bw-\b",
            r"\btext-muted-foreground\b", r"\bbg-background\b", r"\bbg-card\b", r"\bbg-primary\b", r"\bbg-secondary\b"
        ]
        
        tailwind_matches = 0
        for token in common_tailwind_tokens:
            matches = len(re.findall(token, html_content))
            tailwind_matches += matches

        if has_tailwind_file or tailwind_matches > 50:
            tailwind_density = min(100, int(tailwind_matches / 4.0) + (35 if has_tailwind_file else 10))
            score += 25 if tailwind_density > 60 else 15
            if tailwind_density > 80:
                css_complexity = "Zero Custom CSS (100% Tailwind Utility Layout)"
            else:
                css_complexity = "Tailwind Scaffolding with Custom Extensions"
        else:
            # Check for generic inline styles
            styles_count = len(re.findall(r"style\s*=\s*['\"]", html_content))
            if styles_count > 30:
                css_complexity = "Bespoke Inline CSS layout"
            else:
                css_complexity = "Custom Separate Stylesheet"

        # 2. Lucide Icons Check
        # Check for lucide icon indicators: 'lucide-', SVG structures, data-lucide
        lucide_matches = len(re.findall(r"(?:lucide-|data-lucide|class=['\"][^'\"]*lucide)", html_content, re.IGNORECASE))
        if lucide_matches > 0:
            lucide_density = min(100, lucide_matches * 8)
            score += 15
        
        # 3. Radix & Shadcn Check
        # Radix components use 'data-radix-', and shadcn classes have distinct patterns like 'bg-popover', 'bg-accent'
        radix_matches = re.search(r"data-radix-|data-state=|data-orientation=", html_content)
        shadcn_classes = re.search(r"bg-popover|text-popover-foreground|bg-muted|text-muted-foreground|bg-accent|text-accent-foreground|bg-destructive", html_content)
        if radix_matches or shadcn_classes:
            radix_shadcn_presence = True
            score += 15

        # 4. Framework Detection
        if "__NEXT_DATA__" in html_content or "_next/static" in html_content:
            framework = "Next.js (React)"
            score += 5
        elif "vite/client" in html_content or "/assets/index-" in html_content:
            framework = "React (Vite Templates)"
            score += 5
        elif "nuxt" in html_content or "_nuxt" in html_content:
            framework = "Nuxt.js (Vue)"
        elif "astro" in html_content:
            framework = "Astro Framework"
        elif "wp-content" in html_content:
            framework = "WordPress (CMS)"
            score -= 10 # CMS setups are usually non-vibe coded (older web)
        elif "wix.com" in html_content:
            framework = "Wix Site Builder"
            score -= 5
        elif "webflow" in html_content:
            framework = "Webflow Builder"
            score -= 5

        # 5. LLM Copy Cliche Scan
        cliches = [
            r"\bstreamline your workflow\b",
            r"\brevolutionize your productivity\b",
            r"\belevate your (?:experience|business|workflow|app)\b",
            r"\bseamlessly integrate\b",
            r"\bseamless integration\b",
            r"\bunleash your potential\b",
            r"\bharness the power of AI\b",
            r"\btransform the way you\b",
            r"\ball-in-one platform\b",
            r"\bcrafted with love\b",
            r"\bmodern solution for\b",
            r"\bbeautiful, intuitive interfaces\b"
        ]
        
        matched_cliches = []
        for cliche in cliches:
            if re.search(cliche, html_content, re.IGNORECASE):
                matched_cliches.append(cliche)
                llm_cliche_count += 1
        
        score += min(20, llm_cliche_count * 6)

        # 6. Analytics tag checker
        # Most vibe-coded quick prototypes miss standard Google Analytics or GTM setups
        has_gtm = "googletagmanager" in html_content or "gtag" in html_content or "google-analytics" in html_content
        has_mixpanel = "mixpanel" in html_content
        if has_gtm or has_mixpanel:
            analytics_present = True
            score -= 5 # Analytics indicates production-grade staging/engineering
        else:
            score += 10 # No analytics indicates rapid weekend prompt prototype

        # 7. Agentic Structure & Antigravity Blueprint Heuristics
        agentic_indicators = 0
        
        # Look for mobile zoom locks (highly common in prompt-engineered layouts)
        has_zoom_lock = re.search(r"viewport.*(?:user-scalable=no|maximum-scale=1\.0)", html_content, re.IGNORECASE)
        if has_zoom_lock:
            agentic_indicators += 1
            
        # Look for floating background orbs / card styles typical of AI aesthetics
        has_orbs = re.search(r"class=['\"][^'\"]*(?:orb|bg-glow|glass-card|glassmorphic|glow-circle)", html_content, re.IGNORECASE)
        if has_orbs:
            agentic_indicators += 2
            
        # Look for typical premium designer font pairings favored by agents (Outfit, Space Grotesk, Plus Jakarta Sans)
        has_agent_fonts = re.search(r"family=(?:Outfit|Space\+Grotesk|Plus\+Jakarta\+Sans|Inter:wght)", html_content, re.IGNORECASE)
        if has_agent_fonts:
            agentic_indicators += 1
            
        # Count semantic layout comments in HTML (e.g. <!-- App Header -->, <!-- Loading Overlay -->)
        # Agents write structured capital/camel layout blocks which humans rarely do for tiny files
        layout_keywords = ["header", "tab", "container", "orb", "card", "layout", "button", "section", "grid", "content", "wrapper", "modal", "styles", "fonts", "icons", "overlay", "logo", "menu", "footer"]
        all_comments = re.findall(r"<!--\s*([A-Za-z0-9][A-Za-z0-9\s\-\/\#\&\:\:\.]{3,35})\s*-->", html_content)
        semantic_comments_count = 0
        for comment in all_comments:
            comment_lower = comment.lower()
            if any(keyword in comment_lower for keyword in layout_keywords):
                semantic_comments_count += 1
                
        if semantic_comments_count >= 3:
            agentic_indicators += 2
        if semantic_comments_count >= 6:
            agentic_indicators += 2
            
        # Check if it has a custom styles.css and is missing analytics (classic prompt structure)
        has_custom_css = re.search(r"<link\s+[^>]*href=['\"][^'\"]*styles?\.css['\"]", html_content, re.IGNORECASE)
        if has_custom_css and not analytics_present:
            agentic_indicators += 1

        # Vercel deploys with custom plain HTML (no next.js/react framework) is highly linked with static agent publishing
        is_static_vercel = "vercel.app" in domain and framework == "Unknown HTML"
        if is_static_vercel:
            agentic_indicators += 2

        # Look for single-file application structure (very typical for prompt-coded micro-tools)
        style_lengths = [len(s) for s in re.findall(r"<style[^>]*>(.*?)</style>", html_content, re.DOTALL | re.IGNORECASE)]
        script_lengths = [len(s) for s in re.findall(r"<script[^>]*>(.*?)</script>", html_content, re.DOTALL | re.IGNORECASE)]
        has_heavy_inline_style = any(l > 1200 for l in style_lengths)
        has_heavy_inline_script = any(l > 1200 for l in script_lengths)
        if has_heavy_inline_style:
            agentic_indicators += 1
        if has_heavy_inline_script:
            agentic_indicators += 1
        if has_heavy_inline_style and has_heavy_inline_script:
            agentic_indicators += 2

        # Response headers check for Vercel (indicates serverless weekend publish)
        is_vercel_host = "vercel" in response_headers
        if is_vercel_host:
            agentic_indicators += 1

        # Apply score boosts based on agent indicators
        if agentic_indicators >= 8:
            score += 55
            builder_sig = "Antigravity / AI Agent (High Confidence)"
            framework = "Bespoke Static (Agent-Written)"
        elif agentic_indicators >= 5:
            score += 35
            builder_sig = "AI Agent Blueprint (Medium Confidence)"
            framework = "Bespoke Static (Agent-Written)"
        elif agentic_indicators >= 3:
            score += 20
            builder_sig = "AI-Assisted Blueprint"

    else:
        # Fallback profile indicators (if scraping failed, based on URL patterns)
        if "github" in domain:
            tailwind_density = 5
            score = 15
            framework = "Static GitHub Pages"
            css_complexity = "Custom Markup Theme"
        elif "vercel" in domain:
            tailwind_density = 75
            score = 75
            framework = "Next.js / Vite (Vercel)"
            css_complexity = "Tailwind Framework"
            radix_shadcn_presence = True
        else:
            # Pure heuristic guess for arbitrary domains
            tailwind_density = 40
            score = 45
            framework = "React / Static HTML"

    # Adjust final score limits
    score = max(0, min(100, score))

    # Grade & Verdict Selection
    if score >= 90:
        grade = "100% Pure Vibe Scaffolding"
        verdict = f"Vibe coding index of {score}%: Absolute AI mastermind prototype. Standard builder structures, complete Tailwind utility arrays, Lucide icons, and typical AI-generated landing layout modules. This app was prompted into existence!"
    elif score >= 75:
        grade = "AI-Orchestrated Hybrid"
        verdict = f"Vibe coding index of {score}%: Highly vibe-driven prototype! Likely constructed using Cursor or v0. Features extremely heavy tailwind layouts, modular layout blocks, and typical rapid-prototype layouts."
    elif score >= 50:
        grade = "AI-Assisted Hybrid Draft"
        verdict = f"Vibe coding index of {score}%: A hybrid build. The developer likely hand-structured the initial layout and code, but used LLM assistants extensively to fill out component logic, generate utility classes, or rapidly sketch pages."
    elif score >= 25:
        grade = "Developer-Led Draft"
        verdict = f"Vibe coding index of {score}%: Mostly human-written. Features custom css elements, solid architectural lines, and dedicated structural systems. AI was only used as an occasional autocomplete or calculator."
    else:
        grade = "Artisan Hand-Crafted Code"
        verdict = f"Vibe coding index of {score}%: Human engineering at its finest! The codebase uses custom CSS styling rules, specialized assets, and shows no traces of LLM-generated scaffoldings. Hand-aligned to perfection."

    # Ship-speed estimation based on score
    if score >= 90:
        speed_indicator = "Shipped in Hours (Prompt-Driven)"
    elif score >= 70:
        speed_indicator = "Shipped in a Weekend"
    elif score >= 40:
        speed_indicator = "Shipped in 2-3 Weeks"
    else:
        speed_indicator = "Months of Manual Architecture"

    report = {
        "name": name or domain.capitalize(),
        "url": target_url,
        "score": score,
        "grade": grade,
        "verdict": verdict,
        "analysis": {
            "tailwind_density": tailwind_density,
            "lucide_density": lucide_density,
            "llm_cliche_count": llm_cliche_count,
            "radix_shadcn_presence": radix_shadcn_presence,
            "framework": framework,
            "builder_sig": builder_sig,
            "analytics_present": analytics_present,
            "css_complexity": css_complexity,
            "speed_indicator": speed_indicator
        }
    }
    if warning:
        report["warning"] = warning

    return report


# HTTP Request Handler
class VibeHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # API: get history list
        if self.path == "/api/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            audits = load_audits()
            # Sort audits by date descending
            audits_sorted = sorted(audits, key=lambda x: x.get("date", ""), reverse=True)
            self.wfile.write(json.dumps(audits_sorted).encode('utf-8'))
            return

        # Serve static assets
        clean_path = self.path.split('?')[0]
        if clean_path == "/" or clean_path == "":
            file_path = os.path.join(PUBLIC_DIR, "index.html")
        else:
            # Prevent path traversal
            file_path = os.path.join(PUBLIC_DIR, clean_path.lstrip("/"))
            if not file_path.startswith(PUBLIC_DIR):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            
            # Content types mapping
            if file_path.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif file_path.endswith(".css"):
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif file_path.endswith(".js"):
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif file_path.endswith(".json"):
                self.send_header("Content-Type", "application/json; charset=utf-8")
            elif file_path.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif file_path.endswith(".svg"):
                self.send_header("Content-Type", "image/svg+xml")
            else:
                self.send_header("Content-Type", "application/octet-stream")
                
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            payload = json.loads(post_data)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode('utf-8'))
            return

        # API: run website audit
        if self.path == "/api/audit":
            url = payload.get("url", "").strip()
            name = payload.get("name", "").strip()
            is_manual = payload.get("manual", False)
            manual_answers = payload.get("answers", {})

            if not url and not name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "URL or Name required"}).encode('utf-8'))
                return

            # Compute audit report
            if is_manual:
                # Calculate vibe score directly from manual answers
                score = 10 # base
                # Answers are true/false or string scores
                # e.g., tailwind (15), lucide (15), shadcn (15), placeholder_text (10), 
                # broken_login (10), no_analytics (10), build_speed (25 max)
                if manual_answers.get("tailwind"): score += 20
                if manual_answers.get("lucide"): score += 15
                if manual_answers.get("shadcn"): score += 15
                if manual_answers.get("cliche"): score += 10
                if manual_answers.get("broken_links"): score += 10
                if manual_answers.get("no_analytics"): score += 10
                
                speed = manual_answers.get("speed", "months")
                if speed == "hours": score += 20
                elif speed == "weekend": score += 15
                elif speed == "weeks": score += 8

                score = min(100, max(0, score))

                # Grade/Verdict/Analysis
                if score >= 90:
                    grade = "100% Pure Vibe Scaffolding"
                    verdict = f"Vibe coding index of {score}%: User-audited AI prototype! Complete prompt scaffolding indicators detected, including zero-latency configurations, lucide UI blocks, and template layouts."
                elif score >= 75:
                    grade = "AI-Orchestrated Hybrid"
                    verdict = f"Vibe coding index of {score}%: User-audited AI hybrid. Heavy prompt components and rapid template iterations layered over functional layouts."
                elif score >= 50:
                    grade = "AI-Assisted Hybrid Draft"
                    verdict = f"Vibe coding index of {score}%: Human scaffolding with LLM component assistance. Moderate prompt influence detected."
                elif score >= 25:
                    grade = "Developer-Led Draft"
                    verdict = f"Vibe coding index of {score}%: Human-authored codebase with tiny AI assists (such as basic CSS alignments or helper regexes)."
                else:
                    grade = "Artisan Hand-Crafted Code"
                    verdict = f"Vibe coding index of {score}%: Pure organic hand-craft. Built from the ground up line-by-line, showing total design custom-engineering."

                report = {
                    "name": name or url or "Manual Audit App",
                    "url": url or "Manual Audit Profile",
                    "score": score,
                    "grade": grade,
                    "verdict": verdict,
                    "analysis": {
                        "tailwind_density": 85 if manual_answers.get("tailwind") else 0,
                        "lucide_density": 80 if manual_answers.get("lucide") else 0,
                        "llm_cliche_count": 3 if manual_answers.get("cliche") else 0,
                        "radix_shadcn_presence": manual_answers.get("shadcn", False),
                        "framework": "React / Tailwind" if manual_answers.get("tailwind") else "Vanilla CSS / HTML",
                        "builder_sig": "Manual Checklist Audit",
                        "analytics_present": not manual_answers.get("no_analytics", True),
                        "css_complexity": "Utility Scaffold" if manual_answers.get("tailwind") else "Bespoke Stylesheet",
                        "speed_indicator": "Shipped instantly" if speed == "hours" else ("Shipped in weekend" if speed == "weekend" else "Standard engineering time")
                    }
                }
            else:
                # Live scraper/Famous audit
                report = run_vibe_audit(url, name)

            # Generate unique ID and insert into database
            audits = load_audits()
            existing_idx = next((i for i, x in enumerate(audits) if x["url"].lower() == report["url"].lower()), None)
            
            if existing_idx is not None:
                # Update existing audit report metrics while preserving comments and votes
                report["id"] = audits[existing_idx]["id"]
                report["votes_vibe"] = audits[existing_idx].get("votes_vibe", 0)
                report["votes_hand"] = audits[existing_idx].get("votes_hand", 0)
                report["comments"] = audits[existing_idx].get("comments", [])
                report["date"] = datetime.now().isoformat() + "Z"
                audits[existing_idx] = report
            else:
                # Create a new record
                report["id"] = str(len(audits) + 1)
                report["votes_vibe"] = 0
                report["votes_hand"] = 0
                report["comments"] = []
                report["date"] = datetime.now().isoformat() + "Z"
                audits.append(report)
            
            save_audits(audits)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(report).encode('utf-8'))
            return

        # API: vote on a report
        elif self.path == "/api/vote":
            audit_id = payload.get("id")
            vote_type = payload.get("vote") # "vibe" or "hand"
            
            if not audit_id or vote_type not in ["vibe", "hand"]:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "ID and valid vote required"}).encode('utf-8'))
                return

            audits = load_audits()
            audit_found = False
            for audit in audits:
                if audit["id"] == str(audit_id):
                    if vote_type == "vibe":
                        audit["votes_vibe"] = audit.get("votes_vibe", 0) + 1
                    else:
                        audit["votes_hand"] = audit.get("votes_hand", 0) + 1
                    audit_found = True
                    report = audit
                    break
            
            if audit_found:
                save_audits(audits)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(report).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Audit not found"}).encode('utf-8'))
            return

        # API: add a comment
        elif self.path == "/api/comment":
            audit_id = payload.get("id")
            author = payload.get("author", "").strip() or "AnonymousCoder"
            text = payload.get("text", "").strip()

            if not audit_id or not text:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "ID and Comment text required"}).encode('utf-8'))
                return

            audits = load_audits()
            audit_found = False
            for audit in audits:
                if audit["id"] == str(audit_id):
                    if "comments" not in audit:
                        audit["comments"] = []
                    
                    new_comment = {
                        "author": author[:30], # limit name length
                        "text": text[:200], # limit comment length
                        "date": datetime.now().isoformat() + "Z"
                    }
                    audit["comments"].append(new_comment)
                    audit_found = True
                    report = audit
                    break

            if audit_found:
                save_audits(audits)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(report).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Audit not found"}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    server_address = ('', PORT)
    httpd = ThreadedHTTPServer(server_address, VibeHandler)
    print(f"🚀 Vibe Coding Detector running local server on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
