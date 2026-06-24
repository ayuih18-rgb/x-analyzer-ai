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
# تحليل حساب واحد
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
# مقارنة حسابات (خفيفة)
# =========================
def compare(accounts):

    sorted_acc = sorted(accounts, key=lambda x: x["score"], reverse=True)

    return {
        "winner": sorted_acc[0]["username"],
        "ranking": sorted_acc
    }

# =========================
# UI (خفيف جدًا)
# =========================
HTML = """
<div style="max-width:800px;margin:auto;font-family:Arial;background:#0f172a;color:white;padding:20px;border-radius:10px">

<h2>🧠 AI X Analyzer (Light Flask)</h2>

<!-- تحليل حساب -->
<form method="post">
<input name="url" placeholder="رابط الحساب" style="width:100%;padding:10px"><br><br>
<textarea name="tweets" placeholder="التغريدات" rows="6" style="width:100%"></textarea><br><br>
<button style="padding:10px;background:#3b82f6;color:white;border:none">تحليل</button>
</form>

<hr>

<!-- مقارنة -->
<form method="post">
<textarea name="compare" placeholder="كل حساب في سطر" rows="5" style="width:100%"></textarea><br><br>
<button style="padding:10px;background:#10b981;color:white;border:none">مقارنة</button>
</form>

{% if data %}

<hr>
<h3>👤 {{data.username}}</h3>
<p>📊 {{data.score}}</p>
<p>📌 {{data.status}}</p>
<p>📡 {{data.risk}}</p>

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

{% if compare %}

<hr>
<h3>🏆 الفائز: {{compare.winner}}</h3>

{% for acc in compare.ranking %}
<div style="background:#1f2937;padding:10px;margin:10px;border-radius:8px">
<p>👤 {{acc.username}}</p>
<p>📊 {{acc.score}}</p>
</div>
{% endfor %}

{% endif %}

</div>
"""

# =========================
# Flask App
# =========================
@app.route("/", methods=["GET", "POST"])
def home():

    data = None
    compare_result = None

    if request.method == "POST":

        # تحليل
        if request.form.get("url"):

            username = extract_username(request.form["url"])
            tweets = request.form.get("tweets", "")

            data = analyze(username, tweets)

        # مقارنة
        if request.form.get("compare"):

            urls = request.form["compare"].split("\n")

            accounts = []

            for u in urls:
                if not u.strip():
                    continue

                username = extract_username(u)

                # تحليل بسيط (بدون tweets)
                res = analyze(username, "")

                accounts.append({
                    "username": username,
                    "score": res["score"]
                })

            compare_result = compare(accounts)

    return render_template_string(HTML, data=data, compare=compare_result)

