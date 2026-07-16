from flask import Flask, render_template, request, redirect, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

app = Flask(__name__)
app.secret_key = "finance_tracker_secret"

@app.route("/")
def home():
    return redirect("/login")

@app.route("/dashboard", methods=["GET", "POST"])
def index():

    # User must be logged in
    if "user_id" not in session:
        return redirect("/login")

    # Add Transaction
    if request.method == "POST":

        amount = request.form["amount"]
        transaction_type = request.form["type"]
        description = request.form["description"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO transactions
            (amount, type, description, user_id)
            VALUES(%s,%s,%s,%s)
            """,
            (
                amount,
                transaction_type,
                description,
                session["user_id"]
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/dashboard")

    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get("search")
    filter_type = request.args.get("filter")

    # SEARCH + FILTER
    if search:

        cursor.execute(
            """
            SELECT *
            FROM transactions
            WHERE description LIKE %s
            AND user_id=%s
            ORDER BY id DESC
            """,
            (
                "%" + search + "%",
                session["user_id"]
            )
        )

    elif filter_type:

        cursor.execute(
            """
            SELECT *
            FROM transactions
            WHERE type=%s
            AND user_id=%s
            ORDER BY id DESC
            """,
            (
                filter_type,
                session["user_id"]
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM transactions
            WHERE user_id=%s
            ORDER BY id DESC
            """,
            (
                session["user_id"],
            )
        )

    transactions = cursor.fetchall()

    # SUMMARY

    cursor.execute(
        """
        SELECT SUM(amount)
        FROM transactions
        WHERE type='Income'
        AND user_id=%s
        """,
        (
            session["user_id"],
        )
    )

    total_income = cursor.fetchone()[0] or 0

    cursor.execute(
        """
        SELECT SUM(amount)
        FROM transactions
        WHERE type='Expense'
        AND user_id=%s
        """,
        (
            session["user_id"],
        )
    )

    total_expense = cursor.fetchone()[0] or 0

    balance = total_income - total_expense

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )
# DELETE ROUTE
@app.route("/delete/<int:id>")
def delete_transaction(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
    """
    DELETE FROM transactions
    WHERE id=%s
    AND user_id=%s
    """,
    (
        id,
        session["user_id"]
    )
)

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dashboard")

# EDIT ROUTE

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_transaction(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        amount = request.form["amount"]
        transaction_type = request.form["type"]
        description = request.form["description"]

        cursor.execute(
            """
            UPDATE transactions
            SET 
            amount=%s,
            type=%s,
            description=%s
            WHERE id=%s
            AND user_id=%s
            """,
            (
                amount,
                transaction_type,
                description,
                id,
                session["user_id"]
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/dashboard")

    cursor.execute(
    """
    SELECT *
    FROM transactions
    WHERE id=%s
    AND user_id=%s
    """,
    (
        id,
        session["user_id"]
    )
)

    transaction = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "edit.html",
        transaction=transaction
    )

# DOWNLOAD PDF 

@app.route("/download-pdf")
def download_pdf():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM transactions WHERE user_id=%s ORDER BY id DESC",
        (session["user_id"],)
    )

    transactions = cursor.fetchall()

    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE type='Income' AND user_id=%s",
        (session["user_id"],)
    )
    total_income = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE type='Expense' AND user_id=%s",
        (session["user_id"],)
    )
    total_expense = cursor.fetchone()[0] or 0

    balance = total_income - total_expense

    cursor.close()
    conn.close()

    pdf_file = tempfile.NamedTemporaryFile(
    delete=False,
    suffix=".pdf"
    ).name

    doc = SimpleDocTemplate(pdf_file)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "Personal Finance Tracker Report",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"Total Income: ₹ {total_income}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Total Expense: ₹ {total_expense}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Balance: ₹ {balance}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 20))

    for transaction in transactions:

        elements.append(
            Paragraph(
                f"""
                ID: {transaction[0]} |
                Amount: {transaction[1]} |
                Type: {transaction[2]} |
                Description: {transaction[3]}
                """,
                styles["Normal"]
            )
        )

    doc.build(elements)

    return send_file(
        pdf_file,
        as_attachment=True
    )

# SIGNUP ROUTE

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template(
                "signup.html",
                error="Passwords do not match!"
            )

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users(username, password)
                VALUES(%s,%s)
                """,
                (username, hashed_password)
            )

            conn.commit()

        except Exception:

            conn.rollback()

            return render_template(
                "signup.html",
                error="Username already exists!"
            )

        finally:

            cursor.close()
            conn.close()

        return redirect("/login")

    return render_template("signup.html")

# LOGIN ROUTE

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username=%s
            """,
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/dashboard")

        else:

           return render_template(
            "login.html",
            error="Invalid Username or Password"
            )
    return render_template("login.html")

# LOGOUT ROUTE

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )