import tkinter as tk
from tkinter import filedialog, colorchooser, font as tkfont, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор изображений — Paint Pro")
        self.root.geometry("1300x800")
        self.root.configure(bg="#2b2b2b")
        self.set_window_icon()

        # Изображения
        self.original_image = None
        self.working_image = None      # растровое изображение (кисть, ластик)
        self.display_image = None
        self.tk_image = None

        # Текстовые объекты
        self.text_items = []            # каждый: {id, text, x, y, color, font, size}
        self.next_text_id = 1
        self.selected_text_id = None     # id выделенного текста
        self.text_drag_start = None      # для перетаскивания текста (в режиме move)

        # Инструменты
        self.tool = "pen"                # "pen", "eraser", "move"
        self.pen_color = "#000000"
        self.pen_size = 3
        self.drawing = False
        self.last_x = None
        self.last_y = None

        # История (растровое изображение + список текстов)
        self.history = []
        self.history_index = -1

        self.setup_ui()
        self.canvas.bind("<Configure>", self.on_canvas_resize)

    def set_window_icon(self):
        icon_img = Image.new("RGBA", (64, 64), (0,0,0,0))
        draw = ImageDraw.Draw(icon_img)
        draw.ellipse((10,10,54,54), fill="#3498db", outline="#2c3e50", width=2)
        draw.line((40,40,60,20), fill="#e67e22", width=4)
        draw.polygon((58,18,64,24,60,28), fill="#e67e22")
        icon_path = "temp_icon.png"
        icon_img.save(icon_path)
        icon = tk.PhotoImage(file=icon_path)
        self.root.iconphoto(True, icon)
        os.remove(icon_path)

    def setup_ui(self):
        # Верхняя панель
        toolbar = tk.Frame(self.root, bg="#3c3f41", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_load = tk.Button(toolbar, text="📂 Загрузить", command=self.load_image, bg="#5a626e", fg="white")
        btn_load.pack(side=tk.LEFT, padx=5, pady=5)

        btn_save = tk.Button(toolbar, text="💾 Сохранить", command=self.save_image, bg="#5a626e", fg="white")
        btn_save.pack(side=tk.LEFT, padx=5, pady=5)

        btn_undo = tk.Button(toolbar, text="↩️ Отмена", command=self.undo, bg="#5a626e", fg="white")
        btn_undo.pack(side=tk.LEFT, padx=5, pady=5)

        btn_redo = tk.Button(toolbar, text="↪️ Вернуть", command=self.redo, bg="#5a626e", fg="white")
        btn_redo.pack(side=tk.LEFT, padx=5, pady=5)

        # Инструменты
        self.pen_btn = tk.Button(toolbar, text="✏️ Кисть", command=lambda: self.set_tool("pen"), bg="#2ecc71", fg="white")
        self.pen_btn.pack(side=tk.LEFT, padx=2)

        self.eraser_btn = tk.Button(toolbar, text="🧽 Ластик", command=lambda: self.set_tool("eraser"), bg="#5a626e", fg="white")
        self.eraser_btn.pack(side=tk.LEFT, padx=2)

        self.move_btn = tk.Button(toolbar, text="🖐 Перемещение текста", command=lambda: self.set_tool("move"), bg="#5a626e", fg="white")
        self.move_btn.pack(side=tk.LEFT, padx=2)

        self.color_btn = tk.Button(toolbar, text="🎨 Цвет кисти", command=self.choose_color, bg=self.pen_color, width=12)
        self.color_btn.pack(side=tk.LEFT, padx=5, pady=5)

        size_label = tk.Label(toolbar, text="Размер:", bg="#3c3f41", fg="white")
        size_label.pack(side=tk.LEFT, padx=(10,2))
        self.size_var = tk.IntVar(value=self.pen_size)
        size_spin = tk.Spinbox(toolbar, from_=1, to=50, width=3, textvariable=self.size_var, command=self.change_size, bg="white")
        size_spin.pack(side=tk.LEFT, padx=2)

        btn_add_text = tk.Button(toolbar, text="➕ Добавить текст", command=self.open_text_dialog, bg="#5a626e", fg="white")
        btn_add_text.pack(side=tk.LEFT, padx=5, pady=5)

        # Кнопка редактирования выделенного текста (изменить текст, шрифт, цвет, размер)
        btn_edit_text = tk.Button(toolbar, text="✏️ Редактировать текст", command=self.edit_selected_text, bg="#5a626e", fg="white")
        btn_edit_text.pack(side=tk.LEFT, padx=5, pady=5)

        # Кнопка удаления текста (перетаскиванием) оставляем, но добавим также и ручное удаление
        self.delete_bin = tk.Frame(toolbar, bg="#e74c3c", width=80, height=40)
        self.delete_bin.pack(side=tk.RIGHT, padx=10, pady=5)
        self.bin_label = tk.Label(self.delete_bin, text="🗑️ Удалить\nсюда", bg="#e74c3c", fg="white", font=("Arial", 9))
        self.bin_label.pack(expand=True)

        # Canvas
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(canvas_frame, bg="#4a4a4a", xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # События
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.status = tk.Label(self.root, text="Готово. Загрузите изображение.", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#2b2b2b", fg="white")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.scale = 1.0
        self.temp_canvas_text_ids = []  # для хранения id текстов на canvas

    def set_tool(self, tool):
        self.tool = tool
        # Сброс выделения при смене инструмента (чтобы рамка не мешала)
        if tool != "move":
            self.select_text(None)
        # Обновить цвета кнопок
        self.pen_btn.config(bg="#2ecc71" if tool == "pen" else "#5a626e")
        self.eraser_btn.config(bg="#2ecc71" if tool == "eraser" else "#5a626e")
        self.move_btn.config(bg="#2ecc71" if tool == "move" else "#5a626e")

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if not path:
            return
        try:
            self.original_image = Image.open(path).convert("RGB")
            self.working_image = self.original_image.copy()
            self.text_items.clear()
            self.next_text_id = 1
            self.selected_text_id = None
            self.push_to_history()
            self.update_display()
            self.status.config(text=f"Загружено: {os.path.basename(path)}")
        except Exception as e:
            self.status.config(text=f"Ошибка: {e}")

    def update_display(self):
        if self.working_image is None:
            return
        self.display_image = self.working_image.copy()
        draw = ImageDraw.Draw(self.display_image)
        for item in self.text_items:
            try:
                font = ImageFont.truetype(item["font"] + ".ttf", item["size"])
            except:
                font = ImageFont.load_default()
            draw.text((item["x"], item["y"]), item["text"], fill=item["color"], font=font)

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1:
            canvas_w, canvas_h = 800, 600
        img_w, img_h = self.display_image.size
        self.scale = min(canvas_w / img_w, canvas_h / img_h)
        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)
        resized = self.display_image.resize((new_w, new_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Сохраняем текстовые объекты на canvas для взаимодействия
        self.temp_canvas_text_ids = []
        for item in self.text_items:
            x = item["x"] * self.scale
            y = item["y"] * self.scale
            try:
                font_display = tkfont.Font(family=item["font"], size=int(item["size"] * self.scale))
            except:
                font_display = tkfont.Font(size=int(item["size"] * self.scale))
            tid = self.canvas.create_text(x, y, text=item["text"], fill=item["color"], font=font_display, anchor="nw", tags=(f"text_{item['id']}",))
            self.temp_canvas_text_ids.append((tid, item["id"]))
            # Добавим рамку, если этот текст выделен
            if self.selected_text_id == item["id"]:
                bbox = self.canvas.bbox(tid)
                if bbox:
                    self.canvas.create_rectangle(bbox, outline="white", width=2, tags="selection_rect")
        # Привязываем события для выделения
        for tid, tid_item in self.temp_canvas_text_ids:
            self.canvas.tag_bind(tid, "<Button-1>", lambda e, tid=tid, id=tid_item: self.on_text_click(e, tid, id))

    def on_text_click(self, event, canvas_id, text_id):
        if self.tool == "move":
            # Режим перемещения
            self.selected_text_id = text_id
            self.text_drag_start = (event.x, event.y)
            self.update_display()  # перерисует с рамкой
            self.status.config(text="Перемещайте текст, отпустите для фиксации")
        else:
            # Простое выделение без перемещения, чтобы можно было редактировать
            self.select_text(text_id)

    def select_text(self, text_id):
        self.selected_text_id = text_id
        self.update_display()
        if text_id is not None:
            self.status.config(text=f"Выделен текст: {self.get_text_by_id(text_id)['text']}")
        else:
            self.status.config(text="Выделение снято")

    def get_text_by_id(self, text_id):
        for item in self.text_items:
            if item["id"] == text_id:
                return item
        return None

    def edit_selected_text(self):
        if self.selected_text_id is None:
            self.status.config(text="Сначала выделите текст (кликните по нему в режиме Кисть/Ластик)")
            return
        item = self.get_text_by_id(self.selected_text_id)
        if not item:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование текста")
        dialog.geometry("450x500")
        dialog.configure(bg="#3c3f41")

        tk.Label(dialog, text="Текст:", bg="#3c3f41", fg="white").pack(pady=5)
        text_entry = tk.Entry(dialog, width=40)
        text_entry.insert(0, item["text"])
        text_entry.pack(pady=5)

        tk.Label(dialog, text="Цвет:", bg="#3c3f41", fg="white").pack(pady=5)
        color_preview = tk.Button(dialog, text="Выбрать цвет", bg=item["color"], fg="white", width=20)
        selected_color = item["color"]
        def choose_color():
            nonlocal selected_color
            col = colorchooser.askcolor(initialcolor=selected_color)[1]
            if col:
                selected_color = col
                color_preview.config(bg=col)
        color_preview.config(command=choose_color)
        color_preview.pack(pady=5)

        tk.Label(dialog, text="Шрифт:", bg="#3c3f41", fg="white").pack(pady=5)
        fonts_list = sorted(tkfont.families())
        font_var = tk.StringVar(value=item["font"])
        font_menu = tk.OptionMenu(dialog, font_var, *fonts_list)
        font_menu.config(bg="#5a626e", fg="white")
        font_menu.pack(pady=5)

        tk.Label(dialog, text="Размер:", bg="#3c3f41", fg="white").pack(pady=5)
        size_spin = tk.Spinbox(dialog, from_=8, to=200, width=5)
        size_spin.delete(0, tk.END)
        size_spin.insert(0, str(item["size"]))
        size_spin.pack(pady=5)

        def apply():
            item["text"] = text_entry.get().strip() or "Текст"
            item["color"] = selected_color
            item["font"] = font_var.get()
            item["size"] = int(size_spin.get())
            self.push_to_history()
            self.update_display()
            self.status.config(text="Текст изменён")
            dialog.destroy()

        btn_apply = tk.Button(dialog, text="Применить", command=apply, bg="#2ecc71", fg="white")
        btn_apply.pack(pady=20)

    def on_mouse_down(self, event):
        if self.working_image is None:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        img_x = int(x / self.scale)
        img_y = int(y / self.scale)
        # Проверка, попали ли на корзину (для удаления) - обрабатывается в on_mouse_up?
        # Сделаем удаление перетаскиванием текста на корзину.
        # Для этого в on_mouse_move и on_mouse_up будем проверять координаты корзины
        self.drag_active = True
        self.drag_start_pos = (x, y)
        self.dragged_text_id = None
        # Если в режиме move и есть выделенный текст, то перемещаем
        if self.tool == "move" and self.selected_text_id is not None:
            self.dragged_text_id = self.selected_text_id
            self.text_drag_start = (x, y)
        else:
            # Рисование/ластик
            if self.tool == "pen":
                self.drawing = True
                self.last_x = img_x
                self.last_y = img_y
            elif self.tool == "eraser":
                self.drawing = True
                self.erase_at(img_x, img_y)

    def on_mouse_move(self, event):
        if self.working_image is None:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        img_x = int(x / self.scale)
        img_y = int(y / self.scale)
        if self.tool == "move" and self.dragged_text_id is not None:
            # Перемещаем текст
            dx = x - self.text_drag_start[0]
            dy = y - self.text_drag_start[1]
            if dx != 0 or dy != 0:
                item = self.get_text_by_id(self.dragged_text_id)
                if item:
                    # Обновляем координаты в пикселях изображения
                    item["x"] += int(dx / self.scale)
                    item["y"] += int(dy / self.scale)
                    self.text_drag_start = (x, y)
                    self.update_display()
        elif self.tool == "pen" and self.drawing:
            draw = ImageDraw.Draw(self.working_image)
            draw.line([(self.last_x, self.last_y), (img_x, img_y)], fill=self.pen_color, width=self.pen_size)
            self.update_display()
            self.last_x, self.last_y = img_x, img_y
        elif self.tool == "eraser" and self.drawing:
            self.erase_at(img_x, img_y)

    def on_mouse_up(self, event):
        if self.working_image is None:
            return
        # Проверка, если текст перетаскивался и попал на кнопку удаления
        if self.tool == "move" and self.dragged_text_id is not None:
            # Получаем координаты кнопки удаления на экране
            bin_x = self.delete_bin.winfo_rootx()
            bin_y = self.delete_bin.winfo_rooty()
            bin_w = self.delete_bin.winfo_width()
            bin_h = self.delete_bin.winfo_height()
            # Координаты курсора в момент отпуска
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            if bin_x <= mouse_x <= bin_x+bin_w and bin_y <= mouse_y <= bin_y+bin_h:
                # Удалить текст
                self.delete_text_by_id(self.dragged_text_id)
                self.status.config(text="Текст удалён")
                self.selected_text_id = None
            else:
                self.push_to_history()  # сохраняем перемещение
            self.dragged_text_id = None
            self.update_display()
        elif self.drawing:
            self.push_to_history()
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.drag_active = False

    def delete_text_by_id(self, text_id):
        self.text_items = [item for item in self.text_items if item["id"] != text_id]
        self.push_to_history()
        self.update_display()

    def erase_at(self, x, y):
        if self.original_image is None:
            return
        r = self.pen_size // 2
        x0 = max(0, x - r)
        y0 = max(0, y - r)
        x1 = min(self.working_image.width, x + r)
        y1 = min(self.working_image.height, y + r)
        patch = self.original_image.crop((x0, y0, x1, y1))
        self.working_image.paste(patch, (x0, y0))
        self.update_display()

    def open_text_dialog(self):
        if self.working_image is None:
            self.status.config(text="Загрузите изображение")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавление текста")
        dialog.geometry("450x450")
        dialog.configure(bg="#3c3f41")

        tk.Label(dialog, text="Текст:", bg="#3c3f41", fg="white").pack(pady=5)
        text_entry = tk.Entry(dialog, width=40)
        text_entry.pack(pady=5)

        tk.Label(dialog, text="Цвет:", bg="#3c3f41", fg="white").pack(pady=5)
        color_preview = tk.Button(dialog, text="Выбрать цвет", bg="#000000", fg="white", width=20)
        selected_color = "#000000"
        def choose_col():
            nonlocal selected_color
            col = colorchooser.askcolor(initialcolor=selected_color)[1]
            if col:
                selected_color = col
                color_preview.config(bg=col)
        color_preview.config(command=choose_col)
        color_preview.pack(pady=5)

        tk.Label(dialog, text="Шрифт:", bg="#3c3f41", fg="white").pack(pady=5)
        fonts_list = sorted(tkfont.families())
        font_var = tk.StringVar(value="Arial")
        font_menu = tk.OptionMenu(dialog, font_var, *fonts_list)
        font_menu.config(bg="#5a626e", fg="white")
        font_menu.pack(pady=5)

        tk.Label(dialog, text="Размер:", bg="#3c3f41", fg="white").pack(pady=5)
        size_spin = tk.Spinbox(dialog, from_=8, to=200, width=5)
        size_spin.delete(0, tk.END)
        size_spin.insert(0, "24")
        size_spin.pack(pady=5)

        def add():
            text = text_entry.get().strip()
            if not text:
                dialog.destroy()
                return
            x = self.working_image.width // 2
            y = self.working_image.height // 2
            self.text_items.append({
                "id": self.next_text_id,
                "text": text,
                "x": x,
                "y": y,
                "color": selected_color,
                "font": font_var.get(),
                "size": int(size_spin.get())
            })
            self.next_text_id += 1
            self.push_to_history()
            self.update_display()
            self.status.config(text="Текст добавлен")
            dialog.destroy()

        btn_add = tk.Button(dialog, text="Добавить", command=add, bg="#2ecc71", fg="white")
        btn_add.pack(pady=20)

    def push_to_history(self):
        if self.working_image is None:
            return
        while len(self.history) > self.history_index + 1:
            self.history.pop()
        self.history.append((self.working_image.copy(), [item.copy() for item in self.text_items]))
        self.history_index = len(self.history) - 1
        if len(self.history) > 30:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.working_image, self.text_items = self.history[self.history_index]
            self.working_image = self.working_image.copy()
            self.text_items = [item.copy() for item in self.text_items]
            self.selected_text_id = None
            self.update_display()
            self.status.config(text="Отмена")
        else:
            self.status.config(text="Нечего отменять")

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.working_image, self.text_items = self.history[self.history_index]
            self.working_image = self.working_image.copy()
            self.text_items = [item.copy() for item in self.text_items]
            self.selected_text_id = None
            self.update_display()
            self.status.config(text="Вернуть")
        else:
            self.status.config(text="Нечего возвращать")

    def on_canvas_resize(self, event):
        if self.working_image is not None:
            self.update_display()

    def change_size(self):
        self.pen_size = self.size_var.get()

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.pen_color)[1]
        if color:
            self.pen_color = color
            self.color_btn.config(bg=color)

    def save_image(self):
        if self.working_image is None:
            self.status.config(text="Нет изображения")
            return
        final = self.working_image.copy()
        draw = ImageDraw.Draw(final)
        for item in self.text_items:
            try:
                font = ImageFont.truetype(item["font"] + ".ttf", item["size"])
            except:
                font = ImageFont.load_default()
            draw.text((item["x"], item["y"]), item["text"], fill=item["color"], font=font)
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            final.save(path)
            self.status.config(text=f"Сохранено: {os.path.basename(path)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditor(root)
    root.mainloop()