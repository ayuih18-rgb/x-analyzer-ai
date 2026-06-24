from flask import Flask, request, render_template_string
import re
import os
import requests
import time
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ========================
# قائمة خوادم Nitter احتياطية
# ========================
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.1d4.us",
    "https://nitter.pufe.org",
    "https://nitter.moomoo.me",
]

# ========================
# كاش بسيط
# ========================
cache = {}
CACHE_DURATION = 600  # 10 دقائق لتخفيف الضغط

# ========================
# استخراج اسم المستخدم
# ========================
def extract_username(url):
    patterns = [
        r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)",
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return url.strip().lstrip("@")

# ========================
# جلب التغريدات عبر Nitter RSS
# ========================
def fetch_tweets_nitter(username, max_tweets=10):
    """
    يحاول جلب تغريدات من Nitter RSS بالتجربة عبر عدة خوادم.
    """
    for instance in NITTER_INSTANCES:
        rss_url = f"{instance}/{username}/rss"
        try:
            resp = requests.get(rss_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue
            # تحليل RSS
            root = ET.fromstring(resp.content)
            tweets = []
            for item in root.findall(".//item"):
                title = item.find("title")
                if title is not None and title.text:
                    text = title.text.strip()
                    # إزالة "username: " من البداية إن وجدت
                    if text.startswith(f"{username}:"):
                        text = text[len(f"{username}:"):].strip()
                    tweets.append(text)
                if len(tweets) >= max_tweets:
                    break
            if tweets:
                return tweets, None
        except Exception:
            continue
    return None, "تعذر جلب التغريدات تلقائياً. جرب الإدخال اليدوي."

# ========================
# تحليل المشاعر (بسيط)
# ========================
POSITIVE_WORDS = {"رائع", "ممتاز", "جميل", "حب", "سعيد", "مذهل", "شكراً", "👍", "good", "great", "love", "happy", "amazing", "thanks"}
NEGATIVE_WORDS = {"سيء", "حزين", "غضب", "يكره", "فظيع", "ممل", "فشل", "👎", "bad", "sad", "angry", "hate", "terrible", "fail"}

def analyze_sentiment(tweets):
    pos = sum(1 for t in tweets for w in t.lower().split() if w in POSITIVE_WORDS)
    neg = sum(1 for t in tweets for w in t.lower().split() if w in NEGATIVE_WORDS)
    if pos > neg:
        return "إيجابي 😊"
    elif neg > pos:
        return "سلبي 😞"
    else:
        return "محايد 😐"

# ========================
# كلمات التوقف الموسعة
# ========================
AR_STOPWORDS = {
    "في", "من", "على", "الى", "عن", "و", "ثم", "لا", "ما", "هذا", "كان", "مع", "أن", "إن", "كل", "الذي", "التي", "إذا",
    "لم", "لن", "هل", "قد", "أو", "بين", "كما", "بعد", "قبل", "حتى", "إلا", "أيضا", "هو", "هي", "هم", "نحن", "أنت", "أنا"
}
EN_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they", "them", "this", "that", "these", "those",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "up", "about", "into", "through", "during",
    "and", "but", "or", "so", "if", "then", "than", "too", "very", "can", "will", "just", "now", "not", "only"
}
STOPWORDS = AR_STOPWORDS | EN_STOPWORDS

def word_frequency(tweets):
    words = []
    for t in tweets:
        clean = re.sub(r"[^\w\s]", "", t)
        words.extend(clean.lower().split())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 1]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

# ========================
# التحليل الكامل
# ========================
def analyze(username, tweets):
    count = len(tweets)
    if count == 0:
        return {
            "username": username,
            "score": 0,
            "status": "لا بيانات",
            "risk": "غير معروف",
            "issues": ["لا توجد تغريدات"],
            "fixes": ["تأكد من وجود تغريدات حديثة"],
            "top_words": [],
            "sentiment": "غير معروف",
            "error": None
        }

    score = 100
    issues = []
    fixes = []

    avg_len = sum(len(t) for t in tweets) / count
    hashtags = sum(1 for t in tweets if "#" in t)
    questions = sum(1 for t in tweets if "?" in t)

    if avg_len < 40:
        score -= 20
        issues.append("المحتوى قصير")
        fixes.append("اكتب محتوى أطول")
    if hashtags == 0:
        score -= 10
        issues.append("لا يستخدم هاشتاغات")
        fixes.append("أضف هاشتاغات ذات صلة")
    if questions == 0:
        score -= 10
        issues.append("لا يوجد تفاعل")
        fixes.append("استخدم أسئلة لجذب المتابعين")
    if count < 5:
        score -= 15
        issues.append("نشاط ضعيف")
        fixes.append("انشر باستمرار")

    sentiment_label = analyze_sentiment(tweets)
    if "سلبي" in sentiment_label:
        score -= 10
        issues.append("مشاعر سلبية سائدة")
        fixes.append("حاول مشاركة محتوى إيجابي")

    if score >= 80:
        status = "🟢 قوي"
        risk = "منخفض"
    elif score >= 60:
        status = "🟡 متوسط"
        risk = "متوسط"
    else:
        status = "🔴 ضعيف"
        risk = "مرتفع"

    return {
        "username": username,
        "score": max(0, score),
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "top_words": word_frequency(tweets),
        "sentiment": sentiment_label,
        "error": None
    }

