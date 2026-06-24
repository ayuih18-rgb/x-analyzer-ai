from flask import Flask, request, render_template_string
import re
import os

app = Flask(__name__)

# =========================
# الدوال المساعدة
# =========================
def extract_username(url):
    match = re.search(r"x\.com/([A-Za-z0-9_]+)", url)
    return match.group(1) if match else url.strip()

def word_frequency(tweets):
    words = []
    for t in tweets:
        clean = re.sub(r"[^\w\s]", "", t)
        words.extend(clean.lower().split())
    stopwords = {"في","من","على","الى","عن","و","a","an","the","is","are","to"}
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:6]

# =========================
# التحليل الذكي
# =========================
def analyze(username, tweets_text):
    tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
    count = len(tweets)
    
    if count == 0:
        return {"username": username, "score": 0, "status": "لا بيانات", "risk": "غير معروف", "issues": ["لا توجد تغريدات"], "fixes": [], "top_words": []}

    score = 85
    issues = []
    fixes = []
    avg_len = sum(len(t) for t in tweets) / count
    
    if avg_len < 40: score -= 15; issues.append("محتوى قصير"); fixes.append("اكتب أكثر")
    
    risk = "منخفض 🟢"
    status = "🟢 قوي" if score >= 80 else "🟡 متوسط"
    
    return {
        "username": username,
        "score": score,
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "top_words": word_frequency(tweets)
    }

# =========================
# واجهة الويب
# =========================
HTML = """
<div style="background:#111827; color:white; padding:20px; border-radius:15px; text-align:center;">
<h2>🧠 AI X Analyzer</h2>
<form method="post">
<input name="url" placeholder="رابط الحساب"><br>
<textarea name="tweets" rows="5" placeholder="التغريدات هنا"></textarea><br>
<button type="submit">تحليل</button>
</form>
{% if data %}
<p>التقييم: {{data.score}}</p>
<p>الحالة: {{data.status}}</p>
{% endif %}
</div>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    if request.method == "POST":
        data = analyze(extract_username(request.form["url"]), request.form["tweets"])
    return render_template_string(HTML, data=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# التحليل الذكي
# =========================
def analyze(username, tweets_text):

    tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
    count = len(tweets)

    score = 85
    issues = []
    fixes = []

    if count == 0:
        score -= 30
        issues.append("لا توجد تغريدات للتحليل")
        fixes.append("أضف تغريدات لتحليل أدق")

    avg_len = sum(len(t) for t in tweets) / count if count else 0

    hashtags = sum(1 for t in tweets if "#" in t)
    questions = sum(1 for t in tweets if "?" in t)

    # 🔻 جودة المحتوى
    if avg_len < 40:
        score -= 15
        issues.append("ضعف في جودة المحتوى")
        fixes.append("اكتب تغريدات أطول وأكثر وضوحًا")

    # 🔻 التفاعل
    if hashtags == 0:
        score -= 10
        issues.append("لا يستخدم هاشتاغات")
        fixes.append("استخدم هاشتاغات لزيادة الوصول")

    if questions == 0:
        score -= 10
        issues.append("لا يوجد تفاعل مع الجمهور")
        fixes.append("استخدم أسئلة لزيادة التفاعل")

    # 🔻 النشاط
    if count < 5:
        score -= 15
        issues.append("نشاط ضعيف")
        fixes.append("انشر بشكل مستمر يوميًا")

    # 📡 مؤشر الانتشار
    risk = "منخفض 🟢"

    if score < 60:
        risk = "مرتفع ⚠️"
    elif score < 75:
        risk = "متوسط 🟡"

    # 🔥 الكلمات الأكثر تكرارًا
    top_words = word_frequency(tweets)

    # 🧠 النتيجة النهائية
    if score >= 80:
        status = "🟢 حساب قوي"
    elif score >= 60:
        status = "🟡 حساب متوسط"
    else:
        status = "🔴 حساب ضعيف"

    fixes.extend([
        "راقب الترندات يوميًا",
        "تفاعل مع الحسابات المشابهة",
        "حافظ على أسلوب واضح"
    ])

    return {
        "username": username,
        "score": max(0, score),
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "top_words": top_words
    }

# =========================
# واجهة احترافية (Dashboard)
# =========================
HTML = """
<style>
body {
    font-family: Arial;
    background: #0f172a;
    color: white;
    text-align: center;
}

