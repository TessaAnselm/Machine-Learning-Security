import io
import random
import secrets

from captcha.image import ImageCaptcha
from flask import Flask, render_template_string, request, send_file, session

from model import CHARSET, CAPTCHA_LENGTH, IMG_HEIGHT, IMG_WIDTH

# This is the "victim" side of the demo: a real CAPTCHA server, not a mock. The
# attack scripts (solve.py, predict.py) target this exact server over HTTP.
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
image_captcha = ImageCaptcha(width=IMG_WIDTH, height=IMG_HEIGHT)

# Server-side answer store, keyed by an opaque token handed to the client.
# The client only ever sees the token and the rendered image, never the answer.
# This means the only way to pass /verify is to actually read the image, the
# same constraint a real-world attacker faces.
CHALLENGES = {}

PAGE = """
<!doctype html>
<title>CAPTCHA demo</title>
<h1>Prove you're human</h1>
{% if result %}<p><strong>{{ result }}</strong></p>{% endif %}
<img src="/captcha.png" alt="captcha">
<form method="post" action="/verify">
  <input name="answer" autocomplete="off" required>
  <button type="submit">Submit</button>
</form>
"""


def random_text():
    # CAPTCHA_LENGTH/CHARSET live in model.py so the server and the solver
    # always agree on what a valid CAPTCHA looks like.
    return "".join(random.choices(CHARSET, k=CAPTCHA_LENGTH))


@app.route("/")
def index():
    return render_template_string(PAGE, result=None)


@app.route("/captcha.png")
def captcha_image():
    # Every request mints a brand-new challenge and forgets the old one, so a
    # client can't just keep retrying against the same known answer.
    text = random_text()
    token = secrets.token_urlsafe(16)
    CHALLENGES[token] = text
    session["token"] = token

    buf = io.BytesIO()
    image_captcha.write(text, buf)
    buf.seek(0)
    response = send_file(buf, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/verify", methods=["POST"])
def verify():
    answer = request.form.get("answer", "")
    token = session.get("token")
    # Pop (not get): a challenge can only ever be answered once, whether right
    # or wrong, so a solved answer can't be replayed.
    expected = CHALLENGES.pop(token, None) if token else None
    correct = expected is not None and answer.strip().upper() == expected.upper()
    result = "Correct! You passed the CAPTCHA." if correct else "Incorrect. Try again."
    return render_template_string(PAGE, result=result)


if __name__ == "__main__":
    # debug=False on purpose: Flask's debugger exposes remote code execution
    # if this ever ended up reachable beyond localhost. Snyk flagged this.
    app.run(port=5000)
