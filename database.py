import sqlite3
import hashlib
import datetime
import csv
import os

class Database:
    def __init__(self, db_name="birthdays.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        # Таблица контактов (дни рождения)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                photo_path TEXT,
                emoji TEXT DEFAULT '🎂',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        # Таблица настроек напоминаний
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                reminder_days INTEGER DEFAULT 7,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()

    # ----- Методы для пользователей -----
    def add_user(self, username, password, role="user"):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed, role)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, username):
        self.cursor.execute(
            "SELECT id, username, password, role FROM users WHERE username = ?",
            (username,)
        )
        return self.cursor.fetchone()

    def get_all_users(self):
        self.cursor.execute("SELECT id, username, role FROM users")
        return self.cursor.fetchall()

    def delete_user(self, user_id):
        self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()

    def update_user_password(self, user_id, new_password):
        hashed = hashlib.sha256(new_password.encode()).hexdigest()
        self.cursor.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hashed, user_id)
        )
        self.conn.commit()

    # ----- Методы для контактов -----
    def add_contact(self, user_id, name, birth_date, phone="", email="", photo_path="", emoji="🎂"):
        self.cursor.execute('''
            INSERT INTO contacts (user_id, name, birth_date, phone, email, photo_path, emoji)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, birth_date, phone, email, photo_path, emoji))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_contact(self, contact_id, user_id, name, birth_date, phone, email, photo_path, emoji):
        self.cursor.execute('''
            UPDATE contacts
            SET name=?, birth_date=?, phone=?, email=?, photo_path=?, emoji=?
            WHERE id=? AND user_id=?
        ''', (name, birth_date, phone, email, photo_path, emoji, contact_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_contact(self, contact_id, user_id):
        self.cursor.execute(
            "DELETE FROM contacts WHERE id=? AND user_id=?",
            (contact_id, user_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_all_contacts(self, user_id):
        self.cursor.execute(
            "SELECT id, name, birth_date, phone, email, photo_path, emoji FROM contacts WHERE user_id=? ORDER BY name",
            (user_id,)
        )
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'name': r[1], 'birth_date': r[2], 'phone': r[3],
                 'email': r[4], 'photo_path': r[5], 'emoji': r[6]} for r in rows]

    def get_contact_by_id(self, contact_id, user_id):
        self.cursor.execute(
            "SELECT id, name, birth_date, phone, email, photo_path, emoji FROM contacts WHERE id=? AND user_id=?",
            (contact_id, user_id)
        )
        r = self.cursor.fetchone()
        if r:
            return {'id': r[0], 'name': r[1], 'birth_date': r[2], 'phone': r[3],
                    'email': r[4], 'photo_path': r[5], 'emoji': r[6]}
        return None

    # ----- Настройки напоминаний -----
    def get_reminder_days(self, user_id):
        self.cursor.execute(
            "SELECT reminder_days FROM settings WHERE user_id=?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return row[0]
        else:
            # Создаём настройки по умолчанию
            self.cursor.execute(
                "INSERT INTO settings (user_id, reminder_days) VALUES (?, ?)",
                (user_id, 7)
            )
            self.conn.commit()
            return 7

    def set_reminder_days(self, user_id, days):
        self.cursor.execute(
            "UPDATE settings SET reminder_days=? WHERE user_id=?",
            (days, user_id)
        )
        self.conn.commit()

    # ----- Вспомогательные расчёты -----
    @staticmethod
    def calculate_age(birth_date_str):
        today = datetime.date.today()
        birth = datetime.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        age = today.year - birth.year
        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1
        return age

    @staticmethod
    def days_until_next_birthday(birth_date_str):
        today = datetime.date.today()
        birth = datetime.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        # Следующий день рождения в этом году
        next_birthday = birth.replace(year=today.year)
        if next_birthday < today:
            next_birthday = birth.replace(year=today.year + 1)
        delta = (next_birthday - today).days
        return delta

    def get_upcoming_birthdays(self, user_id, days_ahead):
        contacts = self.get_all_contacts(user_id)
        upcoming = []
        today = datetime.date.today()
        for c in contacts:
            days = self.days_until_next_birthday(c['birth_date'])
            if days <= days_ahead:
                upcoming.append({
                    'name': c['name'],
                    'birth_date': c['birth_date'],
                    'days_left': days,
                    'age_next': self.calculate_age(c['birth_date']) + 1
                })
        # Сортируем по количеству дней
        upcoming.sort(key=lambda x: x['days_left'])
        return upcoming

    def export_to_csv(self, user_id, filename):
        contacts = self.get_all_contacts(user_id)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Имя', 'Дата рождения', 'Телефон', 'Email', 'Эмодзи', 'Фото'])
            for c in contacts:
                writer.writerow([c['id'], c['name'], c['birth_date'],
                                 c['phone'], c['email'], c['emoji'], c['photo_path']])

    def close(self):
        self.conn.close()


class AuthManager:
    def __init__(self, db):
        self.db = db
        self.create_default_admin()

    def create_default_admin(self):
        if not self.db.get_user("admin"):
            self.db.add_user("admin", "admin123", "admin")

    def login(self, username, password):
        user = self.db.get_user(username)
        if user:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if user[2] == hashed:
                return user  # (id, username, password, role)
        return None

    def register(self, username, password):
        if len(username) < 3 or len(password) < 3:
            return False, "Логин и пароль должны быть не менее 3 символов."
        if self.db.add_user(username, password):
            return True, "Пользователь зарегистрирован."
        else:
            return False, "Пользователь с таким именем уже существует."

    def change_password(self, user_id, new_password):
        if len(new_password) < 3:
            return False, "Пароль должен быть не менее 3 символов."
        self.db.update_user_password(user_id, new_password)
        return True, "Пароль изменён."