from flask import Flask, request, render_template_string
import re
import os
import requests
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

app = Flask(__name__)

# ========================
# خوادم Nitter احتياطية
# ========================
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.1d4.us",
    "https://nitter.pufe.org",
    "https://nitter.moomoo.me",
]

# ========================
# كاش
# ========================
cache = {}
CACHE_DURATION = 600

# ========================
# دوال RSS
# ========================
def fetch_rss(url, timeout=10):
    """تجربة جميع الخوادم وإرجاع المحتوى XML أو None"""
    for instance in NITTER_INSTANCES:
        full_url = instance + url
        try:
            resp = requests.get(full_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.content) > 100:
                return resp.content
        except:
            continue
    return None

def parse_tweets_from_rss(xml_content, max_items=10):
    """استخراج قائمة التغريدات من XML"""
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
    # دعم الروابط المختلفة
    patterns = [
        r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)",
        r"@?([A-Za-z0-9_]{4,})"  # احتياط: اسم مستخدم صريح (4 أحرف على الأقل)
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return url.lstrip("@")

# ========================
# تحليل النصوص
# ========================
POSITIVE_WORDS = {"رائع","ممتاز","جميل","حب","سعيد","مذهل","شكراً","👍","good","great","love","happy","amazing","thanks"}
NEGATIVE_WORDS = {"سيء","حزين","غضب","يكره","فظيع","ممل","فشل","👎","bad","sad","angry","hate","terrible","fail"}

def analyze_sentiment(tweets):
    pos = sum(1 for t in tweets for w in t.lower().split() if w in POSITIVE_WORDS)
    neg = sum(1 for t in tweets for w in t.lower().split() if w in NEGATIVE_WORDS)
    if pos > neg: return "إيجابي 😊"
    elif neg > pos: return "سلبي 😞"
    else: return "محايد 😐"

AR_STOPWORDS = {"في","من","على","الى","عن","و","ثم","لا","ما","هذا","كان","مع","أن","إن","كل","الذي","التي","إذا","لم","لن","هل","قد","أو","بين","كما","بعد","قبل","حتى","إلا","أيضا","هو","هي","هم","نحن","أنت","أنا"}
EN_STOPWORDS = {"a","an","the","is","are","was","were","be","been","being","have","has","had","do","does","did","i","me","my","we","our","you","your","he","she","it","they","them","this","that","these","those","to","of","in","for","on","with","at","by","from","up","about","into","through","during","and","but","or","so","if","then","than","too","very","can","will","just","now","not","only"}
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
# فحص الحظر المخفي
# ========================
def check_shadowban(username):
    direct_xml = fetch_rss(f"/{username}/rss")
    direct_tweets = parse_tweets_from_rss(direct_xml, 10)

    search_xml = fetch_rss(f"/search/rss?f=tweets&q=from%3A{username}")
    search_tweets = parse_tweets_from_rss(search_xml, 10)

    if len(direct_tweets) == 0:
        return "غير معروف", "لا توجد تغريدات"
    if len(search_tweets) == 0:
        return "🔴 حظر مخفي محتمل", "تغريداتك لا تظهر في البحث"
    elif len(search_tweets) < len(direct_tweets) * 0.5:
        return "🟡 حظر جزئي", "بعض التغريدات لا تظهر"
    else:
        return "🟢 طبيعي", "تغريداتك تظهر في البحث"

# ========================
# البحث عن حسابات مشابهة
# ========================
def find_similar_accounts(keyword, exclude_user):
    query = f"/search/rss?f=users&q={quote(keyword)}"
    xml_content = fetch_rss(query)
    if not xml_content:
        return []
    root = ET.fromstring(xml_content)
    users = []
    for item in root.findall(".//item"):
        title = item.find("title")
        if title is not None:
            uname = title.text.strip().lstrip("@")
            if uname.lower() != exclude_user.lower() and len(uname) >= 4:
                users.append(uname)
                if len(users) >= 2:
                    break
    return users

def compare_accounts(main_stats, similar_usernames):
    comparisons = []
    for uname in similar_usernames:
        xml = fetch_rss(f"/{uname}/rss")
        tweets = parse_tweets_from_rss(xml, 10)
        if not tweets:
            continue
        avg_len = sum(len(t) for t in tweets) / len(tweets)
        hashtags = sum(1 for t in tweets if "#" in t)
        questions = sum(1 for t in tweets if "?" in t)
        sentiment = analyze_sentiment(tweets)
        top_words = word_frequency(tweets, 3)
        comparisons.append({
            "username": uname,
            "avg_len": round(avg_len, 1),
            "hashtags": hashtags,
            "questions": questions,
            "sentiment": sentiment,
            "top_words": top_words,
        })
    return comparisons