# =========================
# تشغيل Flask (Render)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
    count = len(tweets)

    if count == 0:
        return {
            "username": username,
            "total_score": 0,
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
        issues.append("محتوى ضعيف (قصير)")
        fixes.append("اكتب تغريدات أطول")

    if hashtags == 0:
        score -= 10
        issues.append("لا يستخدم هاشتاغات")
        fixes.append("استخدم هاشتاغات")

    if questions == 0:
        score -= 10
        issues.append("ضعف التفاعل")
        fixes.append("استخدم أسئلة")

    if count < 5:
        score -= 15
        issues.append("نشاط ضعيف")
        fixes.append("انشر باستمرار")

    # ===== الحالة =====
    if score >= 80:
        status = "🟢 قوي"
        risk = "منخفض 🟢"
    elif score >= 60:
        status = "🟡 متوسط"
        risk = "متوسط 🟡"
    else:
        status = "🔴 ضعيف"
        risk = "مرتفع ⚠️"

    return {
        "username": username,
        "total_score": round(score, 1),
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "top_words": word_frequency(tweets)
    }

# =========================
# مقارنة الحسابات
# =========================
def compare_accounts(accounts):

    ranked = sorted(accounts, key=lambda x: x["data"]["total_score"], reverse=True)

    return {
        "winner": ranked[0]["username"] if ranked else None,
        "ranking": [
            {
                "username": acc["username"],
                "score": acc["data"]["total_score"],
                "status": acc["data"]["status"],
                "risk": acc["data"]["risk"]
            }
            for acc in ranked
        ]
    }

# =========================
# واجهة احترافية
# =========================
HTML = """
<div style="background:#0b1220;color:white;padding:25px;border-radius:15px;font-family:Arial;max-width:900px;margin:auto">

<h2>🧠 AI X Pro Analyzer + Comparison</h2>

<form method="post">
<input name="url" placeholder="https://x.com/username" style="width:90%;padding:10px"><br><br>
<textarea name="tweets" rows="6" style="width:90%" placeholder="ضع التغريدات هنا"></textarea><br><br>
<button style="padding:10px 15px;background:#2563eb;color:white;border:none;border-radius:10px">
تحليل حساب
</button>
</form>

<hr>

<h3>🆚 مقارنة حسابات</h3>

<form method="post">
<textarea name="compare" rows="6" style="width:90%"
placeholder="كل رابط في سطر:
https://x.com/user1
https://x.com/user2"></textarea><br><br>
<button style="padding:10px 15px;background:#10b981;color:white;border:none;border-radius:10px">
مقارنة الحسابات
</button>
</form>

{% if data %}

<hr>

<h3>👤 {{data.username}}</h3>
<p>📊 Score: {{data.total_score}}</p>
<p>📌 Status: {{data.status}}</p>
<p>📡 Risk: {{data.risk}}</p>

<h3>⚠️ Issues</h3>
{% for i in data.issues %}
<p>• {{i}}</p>
{% endfor %}

<h3>💡 Fixes</h3>
{% for f in data.fixes %}
<p>• {{f}}</p>
{% endfor %}

<h3>🔥 Top Words</h3>
{% for w,c in data.top_words %}
<p>{{w}} → {{c}}</p>
{% endfor %}

{% endif %}

{% if compare %}

<hr>

<h3>🏆 Winner: {{compare.winner}}</h3>

<h3>📊 Ranking</h3>

{% for acc in compare.ranking %}
<div style="background:#1f2937;margin:10px;padding:10px;border-radius:10px">
<p>👤 {{acc.username}}</p>
<p>📊 Score: {{acc.score}}</p>
<p>📌 {{acc.status}}</p>
<p>📡 {{acc.risk}}</p>
</div>
{% endfor %}

{% endif %}

</div>
"""

# =========================
# Flask
# =========================
@app.route("/", methods=["GET", "POST"])
def home():

    data = None
    compare = None

    if request.method == "POST":

        # ===== مقارنة =====
        if "compare" in request.form and request.form["compare"].strip():

            urls = request.form["compare"].split("\n")
            accounts = []

            for url in urls:
                url = url.strip()
                if not url:
                    continue

                username = extract_username(url)

                # تحليل وهمي (لا يوجد scraping)
                dummy = analyze(username, "")

                accounts.append({
                    "username": username,
                    "data": dummy
                })

            compare = compare_accounts(accounts)

        # ===== تحليل حساب =====
        else:
            url = request.form["url"]
            username = extract_username(url)
            tweets = request.form["tweets"]

            data = analyze(username, tweets)

    return render_template_string(HTML, data=data, compare=compare)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)    tweets = [t.strip() for t in tweets_text.split("\n") if t.strip()]
    count = len(tweets)

    if count == 0:
        return {
            "username": username,
            "score": 0,
            "status": "لا توجد بيانات",
            "risk": "غير معروف",
            "issues": ["لا توجد تغريدات"],
            "fixes": ["أضف تغريدات للتحليل"],
            "top_words": []
        }

    # =====================
    # نقاط البداية
    # =====================
    score = 100
    issues = []
    fixes = []

    avg_len = sum(len(t) for t in tweets) / count
    hashtags = sum(1 for t in tweets if "#" in t)
    questions = sum(1 for t in tweets if "?" in t)

    # =====================
    # تحليل المحتوى
    # =====================
    if avg_len < 40:
        score -= 20
        issues.append("ضعف جودة المحتوى")
        fixes.append("اكتب محتوى أطول")

    if hashtags == 0:
        score -= 10
        issues.append("لا يستخدم هاشتاغات")
        fixes.append("استخدم هاشتاغات")

    if questions == 0:
        score -= 10
        issues.append("ضعف التفاعل")
        fixes.append("استخدم أسئلة")

    if count < 5:
        score -= 15
        issues.append("نشاط ضعيف")
        fixes.append("انشر باستمرار")

    # =====================
    # مؤشر المخاطر
    # =====================
    if score >= 80:
        status = "🟢 قوي"
        risk = "منخفض 🟢"
    elif score >= 60:
        status = "🟡 متوسط"
        risk = "متوسط 🟡"
    else:
        status = "🔴 ضعيف"
        risk = "مرتفع ⚠️"

    # =====================
    # الكلمات
    # =====================
    top_words = word_frequency(tweets)

    # =====================
    # تفسير ذكي
    # =====================
    insight = []
    if avg_len < 30:
        insight.append("الحساب يعتمد على محتوى قصير جدًا مما يقلل الانتشار")
    if hashtags == 0:
        insight.append("لا يستخدم استراتيجيات وصول مثل الهاشتاغ")
    if count > 10:
        insight.append("نشاط جيد لكن يحتاج تحسين جودة")

    return {
        "username": username,
        "score": max(0, score),
        "status": status,
        "risk": risk,
        "issues": issues,
        "fixes": fixes,
        "top_words": top_words,
        "insight": insight
    }

# =========================
# واجهة احترافية
# =========================
HTML = """
<div style="background:#0f172a;color:white;padding:25px;border-radius:15px;font-family:Arial;max-width:800px;margin:auto">

<h2>🧠 AI X Advanced Analyzer</h2>

<form method="post">
<input name="url" placeholder="رابط الحساب" style="width:90%;padding:10px"><br><br>
<textarea name="tweets" rows="6" style="width:90%" placeholder="ضع التغريدات"></textarea><br><br>
<button style="padding:10px 20px;background:#3b82f6;color:white;border:none;border-radius:8px">تحليل</button>
</form>

{% if data %}

<hr>

<h3>👤 {{data.username}}</h3>
<p>📊 التقييم: {{data.score}} / 100</p>
<p>📌 الحالة: {{data.status}}</p>
<p>📡 المخاطر: {{data.risk}}</p>

<h3>🧠 التحليل الذكي</h3>
{% for i in data.insight %}
<p>• {{i}}</p>
{% endfor %}

<h3>⚠️ المشاكل</h3>
{% for i in data.issues %}
<p>• {{i}}</p>
{% endfor %}

<h3>💡 الحلول</h3>
{% for f in data.fixes %}
<p>• {{f}}</p>
{% endfor %}

<h3>🔥 الكلمات الأكثر استخدامًا</h3>
{% for w,c in data.top_words %}
<p>{{w}} → {{c}}</p>
{% endfor %}

{% endif %}

</div>
"""

@app.route("/", methods=["GET","POST"])
def home():
    data = None
    if request.method == "POST":
        data = analyze(
            extract_username(request.form["url"]),
            request.form["tweets"]
        )
    return render_template_string(HTML, data=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
