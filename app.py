import sqlite3
from flask import Flask, request, render_template, session, redirect
import models
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from database import db_session, init_db

app = Flask(__name__)
app.secret_key = 'qwefdgyhdtgfjghkghfk34678'
SPEND = 1
INCOME = 2


init_db()


# /user
@app.route('/user', methods=['GET'])
def user_handler():
    if 'user_id' not in session:
        return redirect('/login')

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = select(models.Transaction).filter_by(owner_id=session['user_id'])

    if date_from:
        query = query.filter(models.Transaction.date >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(models.Transaction.date <= datetime.strptime(date_to, '%Y-%m-%d'))

    transactions = db_session.execute(
        query.join(models.Category, models.Transaction.category_id == models.Category.id)
             .options(selectinload(models.Transaction.category))
    ).scalars().all()

    chart_data = {}
    for t in transactions:
        date_str = t.date.strftime("%Y-%m-%d")
        if date_str not in chart_data:
            chart_data[date_str] = {"income": 0, "spend": 0}

        if t.category_type == INCOME:
            chart_data[date_str]["income"] += t.amount
        else:
            chart_data[date_str]["spend"] += t.amount

    labels = list(chart_data.keys())
    incomes = [chart_data[d]["income"] for d in labels]
    spends = [chart_data[d]["spend"] for d in labels]

    return render_template(
        "user_dashboard.html",
        transactions=transactions,
        date_from=date_from,
        date_to=date_to,
        labels=labels,
        incomes=incomes,
        spends=spends
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# /login
@app.route('/login', methods=['GET', 'POST'])
def get_login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        email = request.form['email']
        password = request.form['password']
        user = db_session.execute(
            select(models.User).filter_by(email=email, password=password)
        ).scalar_one_or_none()

        if user:
            session['user_id'] = user.id
            return redirect('/user')
        else:
            error_message = "Неверный email или пароль."
            return render_template("login.html", error=error_message)


# /register
@app.route('/register', methods=['GET', 'POST'])
def get_register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        name = request.form['name']
        surname = request.form['surname']
        password = request.form['password']
        email = request.form['email']

        existing_user = db_session.execute(
            select(models.User).filter_by(email=email)
        ).scalar_one_or_none()

        if existing_user:
            return "Пользователь с таким email уже зарегистрирован", 400

        new_user = models.User(name=name, surname=surname, password=password, email=email)
        db_session.add(new_user)
        db_session.commit()
        return f" account successfully created"


# /category
@app.route('/category', methods=['GET', 'POST'])
def category_list():
    if 'user_id' in session:
        if request.method == 'GET':
            user_id = session['user_id']
            categories = list(db_session.execute(
                select(models.Category).filter(
                    (models.Category.owner_id == session['user_id']) | (models.Category.owner_id == 1)
                )
            ).scalars())
            return render_template("all_categories.html", categories=categories)
        else:
            category_name = request.form.get('category_name')
            category_owner = int(session['user_id'])

            new_category = models.Category(category_name=category_name, owner_id=category_owner)
            db_session.add(new_category)
            db_session.commit()
            return redirect('/category')


# /category/<category_id>
@app.route('/category/<int:category_id>', methods=['GET', 'POST'])
def category_detail(category_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    category = db_session.execute(
        select(models.Category).filter(
            models.Category.id == category_id,
            (models.Category.owner_id == user_id) | (models.Category.owner_id == 1)
        )
    ).scalar_one_or_none()

    if not category:
        return "Категория не найдена", 404
    if request.method == 'GET':
        return render_template(
            "one_category.html",
            category=category
        )
    else:  # POST
        if category.owner_id != user_id:
            return "У вас нет прав на редактирование этой категории.", 403
        new_name = request.form['category_name']
        category.category_name = new_name
        db_session.commit()
        return redirect('/category')


# /category/<int:category_id>/delete
@app.route('/category/<int:category_id>/delete', methods=['GET'])
def delete_category(category_id):
    if 'user_id' not in session:
        return redirect('/login')

    category_to_delete = db_session.execute(
        select(models.Category).filter_by(id=category_id, owner_id=session['user_id'])
    ).scalar_one_or_none()

    if category_to_delete:
        db_session.delete(category_to_delete)
        db_session.commit()

    return redirect("/category")


@app.route('/income', methods=['GET', 'POST'])
def get_income():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'GET':
        transactions = db_session.execute(
            select(
                models.Transaction, models.Category.category_name
            ).join(
                models.Category,
                models.Transaction.category_id == models.Category.id
            ).filter(
                models.Transaction.owner_id == session['user_id'],
                models.Transaction.category_type == INCOME
            )
        ).all()

        categories = list(db_session.execute(
            select(models.Category).filter(
                (models.Category.owner_id == session['user_id']) | (models.Category.owner_id == 1)
            )
        ).scalars())

        return render_template('dashboard.html',
                               transactions=transactions,
                               categories=categories,
                               page_type="income")
    else:  # POST
        new_transaction = models.Transaction(
            description=request.form['description'],
            category_id=int(request.form['category']),
            amount=float(request.form['amount']),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            owner_id=session['user_id'],
            category_type=INCOME
        )
        db_session.add(new_transaction)
        db_session.commit()
        return redirect('/income')


# /income/<income_id>
@app.route('/income/<int:income_id>', methods=['GET', 'POST', 'DELETE'])
def income_detail(income_id):
    transaction = db_session.get(models.Transaction, income_id)
    if not transaction or transaction.owner_id != session.get('user_id'):
        return "Транзакция не найдена", 404

    if request.method == 'GET':
        return render_template("transaction.html", transaction=transaction)
    elif request.method == 'POST':
        transaction.description = request.form['description']
        transaction.amount = float(request.form['amount'])
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        db_session.commit()
        return redirect('/income')
    elif request.method == 'DELETE':
        db_session.delete(transaction)
        db_session.commit()
        return redirect('/income')


@app.route('/spend', methods=['GET', 'POST'])
def get_spend():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'GET':
        transactions = db_session.execute(
            select(
                models.Transaction, models.Category.category_name
            ).join(
                models.Category,
                models.Transaction.category_id == models.Category.id
            ).filter(
                models.Transaction.owner_id == session['user_id'],
                models.Transaction.category_type == SPEND
            )
        ).all()

        categories = list(db_session.execute(
            select(models.Category).filter(
                (models.Category.owner_id == session['user_id']) | (models.Category.owner_id == 1)
            )
        ).scalars())

        return render_template('dashboard.html',
                               transactions=transactions,
                               categories=categories,
                               page_type="spend")
    else:  # POST
        new_transaction = models.Transaction(
            description=request.form['description'],
            category_id=int(request.form['category']),
            amount=float(request.form['amount']),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            owner_id=session['user_id'],
            category_type=SPEND
        )
        db_session.add(new_transaction)
        db_session.commit()
        return redirect('/spend')


# /spend/<spend_id>
@app.route('/spend/<int:spend_id>', methods=['GET', 'POST', 'DELETE'])
def spend_detail(spend_id):
    transaction = db_session.get(models.Transaction, spend_id)
    if not transaction or transaction.owner_id != session.get('user_id'):
        return "Транзакция не найдена", 404

    if request.method == 'GET':
        return render_template("transaction.html", transaction=transaction)
    elif request.method == 'POST':
        transaction.description = request.form['description']
        transaction.amount = float(request.form['amount'])
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        db_session.commit()
        return redirect('/spend')
    elif request.method == 'DELETE':
        db_session.delete(transaction)
        db_session.commit()
        return redirect('/spend')


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == "__main__":
    app.run(debug=True)