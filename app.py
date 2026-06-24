from flask import Flask, request, render_template_string
import re
import requests
import time
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ========================
# قائمة خوادم Nitter (موسعة)
# ========================
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.1d4.us",
    "https://nitter.pufe.org",
    "https://nitter.moomoo.me",
    "https://nitter.unixfox.eu",
    "https://nitter.eu",
]

cache = {}
CACHE_DURATION = 600

# ========================
# دوال جلب RSS
# ========================
def fetch_rss(url, timeout=10):
    """تجربة كل الخوادم لإرجاع محتوى XML"""
    for instance in NITTER_INSTANCES:
        full_url = instance + url
        try:
            resp = requests.get(full_url, timeout=timeout,
                                headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.content) > 100:
                content = resp.content.strip()
                if content.startswith(b'<?xml') or content.startswith(b'<rss'):
                    return content
        except Exception:
            continue
    return None

def parse_tweets_from_rss(xml_content, max_items=10):
    if xml_content is None:
        return []
    try:
        root = ET.fromstring(xml_content)
        tweets = []
        for item in root.findall(".//item")[:max_items]:
            title = item.find("title")
            if title is not None and title.text:
                text = title.text.strip()
                if ':' in text:
                    text = text.split(':', 1)[1].strip()
                if text:
                    tweets.append(text)
        return tweets
    except ET.ParseError:
        return []

# ========================
# استخراج اسم المستخدم
# ========================
def extract_username(url):
    url = url.strip()
    patterns = [
        r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)",
        r"@?([A-Za-z0-9_]{4,})"
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return url.lstrip("@")

# ========================
# تحليل النصوص
# ========================
POSITIVE_WORDS = {"رائع","ممتاز","جميل","حب","سعيد","مذهل","شكراً","👍",
                  "good","great","love","happy","amazing","thanks"}
NEGATIVE_WORDS = {"سيء","حزين","غضب","يكره","فظيع","ممل","فشل","👎",
                  "bad","sad","angry","hate","terrible","fail"}

def analyze_sentiment(tweets):
    pos = sum(1 for t in tweets for w in t.lower().split() if w in POSITIVE_WORDS)
    neg = sum(1 for t in tweets for w in t.lower().split() if w in NEGATIVE_WORDS)
    if pos > neg: return "إيجابي 😊"
    elif neg > pos: return "سلبي 😞"
    else: return "محايد 😐"

AR_STOPWORDS = {"في","من","على","الى","عن","و","ثم","لا","ما","هذا","كان","مع","أن",
                "إن","كل","الذي","التي","إذا","لم","لن","هل","قد","أو","بين","كما",
                "بعد","قبل","حتى","إلا","أيضا","هو","هي","هم","نحن","أنت","أنا"}
EN_STOPWORDS = {"a","an","the","is","are","was","were","be","been","being","have",
                "has","had","do","does","did","i","me","my","we","our","you","your",
                "he","she","it","they","them","this","that","these","those","to","of",
                "in","for","on","with","at","by","from","up","about","into","through",
                "during","and","but","or","so","if","then","than","too","very","can",
                "will","just","now","not","only"}
STOPWORDS = AR_STOPWORDS | EN_STOPWORDS

def word_frequency(tweets, top_n=5):
    words = []
    for t in tweets:
        clean = re.sub(r"[^\w\s]", "", t)
        words.extend(clean.lower().split())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 1]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]

