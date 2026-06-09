import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from functools import partial
import datetime
import os
from PIL import Image, ImageTk

import customtkinter as ctk

from database import Database, AuthManager

# Настройка внешнего вида
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

PALETTE = {
    "bg": "#f4f8ff",
    "surface": "#ffffff",
    "surface_alt": "#eef4ff",
    "primary": "#2f6df6",
    "primary_hover": "#2559cb",
    "secondary": "#1aa39a",
    "secondary_hover": "#13857f",
    "text_dark": "#1f2937",
    "text_muted": "#6b7280",
    "tree_heading": "#dfe9ff",
    "tree_row_even": "#f8fbff",
    "tree_row_odd": "#edf3ff",
    "today": "#ffefb0",
    "soon": "#ffd3a8",
}

class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, auth_manager, on_success):
        super().__init__(master)
        self.auth = auth_manager
        self.on_success = on_success
        self.title("Авторизация")
        self.geometry("500x350")
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.create_widgets()

    def create_widgets(self):
        frame = ctk.CTkFrame(self, corner_radius=15, border_width=1, fg_color=PALETTE["surface"], border_color="#d6e0f5")
        frame.pack(padx=30, pady=30, fill="both", expand=True)

        ctk.CTkLabel(frame, text="🎂 Органайзер дней рождения", text_color=PALETTE["text_dark"], font=("Segoe UI", 20, "bold")).pack(pady=(10, 25))

        ctk.CTkLabel(frame, text="👤 Логин:", text_color=PALETTE["text_dark"], font=("Segoe UI", 12)).pack(anchor="w", padx=10)
        self.entry_username = ctk.CTkEntry(frame, width=280, placeholder_text="Введите логин", font=("Segoe UI", 11), fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.entry_username.pack(pady=(0, 12), padx=10)

        ctk.CTkLabel(frame, text="🔒 Пароль:", text_color=PALETTE["text_dark"], font=("Segoe UI", 12)).pack(anchor="w", padx=10)
        self.entry_password = ctk.CTkEntry(frame, width=280, placeholder_text="Введите пароль", show="*", font=("Segoe UI", 11), fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.entry_password.pack(pady=(0, 20), padx=10)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="Войти", command=self.do_login, width=120, height=35, font=("Segoe UI", 12),
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"], text_color="#ffffff").pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Регистрация", command=self.do_register, width=120, height=35, font=("Segoe UI", 12),
                      fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"], text_color="#ffffff").pack(side="left", padx=8)

        self.entry_password.bind("<Return>", lambda e: self.do_login())

    def do_login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        user = self.auth.login(username, password)
        if user:
            self.destroy()
            self.on_success(user)
        else:
            messagebox.showerror("Ошибка", "Неверное имя пользователя или пароль.")

    def do_register(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        ok, msg = self.auth.register(username, password)
        if ok:
            messagebox.showinfo("Успех", msg)
        else:
            messagebox.showerror("Ошибка", msg)


class AdminWindow(ctk.CTkToplevel):
    def __init__(self, master, db, auth):
        super().__init__(master)
        self.db = db
        self.auth = auth
        self.title("Управление пользователями")
        self.geometry("760x580")
        self.transient(master)
        self.lift()
        self.focus_force()
        self.create_widgets()
        self.load_users()

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Admin.Treeview", background=PALETTE["surface"], fieldbackground=PALETTE["surface"], foreground=PALETTE["text_dark"], rowheight=28, borderwidth=0)
        style.configure("Admin.Treeview.Heading", background=PALETTE["tree_heading"], foreground=PALETTE["text_dark"], font=("Segoe UI", 10, "bold"))
        style.map("Admin.Treeview", background=[("selected", "#b8d1ff")], foreground=[("selected", PALETTE["text_dark"])])

        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=PALETTE["surface"])
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        columns = ("ID", "Имя", "Роль")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15, style="Admin.Treeview")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Удалить пользователя", command=self.delete_user, width=150,
                      fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Сбросить пароль", command=self.reset_password, width=150,
                      fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"], text_color="#ffffff").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Закрыть", command=self.destroy, width=100,
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"], text_color="#ffffff").pack(side="left", padx=5)

    def load_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        users = self.db.get_all_users()
        for idx, user in enumerate(users):
            tag = "oddrow" if idx % 2 == 0 else "evenrow"
            self.tree.insert("", tk.END, values=user, tags=(tag,))
        self.tree.tag_configure("oddrow", background=PALETTE["tree_row_odd"])
        self.tree.tag_configure("evenrow", background=PALETTE["tree_row_even"])

    def delete_user(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя для удаления.")
            return
        values = self.tree.item(selected[0], "values")
        user_id = values[0]
        if user_id == 1:
            messagebox.showerror("Ошибка", "Нельзя удалить администратора по умолчанию.")
            return
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя {values[1]}?"):
            self.db.delete_user(user_id)
            self.load_users()

    def reset_password(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя.")
            return
        values = self.tree.item(selected[0], "values")
        user_id = values[0]
        new_password = simpledialog.askstring("Сброс пароля", "Введите новый пароль:", show="*")
        if new_password:
            ok, msg = self.auth.change_password(user_id, new_password)
            if ok:
                messagebox.showinfo("Успех", msg)
            else:
                messagebox.showerror("Ошибка", msg)


class BirthdayApp(ctk.CTkFrame):
    def __init__(self, master, db, user_id, username, role):
        super().__init__(master)
        self.master = master
        self.db = db
        self.user_id = user_id
        self.username = username
        self.role = role
        self.current_contact_id = None
        self.photo_path = ""
        self.listbox_contact_ids = []

        master.title("Дни рождения")
        master.geometry("1200x750")
        master.configure(fg_color=PALETTE["bg"])
        master.protocol("WM_DELETE_WINDOW", self.on_close)

        self.create_menu()
        self.create_widgets()
        self.bind_hotkeys()
        self.load_contacts()
        self.check_reminders_on_startup()

    def create_menu(self):
        menu_style = dict(bg=PALETTE["surface"], fg=PALETTE["text_dark"], activebackground=PALETTE["tree_heading"], activeforeground=PALETTE["text_dark"])
        menubar = tk.Menu(self.master, **menu_style)
        file_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        file_menu.add_command(label="Новый контакт", command=self.new_contact, accelerator="Ctrl+N")
        file_menu.add_command(label="Удалить", command=self.delete_contact, accelerator="Ctrl+D")
        file_menu.add_command(label="Экспорт в CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_close)
        menubar.add_cascade(label="Файл", menu=file_menu)

        remind_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        remind_menu.add_command(label="Настроить за сколько дней", command=self.configure_reminder)
        remind_menu.add_command(label="Проверить сейчас", command=self.check_reminders_manual, accelerator="Ctrl+R")
        menubar.add_cascade(label="Напоминания", menu=remind_menu)

        view_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        view_menu.add_command(label="Режим таблицы", command=self.set_table_mode)
        view_menu.add_command(label="Режим форма+список", command=self.set_split_mode)
        menubar.add_cascade(label="Вид", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        if self.role == "admin":
            admin_menu = tk.Menu(menubar, tearoff=0, **menu_style)
            admin_menu.add_command(label="Управление пользователями", command=self.open_admin_panel)
            menubar.add_cascade(label="Администрирование", menu=admin_menu)

        self.master.config(menu=menubar)

    def create_widgets(self):
        # Верхняя панель
        top_bar = ctk.CTkFrame(self.master, height=50, corner_radius=0, fg_color=PALETTE["surface"])
        top_bar.pack(side="top", fill="x")
        role_text = "Администратор" if self.role == "admin" else "Пользователь"
        ctk.CTkLabel(top_bar, text=f"👋 Добро пожаловать, {self.username} ({role_text})",
                     text_color=PALETTE["text_dark"], font=("Segoe UI", 14, "bold")).pack(side="left", padx=15, pady=10)

        # Форма добавления/редактирования (общая для обоих режимов)
        self.form_frame = ctk.CTkFrame(self.master, corner_radius=10, border_width=1, fg_color=PALETTE["surface"], border_color="#d6e0f5")
        self.form_frame.pack(side="top", fill="x", padx=10, pady=(5, 10))

        # 1-я строка
        ctk.CTkLabel(self.form_frame, text="Имя*:", font=("Segoe UI", 11)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self.form_frame, width=200, fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(self.form_frame, text="Дата рождения (ГГГГ-ММ-ДД):", font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.birth_entry = ctk.CTkEntry(self.form_frame, width=120, fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.birth_entry.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(self.form_frame, text="Телефон:", font=("Segoe UI", 11)).grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.phone_entry = ctk.CTkEntry(self.form_frame, width=120, fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.phone_entry.grid(row=0, column=5, padx=5, pady=5)

        # 2-я строка
        ctk.CTkLabel(self.form_frame, text="Email:", font=("Segoe UI", 11)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.email_entry = ctk.CTkEntry(self.form_frame, width=200, fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.email_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(self.form_frame, text="Эмодзи:", font=("Segoe UI", 11)).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.emoji_entry = ctk.CTkEntry(self.form_frame, width=60, placeholder_text="🎂", fg_color=PALETTE["surface_alt"], border_color="#c3d4ff")
        self.emoji_entry.insert(0, "🎂")
        self.emoji_entry.grid(row=1, column=3, padx=5, pady=5)

        ctk.CTkLabel(self.form_frame, text="Фото:", font=("Segoe UI", 11)).grid(row=1, column=4, padx=5, pady=5, sticky="w")
        self.btn_photo = ctk.CTkButton(self.form_frame, text="Выбрать фото", command=self.choose_photo, width=100,
                                       fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"], text_color="#ffffff")
        self.btn_photo.grid(row=1, column=5, padx=5, pady=5)
        self.photo_label = ctk.CTkLabel(self.form_frame, text="", font=("Segoe UI", 9))
        self.photo_label.grid(row=1, column=6, padx=5, pady=5, sticky="w")

        btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=7, pady=8)
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.save_contact, width=120,
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"], text_color="#ffffff").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Очистить", command=self.clear_form, width=120,
                      fg_color="#8b9bb8", hover_color="#7184a6", text_color="#ffffff").pack(side="left", padx=5)

        # Основная область для двух режимов
        self.main_container = ctk.CTkFrame(self.master, fg_color=PALETTE["surface"])
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Режим по умолчанию – таблица
        self.current_mode = "table"
        self.create_table_mode()

    def create_table_mode(self):
        """Режим отображения: только таблица Treeview"""
        # Удаляем старые виджеты
        for widget in self.main_container.winfo_children():
            widget.destroy()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Contacts.Treeview", background=PALETTE["surface"], fieldbackground=PALETTE["surface"], foreground=PALETTE["text_dark"], rowheight=29, borderwidth=0)
        style.configure("Contacts.Treeview.Heading", background=PALETTE["tree_heading"], foreground=PALETTE["text_dark"], font=("Segoe UI", 10, "bold"))
        style.map("Contacts.Treeview", background=[("selected", "#b8d1ff")], foreground=[("selected", PALETTE["text_dark"])])

        # Таблица
        columns = ("Имя", "Дата рождения", "Возраст", "Ближайший ДР (дней)", "Телефон")
        self.tree = ttk.Treeview(self.main_container, columns=columns, show="headings", height=20, style="Contacts.Treeview")
        for col in columns:
            self.tree.heading(col, text=col, command=partial(self.sort_treeview, col))
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure('today', background=PALETTE["today"], foreground=PALETTE["text_dark"])
        self.tree.tag_configure('soon', background=PALETTE["soon"], foreground=PALETTE["text_dark"])
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-1>', lambda e: self.load_contact_to_form())

        # Загружаем данные
        self.populate_tree()

    def create_split_mode(self):
        """Альтернативный режим: список (Listbox) + форма"""
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Левая панель – список
        left_frame = ctk.CTkFrame(self.main_container, width=300, corner_radius=10, fg_color=PALETTE["surface_alt"])
        left_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Список контактов", font=("Segoe UI", 12, "bold")).pack(pady=5)

        listbox_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        listbox_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.listbox = tk.Listbox(listbox_frame, bg=PALETTE["surface"], fg=PALETTE["text_dark"], selectbackground="#b8d1ff", selectforeground=PALETTE["text_dark"],
                                  font=("Segoe UI", 10))
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)

        # Правая панель – дублирует форму (можно показать детали)
        right_frame = ctk.CTkFrame(self.main_container, corner_radius=10, fg_color=PALETTE["surface_alt"])
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ctk.CTkLabel(right_frame, text="Детали контакта", font=("Segoe UI", 12, "bold")).pack(pady=5)
        self.detail_text = ctk.CTkTextbox(right_frame, wrap="word", font=("Segoe UI", 11))
        self.detail_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Загружаем список
        self.populate_listbox()

    def populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        contacts = self.db.get_all_contacts(self.user_id)
        today = datetime.date.today()
        for c in contacts:
            age = self.db.calculate_age(c['birth_date'])
            days = self.db.days_until_next_birthday(c['birth_date'])
            values = (c['name'], c['birth_date'], age, days, c['phone'])
            # Определяем тег для подсветки
            if days == 0:
                tag = 'today'
            elif days <= 3:
                tag = 'soon'
            else:
                tag = ''
            self.tree.insert("", tk.END, values=values, iid=c['id'], tags=(tag,))

    def populate_listbox(self):
        self.listbox.delete(0, tk.END)
        self.listbox_contact_ids = []
        contacts = self.db.get_all_contacts(self.user_id)
        for c in contacts:
            display = f"{c['emoji']} {c['name']} ({c['birth_date']})"
            self.listbox.insert(tk.END, display)
            self.listbox_contact_ids.append(c['id'])

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.current_contact_id = int(selection[0])
            self.load_contact_to_form()

    def on_listbox_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            if idx >= len(self.listbox_contact_ids):
                return
            contact_id = self.listbox_contact_ids[idx]
            # Получаем контакт из БД
            contact = self.db.get_contact_by_id(contact_id, self.user_id)
            if contact:
                self.current_contact_id = contact['id']
                self.load_contact_to_form()
                # Показать детали в текстовом поле
                self.detail_text.delete(1.0, tk.END)
                details = f"Имя: {contact['name']}\n"
                details += f"Дата рождения: {contact['birth_date']}\n"
                details += f"Возраст: {self.db.calculate_age(contact['birth_date'])}\n"
                details += f"Ближайший ДР через: {self.db.days_until_next_birthday(contact['birth_date'])} дн.\n"
                details += f"Телефон: {contact['phone']}\n"
                details += f"Email: {contact['email']}\n"
                details += f"Эмодзи: {contact['emoji']}\n"
                details += f"Фото: {contact['photo_path'] or 'Нет'}\n"
                self.detail_text.insert(1.0, details)

    def load_contact_to_form(self):
        if self.current_contact_id is None:
            return
        contact = self.db.get_contact_by_id(self.current_contact_id, self.user_id)
        if contact:
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, contact['name'])
            self.birth_entry.delete(0, tk.END)
            self.birth_entry.insert(0, contact['birth_date'])
            self.phone_entry.delete(0, tk.END)
            self.phone_entry.insert(0, contact['phone'] or "")
            self.email_entry.delete(0, tk.END)
            self.email_entry.insert(0, contact['email'] or "")
            self.emoji_entry.delete(0, tk.END)
            self.emoji_entry.insert(0, contact['emoji'] or "🎂")
            self.photo_path = contact['photo_path'] or ""
            self.photo_label.configure(text=os.path.basename(self.photo_path) if self.photo_path else "")

    def sort_treeview(self, col):
        # Простая сортировка по значениям
        items = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        if col in ("Возраст", "Ближайший ДР (дней)"):
            items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        else:
            items.sort(key=lambda x: x[0].lower())
        for idx, (val, child) in enumerate(items):
            self.tree.move(child, '', idx)

    def choose_photo(self):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if filename:
            self.photo_path = filename
            self.photo_label.configure(text=os.path.basename(filename))

    def save_contact(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Имя обязательно.")
            return
        birth_date = self.birth_entry.get().strip()
        try:
            datetime.datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
        phone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        emoji = self.emoji_entry.get().strip() or "🎂"

        if self.current_contact_id is None:
            self.db.add_contact(self.user_id, name, birth_date, phone, email, self.photo_path, emoji)
            messagebox.showinfo("Успех", "Контакт добавлен.")
        else:
            self.db.update_contact(self.current_contact_id, self.user_id, name, birth_date, phone, email, self.photo_path, emoji)
            messagebox.showinfo("Успех", "Контакт обновлён.")

        self.clear_form()
        if self.current_mode == "table":
            self.populate_tree()
        else:
            self.populate_listbox()

    def delete_contact(self):
        if self.current_contact_id is None:
            messagebox.showinfo("Информация", "Выберите контакт для удаления.")
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранный контакт?"):
            self.db.delete_contact(self.current_contact_id, self.user_id)
            self.clear_form()
            if self.current_mode == "table":
                self.populate_tree()
            else:
                self.populate_listbox()
                self.detail_text.delete(1.0, tk.END)
            messagebox.showinfo("Успех", "Контакт удалён.")

    def clear_form(self):
        self.current_contact_id = None
        self.name_entry.delete(0, tk.END)
        self.birth_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.emoji_entry.delete(0, tk.END)
        self.emoji_entry.insert(0, "🎂")
        self.photo_path = ""
        self.photo_label.configure(text="")
        if self.current_mode == "table":
            self.tree.selection_remove(self.tree.selection())
        else:
            self.listbox.selection_clear(0, tk.END)

    def new_contact(self):
        self.clear_form()
        self.name_entry.focus()

    def configure_reminder(self):
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Настройка напоминаний")
        dialog.geometry("300x150")
        dialog.grab_set()

        current = self.db.get_reminder_days(self.user_id)

        ctk.CTkLabel(dialog, text="Напоминать за сколько дней?").pack(pady=10)
        spin = tk.Spinbox(dialog, from_=1, to=30, width=6)
        spin.delete(0, "end")
        spin.insert(0, str(current))
        spin.pack(pady=5)

        def save():
            days = int(spin.get())
            self.db.set_reminder_days(self.user_id, days)
            messagebox.showinfo("Успех", f"Напоминания установлены за {days} дней.")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=10)

    def check_reminders_on_startup(self):
        days = self.db.get_reminder_days(self.user_id)
        upcoming = self.db.get_upcoming_birthdays(self.user_id, days)
        if upcoming:
            msg = "Предстоящие дни рождения:\n\n"
            for b in upcoming:
                msg += f"• {b['name']} ({b['birth_date']}) – через {b['days_left']} дн. (исполнится {b['age_next']})\n"
            messagebox.showinfo("Напоминание", msg)

    def check_reminders_manual(self):
        days = self.db.get_reminder_days(self.user_id)
        upcoming = self.db.get_upcoming_birthdays(self.user_id, days)
        if upcoming:
            msg = "Предстоящие дни рождения:\n\n"
            for b in upcoming:
                msg += f"• {b['name']} ({b['birth_date']}) – через {b['days_left']} дн. (исполнится {b['age_next']})\n"
            messagebox.showinfo("Напоминание", msg)
        else:
            messagebox.showinfo("Напоминание", "Нет предстоящих дней рождения в ближайшие дни.")

    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            self.db.export_to_csv(self.user_id, filename)
            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")

    def set_table_mode(self):
        if self.current_mode == "table":
            return
        self.current_mode = "table"
        self.create_table_mode()
        self.populate_tree()

    def set_split_mode(self):
        if self.current_mode == "split":
            return
        self.current_mode = "split"
        self.create_split_mode()
        self.populate_listbox()

    def bind_hotkeys(self):
        self.master.bind_all("<Control-n>", lambda e: self.new_contact())
        self.master.bind_all("<Control-d>", lambda e: self.delete_contact())
        self.master.bind_all("<Control-r>", lambda e: self.check_reminders_manual())

    def open_admin_panel(self):
        AdminWindow(self.master, self.db, AuthManager(self.db))

    def show_about(self):
        about_text = """
        Органайзер дней рождения
        Версия 2.0 (CustomTkinter)

        Возможности:
        ✓ Хранение контактов с датами рождения
        ✓ Автоматический расчёт возраста и дней до ДР
        ✓ Напоминания о предстоящих днях рождения
        ✓ Два режима отображения: таблица и форма+список
        ✓ Экспорт в CSV
        ✓ Загрузка фото для контакта
        ✓ Эмодзи для персонализации
        ✓ Подсветка ближайших ДР (жёлтый/оранжевый)
        ✓ Разделение ролей (администратор)

        Разработано на Python с использованием CustomTkinter и SQLite
        """
        messagebox.showinfo("О программе", about_text)

    def on_close(self):
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            self.db.close()
            self.master.destroy()


def main():
    root = ctk.CTk()
    root.withdraw()
    db = Database()
    auth = AuthManager(db)

    def on_login_success(user):
        root.deiconify()
        app = BirthdayApp(root, db, user[0], user[1], user[3])
        app.pack(fill="both", expand=True)

    login = LoginWindow(root, auth, on_login_success)
    root.mainloop()

if __name__ == "__main__":
    main()