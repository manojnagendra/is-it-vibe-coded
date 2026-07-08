from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import re
import socket
import time
from urllib.parse import urlparse
from datetime import datetime

DATA_FILE = "/tmp/audits.json"
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audits.json")

# Safety & Compliance Globals
RATE_LIMIT_STORE = {}
RATE_LIMIT_COOLDOWN = 3.0

def load_audits():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    if os.path.exists(SEED_FILE):
        try:
            with open(SEED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    return []

def save_audits(audits):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(audits, f, indent=4)
    except Exception as e:
        print(f"Error saving audits: {e}")

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
        if hostname_lower in ["localhost", "loopback", "127.0.0.1", "0.0.0.0"] or hostname_lower.endswith(".local"):
            return False, "Internal loopback target block active. Local domain scans restricted for security."
            
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            return True, None
            
        if ip.startswith("127."):
            return False, "Access to loopback address range blocked for security."
            
        if ip.startswith("10.") or ip.startswith("192.168."):
            return False, "Request target resolved to private network range. Connection blocked."
            
        if ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return False, "Request target resolved to private network range. Connection blocked."
                    
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

def run_vibe_audit(url, name=""):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower() or url
    if domain.startswith("www."):
        domain = domain[4:]

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

    html_content = ""
    fetch_success = False
    warning = None

    target_url = url
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    response_headers = ""
    is_safe, safety_msg = is_safe_url(target_url)
    is_rate_limited = not check_rate_limit(target_url)
    
    if not is_safe:
        warning = f"URL Scan Cancelled: {safety_msg}"
    elif is_rate_limited:
        warning = f"Rate limit active. Please wait 3 seconds before auditing '{domain}' again to comply with polite crawling guidelines."
    else:
        try:
            current_url = target_url
            for redirect_depth in range(5):
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
                        html_content = response.read(250000).decode('utf-8', errors='ignore')
                        fetch_success = True
                        break
                except urllib.error.HTTPError as e:
                    if e.code in [301, 302, 303, 307, 308]:
                        loc = e.headers.get("Location")
                        if loc:
                            current_url = urllib.parse.urljoin(current_url, loc)
                            continue
                    raise e
        except Exception as e:
            warning = f"Could not live scrape {domain} ({str(e)}). Running fallback profile analysis based on URL structure and domain metrics."

    score = 15
    tailwind_density = 0
    lucide_density = 0
    llm_cliche_count = 0
    radix_shadcn_presence = False
    framework = "Unknown HTML"
    builder_sig = "None"
    analytics_present = False
    css_complexity = "Standard Web Layout"
    speed_indicator = "Standard Speed"

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
        tailwind_patterns = [r"tailwind", r"cdn\.tailwindcss\.com", r"/_next/static/css/[a-f0-9]{16}\.css"]
        has_tailwind_file = any(re.search(pat, html_content, re.IGNORECASE) for pat in tailwind_patterns)
        
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
            styles_count = len(re.findall(r"style\s*=\s*['\"]", html_content))
            if styles_count > 30:
                css_complexity = "Bespoke Inline CSS layout"
            else:
                css_complexity = "Custom Separate Stylesheet"

        lucide_matches = len(re.findall(r"(?:lucide-|data-lucide|class=['\"][^'\"]*lucide)", html_content, re.IGNORECASE))
        if lucide_matches > 0:
            lucide_density = min(100, lucide_matches * 8)
            score += 15
        
        radix_matches = re.search(r"data-radix-|data-state=|data-orientation=", html_content)
        shadcn_classes = re.search(r"bg-popover|text-popover-foreground|bg-muted|text-muted-foreground|bg-accent|text-accent-foreground|bg-destructive", html_content)
        if radix_matches or shadcn_classes:
            radix_shadcn_presence = True
            score += 15

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
            score -= 10
        elif "wix.com" in html_content:
            framework = "Wix Site Builder"
            score -= 5
        elif "webflow" in html_content:
            framework = "Webflow Builder"
            score -= 5

        cliches = [
            r"\bstreamline your workflow\b", r"\brevolutionize your productivity\b", r"\belevate your (?:experience|business|workflow|app)\b",
            r"\bseamlessly integrate\b", r"\bseamless integration\b", r"\bunleash your potential\b", r"\bharness the power of AI\b",
            r"\btransform the way you\b", r"\ball-in-one platform\b", r"\bcrafted with love\b", r"\bmodern solution for\b",
            r"\bbeautiful, intuitive interfaces\b"
        ]
        
        matched_cliches = []
        for cliche in cliches:
            if re.search(cliche, html_content, re.IGNORECASE):
                matched_cliches.append(cliche)
                llm_cliche_count += 1
        
        score += min(20, llm_cliche_count * 6)

        has_gtm = "googletagmanager" in html_content or "gtag" in html_content or "google-analytics" in html_content
        has_mixpanel = "mixpanel" in html_content
        if has_gtm or has_mixpanel:
            analytics_present = True
            score -= 5
        else:
            score += 10

        agentic_indicators = 0
        has_zoom_lock = re.search(r"viewport.*(?:user-scalable=no|maximum-scale=1\.0)", html_content, re.IGNORECASE)
        if has_zoom_lock:
            agentic_indicators += 1
            
        has_orbs = re.search(r"class=['\"][^'\"]*(?:orb|bg-glow|glass-card|glassmorphic|glow-circle)", html_content, re.IGNORECASE)
        if has_orbs:
            agentic_indicators += 2
            
        has_agent_fonts = re.search(r"family=(?:Outfit|Space\+Grotesk|Plus\+Jakarta\+Sans|Inter:wght)", html_content, re.IGNORECASE)
        if has_agent_fonts:
            agentic_indicators += 1
            
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
            
        has_custom_css = re.search(r"<link\s+[^>]*href=['\"][^'\"]*styles?\.css['\"]", html_content, re.IGNORECASE)
        if has_custom_css and not analytics_present:
            agentic_indicators += 1

        is_static_vercel = "vercel.app" in domain and framework == "Unknown HTML"
        if is_static_vercel:
            agentic_indicators += 2

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

        is_vercel_host = "vercel" in response_headers
        if is_vercel_host:
            agentic_indicators += 1

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
            tailwind_density = 40
            score = 45
            framework = "React / Static HTML"

    score = max(0, min(100, score))

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

def reset_audits():
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except Exception:
            pass
            
    if os.path.exists(SEED_FILE):
        try:
            with open(SEED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        return

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        if self.path == "/api/history":
            audits = load_audits()
            audits_sorted = sorted(audits, key=lambda x: x.get("date", ""), reverse=True)
            self.wfile.write(json.dumps(audits_sorted).encode('utf-8'))
            return

        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))
        return

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        content_length_header = self.headers.get('Content-Length')
        content_length = int(content_length_header) if content_length_header else 0
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            payload = json.loads(post_data)
        except Exception:
            payload = {}

        # 1. Clear Registry Route
        if self.path == "/api/clear":
            baseline = reset_audits()
            self.wfile.write(json.dumps(baseline).encode('utf-8'))
            return

        # 2. Vote Route
        if self.path == "/api/vote":
            audit_id = payload.get("id")
            vote_type = payload.get("vote")

            if not audit_id or vote_type not in ["vibe", "hand"]:
                self.wfile.write(json.dumps({"error": "ID and valid vote required"}).encode('utf-8'))
                return

            audits = load_audits()
            audit_found = False
            report = {}
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
                self.wfile.write(json.dumps(report).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "Audit not found"}).encode('utf-8'))
            return

        # 3. Comment Route
        if self.path == "/api/comment":
            audit_id = payload.get("id")
            author = payload.get("author", "").strip() or "AnonymousCoder"
            text = payload.get("text", "").strip()

            if not audit_id or not text:
                self.wfile.write(json.dumps({"error": "ID and Comment text required"}).encode('utf-8'))
                return

            audits = load_audits()
            audit_found = False
            report = {}
            for audit in audits:
                if audit["id"] == str(audit_id):
                    if "comments" not in audit:
                        audit["comments"] = []
                    
                    new_comment = {
                        "author": author[:30],
                        "text": text[:200],
                        "date": datetime.now().isoformat() + "Z"
                    }
                    audit["comments"].append(new_comment)
                    audit_found = True
                    report = audit
                    break

            if audit_found:
                save_audits(audits)
                self.wfile.write(json.dumps(report).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "Audit not found"}).encode('utf-8'))
            return

        # 4. Audit Scan Route
        if self.path == "/api/audit":
            url = payload.get("url", "").strip()
            name = payload.get("name", "").strip()
            is_manual = payload.get("manual", False)
            manual_answers = payload.get("answers", {})

            if not url and not name:
                self.wfile.write(json.dumps({"error": "URL or Name required"}).encode('utf-8'))
                return

            if is_manual:
                score = 10
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

                if score >= 90:
                    grade = "100% Pure Vibe Scaffolding"
                    verdict = f"Vibe coding index of {score}%: User-audited AI prototype! Complete prompt scaffolding indicators detected."
                elif score >= 75:
                    grade = "AI-Orchestrated Hybrid"
                    verdict = f"Vibe coding index of {score}%: User-audited AI hybrid. Heavy prompt components."
                elif score >= 50:
                    grade = "AI-Assisted Hybrid Draft"
                    verdict = f"Vibe coding index of {score}%: Human scaffolding with LLM component assistance."
                elif score >= 25:
                    grade = "Developer-Led Draft"
                    verdict = f"Vibe coding index of {score}%: Human-authored codebase with tiny AI assists."
                else:
                    grade = "Artisan Hand-Crafted Code"
                    verdict = f"Vibe coding index of {score}%: Pure organic hand-craft. Built from the ground up."

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
                report = run_vibe_audit(url, name)

            audits = load_audits()
            existing_idx = next((i for i, x in enumerate(audits) if x["url"].lower() == report["url"].lower()), None)
            
            if existing_idx is not None:
                report["id"] = audits[existing_idx]["id"]
                report["votes_vibe"] = audits[existing_idx].get("votes_vibe", 0)
                report["votes_hand"] = audits[existing_idx].get("votes_hand", 0)
                report["comments"] = audits[existing_idx].get("comments", [])
                report["date"] = datetime.now().isoformat() + "Z"
                audits[existing_idx] = report
            else:
                report["id"] = str(len(audits) + 1)
                report["votes_vibe"] = 0
                report["votes_hand"] = 0
                report["comments"] = []
                report["date"] = datetime.now().isoformat() + "Z"
                audits.append(report)
            
            save_audits(audits)
            self.wfile.write(json.dumps(report).encode('utf-8'))
            return

        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))
        return
