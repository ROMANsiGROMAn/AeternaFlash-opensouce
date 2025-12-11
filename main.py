import subprocess
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import win32gui
import win32con
import win32process
import time
import sys


class EmbeddedFlashPlayer:
    def __init__(self):
        self.flash_path = r".\flashplayer32.exe"
        self.current_process = None
        self.flash_hwnd = None
        self.games = []
        self.is_fullscreen = False
        self.original_geometry = None

        # Создаем главное окно
        self.root = tk.Tk()
        self.root.title("AeternaFlash Player")
        self.root.geometry("1100x800")
        self.root.configure(bg='#2b2b2b')

        # Минимальный размер окна
        self.root.minsize(800, 600)

        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Биндим изменение размеров окна
        self.root.bind('<Configure>', self.on_window_resize)

        self.setup_ui()

    def setup_ui(self):
        # Заголовок
        title_label = tk.Label(self.root, text="🎮AeternaFPlayer",
                               font=("Arial", 24, "bold"),
                               bg='#2b2b2b', fg='#00ff88')
        title_label.pack(pady=20)

        # Основной контейнер
        main_container = tk.Frame(self.root, bg='#2b2b2b')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Левая панель - управление
        left_panel = tk.Frame(main_container, bg='#2b2b2b', width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        # Правая панель - игра
        right_panel = tk.Frame(main_container, bg='#2b2b2b')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        # === ЛЕВАЯ ПАНЕЛЬ ===
        # Заголовок списка игр
        list_label = tk.Label(left_panel, text="📂 Мои игры:",
                              bg='#2b2b2b', fg='white',
                              font=("Arial", 14, "bold"))
        list_label.pack(anchor='w', pady=(0, 10))

        # Кнопки управления
        btn_frame = tk.Frame(left_panel, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        add_btn = tk.Button(btn_frame, text="+ Добавить игру",
                            command=self.add_game,
                            bg='#4c4c4c', fg='white',
                            font=("Arial", 11),
                            padx=15, pady=8)
        add_btn.pack(side=tk.LEFT, padx=2)

        remove_btn = tk.Button(btn_frame, text="− Удалить",
                               command=self.remove_game,
                               bg='#aa0000', fg='white',
                               font=("Arial", 11),
                               padx=15, pady=8)
        remove_btn.pack(side=tk.LEFT, padx=2)

        # Список игр с прокруткой
        list_frame = tk.Frame(left_panel, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.games_listbox = tk.Listbox(list_frame,
                                        bg='#3c3c3c',
                                        fg='white',
                                        font=("Arial", 11),
                                        selectbackground='#00aa44',
                                        selectforeground='white',
                                        yscrollcommand=scrollbar.set)
        self.games_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.games_listbox.yview)

        self.games_listbox.bind('<<ListboxSelect>>', self.on_game_select)
        self.games_listbox.bind('<Double-Button-1>', lambda e: self.launch_embedded_game())

        # Информация об игре
        info_frame = tk.Frame(left_panel, bg='#3c3c3c', relief='sunken', borderwidth=2)
        info_frame.pack(fill=tk.X, pady=20)

        info_label = tk.Label(info_frame, text="ℹ️ Информация:",
                              bg='#3c3c3c', fg='white',
                              font=("Arial", 12, "bold"))
        info_label.pack(anchor='w', padx=10, pady=10)

        self.game_info_text = tk.Text(info_frame,
                                      bg='#3c3c3c',
                                      fg='white',
                                      font=("Arial", 9),
                                      height=8,
                                      wrap=tk.WORD,
                                      borderwidth=0)
        self.game_info_text.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        self.game_info_text.insert(tk.END, "Выберите игру из списка")
        self.game_info_text.config(state='disabled')

        # Кнопка запуска
        self.launch_btn = tk.Button(left_panel, text="▶ ЗАПУСТИТЬ В ОКНЕ",
                                    command=self.launch_embedded_game,
                                    bg='#00aa44', fg='white',
                                    font=("Arial", 12, "bold"),
                                    padx=20, pady=12,
                                    state='disabled')
        self.launch_btn.pack(fill=tk.X, pady=10)

        # Кнопка остановки
        stop_btn = tk.Button(left_panel, text="⏹ ОСТАНОВИТЬ",
                             command=self.stop_game,
                             bg='#aa0000', fg='white',
                             font=("Arial", 12),
                             padx=20, pady=12)
        stop_btn.pack(fill=tk.X)

        # Кнопка выхода из полноэкранного режима (изначально скрыта)
        self.exit_fullscreen_btn = tk.Button(left_panel, text="⎋ ВЫЙТИ ИЗ ПОЛНОГО ЭКРАНА",
                                             command=self.exit_fullscreen,
                                             bg='#ff8800', fg='white',
                                             font=("Arial", 10, "bold"),
                                             padx=10, pady=8)
        self.exit_fullscreen_btn.pack(fill=tk.X, pady=5)
        self.exit_fullscreen_btn.pack_forget()  # Скрываем

        # === ПРАВАЯ ПАНЕЛЬ ===
        # Контейнер для встроенного Flash
        self.game_container = tk.Frame(right_panel, bg='black', relief='sunken', borderwidth=3)
        self.game_container.pack(fill=tk.BOTH, expand=True)

        # Заглушка когда игра не запущена
        self.placeholder_label = tk.Label(self.game_container,
                                          text="Здесь будет игра\n\nВыберите игру слева и нажмите 'ЗАПУСТИТЬ В ОКНЕ'",
                                          bg='black', fg='white',
                                          font=("Arial", 14),
                                          justify='center')
        self.placeholder_label.place(relx=0.5, rely=0.5, anchor='center')

        # Панель управления игрой
        control_panel = tk.Frame(right_panel, bg='#2b2b2b')
        control_panel.pack(fill=tk.X, pady=10)

        # Кнопки управления размером
        size_frame = tk.Frame(control_panel, bg='#2b2b2b')
        size_frame.pack()

        tk.Button(size_frame, text="Исходный размер",
                  command=self.reset_game_size,
                  bg='#555555', fg='white').pack(side=tk.LEFT, padx=2)

        tk.Button(size_frame, text="Растянуть",
                  command=self.stretch_game,
                  bg='#555555', fg='white').pack(side=tk.LEFT, padx=2)

        tk.Button(size_frame, text="Сохранить пропорции",
                  command=self.keep_aspect_ratio,
                  bg='#555555', fg='white').pack(side=tk.LEFT, padx=2)

        self.fullscreen_btn = tk.Button(size_frame, text="🖥️ Полный экран",
                                        command=self.toggle_fullscreen,
                                        bg='#0066cc', fg='white')
        self.fullscreen_btn.pack(side=tk.LEFT, padx=2)

        # Статус бар
        self.status_bar = tk.Label(self.root,
                                   text="Готов к работе | Выберите игру",
                                   bg='#1a1a1a', fg='#888888',
                                   font=("Arial", 9),
                                   anchor='w')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_game(self):
        files = filedialog.askopenfilenames(
            title="Выберите SWF файлы",
            filetypes=[("SWF files", "*.swf"), ("All files", "*.*")]
        )

        for file in files:
            if file not in self.games:
                self.games.append(file)
                game_name = os.path.basename(file)
                self.games_listbox.insert(tk.END, f"🎮 {game_name}")
                self.update_status(f"Добавлена игра: {game_name}")

    def on_game_select(self, event):
        selection = self.games_listbox.curselection()
        if selection:
            index = selection[0]
            game_path = self.games[index]

            # Обновляем информацию
            game_name = os.path.basename(game_path)
            info_text = f"Название: {game_name}\n\n"
            info_text += f"Путь: {game_path}\n\n"

            try:
                size = os.path.getsize(game_path)
                if size < 1024:
                    size_text = f"{size} байт"
                elif size < 1024 * 1024:
                    size_text = f"{size / 1024:.1f} КБ"
                else:
                    size_text = f"{size / (1024 * 1024):.1f} МБ"
                info_text += f"Размер: {size_text}\n\n"
            except:
                info_text += "Размер: неизвестно\n\n"

            self.game_info_text.config(state='normal')
            self.game_info_text.delete(1.0, tk.END)
            self.game_info_text.insert(1.0, info_text)
            self.game_info_text.config(state='disabled')

            # Активируем кнопку запуска
            self.launch_btn.config(state='normal')
            self.update_status(f"Выбрана игра: {game_name}")

    def launch_embedded_game(self):
        selection = self.games_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите игру из списка!")
            return

        index = selection[0]
        game_path = self.games[index]
        game_name = os.path.basename(game_path)

        self.update_status(f"Запуск встроенной игры: {game_name}...")

        # Скрываем заглушку
        self.placeholder_label.place_forget()

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._launch_embedded, args=(game_path,))
        thread.daemon = True
        thread.start()

    def _launch_embedded(self, game_path):
        try:
            # Останавливаем предыдущую игру если есть
            if self.current_process:
                self.stop_game()
                time.sleep(1)

            # Запускаем Flash Player скрыто
            self.current_process = subprocess.Popen(
                [self.flash_path, game_path],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.update_status(f"Игра запущена (PID: {self.current_process.pid}), ищем окно...")

            # Ждем запуска
            time.sleep(2)

            # Ищем окно Flash
            self.find_and_embed_flash_window()

            # Мониторим процесс
            self.monitor_process()

        except Exception as e:
            self.update_status(f"Ошибка запуска: {str(e)}")
            self.root.after(0, self.placeholder_label.place, {'relx': 0.5, 'rely': 0.5, 'anchor': 'center'})

    def find_and_embed_flash_window(self):
        """Ищет окно Flash Player и встраивает его"""
        attempts = 0
        max_attempts = 10

        def try_find_window():
            nonlocal attempts
            attempts += 1

            # Ищем все окна и проверяем их
            def enum_windows(hwnd, extra):
                try:
                    # Проверяем процесс окна
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)

                    if pid == self.current_process.pid:
                        # Получаем заголовок окна
                        window_text = win32gui.GetWindowText(hwnd)

                        # Ищем окно Flash (может быть с заголовком или без)
                        if "Flash" in window_text or game_name in window_text or window_text == "":
                            self.flash_hwnd = hwnd

                            # Получаем размеры контейнера
                            self.game_container.update_idletasks()
                            width = self.game_container.winfo_width()
                            height = self.game_container.winfo_height()

                            # Убираем ВСЕ рамки и заголовок
                            style = win32gui.GetWindowLong(self.flash_hwnd, win32con.GWL_STYLE)
                            style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME |
                                       win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX |
                                       win32con.WS_BORDER | win32con.WS_DLGFRAME |
                                       win32con.WS_SYSMENU | win32con.WS_OVERLAPPED)
                            win32gui.SetWindowLong(self.flash_hwnd, win32con.GWL_STYLE, style)

                            # Убираем расширенный стиль
                            ex_style = win32gui.GetWindowLong(self.flash_hwnd, win32con.GWL_EXSTYLE)
                            ex_style &= ~(win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_CLIENTEDGE |
                                          win32con.WS_EX_STATICEDGE | win32con.WS_EX_WINDOWEDGE)
                            win32gui.SetWindowLong(self.flash_hwnd, win32con.GWL_EXSTYLE, ex_style)

                            # Встраиваем окно
                            win32gui.SetParent(self.flash_hwnd, self.game_container.winfo_id())

                            # Устанавливаем размер на весь контейнер
                            win32gui.MoveWindow(self.flash_hwnd, 0, 0, width, height, True)

                            # Показываем окно
                            win32gui.ShowWindow(self.flash_hwnd, win32con.SW_SHOW)
                            win32gui.UpdateWindow(self.flash_hwnd)

                            self.update_status("✓ Игра встроена в окно!")
                            return False
                except:
                    pass
                return True

            win32gui.EnumWindows(enum_windows, None)

            if self.flash_hwnd:
                self.update_status("Окно игры найдено и встроено")
            elif attempts < max_attempts:
                # Пробуем еще раз через 500 мс
                self.root.after(500, try_find_window)
            else:
                self.update_status("✗ Не удалось найти окно игры")
                if self.current_process:
                    self.current_process.terminate()
                    self.current_process = None
                self.root.after(0, self.placeholder_label.place, {'relx': 0.5, 'rely': 0.5, 'anchor': 'center'})

        # Получаем имя игры для поиска
        selection = self.games_listbox.curselection()
        if selection:
            index = selection[0]
            game_path = self.games[index]
            game_name = os.path.basename(game_path)

            # Начинаем поиск
            self.root.after(100, try_find_window)

    def on_window_resize(self, event):
        """Обработчик изменения размеров окна"""
        if self.flash_hwnd and not self.is_fullscreen:
            # Ждем немного чтобы окно успело обновиться
            self.root.after(100, self.adjust_game_size)

    def adjust_game_size(self):
        """Подгоняет размер игры под контейнер"""
        if self.flash_hwnd:
            try:
                # Получаем размеры контейнера
                self.game_container.update_idletasks()
                width = self.game_container.winfo_width()
                height = self.game_container.winfo_height()

                # Устанавливаем размер игры
                win32gui.MoveWindow(self.flash_hwnd, 0, 0, width, height, True)

                # Обновляем окно
                win32gui.UpdateWindow(self.flash_hwnd)

            except Exception as e:
                print(f"Ошибка изменения размера: {e}")

    def reset_game_size(self):
        """Сбрасывает размер игры к исходному"""
        if self.flash_hwnd:
            # Устанавливаем стандартный размер
            self.game_container.config(width=800, height=600)
            self.adjust_game_size()
            self.update_status("Размер сброшен к 800x600")

    def stretch_game(self):
        """Растягивает игру на весь контейнер"""
        if self.flash_hwnd:
            self.adjust_game_size()
            self.update_status("Игра растянута на весь контейнер")

    def keep_aspect_ratio(self):
        """Сохраняет пропорции игры"""
        if self.flash_hwnd:
            try:
                # Получаем размеры контейнера
                container_width = self.game_container.winfo_width()
                container_height = self.game_container.winfo_height()

                # Сохраняем пропорции 4:3
                aspect_ratio = 4 / 3
                if container_width / container_height > aspect_ratio:
                    # Слишком широкий, подгоняем по высоте
                    new_width = int(container_height * aspect_ratio)
                    x = (container_width - new_width) // 2
                    win32gui.MoveWindow(self.flash_hwnd, x, 0, new_width, container_height, True)
                else:
                    # Слишком высокий, подгоняем по ширине
                    new_height = int(container_width / aspect_ratio)
                    y = (container_height - new_height) // 2
                    win32gui.MoveWindow(self.flash_hwnd, 0, y, container_width, new_height, True)

                self.update_status("Сохраняются пропорции 4:3")

            except Exception as e:
                self.update_status(f"Ошибка: {str(e)}")

    def toggle_fullscreen(self):
        """Переключает полноэкранный режим ВСЕГО приложения"""
        if not self.is_fullscreen:
            # Входим в полноэкранный режим
            self.original_geometry = self.root.geometry()
            self.root.attributes('-fullscreen', True)
            self.is_fullscreen = True
            self.fullscreen_btn.config(text="🖥️ Оконный режим")
            self.exit_fullscreen_btn.pack(fill=tk.X, pady=5)  # Показываем кнопку выхода

            # Обновляем размер игры
            self.root.after(100, self.adjust_game_size)
            self.update_status("Полноэкранный режим")
        else:
            # Выходим из полноэкранного режима
            self.exit_fullscreen()

    def exit_fullscreen(self):
        """Выход из полноэкранного режима"""
        if self.is_fullscreen:
            self.root.attributes('-fullscreen', False)
            if self.original_geometry:
                self.root.geometry(self.original_geometry)
            self.is_fullscreen = False
            self.fullscreen_btn.config(text="🖥️ Полный экран")
            self.exit_fullscreen_btn.pack_forget()  # Скрываем кнопку выхода

            # Обновляем размер игры
            self.root.after(100, self.adjust_game_size)
            self.update_status("Оконный режим")

    def monitor_process(self):
        """Мониторит процесс игры"""
        if self.current_process:
            return_code = self.current_process.poll()
            if return_code is not None:
                # Процесс завершен
                self.update_status(f"Игра завершена. Код выхода: {return_code}")
                self.flash_hwnd = None
                self.current_process = None
                if self.is_fullscreen:
                    self.exit_fullscreen()
                self.root.after(0, self.placeholder_label.place, {'relx': 0.5, 'rely': 0.5, 'anchor': 'center'})
            else:
                # Проверяем снова через 1 секунду
                self.root.after(1000, self.monitor_process)

    def stop_game(self):
        """Останавливает текущую игру"""
        if self.current_process:
            try:
                # Сначала пытаемся закрыть окно
                if self.flash_hwnd:
                    win32gui.PostMessage(self.flash_hwnd, win32con.WM_CLOSE, 0, 0)
                    time.sleep(0.5)

                # Если процесс еще жив, завершаем его
                if self.current_process and self.current_process.poll() is None:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=1)

                self.update_status("Игра остановлена")

            except:
                try:
                    self.current_process.kill()
                except:
                    pass
                finally:
                    self.update_status("Игра принудительно остановлена")

            self.flash_hwnd = None
            self.current_process = None

            if self.is_fullscreen:
                self.exit_fullscreen()

            self.root.after(0, self.placeholder_label.place, {'relx': 0.5, 'rely': 0.5, 'anchor': 'center'})
        else:
            messagebox.showinfo("Инфо", "Нет запущенных игр")

    def remove_game(self):
        selection = self.games_listbox.curselection()
        if selection:
            index = selection[0]
            game_path = self.games.pop(index)
            self.games_listbox.delete(index)

            # Сбрасываем информацию
            self.game_info_text.config(state='normal')
            self.game_info_text.delete(1.0, tk.END)
            self.game_info_text.insert(tk.END, "Выберите игру из списка")
            self.game_info_text.config(state='disabled')

            self.launch_btn.config(state='disabled')
            self.update_status(f"Удалена игра: {os.path.basename(game_path)}")

    def update_status(self, message):
        self.status_bar.config(text=f"Статус: {message}")
        print(f"Статус: {message}")

    def on_closing(self):
        """Обработка закрытия окна"""
        if self.current_process:
            self.stop_game()
            time.sleep(0.5)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # Проверяем наличие pywin32
    try:
        import win32gui
        import win32con
    except ImportError:
        print("Установите библиотеку pywin32:")
        print("pip install pywin32")
        messagebox.showerror("Ошибка",
                             "Установите библиотеку pywin32:\n"
                             "pip install pywin32")
        sys.exit(1)

    # Проверяем Flash Player
    flash_path = r"C:\Users\roman\OneDrive\Documents\flashplayer32.exe"

    if not os.path.exists(flash_path):
        messagebox.showerror("Ошибка",
                             f"Flash Player не найден!\n"
                             f"Убедитесь, что файл находится по пути:\n{flash_path}")
    else:
        app = EmbeddedFlashPlayer()
        app.run()
