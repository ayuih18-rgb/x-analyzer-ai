from flask import Flask, request, render_template_string
import snscrape.modules.twitter as sntwitter
from collections import Counter
import datetime

app = Flask(__name__)

# =========================
# جلب التغريدات
# =========================
def get_tweets(user, limit=120):
    tweets = []

    for i, t in enumerate(sntwitter.TwitterUserScraper(user).get_items()):
        if i >= limit:
            break

        tweets.append({
            "text": t.content,
            "likes": t.likeCount or 0,
            "retweets": t.retweetCount or 0,
            "date": t.date
        })

    return tweets


# =========================
# تحليل احترافي
# =========================
def analyze(tweets, competitor=None):

    if not tweets:
        return None

    total = len(tweets)

    likes = sum(t["likes"] for t in tweets)
    retweets = sum(t["retweets"] for t in tweets)

    avg_likes = likes / total
    avg_retweets = retweets / total

    engagement = avg_likes + avg_retweets

    # ======================
    # تحليل الوقت
    # ======================
    hours = []
    for t in tweets:
        if t["date"]:
            hours.append(t["date"].hour)

    best_hour = Counter(hours).most_common(1)[0][0] if hours else None

    # ======================
    # نقاط ضعف
    # ======================
    weaknesses = []

    if avg_likes < 5:
        weaknesses.append("ضعف كبير في جذب التفاعل")

    if avg_retweets < 1:
        weaknesses.append("المحتوى غير قابل للنشر (share)")

    if engagement < 10:
        weaknesses.append("ضعف عام في الوصول")

    # ======================
    # أفضل تغريدة
    # ======================
    best = max(tweets, key=lambda x: x["likes"])

    # ======================
    # مقارنة منافس
    # ======================
    comparison = None
    if competitor:
        comp_tweets = get_tweets(competitor, 50)
        if comp_tweets:
            comp_avg = sum(t["likes"] for t in comp_tweets) / len(comp_tweets)
            comparison = round((avg_likes / comp_avg) * 100, 2) if comp_avg else None

    return {
        "total": total,
        "avg_likes": round(avg_likes, 2),
        "avg_retweets": round(avg_retweets, 2),
        "engagement": round(engagement, 2),
        "best_hour": best_hour,
        "weaknesses": weaknesses,
        "best": best,
        "comparison": comparison
    }


# =========================
# واجهة
# =========================
HTML = """
<h2>📊 Pro X Analyzer AI</h2>

<form method="post">
<input name="user" placeholder="الحساب الأساسي">
<br><br>
<input name="comp" placeholder="حساب منافس (اختياري)">
<br><br>
<button>تحليل</button>
</form>

{% if data %}

<hr>

<h3>📊 النتائج</h3>
<p>عدد التغريدات: {{data.total}}</p>
<p>متوسط الإعجابات: {{data.avg_likes}}</p>
<p>متوسط الريتويت: {{data.avg_retweets}}</p>

<h3>🧠 نقاط الضعف</h3>
<ul>
{% for w in data.weaknesses %}
<li>⚠️ {{w}}</li>
{% endfor %}
</ul>

<h3>⏰ أفضل وقت للنشر</h3>
<p>{{data.best_hour}}:00</p>

<h3>⭐ أفضل تغريدة</h3>
<p>{{data.best.text}}</p>

<h3>📈 مقارنة المنافس</h3>
<p>{{data.comparison}} % مقارنة بالمنافس</p>

{% endif %}
"""


@app.route("/", methods=["GET","POST"])
def home():

    data = None

    if request.method == "POST":
        user = request.form["user"].split("/")[-1]
        comp = request.form.get("comp")

        tweets = get_tweets(user)
        data = analyze(tweets, comp)

    return render_template_string(HTML, data=data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
