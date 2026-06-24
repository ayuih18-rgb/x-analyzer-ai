from flask import Flask, request, render_template_string
import re
import os

app = Flask(__name__)

# =========================
# استخراج اسم الحساب
# =========================
def extract_username(url):
    match = re.search(r"x\.com/([A-Za-z0-9_]+)", url)
    return match.group(1) if match else url.strip()

# =========================
# تحليل الكلمات
# =========================
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

    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

# =========================
# تحليل الحساب
# =========================
def analyze(username, tweets_text):

    tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
    count = len(tweets)

    if count == 0:
        return {
            "username": username,
            "score": 0,
            "status": "لا بيانات",
            "risk": "غير معروف",
            "issues": ["لا توجد تغريدات"],
            "fixes": ["أضف تغريدات"],
            "top_words": []
        }

    score = 100
    issues = []
    fixes = []

    avg_len = sum(len(t) for t in tweets) / count
    hashtags = sum(1 for t in tweets if "#" in t)
    questions = sum(1 for t in tweets if "?" in t)

    # ===== تحليل =====
    if avg_len < 40:
        score -= 20
        issues.append("المحتوى قصير")
        fixes.append("اكتب محتوى أطول")

    if hashtags == 0:
        score -= 10
        issues.append("لا يستخدم هاشتاغات")
        fixes.append("أضف هاشتاغات")

    if questions == 0:
        score -= 10
        issues.append("لا يوجد تفاعل")
        fixes.append("استخدم أسئلة")

    if count < 5:
        score -= 15
        issues.append("نشاط ضعيف")
        fixes.append("انشر باستمرار")

    # ===== الحالة =====
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
        "top_words": word_frequency(tweets)
    }

# =========================
# واجهة بسيطة
# =========================
HTML = """
<div style="max-width:800px;margin:auto;font-family:Arial;background:#0f172a;color:white;padding:20px;border-radius:10px">

<h2>🧠 AI X Analyzer</h2>

<form method="post">
<input name="url" placeholder="رابط الحساب" style="width:100%;padding:10px"><br><br>
<textarea name="tweets" placeholder="التغريدات" rows="6" style="width:100%"></textarea><br><br>
<button style="padding:10px;background:#3b82f6;color:white;border:none">
تحليل
</button>
</form>

{% if data %}

<hr>

<h3>👤 {{data.username}}</h3>
<p>📊 Score: {{data.score}}</p>
<p>📌 Status: {{data.status}}</p>
<p>📡 Risk: {{data.risk}}</p>

<h4>⚠️ مشاكل</h4>
{% for i in data.issues %}
<p>- {{i}}</p>
{% endfor %}

<h4>💡 حلول</h4>
{% for f in data.fixes %}
<p>- {{f}}</p>
{% endfor %}

<h4>🔥 كلمات</h4>
{% for w,c in data.top_words %}
<p>{{w}} → {{c}}</p>
{% endfor %}

{% endif %}

</div>
"""

# =========================
# Flask Route
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    data = None

    if request.method == "POST":
        username = extract_username(request.form["url"])
        tweets = request.form.get("tweets", "")
        data = analyze(username, tweets)

    return render_template_string(HTML, data=data)

# =========================
# تشغيل السيرفر (Render)
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
