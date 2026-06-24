From flask import Flask, request, render_template_string
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

# =========================
# جلب التغريدات من الصفحة مباشرة
# =========================
def scrape_tweets(url):

    tweets = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        content = page.content()

        # استخراج نصوص تقريبية (بسيط لكن عملي)
        texts = re.findall(r'"text":"(.*?)"', content)

        for t in texts[:30]:
            tweets.append(t)

        browser.close()

    return tweets


# =========================
# تحليل ذكي
# =========================
def analyze(tweets):

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
