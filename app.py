import os
import uuid
from datetime import date
from pathlib import Path
from io import BytesIO
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
COURSES = range(1, 7)
DEGREES = ("Бакалавриат", "Специалитет", "Магистратура")

# Примерные данные, которыми заполняется профиль нового пользователя
DEFAULT_PROFILE = {
    "first_name": "Иван",
    "last_name": "Петров",
    "city": "Москва",
    "birthday": "2005-09-01",
    "phone": "+7 999 000-00-00",
    "about": "Студент Московского технологического института.",
    "institute": "Институт информационных технологий",
    "direction": "09.03.01 Информатика и вычислительная техника",
    "specialization": "Веб-разработка",
    "course": 1,
    "degree": "Бакалавриат",
}

# Заглушки для главной страницы личного кабинета
DEMO_SCHEDULE = {
    "Пн": [
        {"time": "09:00 – 10:30", "title": "Математический анализ", "kind": "Лекция", "room": "А-301", "teacher": "Смирнова Е. А."},
        {"time": "10:40 – 12:10", "title": "Программирование на Python", "kind": "Практика", "room": "Б-214", "teacher": "Кузнецов Д. В."},
        {"time": "12:40 – 14:10", "title": "Английский язык", "kind": "Семинар", "room": "В-105", "teacher": "Орлова М. С."},
    ],
    "Вт": [
        {"time": "10:40 – 12:10", "title": "Дискретная математика", "kind": "Лекция", "room": "А-204", "teacher": "Волков А. Н."},
        {"time": "12:40 – 14:10", "title": "Базы данных", "kind": "Лабораторная", "room": "Б-310", "teacher": "Соколова И. П."},
    ],
    "Ср": [
        {"time": "09:00 – 10:30", "title": "История России", "kind": "Лекция", "room": "Актовый зал", "teacher": "Морозов П. К."},
        {"time": "10:40 – 12:10", "title": "Программирование на Python", "kind": "Лекция", "room": "А-301", "teacher": "Кузнецов Д. В."},
        {"time": "12:40 – 14:10", "title": "Физическая культура", "kind": "Практика", "room": "Спортзал", "teacher": "Егоров С. В."},
    ],
    "Чт": [
        {"time": "10:40 – 12:10", "title": "Веб-разработка", "kind": "Практика", "room": "Б-214", "teacher": "Лебедева А. Р."},
        {"time": "12:40 – 14:10", "title": "Математический анализ", "kind": "Семинар", "room": "А-118", "teacher": "Смирнова Е. А."},
    ],
    "Пт": [
        {"time": "09:00 – 10:30", "title": "Базы данных", "kind": "Лекция", "room": "А-301", "teacher": "Соколова И. П."},
    ],
    "Сб": [],
}

DEMO_MESSAGES = [
    {"from": "Кузнецов Д. В.", "role": "Преподаватель", "text": "Напоминаю: лабораторную №3 нужно сдать до пятницы.", "time": "10:24", "unread": True},
    {"from": "Деканат ИИТ", "role": "Администрация", "text": "Расписание сессии опубликовано в разделе «Документы».", "time": "Вчера", "unread": True},
    {"from": "Староста группы", "role": "Студент", "text": "Завтра пара по английскому переносится в В-107.", "time": "Вчера", "unread": False},
    {"from": "Библиотека МТИ", "role": "Сервис", "text": "Срок возврата книги «Алгоритмы» истекает через 3 дня.", "time": "Пн", "unread": False},
]

DEMO_GRADES = [
    {"subject": "Математический анализ", "grade": 5, "note": "Контрольная работа №2"},
    {"subject": "Программирование на Python", "grade": 5, "note": "Лабораторная №2"},
    {"subject": "Дискретная математика", "grade": 4, "note": "Домашнее задание"},
    {"subject": "Английский язык", "grade": 4, "note": "Эссе"},
    {"subject": "История России", "grade": 3, "note": "Тест по разделу 1"},
]