# ========================
# كشف الحظر المخفي (محسّن)
# ========================
def search_tweets_fallback(username):
    """
    محاولة جلب التغريدات من البحث عبر Nitter بصيغ مختلفة.
    تُعيد قائمة التغريدات (حتى 10) أو None إذا فشل.
    """
    # 1. RSS عادي
    search_xml = fetch_rss(f"/search/rss?q=from%3A{username}")
    if search_xml:
        return parse_tweets_from_rss(search_xml, 10)

    # 2. JSON (بعض الخوادم)
    for instance in NITTER_INSTANCES:
        try:
            resp = requests.get(
                f"{instance}/search.json?q=from%3A{username}",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                tweets = []
                for item in data.get("tweets", [])[:10]:
                    text = item.get("text", "")
                    if text:
                        tweets.append(text)
                if tweets:
                    return tweets
        except Exception:
            continue

    # 3. تحليل HTML صفحة البحث (خطة أخيرة)
    for instance in NITTER_INSTANCES:
        try:
            resp = requests.get(
                f"{instance}/search?q=from%3A{username}",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                tweets = re.findall(r'<div class="tweet-content[^"]*">(.*?)</div>', resp.text, re.DOTALL)
                if tweets:
                    clean_tweets = [re.sub(r'<[^>]+>', '', t).strip() for t in tweets[:10]]
                    if any(clean_tweets):
                        return clean_tweets
        except Exception:
            continue

    return None

def check_shadowban(username):
    # التغريدات المباشرة (البروفايل)
    direct_xml = fetch_rss(f"/{username}/rss")
    direct_tweets = parse_tweets_from_rss(direct_xml, 10)

    if not direct_tweets:
        return "غير معروف", "لا توجد تغريدات في الملف الشخصي"

    # البحث عن التغريدات عبر محرك البحث
    search_tweets = search_tweets_fallback(username)

    if search_tweets is None:
        return "⚠️ غير معروف", "تعذر التحقق من البحث (حاول لاحقًا أو استخدم إدخال يدوي)"

    if len(search_tweets) == 0:
        return "🔴 حظر مخفي محتمل", "تغريداتك لا تظهر في البحث"
    elif len(search_tweets) < len(direct_tweets) * 0.5:
        return "🟡 حظر جزئي", "بعض التغريدات لا تظهر"
    else:
        return "🟢 طبيعي", "تغريداتك تظهر في البحث"

# ========================
# التحليل الكامل
# ========================
def analyze_full(username, tweets):
    if not tweets:
        return {"error": "لا توجد تغريدات"}

    score = 100
    issues = []
    fixes = []
    count = len(tweets)
    avg_len = sum(len(t) for t in tweets) / count
    hashtags = sum(1 for t in tweets if "#" in t)
    questions = sum(1 for t in tweets if "?" in t)

    if avg_len < 40:
        score -= 20; issues.append("المحتوى قصير"); fixes.append("اكتب محتوى أطول")
    if hashtags == 0:
        score -= 10; issues.append("لا يستخدم هاشتاغات"); fixes.append("أضف هاشتاغات ذات صلة")
    if questions == 0:
        score -= 10; issues.append("لا يوجد تفاعل"); fixes.append("استخدم أسئلة")
    if count < 5:
        score -= 15; issues.append("نشاط ضعيف"); fixes.append("انشر باستمرار")

    sentiment = analyze_sentiment(tweets)
    if "سلبي" in sentiment:
        score -= 10; issues.append("مشاعر سلبية"); fixes.append("شارك محتوى إيجابي")

    shadow_status, shadow_note = check_shadowban(username)
    if "مخفي" in shadow_status:
        score -= 25
        issues.append(f"حظر: {shadow_note}")
        fixes.append("راجع سياسات المنصة وتفاعل بشكل طبيعي")

    top_words = word_frequency(tweets)

    if score >= 80: status, risk = "🟢 قوي", "منخفض"
    elif score >= 60: status, risk = "🟡 متوسط", "متوسط"
    else: status, risk = "🔴 ضعيف", "مرتفع"

    return {
        "username": username,
        "score": max(0, score),
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": list(set(fixes)),
        "top_words": top_words,
        "sentiment": sentiment,
        "shadow_status": shadow_status,
        "shadow_note": shadow_note,
        "avg_len": round(avg_len, 1),
        "hashtags": hashtags,
        "questions": questions,
        "comparison": None,
    }

# ========================
# واجهة HTML (مبسطة)
# ========================
HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>محلل X شامل</title>
<style>
body { background:#0f172a; color:#e2e8f0; font-family:Arial; padding:20px; }
.container { max-width:800px; margin:auto; background:#1e293b; border-radius:15px; padding:25px; }
h1 { color:#38bdf8; text-align:center; }
.tabs { display:flex; margin-bottom:20px; }
.tab { flex:1; padding:12px; background:#334155; text-align:center; cursor:pointer; border-radius:8px 8px 0 0; }
.tab.active { background:#3b82f6; font-weight:bold; }
.panel { display:none; }
.panel.active { display:block; }
input, textarea, button { width:100%; padding:12px; margin:10px 0; border-radius:8px; border:none; font-size:16px; }
input, textarea { background:#334155; color:white; }
button { background:#3b82f6; color:white; font-weight:bold; cursor:pointer; }
button:hover { background:#2563eb; }
.result { background:#0f172a; border-radius:8px; padding:15px; margin-top:20px; }
.issues { color:#f87171; }
.fixes { color:#4ade80; }
.error { color:#facc15; background:#422006; padding:10px; border-radius:5px; }
</style>
</head>
<body>
<div class="container">
<h1>🧠 محلل X متقدم</h1>

<div class="tabs">
  <div class="tab active" onclick="switchTab('auto')">تحليل تلقائي</div>
  <div class="tab" onclick="switchTab('manual')">إدخال يدوي</div>
</div>

<form method="post">
  <div id="auto-panel" class="panel active">
    <input name="url" placeholder="رابط الحساب (x.com/username)" value="{{ form_data.get('url', '') }}">
    <input type="hidden" name="mode" value="auto">
  </div>

  <div id="manual-panel" class="panel">
    <textarea name="tweets" placeholder="الصق التغريدات (كل سطر تغريدة)" rows="6">{{ form_data.get('tweets', '') }}</textarea>
    <input name="manual_username" placeholder="اسم المستخدم (اختياري)" value="{{ form_data.get('manual_username', '') }}">
    <input type="hidden" name="mode" value="manual">
  </div>

  <button type="submit">تحليل</button>
</form>

{% if data %}
<div class="result">
  {% if data.error %}
    <div class="error">{{ data.error }}</div>
  {% else %}
    <h2>👤 @{{ data.username }}</h2>
    <p>📊 النقاط: <strong>{{ data.score }}/100</strong> | الحالة: {{ data.status }} | الخطورة: {{ data.risk }}</p>
    <p>😶 المشاعر: {{ data.sentiment }}</p>
    <p>🕵️ الحظر: {{ data.shadow_status }} ({{ data.shadow_note }})</p>

    <div>
      <h4>⚠️ مشاكل</h4>
      {% for i in data.issues %}<p class="issues">- {{ i }}</p>{% endfor %}
      <h4>💡 حلول</h4>
      {% for f in data.fixes %}<p class="fixes">- {{ f }}</p>{% endfor %}
    </div>

    {% if data.top_words %}
    <h4>🔥 كلماتك الشائعة</h4>
    {% for w,c in data.top_words %}
      <span style="background:#334155; padding:5px 12px; border-radius:15px; margin:3px; display:inline-block;">{{ w }} ({{ c }})</span>
    {% endfor %}
    {% endif %}

    <hr>
    <small>📏 متوسط الطول: {{ data.avg_len }} | #️⃣ هاشتاغ: {{ data.hashtags }} | ❓ أسئلة: {{ data.questions }}</small>
  {% endif %}
</div>
{% endif %}
</div>

<script>
function switchTab(mode) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  if (mode === 'auto') {
    document.querySelector('.tab:nth-child(1)').classList.add('active');
    document.getElementById('auto-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'auto';
  } else {
    document.querySelector('.tab:nth-child(2)').classList.add('active');
    document.getElementById('manual-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'manual';
  }
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    form_data = {}
    if request.method == "POST":
        mode = request.form.get("mode", "auto")
        form_data = request.form.to_dict()
        if mode == "manual":
            tweets_text = request.form.get("tweets", "").strip()
            username = request.form.get("manual_username", "").strip() or "مستخدم"
            if not tweets_text:
                data = {"error": "يرجى لصق التغريدات"}
            else:
                tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
                data = analyze_full(username, tweets)
        else:
            url = request.form.get("url", "").strip()
            if not url:
                data = {"error": "أدخل رابط الحساب"}
            else:
                username = extract_username(url)
                now = time.time()
                cached = cache.get(username)
                if cached and (now - cached["time"] < CACHE_DURATION):
                    data = cached["data"]
                else:
                    xml = fetch_rss(f"/{username}/rss")
                    tweets = parse_tweets_from_rss(xml, 10)
                    if not tweets:
                        data = {"error": "تعذر جلب التغريدات (الحساب قد لا يكون موجودًا أو Nitter معطل)"}
                    else:
                        data = analyze_full(username, tweets)
                        cache[username] = {"data": data, "time": now}
    return render_template_string(HTML, data=data, form_data=form_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
