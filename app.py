from flask import Flask, render_template, request, redirect, session, jsonify
from supabase import create_client
import os, random, string, datetime
from resend import Resend

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# 🔗 Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# 🔗 Resend (email)
resend = Resend(api_key=os.getenv("RESEND_KEY"))

# -------------------------------------------------------
# FUNÇÃO: Enviar código por email
# -------------------------------------------------------
def enviar_codigo(email, codigo):
    resend.emails.send({
        "from": os.getenv("EMAIL_SENDER"),
        "to": email,
        "subject": "Seu código de acesso",
        "html": f"<h1>Seu código é: {codigo}</h1>"
    })


# -------------------------------------------------------
# ROTA 1 – Tela inicial
# -------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------------------------------------------------
# ROTA 2 – Login
# -------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower()

        codigo = "".join(random.choices(string.digits, k=6))

        supabase.table("auth_codes").insert({
            "email": email,
            "codigo": codigo,
            "created_at": str(datetime.datetime.utcnow())
        }).execute()

        enviar_codigo(email, codigo)

        session["email_temp"] = email
        return redirect("/verificar")

    return render_template("login.html")


# -------------------------------------------------------
# ROTA 3 – Confirmar código
# -------------------------------------------------------
@app.route("/verificar", methods=["GET", "POST"])
def verificar():
    if request.method == "POST":
        email = session.get("email_temp")
        codigo_digitado = request.form["codigo"]

        result = supabase.table("auth_codes").select("*").eq("email", email).order("created_at", desc=True).limit(1).execute()

        if not result.data:
            return "Erro interno"

        codigo_real = result.data[0]["codigo"]

        if codigo_digitado != codigo_real:
            return render_template("verificar.html", erro=True)

        # Código correto → verificar usuário
        user = supabase.table("usuarios").select("*").eq("email", email).execute()

        if not user.data:
            # criar usuário trial
            hoje = datetime.date.today()
            fim_trial = hoje + datetime.timedelta(days=3)

            supabase.table("usuarios").insert({
                "email": email,
                "plano": "trial",
                "trial_start": str(hoje),
                "trial_expire": str(fim_trial),
                "trial_used": True
            }).execute()

        session["email"] = email
        return redirect("/dashboard")

    return render_template("verificar.html")


# -------------------------------------------------------
# ROTA 4 – Painel (dashboard)
# -------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    user = supabase.table("usuarios").select("*").eq("email", email).execute().data[0]

    return render_template(
        "dashboard.html",
        nome=email.split("@")[0],
        plano=user["plano"],
    )


# -------------------------------------------------------
# ROTA 5 – Top 3
# -------------------------------------------------------
@app.route("/top3")
def top3():
    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    user = supabase.table("usuarios").select("*").eq("email", email).execute().data[0]

    if user["plano"] == "trial":
        return redirect("/dashboard")

    bets = supabase.table("top3_bets").select("*").execute().data

    return render_template("top3.html", bets=bets)


# -------------------------------------------------------
# ROTA 6 – Pagamento
# -------------------------------------------------------
@app.route("/pagamento")
def pagamento():
    plano = request.args.get("plano")
    return render_template("pagamento.html", plano=plano)


# -------------------------------------------------------
# ROTA 7 – Logout
# -------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------------------------------------
# INICIAR
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