# ========================
# التحليل الشامل
# ========================
def analyze_full(username, tweets, do_compare=False):
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

    # فحص الحظر
    shadow_status, shadow_note = check_shadowban(username)
    if "مخفي" in shadow_status:
        score -= 25
        issues.append(f"حظر: {shadow_note}")
        fixes.append("راجع سياسات المنصة وتفاعل بشكل طبيعي")

    top_words = word_frequency(tweets)
    main_stats = {
        "username": username,
        "score": max(0, score),
        "avg_len": round(avg_len, 1),
        "hashtags": hashtags,
        "questions": questions,
        "sentiment": sentiment,
        "shadow_status": shadow_status,
        "shadow_note": shadow_note,
    }

    comparison = None
    if do_compare and top_words:
        keywords = [w for w, _ in top_words[:2] if len(w) > 2]
        similar = []
        for kw in keywords:
            similar += find_similar_accounts(kw, username)
        similar = list(dict.fromkeys(similar))[:2]
        if similar:
            comp_data = compare_accounts(main_stats, similar)
            if comp_data:
                comparison = comp_data
                for comp in comp_data:
                    if comp['avg_len'] > main_stats['avg_len'] + 10:
                        fixes.append(f"متوسط طول تغريداتك أقل من @{comp['username']}، حاول زيادة التفاصيل")
                    if comp['hashtags'] > main_stats['hashtags']:
                        fixes.append(f"استخدم هاشتاغات أكثر مثل @{comp['username']}")

    if score >= 80: status, risk = "🟢 قوي", "منخفض"
    elif score >= 60: status, risk = "🟡 متوسط", "متوسط"
    else: status, risk = "🔴 ضعيف", "مرتفع"

    return {
        "username": username,
        "score": score,
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": list(set(fixes)),
        "top_words": top_words,
        "sentiment": sentiment,
        "shadow_status": shadow_status,
        "shadow_note": shadow_note,
        "comparison": comparison,
    }

# ========================
# واجهة HTML
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
.badge { padding:5px 10px; border-radius:20px; font-weight:bold; }
.issues { color:#f87171; }
.fixes { color:#4ade80; }
.error { color:#facc15; background:#422006; padding:10px; border-radius:5px; }
table { width:100%; border-collapse:collapse; margin:10px 0; }
th, td { padding:8px; border-bottom:1px solid #334155; text-align:center; }
</style>
</head>
<body>
<div class="container">
<h1>🧠 محلل X متقدم</h1>

<div class="tabs">
  <div class="tab active" onclick="switchTab('auto')">تحليل تلقائي</div>
  <div class="tab" onclick="switchTab('manual')">إدخال يدوي</div>
  <div class="tab" onclick="switchTab('deep')">تحليل متقدم (مقارنة)</div>
</div>

<form method="post">
  <div id="auto-panel" class="panel active">
    <input name="url" placeholder="رابط الحساب (x.com/username)" value="{{ form_data.get('url', '')|e }}">
    <input type="hidden" name="mode" value="auto">
  </div>

  <div id="manual-panel" class="panel">
    <textarea name="tweets" placeholder="الصق التغريدات (كل سطر تغريدة)" rows="6">{{ form_data.get('tweets', '')|e }}</textarea>
    <input name="manual_username" placeholder="اسم المستخدم (اختياري)" value="{{ form_data.get('manual_username', '')|e }}">
    <input type="hidden" name="mode" value="manual">
  </div>

  <div id="deep-panel" class="panel">
    <input name="deep_url" placeholder="رابط الحساب للمقارنة المتقدمة" value="{{ form_data.get('deep_url', '')|e }}">
    <input type="hidden" name="mode" value="deep">
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

    {% if data.comparison %}
    <h4>🔄 مقارنة مع حسابات مشابهة</h4>
    <table>
      <tr><th>الحساب</th><th>متوسط الطول</th><th>هاشتاغات</th><th>أسئلة</th><th>المشاعر</th></tr>
      <tr>
        <td>@{{ data.username }}</td>
        <td>{{ data.avg_len }}</td>
        <td>{{ data.hashtags }}</td>
        <td>{{ data.questions }}</td>
        <td>{{ data.sentiment }}</td>
      </tr>
      {% for comp in data.comparison %}
      <tr>
        <td>@{{ comp.username }}</td>
        <td>{{ comp.avg_len }}</td>
        <td>{{ comp.hashtags }}</td>
        <td>{{ comp.questions }}</td>
        <td>{{ comp.sentiment }}</td>
      </tr>
      {% endfor %}
    </table>
    {% endif %}
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
  } else if (mode === 'manual') {
    document.querySelector('.tab:nth-child(2)').classList.add('active');
    document.getElementById('manual-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'manual';
  } else {
    document.querySelector('.tab:nth-child(3)').classList.add('active');
    document.getElementById('deep-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'deep';
  }
}
</script>
</body>
</html>
"""

# ========================
# المسار الرئيسي
# ========================
@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    form_data = {}
    if request.method == "POST":
        mode = request.form.get("mode", "auto")
        form_data = request.form.to_dict()  # حفظ المدخلات لإعادة تعبئتها
        if mode == "manual":
            tweets_text = request.form.get("tweets", "").strip()
            username = request.form.get("manual_username", "").strip() or "مستخدم"
            if not tweets_text:
                data = {"error": "يرجى لصق التغريدات"}
            else:
                tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
                data = analyze_full(username, tweets)
        elif mode == "deep":
            url = request.form.get("deep_url", "").strip()
            if not url:
                data = {"error": "أدخل رابط الحساب"}
            else:
                username = extract_username(url)
                xml = fetch_rss(f"/{username}/rss")
                tweets = parse_tweets_from_rss(xml, 10)
                if not tweets:
                    data = {"error": "تعذر جلب التغريدات"}
                else:
                    data = analyze_full(username, tweets, do_compare=True)
        else:  # auto
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
                        data = {"error": "تعذر جلب التغريدات"}
                    else:
                        data = analyze_full(username, tweets)
                        cache[username] = {"data": data, "time": now}
    return render_template_string(HTML, data=data, form_data=form_data)

# ========================
# تشغيل
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