.container {
    max-width: 750px;
    margin: auto;
    background: #111827;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 0 20px black;
}

input, textarea {
    width: 90%;
    padding: 10px;
    margin: 10px;
    border-radius: 10px;
    border: none;
}

button {
    padding: 10px 20px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 10px;
    cursor: pointer;
}

button:hover {
    background: #2563eb;
}

.box {
    background: #1f2937;
    padding: 12px;
    margin-top: 10px;
    border-radius: 10px;
}
</style>

<div class="container">

<h2>🧠 AI X Super Analyzer</h2>

<form method="post">
<input name="url" placeholder="https://x.com/username"><br>
<textarea name="tweets" rows="8" placeholder="ضع التغريدات (كل تغريدة في سطر)"></textarea><br>
<button>تحليل احترافي</button>
</form>

{% if data %}

<div class="box">
<h3>👤 {{data.username}}</h3>
<p>📊 التقييم: {{data.score}} / 100</p>
<p>📌 الحالة: {{data.status}}</p>
<p>📡 مؤشر الانتشار: {{data.risk}}</p>
</div>

<div class="box">
<h3>⚠️ المشاكل</h3>
{% for i in data.issues %}
<p>• {{i}}</p>
{% endfor %}
</div>

<div class="box">
<h3>💡 الحلول</h3>
{% for f in data.fixes %}
<p>• {{f}}</p>
{% endfor %}
</div>

<div class="box">
<h3>🔥 أكثر الكلمات استخدامًا</h3>
{% for w, c in data.top_words %}
<p>{{w}} → {{c}}</p>
{% endfor %}
</div>

{% endif %}

</div>
"""

# =========================
# Flask App
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    data = None

    if request.method == "POST":
        url = request.form["url"]
        username = extract_username(url)
        tweets = request.form["tweets"]

        data = analyze(username, tweets)

    return render_template_string(HTML, data=data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)def analyze(tweets):

    if not tweets:
        return None

    total = len(tweets)

    lengths = [len(t) for t in tweets]
    avg_len = sum(lengths) / total

    short = sum(1 for t in tweets if len(t) < 40)

    score = 100
    issues = []
    fixes = []

    if avg_len < 50:
        score -= 20
        issues.append("المحتوى ضعيف أو قصير")
        fixes.append("اكتب تغريدات أطول وأكثر شرحًا")

    if short > total * 0.5:
        score -= 25
        issues.append("أكثر من نصف المحتوى ضعيف جدًا")
        fixes.append("ركز على محتوى قيم وليس قصير")

    if total < 10:
        score -= 15
        issues.append("عدد التغريدات قليل")

    # مؤشر ضعف الانتشار
    risk = "منخفض 🟢"
    if score < 60:
        risk = "مرتفع ⚠️"

    return {
        "total": total,
        "score": max(0, score),
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "sample": tweets[:3]
    }


# =========================
# واجهة
# =========================
HTML = """
<h2>🧠 AI X Live Analyzer (Browser Mode)</h2>

<form method="post">
<input name="url" placeholder="https://x.com/username"><br><br>
<button>تحليل مباشر</button>
</form>

{% if data %}

<hr>

<p>📊 عدد التغريدات: {{data.total}}</p>
<p>📈 التقييم: {{data.score}} / 100</p>
<p>⚠️ مستوى الخطر: {{data.risk}}</p>

<h3>⚠️ المشاكل</h3>
<ul>
{% for i in data.issues %}
<li>{{i}}</li>
{% endfor %}
</ul>

<h3>💡 الحلول</h3>
<ul>
{% for f in data.fixes %}
<li>{{f}}</li>
{% endfor %}
</ul>

<h3>🧾 أمثلة من التغريدات</h3>
<ul>
{% for s in data.sample %}
<li>{{s}}</li>
{% endfor %}
</ul>

{% endif %}
"""


@app.route("/", methods=["GET","POST"])
def home():

    data = None

    if request.method == "POST":
        url = request.form["url"]
        tweets = scrape_tweets(url)
        data = analyze(tweets)

    return render_template_string(HTML, data=data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
