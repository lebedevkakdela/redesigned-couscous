import math
import sqlite3
import time
from flask import *
from json import *
import os
from werkzeug.security import *
from flask_login import LoginManager, login_user, login_required, UserMixin
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)  # открываем фласк
dir_path = os.path.dirname(os.path.realpath(__file__))  # находим полный путь
login_manager = LoginManager(app)  # передаем фласк в лм для корректной работы
app.secret_key = os.urandom(24)  # регистрация секретного ключа
p = os.path.join(app.root_path, 'users.db')  # путь до бд юзеров
app.config.update(dict(DATABASE=p))  # делаем легкодоступной базу
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///menu.db'  # связываение базы в алхимии
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
food = SQLAlchemy(app)  # инит алхимии


class Menu(food.Model):  # работа с бд меню
    Dish = food.Column(food.Integer, primary_key=True)
    Price = food.Column(food.String(50))


@login_manager.user_loader  # авторизация
def load_user(user_id):
    return UserLogin().fromDB(user_id, dbase)


class UserLogin(UserMixin):  #
    def fromDB(self, user_id, db):
        self.__user = db.getUser(user_id)
        return self

    def registration(self, user):
        self.__user = user
        return self

    def get_id(self):
        return str(self.__user['id'])

    def UserEmail(self, user_email):
        try:
            self.cur.execute(f"SELECT * FROM users WHERE email = {user_email} LIMIT 1")
            res = self.cur.fetchone()
            if not res:
                return False

            return res
        except:
            pass

        return False


class FDB:  # регистрация
    def __init__(self, db):
        self.__db = db
        self.cur = db.cursor()

    def addUser(self, name, email, hpsw):
        try:
            self.cur.execute(f"SELECT COUNT() as `count` FROM users WHERE email LIKE '{email}'")
            res = self.cur.fetchone()
            if res['count'] > 0:
                print("Пользователь с таким email уже существует")
                return False

            tm = math.floor(time.time())
            self.cur.execute("INSERT INTO users VALUES(NULL, ?, ?, ?, ?)", (name, email, hpsw, tm))
            self.__db.commit()
        except sqlite3.Error as e:
            print("Ошибка добавления пользователя в БД " + str(e))
            return False

        return True

    def getUser(self, user_id):
        try:
            self.cur.execute(f"SELECT * FROM users WHERE id = {user_id} LIMIT 1")
            res = self.cur.fetchone()
            if not res:
                print("Пользователь не найден")
                return False

            return res
        except sqlite3.Error as e:
            print("Ошибка получения данных из БД " + str(e))

        return False

    def UserEmail(self, email):
        try:
            self.cur.execute(f"SELECT * FROM users WHERE email = '{email}' LIMIT 1")
            res = self.cur.fetchone()
            if not res:
                print("Пользователь не найден")
                return False
            return res
        except sqlite3.Error as e:
            print("Ошибка получения данных из БД " + str(e))
        return False


@login_manager.user_loader  # подгрузка юзера из бд
def load_user(user_id):
    return UserLogin().fromDB(user_id, dbase)


def connection_db():  # цикл подключения к бд
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():  # cоединение с БД, если оно еще не установлено
    if not hasattr(g, 'link_db'):
        g.link_db = connection_db()
    return g.link_db


dbase = None


@app.before_request
def before_request():  # yстановление соединения с БД перед выполнением запроса
    global dbase
    db = get_db()
    dbase = FDB(db)


@app.route('/')  # главная
def index():
    db = get_db()
    dbase = FDB(db)
    return render_template('index.html')


@app.route("/login", methods=["POST", "GET"])  # авторизация
def login():
    if request.method == "POST":
        user = dbase.UserEmail(request.form['email'])
        if user and check_password_hash(user['psw'], request.form['psw']):  # поиск в бд
            userlogin = UserLogin().registration(user)
            login_user(userlogin)
            return redirect(url_for('index'))

        flash("Неверная пара логин/пароль", "error")

    return render_template("login.html")


@app.route("/register", methods=["POST", "GET"])  # страница регистрации
def register():
    if request.method == "POST":
        session.pop('_flashes', None)
        if len(request.form['name']) > 4 and len(request.form['email']) > 4 \
                and len(request.form['psw']) > 4 and request.form['psw'] == request.form[
            'psw2']:  # проверка данных в форме
            hash = generate_password_hash(request.form['psw'])  # генерация хеша и запись в бд
            res = dbase.addUser(request.form['name'], request.form['email'], hash)
            if res:
                flash("Вы успешно зарегистрированы", "success")
                return redirect(url_for('login'))
            else:
                flash("Ошибка при добавлении в БД", "error")
        else:
            flash("Неверно заполнены поля", "error")

    return render_template("register.html")


@app.route('/menu')  # страница меню
@login_required  # запрет на вход незалогиненным пользователям
def menu():
    data = []
    try:
        data = Menu.query.all()
    except:
        pass
    return render_template('menu.html', main=data)


@app.route('/position')  # страница местоположения
def position():
    return render_template('map.html')


@app.route('/events')  # страница актуальное
def events():
    with open(dir_path + '/news/' + "news.json", "rt", encoding="utf8") as f:
        news_list = loads(f.read())
    return render_template('events.html', news=news_list)


@app.route('/about')  # страница о нас
def about():
    return render_template('about.html')


if __name__ == '__main__':  # запуск проекта в порт
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