DEMO_NEWS = [
    {"date": "25 сентября", "title": "Открыта запись в студенческие клубы", "text": "Робототехника, киберспорт, дебаты и ещё 20 направлений."},
    {"date": "22 сентября", "title": "Хакатон МТИ пройдёт в октябре", "text": "Команды до 4 человек, призовой фонд — 300 000 ₽."},
    {"date": "18 сентября", "title": "Новая коворкинг-зона в корпусе Б", "text": "Работает ежедневно с 8:00 до 21:00."},
]

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'site.db'}"
).replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "0") == "1"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    birthday = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    about = db.Column(db.Text, nullable=True)
    institute = db.Column(db.String(200), nullable=True)
    direction = db.Column(db.String(200), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    course = db.Column(db.Integer, nullable=True)
    degree = db.Column(db.String(40), nullable=True)
    photo_data = db.Column(db.LargeBinary, nullable=True)
    photo_mimetype = db.Column(db.String(100), nullable=True)

    @property
    def display_name(self):
        full = " ".join(filter(None, [self.first_name, self.last_name])).strip()
        return full or self.email.split("@")[0]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Сначала войдите в аккаунт.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_profile_photo(file_storage, user):
    if not file_storage or not file_storage.filename:
        return

    if not allowed_file(file_storage.filename):
        raise ValueError("Можно загружать только JPG, JPEG, PNG или WebP.")

    mimetype = (file_storage.mimetype or "").lower()
    if mimetype not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Файл должен быть изображением JPG, PNG или WebP.")

    data = file_storage.read()
    if not data:
        raise ValueError("Файл фотографии пустой.")
    if len(data) > MAX_UPLOAD_SIZE:
        raise ValueError("Файл слишком большой. Максимальный размер — 5 МБ.")

    user.photo_data = data
    user.photo_mimetype = mimetype


@app.template_filter("ru_date")
def ru_date(value):
    parts = (value or "").split("-")
    return ".".join(reversed(parts)) if len(parts) == 3 else value


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    if not current_user():
        return render_template("index.html")

    today = WEEKDAYS[date.today().weekday()]
    grades = [g["grade"] for g in DEMO_GRADES]
    return render_template(
        "index.html",
        schedule=DEMO_SCHEDULE,
        today=today if today in DEMO_SCHEDULE else "Пн",
        messages=DEMO_MESSAGES,
        unread=sum(m["unread"] for m in DEMO_MESSAGES),
        grades=DEMO_GRADES,
        average=round(sum(grades) / len(grades), 2),
        news=DEMO_NEWS,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_repeat = request.form.get("password_repeat", "")

        if not email or "@" not in email:
            flash("Введите корректный email.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Пароль должен содержать минимум 6 символов.", "danger")
            return render_template("register.html")
        if password != password_repeat:
            flash("Пароли не совпадают.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже существует.", "danger")
            return render_template("register.html")

        user = User(email=email, password_hash=generate_password_hash(password), **DEFAULT_PROFILE)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Аккаунт создан. Профиль заполнен примерными данными — изменить их можно в настройках.", "success")
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "danger")
            return render_template("login.html")

        session["user_id"] = user.id
        flash("Вы вошли в аккаунт.", "success")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user())


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", user=current_user())


@app.route("/settings/profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = current_user()

    if request.method == "POST":
        for field in ("first_name", "last_name", "city", "birthday", "phone", "about",
                      "institute", "direction", "specialization"):
            setattr(user, field, request.form.get(field, "").strip() or None)

        degree = request.form.get("degree", "")
        user.degree = degree if degree in DEGREES else None

        course = request.form.get("course", "").strip()
        user.course = int(course) if course.isdigit() and int(course) in COURSES else None

        try:
            save_profile_photo(request.files.get("photo"), user)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("edit_profile.html", user=user, courses=COURSES, degrees=DEGREES)

        db.session.commit()
        flash("Профиль сохранён.", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user, courses=COURSES, degrees=DEGREES)


@app.route("/profile/photo")
@login_required
def profile_photo():
    user = current_user()
    if not user.photo_data:
        return ("", 404)
    return send_file(
        BytesIO(user.photo_data),
        mimetype=user.photo_mimetype or "application/octet-stream",
        max_age=3600,
    )


@app.errorhandler(413)
def file_too_large(_):
    flash("Файл слишком большой. Максимальный размер — 5 МБ.", "danger")
    return redirect(request.referrer or url_for("edit_profile"))


def add_missing_columns():
    # db.create_all() не добавляет новые колонки в уже существующую таблицу
    existing = {col["name"] for col in inspect(db.engine).get_columns("user")}
    with db.engine.begin() as conn:
        for column in User.__table__.columns:
            if column.name not in existing:
                col_type = column.type.compile(dialect=db.engine.dialect)
                conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {column.name} {col_type}'))


with app.app_context():
    db.create_all()
    add_missing_columns()
    User.query.filter(User.degree.is_(None)).update({"degree": DEFAULT_PROFILE["degree"]})
    db.session.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
