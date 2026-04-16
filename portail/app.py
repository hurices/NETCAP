import sys
import os
import flask

# 🔧 rendre proxy visible
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "proxy")
    )
)

import session_manager

app = flask.Flask(__name__)


@app.route("/portail", methods=["GET", "POST"])
def portail():

    if flask.request.method == "POST":

        username = flask.request.form.get("username")
        password = flask.request.form.get("password")

        if username == "admin" and password == "1234":

            ip = flask.request.remote_addr

            print(f"[LOGIN] IP authentifiée: {ip}")

            session_manager.create_session(ip)

            redirect_url = flask.request.args.get("redirect_url")

            if redirect_url:
                return flask.redirect(redirect_url)

            return "Authentifié"

        return "Erreur login"

    return flask.render_template("login.html")


if __name__ == "__main__":
    app.run(port=5000)