# ========================
# واجهة HTML (محدثة)
# ========================
HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>محلل حسابات X (بدون توكن)</title>
<style>
body { background:#0f172a; color:#e2e8f0; font-family:Arial; padding:20px; }
.container { max-width:700px; margin:auto; background:#1e293b; border-radius:15px; padding:25px; }
h1 { text-align:center; color:#38bdf8; }
.tabs { display:flex; margin-bottom:15px; }
.tab { flex:1; padding:10px; background:#334155; text-align:center; cursor:pointer; border-radius:8px 8px 0 0; }
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
</style>
</head>
<body>
<div class="container">
<h1>🧠 محلل حسابات X (مجاني)</h1>

<div class="tabs">
  <div class="tab active" onclick="switchTab('auto')">تحليل تلقائي</div>
  <div class="tab" onclick="switchTab('manual')">إدخال يدوي</div>
</div>

<form method="post">
  <div id="auto-panel" class="panel active">
    <input name="url" placeholder="رابط الحساب (x.com/username)" value="{{ request.form['url'] if request.form else '' }}">
    <input type="hidden" name="mode" value="auto">
  </div>

  <div id="manual-panel" class="panel">
    <textarea name="tweets" placeholder="الصق التغريدات هنا (كل تغريدة في سطر)" rows="6">{{ request.form['tweets'] if request.form else '' }}</textarea>
    <input name="manual_username" placeholder="اسم المستخدم (اختياري)" value="{{ request.form['manual_username'] if request.form else '' }}">
    <input type="hidden" name="mode" value="manual">
  </div>

  <button type="submit">تحليل</button>
</form>

{% if data %}
<div class="result">
  {% if data.error %}
    <div class="error">⚠️ {{ data.error }}</div>
    {% if 'يدوي' in data.error %}
      <p style="font-size:14px;">يمكنك التبديل إلى تبويب "إدخال يدوي" ولصق التغريدات.</p>
    {% endif %}
  {% else %}
    <h2>👤 @{{ data.username }}</h2>
    <p>📊 النقاط: <strong>{{ data.score }}/100</strong></p>
    <p>📌 الحالة: <span class="badge">{{ data.status }}</span> | الخطورة: <strong>{{ data.risk }}</strong></p>
    <p>😶 المشاعر: {{ data.sentiment }}</p>
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
  {% endif %}
</div>
{% endif %}
</div>

<script>
function switchTab(mode) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  if (mode === 'auto') {
    document.querySelector('.tab:first-child').classList.add('active');
    document.getElementById('auto-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'auto';
  } else {
    document.querySelector('.tab:last-child').classList.add('active');
    document.getElementById('manual-panel').classList.add('active');
    document.querySelector('input[name="mode"]').value = 'manual';
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
    if request.method == "POST":
        mode = request.form.get("mode", "auto")
        if mode == "manual":
            # إدخال يدوي
            tweets_text = request.form.get("tweets", "").strip()
            username = request.form.get("manual_username", "").strip()
            if not tweets_text:
                data = {"error": "يرجى لصق بعض التغريدات."}
                return render_template_string(HTML, data=data)
            tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
            if not username:
                username = "مستخدم"
            data = analyze(username, tweets)
        else:
            # تلقائي عبر Nitter
            url = request.form.get("url", "").strip()
            if not url:
                data = {"error": "يرجى إدخال رابط الحساب."}
                return render_template_string(HTML, data=data)
            username = extract_username(url)
            if not username:
                data = {"error": "تعذر استخراج اسم المستخدم. تأكد من الرابط."}
                return render_template_string(HTML, data=data)

            # تحقق من الكاش
            now = time.time()
            cached = cache.get(username)
            if cached and (now - cached["time"] < CACHE_DURATION):
                data = cached["data"]
            else:
                tweets, error = fetch_tweets_nitter(username)
                if error:
                    data = {"error": error, "username": username}
                else:
                    data = analyze(username, tweets)
                    cache[username] = {"data": data, "time": now}

    return render_template_string(HTML, data=data)

# ========================
# تشغيل
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
