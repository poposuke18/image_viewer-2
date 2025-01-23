import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import csv
from PIL import Image, ImageTk, ExifTags
import re
import os
import json
import shutil
import subprocess
from datetime import datetime
import pyperclip
from tkinter import messagebox, Menu, filedialog, ttk, simpledialog

# プロンプト要素を分割して表示するためのクラス
class PromptElementFrame(tk.Frame):
    def __init__(self, parent, text, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="white", relief="solid", borderwidth=1)
        
        self.label = tk.Label(self, text=text, bg="white", padx=5, pady=2)
        self.label.pack(side=tk.LEFT)
        
        self.copy_button = tk.Button(self, text="📋", command=lambda: self.copy_text(text))
        self.copy_button.pack(side=tk.RIGHT)
        
    def copy_text(self, text):
        pyperclip.copy(text)

class BatchProcessingWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Batch Processing")
        self.window.geometry("800x600")
        self.window.transient(parent)  # 親ウィンドウに従属させる
        self.window.grab_set()  # モーダルウィンドウとして設定
        
        # 最小化時の挙動を制御
        self.parent = parent
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 入出力パス
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        
        # 処理オプション
        self.process_type = tk.StringVar(value="convert")  # convert または organize
        
        # コンバートオプション
        self.convert_format = tk.StringVar(value="PNG")
        self.enable_rename = tk.BooleanVar(value=False)
        self.rename_format = tk.StringVar(value="original")  # original, model, timestamp
        
        # 整理オプション
        self.organize_by = tk.StringVar(value="model")  # model, vae, date, size
        
        self.include_model = tk.BooleanVar(value=False)
        self.model_position = tk.StringVar(value="after")
        self.include_date = tk.BooleanVar(value=False)
        self.date_position = tk.StringVar(value="after")
        self.include_number = tk.BooleanVar(value=True)
        self.number_digits = tk.StringVar(value="3")

        self.output_type = tk.StringVar(value="same_as_input")
        self.subfolder_name = tk.StringVar(value="output")
        
        self.setup_ui()

    def select_input_folder(self):
        folder = filedialog.askdirectory(parent=self.window)  # parentを指定
        if folder:
            self.input_path.set(folder)
            self.window.lift()  # ウィンドウを前面に
            self.window.focus_force()  # フォーカスを強制的に設定
                
    def select_output_folder(self):
        folder = filedialog.askdirectory(parent=self.window)  # parentを指定
        if folder:
            self.output_path.set(folder)
            self.window.lift()  # ウィンドウを前面に
            self.window.focus_force()  # フォーカスを強制的に設定
        
    def setup_ui(self):
    # パス選択フレーム
        path_frame = ttk.LabelFrame(self.window, text="Folders")
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        # Input Folder
        input_frame = ttk.Frame(path_frame)
        input_frame.pack(fill=tk.X, pady=2)
        ttk.Label(input_frame, text="Input Folder:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(input_frame, textvariable=self.input_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(input_frame, text="Browse", command=self.select_input_folder).pack(side=tk.LEFT, padx=5)
        
        # Output Folder オプション
        output_option_frame = ttk.Frame(path_frame)
        output_option_frame.pack(fill=tk.X, pady=2)
        
        self.output_type = tk.StringVar(value="same_as_input")
        ttk.Radiobutton(output_option_frame, text="Same as Input", 
                        variable=self.output_type, value="same_as_input",
                        command=self.update_output_visibility).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(output_option_frame, text="Create subfolder in Input", 
                        variable=self.output_type, value="subfolder",
                        command=self.update_output_visibility).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(output_option_frame, text="Custom folder", 
                        variable=self.output_type, value="custom",
                        command=self.update_output_visibility).pack(side=tk.LEFT, padx=5)
        
        # サブフォルダー名入力フレーム
        self.subfolder_frame = ttk.Frame(path_frame)
        ttk.Label(self.subfolder_frame, text="Subfolder name:").pack(side=tk.LEFT, padx=5)
        self.subfolder_name = tk.StringVar(value="output")
        ttk.Entry(self.subfolder_frame, textvariable=self.subfolder_name).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # カスタム出力フォルダー選択フレーム
        self.custom_output_frame = ttk.Frame(path_frame)
        ttk.Label(self.custom_output_frame, text="Output Folder:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.custom_output_frame, textvariable=self.output_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(self.custom_output_frame, text="Browse", 
                command=self.select_output_folder).pack(side=tk.LEFT, padx=5)        

        # 処理タイプ選択フレーム
        process_frame = ttk.LabelFrame(self.window, text="Processing Type")
        process_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(process_frame, text="Convert Images", 
                    variable=self.process_type, value="convert",
                    command=self.update_options_visibility).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(process_frame, text="Organize Files", 
                    variable=self.process_type, value="organize",
                    command=self.update_options_visibility).pack(anchor=tk.W, padx=5, pady=2)

        # コンバートオプションフレーム
        self.convert_options_frame = ttk.LabelFrame(self.window, text="Convert Options")
        
        # フォーマット選択
        format_frame = ttk.Frame(self.convert_options_frame)
        format_frame.pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(format_frame, text="Format:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="PNG", variable=self.convert_format, value="PNG").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="JPEG", variable=self.convert_format, value="JPEG").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="WEBP", variable=self.convert_format, value="WEBP").pack(side=tk.LEFT, padx=5)
        
        # リネームオプションの拡張
        rename_frame = ttk.Frame(self.convert_options_frame)
        rename_frame.pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(rename_frame, text="Rename Files", 
                    variable=self.enable_rename,
                    command=self.update_options_visibility).pack(side=tk.LEFT, padx=5)

        # カスタム名前入力フレーム
        self.rename_options_frame = ttk.Frame(self.convert_options_frame)
        custom_name_frame = ttk.Frame(self.rename_options_frame)
        custom_name_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(custom_name_frame, text="Base Name:").pack(side=tk.LEFT, padx=5)
        self.custom_name_entry = ttk.Entry(custom_name_frame)
        self.custom_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # モデル名と日付のオプション
        options_frame = ttk.Frame(self.rename_options_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=2)

        # モデル名オプション
        self.include_model = tk.BooleanVar(value=False)
        self.model_position = tk.StringVar(value="after")
        model_frame = ttk.Frame(options_frame)
        model_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(model_frame, text="Include Model Name", 
                        variable=self.include_model).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(model_frame, text="Before", variable=self.model_position, 
                        value="before").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(model_frame, text="After", variable=self.model_position, 
                        value="after").pack(side=tk.LEFT, padx=5)

        # 日付オプション
        self.include_date = tk.BooleanVar(value=False)
        self.date_position = tk.StringVar(value="after")
        date_frame = ttk.Frame(options_frame)
        date_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(date_frame, text="Include Date", 
                        variable=self.include_date).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(date_frame, text="Before", variable=self.date_position, 
                        value="before").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(date_frame, text="After", variable=self.date_position, 
                        value="after").pack(side=tk.LEFT, padx=5)

        # 連番オプション
        numbering_frame = ttk.Frame(options_frame)
        numbering_frame.pack(fill=tk.X, pady=2)
        self.include_number = tk.BooleanVar(value=True)
        self.number_digits = tk.StringVar(value="3")
        ttk.Checkbutton(numbering_frame, text="Include Number", 
                        variable=self.include_number).pack(side=tk.LEFT, padx=5)
        ttk.Label(numbering_frame, text="Digits:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(numbering_frame, textvariable=self.number_digits, 
                width=5).pack(side=tk.LEFT, padx=5)
        
        # 整理オプションフレーム
        self.organize_options_frame = ttk.LabelFrame(self.window, text="Organization Options")
        
        ttk.Radiobutton(self.organize_options_frame, text="By Model", 
                    variable=self.organize_by, value="model").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(self.organize_options_frame, text="By VAE", 
                    variable=self.organize_by, value="vae").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(self.organize_options_frame, text="By Date", 
                    variable=self.organize_by, value="date").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(self.organize_options_frame, text="By Size", 
                    variable=self.organize_by, value="size").pack(anchor=tk.W, padx=5, pady=2)
        
        # 進行状況フレーム
        progress_frame = ttk.LabelFrame(self.window, text="Progress")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(padx=5, pady=5)
        
        # 実行ボタン
        ttk.Button(self.window, text="Start Processing", command=self.start_processing).pack(pady=10)
        
        # 初期表示状態の設定
        self.update_options_visibility()

    def update_options_visibility(self):
        if self.process_type.get() == "convert":
            self.convert_options_frame.pack(fill=tk.X, padx=5, pady=5)
            self.organize_options_frame.pack_forget()
            # リネームオプションの表示/非表示
            if self.enable_rename.get():
                self.rename_options_frame.pack(anchor=tk.W, padx=20, pady=2)
            else:
                self.rename_options_frame.pack_forget()
        else:  # organize
            self.convert_options_frame.pack_forget()
            self.organize_options_frame.pack(fill=tk.X, padx=5, pady=5)
            
    def on_closing(self):
        self.window.grab_release()  # モーダル状態を解除
        self.window.destroy()

    def update_output_visibility(self):
        """出力フォルダーの選択タイプに応じてUIを更新"""
        output_type = self.output_type.get()
        
        # 全てのフレームを一旦非表示
        self.subfolder_frame.pack_forget()
        self.custom_output_frame.pack_forget()
        
        # 選択に応じて必要なフレームを表示
        if output_type == "subfolder":
            self.subfolder_frame.pack(fill=tk.X, pady=2)
        elif output_type == "custom":
            self.custom_output_frame.pack(fill=tk.X, pady=2)

    def start_processing(self):
        # 入力フォルダーのチェック
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select input folder")
            return
        
        if not os.path.exists(self.input_path.get()):
            messagebox.showerror("Error", "Input folder does not exist")
            return
        
        # 出力フォルダーの設定
        output_type = self.output_type.get()
        if output_type == "same_as_input":
            self.output_path.set(self.input_path.get())
        elif output_type == "subfolder":
            subfolder = self.subfolder_name.get().strip()
            if not subfolder:
                messagebox.showerror("Error", "Please enter subfolder name")
                return
            self.output_path.set(os.path.join(self.input_path.get(), subfolder))
        else:  # custom
            if not self.output_path.get():
                messagebox.showerror("Error", "Please select output folder")
                return
        
        # 出力フォルダーの作成
        if not os.path.exists(self.output_path.get()):
            try:
                os.makedirs(self.output_path.get())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder: {str(e)}")
                return

        # 処理対象のファイルを取得
        image_files = []
        for root, _, files in os.walk(self.input_path.get()):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_files.append(os.path.join(root, file))

        if not image_files:
            messagebox.showinfo("Info", "No image files found in input folder")
            return

        total_files = len(image_files)
        
        for i, file_path in enumerate(image_files):
            try:
                # 進捗状況の更新
                progress = (i + 1) / total_files * 100
                self.progress_var.set(progress)
                self.status_var.set(f"Processing {i+1}/{total_files}: {os.path.basename(file_path)}")
                self.window.update()

                if self.process_type.get() == "convert":
                    self.process_convert_file(file_path, i)  # インデックスiを渡す
                else:  # organize
                    self.process_organize_file(file_path)

            except Exception as e:
                messagebox.showerror("Error", f"Error processing {file_path}: {str(e)}")

        messagebox.showinfo("Success", "Processing completed!")

    def process_convert_file(self, file_path, index):
        # 画像を開く
        image = Image.open(file_path)
        output_format = self.convert_format.get()
        
        # 出力ファイル名の生成
        if self.enable_rename.get():
            output_filename = self.generate_new_filename(file_path, image, index)
        else:
            output_filename = os.path.basename(file_path)
        
        # 拡張子の変更
        base_name = os.path.splitext(output_filename)[0]
        output_filename = f"{base_name}.{output_format.lower()}"
        output_path = os.path.join(self.output_path.get(), output_filename)

        # JPEGの場合は背景を白にして保存
        if output_format == "JPEG":
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                background.save(output_path, format=output_format, quality=95)
            else:
                image.save(output_path, format=output_format, quality=95)
        else:
            image.save(output_path, format=output_format)

    def process_organize_file(self, file_path):
        # 画像を開いてメタデータを取得
        image = Image.open(file_path)
        organize_by = self.organize_by.get()
        
        # 整理方法に基づいてサブフォルダを決定
        if organize_by == "model":
            info = image.info.get("parameters", "")
            model_match = re.search(r"Model:\s*(.*?)(,|$)", info)
            subfolder = model_match.group(1).split('_')[0] if model_match else "Unknown"
        elif organize_by == "vae":
            info = image.info.get("parameters", "")
            vae_match = re.search(r"VAE:\s*(.*?)(,|$)", info)
            subfolder = vae_match.group(1).split('_')[0] if vae_match else "Unknown"
        elif organize_by == "date":
            creation_time = os.path.getctime(file_path)
            subfolder = datetime.fromtimestamp(creation_time).strftime("%Y-%m")
        else:  # size
            width, height = image.size
            ratio = width / height
            if 0.9 <= ratio <= 1.1:
                subfolder = "Square"
            elif ratio > 1.1:
                subfolder = "Landscape"
            else:
                subfolder = "Portrait"

        # サブフォルダの作成と移動
        subfolder_path = os.path.join(self.output_path.get(), subfolder)
        os.makedirs(subfolder_path, exist_ok=True)
        
        output_path = os.path.join(subfolder_path, os.path.basename(file_path))
        shutil.copy2(file_path, output_path)

    def generate_new_filename(self, file_path, image, index):
        # ベース名を取得
        base_name = self.custom_name_entry.get().strip()
        if not base_name:
            base_name = os.path.splitext(os.path.basename(file_path))[0]

        # 連番を生成
        if self.include_number.get():
            digits = int(self.number_digits.get())
            number = str(index).zfill(digits)
        else:
            number = ""

        # モデル名を取得
        model_name = ""
        if self.include_model.get():
            info = image.info.get("parameters", "")
            model_match = re.search(r"Model:\s*(.*?)(,|$)", info)
            if model_match:
                model_name = model_match.group(1).split('_')[0]

        # 日付を取得
        date_str = ""
        if self.include_date.get():
            date_str = datetime.now().strftime("%Y%m%d")

        # 名前の組み立て
        elements = []
        
        # 前置要素
        if self.include_model.get() and self.model_position.get() == "before" and model_name:
            elements.append(model_name)
        if self.include_date.get() and self.date_position.get() == "before" and date_str:
            elements.append(date_str)
        
        # ベース名と連番
        if base_name:
            elements.append(base_name)
        if number:
            elements.append(number)
        
        # 後置要素
        if self.include_model.get() and self.model_position.get() == "after" and model_name:
            elements.append(model_name)
        if self.include_date.get() and self.date_position.get() == "after" and date_str:
            elements.append(date_str)
        
        return "_".join(elements)

class FavoritePromptsManager:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Favorite Prompts")
        self.window.geometry("800x600")
        self.window.transient(parent)  # 親ウィンドウに従属させる
        self.window.grab_set()  # モーダルウィンドウとして設定
        
        # 最小化時の挙動を制御
        self.parent = parent
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.favorites_file = "favorite_prompts.json"
        self.favorites = self.load_favorites()
        self.category_var = tk.StringVar(value="General")
        
        self.setup_ui()
    
    def setup_ui(self):
    # カテゴリ管理フレーム
        category_frame = ttk.LabelFrame(self.window, text="Categories")
        category_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 既存のself.category_varは削除（__init__で定義済み）
        self.category_combo = ttk.Combobox(category_frame, textvariable=self.category_var)
        self.category_combo['values'] = list(self.favorites.keys())
        # 初期値を設定
        if "General" in self.favorites.keys():
            self.category_var.set("General")
            self.category_combo.set("General")
        self.category_combo.pack(side=tk.LEFT, padx=5)
        
        # カテゴリー変更時のイベントバインドを追加
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_changed)
    
        ttk.Button(category_frame, text="Add Category", command=self.add_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(category_frame, text="Remove Category", command=self.remove_category).pack(side=tk.LEFT, padx=5)
    
        # プロンプトリストフレーム
        prompts_frame = ttk.LabelFrame(self.window, text="Prompts")
        prompts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # プロンプトリストと入力エリアを横に並べるフレーム
        list_input_frame = ttk.Frame(prompts_frame)
        list_input_frame.pack(fill=tk.BOTH, expand=True)
        
        # リストボックスフレーム（左側）
        list_frame = ttk.Frame(list_input_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.prompt_listbox = tk.Listbox(list_frame)
        self.prompt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.prompt_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 入力エリアフレーム（右側）
        input_frame = ttk.Frame(list_input_frame)
        input_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # プロンプト名入力フレーム
        name_frame = ttk.Frame(input_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Prompt Name:").pack(side=tk.LEFT, padx=5)
        self.prompt_name_entry = ttk.Entry(name_frame)
        self.prompt_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Positive Promptフレーム
        pos_frame = ttk.LabelFrame(input_frame, text="Positive Prompt")
        pos_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.pos_prompt_text = tk.Text(pos_frame, height=5)
        self.pos_prompt_text.pack(fill=tk.BOTH, expand=True)
        
        # Negative Promptフレーム
        neg_frame = ttk.LabelFrame(input_frame, text="Negative Prompt")
        neg_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.neg_prompt_text = tk.Text(neg_frame, height=5)
        self.neg_prompt_text.pack(fill=tk.BOTH, expand=True)
        
        # ボタンフレーム
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Save Prompt", command=self.save_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Delete Prompt", command=self.remove_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Copy to Clipboard", command=self.copy_prompt).pack(side=tk.LEFT, padx=5)
        
        # リストボックスの選択イベント
        self.prompt_listbox.bind('<<ListboxSelect>>', self.on_select_prompt)
        self.update_prompts_list()


    def add_category(self):
        """新しいカテゴリを追加"""
        category = simpledialog.askstring("Add Category", "Enter new category name:")
        if category and category not in self.favorites:
            self.favorites[category] = []
            self.category_combo['values'] = list(self.favorites.keys())
            self.save_favorites()
            self.category_var.set(category)

    def on_closing(self):
        self.window.grab_release()  # モーダル状態を解除
        self.window.destroy()

    def remove_category(self):
        """現在選択されているカテゴリを削除"""
        category = self.category_var.get()
        if category == "General":
            messagebox.showwarning("Warning", "Cannot delete General category")
            return
            
        if category and messagebox.askyesno("Confirm", f"Delete category '{category}'?"):
            del self.favorites[category]
            self.category_combo['values'] = list(self.favorites.keys())
            self.save_favorites()
            self.category_var.set("General")
            self.update_prompts_list()

    def on_category_changed(self, event=None):
        """カテゴリが変更された時の処理"""
        category = self.category_var.get()
        # 入力欄をクリア
        self.prompt_name_entry.delete(0, tk.END)
        self.pos_prompt_text.delete("1.0", tk.END)
        self.neg_prompt_text.delete("1.0", tk.END)
        # リストを更新
        self.update_prompts_list()

    def remove_prompt(self):
        """選択されているプロンプトを削除"""
        selection = self.prompt_listbox.curselection()
        if selection:
            category = self.category_var.get() or "General"
            index = selection[0]
            del self.favorites[category][index]
            self.save_favorites()
            self.update_prompts_list()

    def copy_prompt(self):
        """選択されているプロンプトをクリップボードにコピー"""
        selection = self.prompt_listbox.curselection()
        if selection:
            category = self.category_var.get() or "General"
            index = selection[0]
            prompt_data = self.favorites[category][index]
            
            copy_text = f"""Positive Prompt:
    {prompt_data.get('positive', '')}

    Negative Prompt:
    {prompt_data.get('negative', '')}"""
            
            pyperclip.copy(copy_text)
            messagebox.showinfo("Success", "Prompt copied to clipboard!")

    def on_category_changed(self, event=None):
        """カテゴリが変更された時の処理"""
        self.update_prompts_list()
        
    def save_prompt(self):
        category = self.category_var.get() or "General"
        prompt_name = self.prompt_name_entry.get().strip()
        pos_prompt = self.pos_prompt_text.get("1.0", tk.END).strip()
        neg_prompt = self.neg_prompt_text.get("1.0", tk.END).strip()
        
        if not prompt_name:
            messagebox.showwarning("Warning", "Please enter a prompt name")
            return
        
        if not pos_prompt and not neg_prompt:
            messagebox.showwarning("Warning", "Please enter prompt content")
            return
        
        if category not in self.favorites:
            self.favorites[category] = []
        
        prompt_data = {
            "name": prompt_name,
            "positive": pos_prompt,
            "negative": neg_prompt
        }
        
        # 同じ名前のプロンプトが存在するか確認
        for i, existing_prompt in enumerate(self.favorites[category]):
            if existing_prompt.get("name") == prompt_name:
                # 更新の確認
                if messagebox.askyesno("Update Prompt", f"Prompt '{prompt_name}' already exists. Update it?"):
                    self.favorites[category][i] = prompt_data
                    self.save_favorites()
                    self.update_prompts_list()
                return
        
        # 新規追加
        self.favorites[category].append(prompt_data)
        self.save_favorites()
        self.update_prompts_list()
        
    def load_favorites(self):
        try:
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"General": []}
            
    def save_favorites(self):
        with open(self.favorites_file, 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)
            
    def on_select_prompt(self, event):
        selection = self.prompt_listbox.curselection()
        if selection:
            category = self.category_var.get() or "General"
            index = selection[0]
            prompt_data = self.favorites[category][index]
            
            self.prompt_name_entry.delete(0, tk.END)
            self.prompt_name_entry.insert(0, prompt_data.get("name", ""))
            
            self.pos_prompt_text.delete("1.0", tk.END)
            self.neg_prompt_text.delete("1.0", tk.END)
            
            self.pos_prompt_text.insert("1.0", prompt_data.get("positive", ""))
            self.neg_prompt_text.insert("1.0", prompt_data.get("negative", ""))

    def update_prompts_list(self):
        self.prompt_listbox.delete(0, tk.END)
        category = self.category_var.get() or "General"
        prompts = self.favorites.get(category, [])
        
        for prompt in prompts:
            name = prompt.get("name", "Unnamed")
            self.prompt_listbox.insert(tk.END, name)

class ImageMetadataViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced AI Image Metadata Viewer")
        self.root.geometry("800x700")
        self.root.configure(bg="#f4f4f4")

        self.root.bind("<Unmap>", self.on_minimize)
    
    # 各種テキスト変数の初期化
        self.current_file_path = None  # 現在表示中のファイルパスを保存
        self.image_info_text = tk.StringVar()
        self.model_text = tk.StringVar()
        self.vae_text = tk.StringVar()
        self.prompt_text = tk.StringVar()
        self.negative_prompt_text = tk.StringVar()
        self.other_parameters_text = tk.StringVar()
    
        self.setup_ui()
        self.create_menu()

    def format_parameters(self, params_text):
        formatted_params = {}
        for param in params_text.split(", "):
            if ": " in param:
                key, value = param.split(": ", 1)
                formatted_params[key.strip()] = value.strip()
        
        formatted_text = ""
        for key, value in formatted_params.items():
            formatted_text += f"{key}: {value}\n"
        
        return formatted_text

    def on_minimize(self, event):
        if event.widget is self.root:
            # 子ウィンドウの状態も保存して最小化
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    child.withdraw()
                    child.grab_release()

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        self.menubar = menubar
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open containing folder", command=self.open_containing_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Transform submenu
        transform_menu = Menu(edit_menu, tearoff=0)
        edit_menu.add_cascade(label="Transform", menu=transform_menu)
        transform_menu.add_command(label="Flip Horizontal", command=self.flip_horizontal)
        transform_menu.add_command(label="Flip Vertical", command=self.flip_vertical)
        transform_menu.add_command(label="Rotate 90° Right", command=self.rotate_right)
        transform_menu.add_command(label="Rotate 90° Left", command=self.rotate_left)
        
        # Convert submenu
        convert_menu = Menu(edit_menu, tearoff=0)
        edit_menu.add_cascade(label="Convert to", menu=convert_menu)
        convert_menu.add_command(label="PNG", command=lambda: self.convert_image("PNG"))
        convert_menu.add_command(label="JPEG", command=lambda: self.convert_image("JPEG"))
        convert_menu.add_command(label="WEBP", command=lambda: self.convert_image("WEBP"))
        
        # リサイズとトリミング
        edit_menu.add_command(label="Resize...", command=self.show_resize_dialog)
        edit_menu.add_command(label="Crop...", command=self.show_crop_dialog)
        
        # メタデータ編集
        edit_menu.add_separator()
        edit_menu.add_command(label="Edit Metadata...", command=self.show_metadata_editor)

        # Favorites menu
        favorites_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Favorites", menu=favorites_menu)
        favorites_menu.add_command(label="Manage Favorites", command=self.show_favorites_manager)

        # Batch menu
        batch_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Batch", menu=batch_menu)
        batch_menu.add_command(label="Batch Process", command=self.show_batch_processor)

    def flip_horizontal(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
        try:
            image = Image.open(self.current_file_path)
            flipped = image.transpose(Image.FLIP_LEFT_RIGHT)
            self.save_edited_image(flipped, "flipped_h")
        except Exception as e:
            messagebox.showerror("Error", f"Error flipping image: {str(e)}")

    def flip_vertical(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
        try:
            image = Image.open(self.current_file_path)
            flipped = image.transpose(Image.FLIP_TOP_BOTTOM)
            self.save_edited_image(flipped, "flipped_v")
        except Exception as e:
            messagebox.showerror("Error", f"Error flipping image: {str(e)}")

    def rotate_right(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
        try:
            image = Image.open(self.current_file_path)
            rotated = image.rotate(-90, expand=True)
            self.save_edited_image(rotated, "rotated_r")
        except Exception as e:
            messagebox.showerror("Error", f"Error rotating image: {str(e)}")

    def rotate_left(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
        try:
            image = Image.open(self.current_file_path)
            rotated = image.rotate(90, expand=True)
            self.save_edited_image(rotated, "rotated_l")
        except Exception as e:
            messagebox.showerror("Error", f"Error rotating image: {str(e)}")

    def show_resize_dialog(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
            
        # 現在の画像サイズを取得
        image = Image.open(self.current_file_path)
        original_width, original_height = image.size
        
        # ダイアログウィンドウの作成
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Image")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # サイズ入力フレーム
        size_frame = ttk.LabelFrame(dialog, text="New Size")
        size_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # 幅の入力
        width_frame = ttk.Frame(size_frame)
        width_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        width_var = tk.StringVar(value=str(original_width))
        width_entry = ttk.Entry(width_frame, textvariable=width_var, width=10)
        width_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(width_frame, text="px").pack(side=tk.LEFT)
        
        # 高さの入力
        height_frame = ttk.Frame(size_frame)
        height_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(height_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        height_var = tk.StringVar(value=str(original_height))
        height_entry = ttk.Entry(height_frame, textvariable=height_var, width=10)
        height_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(height_frame, text="px").pack(side=tk.LEFT)
        
        # アスペクト比維持のチェックボックス
        maintain_aspect = tk.BooleanVar(value=True)
        ttk.Checkbutton(size_frame, text="Maintain aspect ratio", 
                        variable=maintain_aspect).pack(padx=5, pady=5)
        
        def update_height(*args):
            if maintain_aspect.get():
                try:
                    new_width = int(width_var.get())
                    new_height = int(new_width * original_height / original_width)
                    height_var.set(str(int(new_height)))
                except ValueError:
                    pass
                    
        def update_width(*args):
            if maintain_aspect.get():
                try:
                    new_height = int(height_var.get())
                    new_width = int(new_height * original_width / original_height)
                    width_var.set(str(int(new_width)))
                except ValueError:
                    pass
        
        # アスペクト比維持時の自動更新
        width_var.trace_add("write", update_height)
        height_var.trace_add("write", update_width)
        
        # OKボタンの処理
        def on_ok():
            try:
                new_width = int(width_var.get())
                new_height = int(height_var.get())
                if new_width <= 0 or new_height <= 0:
                    raise ValueError("Size must be positive")
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.save_edited_image(resized, "resized")
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        # ボタンフレーム
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def setup_prompt_elements(self, frame, prompt_text):
        elements = prompt_text.split(",")
        for element in elements:
            element = element.strip()
            if element:
                element_frame = PromptElementFrame(frame, element)
                element_frame.pack(side=tk.LEFT, padx=2, pady=2)

    def save_edited_image(self, edited_image, suffix):
        # オリジナルのファイルパスから情報を取得
        original_dir = os.path.dirname(self.current_file_path)
        original_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        original_ext = os.path.splitext(self.current_file_path)[1]
        
        # 新しいファイル名を生成（例: image_resized.png）
        new_filename = f"{original_name}_{suffix}{original_ext}"
        
        # 保存先を選択
        save_path = filedialog.asksaveasfilename(
            initialdir=original_dir,
            initialfile=new_filename,
            defaultextension=original_ext,
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg;*.jpeg"),
                ("WEBP files", "*.webp"),
                ("All files", "*.*")
            ]
        )
        
        if save_path:
            try:
                # 画像を保存
                if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                    # JPEGの場合は背景を白にして保存
                    if edited_image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', edited_image.size, (255, 255, 255))
                        background.paste(edited_image, mask=edited_image.split()[-1])
                        background.save(save_path, quality=95)
                    else:
                        edited_image.save(save_path, quality=95)
                else:
                    edited_image.save(save_path)
                
                # メタデータの保持
                if "parameters" in Image.open(self.current_file_path).info:
                    original_metadata = Image.open(self.current_file_path).info["parameters"]
                    with Image.open(save_path) as img:
                        img.info["parameters"] = original_metadata
                        img.save(save_path)
                
                messagebox.showinfo("Success", "Image saved successfully!")
                
                # 保存した画像を現在の画像として表示
                self.current_file_path = save_path
                self.display_metadata(save_path)
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving image: {str(e)}")

    def show_batch_processor(self):
        BatchProcessingWindow(self.root)

    def show_metadata_editor(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return

        # メタデータ編集用のウィンドウを作成
        editor = tk.Toplevel(self.root)
        editor.title("Edit Metadata")
        editor.geometry("600x800")
        editor.transient(self.root)
        editor.grab_set()

        # プロンプト編集フレーム
        prompt_frame = ttk.LabelFrame(editor, text="Positive Prompt")
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        prompt_text = tk.Text(prompt_frame, height=8, wrap=tk.WORD)
        prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        prompt_text.insert("1.0", self.prompt_text.get())

        # ネガティブプロンプト編集フレーム
        neg_prompt_frame = ttk.LabelFrame(editor, text="Negative Prompt")
        neg_prompt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        neg_prompt_text = tk.Text(neg_prompt_frame, height=8, wrap=tk.WORD)
        neg_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        neg_prompt_text.insert("1.0", self.negative_prompt_text.get())

        # その他のパラメータ編集フレーム
        params_frame = ttk.LabelFrame(editor, text="Parameters")
        params_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # モデル名とVAE
        model_frame = ttk.Frame(params_frame)
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT, padx=5)
        model_var = tk.StringVar(value=self.model_text.get())
        ttk.Entry(model_frame, textvariable=model_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        vae_frame = ttk.Frame(params_frame)
        vae_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(vae_frame, text="VAE:").pack(side=tk.LEFT, padx=5)
        vae_var = tk.StringVar(value=self.vae_text.get())
        ttk.Entry(vae_frame, textvariable=vae_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # その他のパラメータ
        other_params_text = tk.Text(params_frame, height=8, wrap=tk.WORD)
        other_params_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        other_params_text.insert("1.0", self.other_parameters_text.get())

        def save_metadata():
            try:
                # メタデータを構築
                parameters = prompt_text.get("1.0", "end-1c")
                parameters += "\nNegative prompt: " + neg_prompt_text.get("1.0", "end-1c")
                if other_params_text.get("1.0", "end-1c").strip():
                    parameters += "\n" + other_params_text.get("1.0", "end-1c")

                # モデルとVAEの情報を更新
                if "Model:" not in parameters:
                    parameters = f"Model: {model_var.get()}, " + parameters
                if "VAE:" not in parameters:
                    parameters = f"VAE: {vae_var.get()}, " + parameters

                # 画像を開いてメタデータを更新
                image = Image.open(self.current_file_path)
                image.info["parameters"] = parameters

                # 保存先を選択
                save_path = filedialog.asksaveasfilename(
                    initialdir=os.path.dirname(self.current_file_path),
                    initialfile=os.path.basename(self.current_file_path),
                    defaultextension=os.path.splitext(self.current_file_path)[1],
                    filetypes=[
                        ("PNG files", "*.png"),
                        ("JPEG files", "*.jpg;*.jpeg"),
                        ("WEBP files", "*.webp"),
                        ("All files", "*.*")
                    ]
                )

                if save_path:
                    # 画像を保存
                    image.save(save_path, pnginfo=image.info)
                    messagebox.showinfo("Success", "Metadata saved successfully!")
                    
                    # 現在の画像として設定
                    self.current_file_path = save_path
                    self.display_metadata(save_path)
                    
                    # エディタを閉じる
                    editor.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Error saving metadata: {str(e)}")

        # ボタンフレーム
        button_frame = ttk.Frame(editor)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Save", command=save_metadata).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=editor.destroy).pack(side=tk.LEFT, padx=5)

    def show_crop_dialog(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return

        # クロップ用のウィンドウを作成
        crop_window = tk.Toplevel(self.root)
        crop_window.title("Crop Image")
        crop_window.geometry("800x600")
        crop_window.transient(self.root)
        crop_window.grab_set()

        # 画像を読み込み
        image = Image.open(self.current_file_path)
        
        # キャンバスのサイズに合わせて画像をリサイズ
        display_size = (780, 500)  # キャンバスサイズ
        image.thumbnail(display_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)

        # キャンバスの作成
        canvas = tk.Canvas(crop_window, width=display_size[0], height=display_size[1])
        canvas.pack(pady=5)
        canvas.create_image(0, 0, image=photo, anchor="nw")

        # クロップ範囲の初期化
        crop_rect = None
        start_x = None
        start_y = None
        scale_factor_x = image.size[0] / display_size[0]
        scale_factor_y = image.size[1] / display_size[1]

        def start_crop(event):
            nonlocal start_x, start_y, crop_rect
            start_x = event.x
            start_y = event.y
            if crop_rect:
                canvas.delete(crop_rect)
            crop_rect = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline='red', width=2
            )

        def drag_crop(event):
            nonlocal crop_rect
            if start_x is not None:
                if crop_rect:
                    canvas.coords(crop_rect, start_x, start_y, event.x, event.y)

        def end_crop(event):
            nonlocal start_x, start_y
            if start_x is None or start_y is None:
                return

            end_x = event.x
            end_y = event.y

            # 座標を並び替え
            left = min(start_x, end_x)
            top = min(start_y, end_y)
            right = max(start_x, end_x)
            bottom = max(start_y, end_y)

            # 実際の画像サイズに変換
            orig_left = int(left * scale_factor_x)
            orig_top = int(top * scale_factor_y)
            orig_right = int(right * scale_factor_x)
            orig_bottom = int(bottom * scale_factor_y)

            # クロップを実行
            try:
                original_image = Image.open(self.current_file_path)
                cropped = original_image.crop((orig_left, orig_top, orig_right, orig_bottom))
                self.save_edited_image(cropped, "cropped")
                crop_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error cropping image: {str(e)}")

        # マウスイベントのバインド
        canvas.bind("<ButtonPress-1>", start_crop)
        canvas.bind("<B1-Motion>", drag_crop)
        canvas.bind("<ButtonRelease-1>", end_crop)

        # 説明ラベル
        ttk.Label(crop_window, 
                text="Click and drag to select crop area. Release mouse button to crop.").pack(pady=5)

        # キャンセルボタン
        ttk.Button(crop_window, text="Cancel", 
                command=crop_window.destroy).pack(pady=5)

        # 画像の参照を保持
        crop_window.photo = photo

    def convert_image(self, format_):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
            
        try:
            image = Image.open(self.current_file_path)
            save_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_.lower()}",
                filetypes=[(f"{format_} files", f"*.{format_.lower()}")])
            
            if save_path:
                image.save(save_path, format_)
                messagebox.showinfo("Success", f"Image saved as {format_}")
        except Exception as e:
            messagebox.showerror("Error", f"Error converting image: {str(e)}")

    def open_containing_folder(self):
        if self.current_file_path:
            folder_path = os.path.dirname(self.current_file_path)
            try:
                os.startfile(folder_path)  # Windowsの場合
            except AttributeError:
                subprocess.run(['xdg-open', folder_path])  # Linuxの場合
        else:
            messagebox.showinfo("Info", "No image is currently loaded")

    def copy_all_metadata(self):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is currently loaded")
            return
            
        metadata = f"""Image Information:
{self.image_info_text.get()}

Model: {self.model_text.get()}
VAE: {self.vae_text.get()}

Prompt:
{self.prompt_text.get()}

Negative Prompt:
{self.negative_prompt_text.get()}

Other Parameters:
{self.other_parameters_text.get()}"""
        
        pyperclip.copy(metadata)

    def copy_text(self, text):
        if text:
            pyperclip.copy(text)
        else:
            messagebox.showinfo("Info", "No text to copy")

    def on_drop(self, event):
        file_path = event.data.strip('{}')
        self.current_file_path = file_path
        self.display_metadata(file_path)

    def show_favorites_manager(self):
        FavoritePromptsManager(self.root)

    def setup_ui(self):
        # ドラッグ&ドロップエリア
        self.drop_area = tk.Label(self.root, text="Drag & Drop an image here",
                            font=("Meiryo", 12, "bold"),
                            bg="#e0e0e0", fg="#333333",
                            width=40, height=2, relief="ridge", bd=2)
        self.drop_area.pack(pady=10)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.on_drop)

        # 画像表示エリア
        self.frame = tk.Frame(self.root, bg="#f4f4f4")
        self.frame.pack(pady=10)
        
        self.image_label = tk.Label(self.frame, bg="white",
                                  width=200, height=200, relief="solid")
        self.image_label.grid(row=0, column=0, padx=10)
        
        self.image_info_label = tk.Label(self.frame, textvariable=self.image_info_text, 
                                       font=("Meiryo", 10), bg="#f4f4f4", justify="left")
        self.image_info_label.grid(row=0, column=1, sticky="nw")

        # ModelとVAEの表示エリア
        model_frame = tk.Frame(self.root, bg="#f4f4f4")
        model_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(model_frame, text="Model:", font=("Meiryo", 10, "bold"), 
                bg="#f4f4f4").pack(side=tk.LEFT, padx=5)
        tk.Label(model_frame, textvariable=self.model_text, 
                font=("Meiryo", 10), bg="#f4f4f4").pack(side=tk.LEFT, padx=5)

        tk.Label(model_frame, text="VAE:", font=("Meiryo", 10, "bold"), 
                bg="#f4f4f4").pack(side=tk.LEFT, padx=20)
        tk.Label(model_frame, textvariable=self.vae_text, 
                font=("Meiryo", 10), bg="#f4f4f4").pack(side=tk.LEFT, padx=5)

        # テキスト表示エリアの作成
        self.setup_text_sections()

    def setup_text_sections(self):
        section_frame = tk.Frame(self.root, bg="#f4f4f4")
        section_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # プロンプト、ネガティブプロンプト、その他パラメータの表示セクション
        self.create_text_section(section_frame, "Prompt", self.prompt_text)
        self.create_text_section(section_frame, "Negative Prompt", self.negative_prompt_text)
        self.create_text_section(section_frame, "Other Parameters", self.other_parameters_text)

    def create_text_section(self, parent, label_text, text_variable):
        section_label = tk.Label(parent, text=label_text, font=("Meiryo", 10, "bold"), 
                               bg="#f4f4f4")
        section_label.pack(anchor="w", padx=5)

        container = tk.Frame(parent, bg="white", relief="solid", borderwidth=1)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_box = tk.Text(container, font=("Meiryo", 10), wrap="word", 
                          yscrollcommand=scrollbar.set, relief="flat", height=5)
        text_box.pack(fill=tk.BOTH, expand=True)
        
        # 右クリックメニューの追加
        self.add_right_click_menu(text_box)
        
        scrollbar.config(command=text_box.yview)

        text_box.insert("1.0", text_variable.get())
        text_box.config(state="disabled")
        
        # テキスト更新時の処理を設定
        text_variable.trace_add("write", 
                              lambda *args: self.update_text(text_box, text_variable))

    def add_right_click_menu(self, widget):
        menu = Menu(widget, tearoff=0)
        menu.add_command(label="Copy", command=lambda: self.copy_text(widget.get("1.0", "end-1c")))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)  # Windows/Linux
        widget.bind("<Button-2>", show_menu)  # Mac

    def display_metadata(self, filepath):
        try:
            image = Image.open(filepath)
            img_thumbnail = image.copy()
            img_thumbnail.thumbnail((200, 200))
            img_tk = ImageTk.PhotoImage(img_thumbnail)

            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
            self.image_label.drop_target_register(DND_FILES)
            self.image_label.dnd_bind('<<Drop>>', self.on_drop)

            # ドラッグ＆ドロップ枠を非表示
            self.drop_area.pack_forget()

            # 基本情報の表示
            file_size = os.path.getsize(filepath) // 1024
            creation_time = os.path.getctime(filepath)
            creation_time_str = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
            
            image_info = f"File: {os.path.basename(filepath)}\n"
            image_info += f"Format: {image.format}\n"
            image_info += f"Size: {image.size[0]} x {image.size[1]} pixels\n"
            image_info += f"File Size: {file_size} KB\n"
            image_info += f"Mode: {image.mode}\n"
            image_info += f"Created: {creation_time_str}"
            
            self.image_info_text.set(image_info)

            # AI生成パラメータの取得と表示
            self.extract_ai_parameters(image)

        except Exception as e:
            messagebox.showerror("Error", f"Error loading image: {str(e)}")
            self.reset_display()

    def extract_ai_parameters(self, image):
        info = image.info
        if "parameters" in info:
            parameters = info["parameters"]

            # ModelとVAEの抽出
            model_match = re.search(r"Model:\s*(.*?)(,|$)", parameters)
            vae_match = re.search(r"VAE:\s*(.*?)(,|$)", parameters)
            self.model_text.set(model_match.group(1) if model_match else "N/A")
            self.vae_text.set(vae_match.group(1) if vae_match else "N/A")

            # プロンプト等の抽出
            prompt_match = re.search(r"^(.*?)(Negative prompt:)", parameters, re.DOTALL)
            negative_prompt_match = re.search(r"Negative prompt:\s*(.*?)(Steps:)", parameters, re.DOTALL)
            other_parameters_match = re.search(r"(Steps:.*)", parameters, re.DOTALL)

            self.prompt_text.set(prompt_match.group(1).strip() if prompt_match else "No Prompt Found")
            self.negative_prompt_text.set(negative_prompt_match.group(1).strip() if negative_prompt_match else "No Negative Prompt Found")
            self.other_parameters_text.set(other_parameters_match.group(1).strip() if other_parameters_match else "No Other Parameters Found")
        else:
            self.reset_parameters()

    def reset_display(self):
        self.current_file_path = None
        self.image_info_text.set("")
        self.reset_parameters()
        self.drop_area.pack(pady=10)
        self.image_label.config(image="")

    def reset_parameters(self):
        self.model_text.set("N/A")
        self.vae_text.set("N/A")
        self.prompt_text.set("No AI parameters found")
        self.negative_prompt_text.set("")
        self.other_parameters_text.set("")

    def update_text(self, text_widget, text_variable):
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", text_variable.get())
        text_widget.config(state="disabled")

    def setup_format_conversion_menu(self):
        convert_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Convert", menu=convert_menu)
        
        convert_menu.add_command(label="Save as PNG", 
                            command=lambda: self.convert_image("PNG"))
        convert_menu.add_command(label="Save as JPEG", 
                            command=lambda: self.convert_image("JPEG"))
        convert_menu.add_command(label="Save as WEBP", 
                            command=lambda: self.convert_image("WEBP"))

    def convert_image(self, format_):
        if not self.current_file_path:
            messagebox.showinfo("Info", "No image is loaded")
            return
            
        try:
            image = Image.open(self.current_file_path)
            save_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_.lower()}",
                filetypes=[(f"{format_} files", f"*.{format_.lower()}")])
            
            if save_path:
                image.save(save_path, format_)
                messagebox.showinfo("Success", f"Image saved as {format_}")
        except Exception as e:
            messagebox.showerror("Error", f"Error converting image: {str(e)}")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageMetadataViewer(root)
    root.mainloop()

