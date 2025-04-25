import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import psycopg2
import locale
import pandas as pd
import os
import sys # For checking OS platform
import decimal # Import decimal

# Configurar locale para formato brasileiro (Best effort)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass # Use system default if pt_BR fails

# Unicode characters for status
PAID_MARK = " ✅"
DEBTOR_MARK = " ❌" # Used for Pendente or Em Negociação

class StudentPaymentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Pagamentos - Relatório Financeiro")
        # self.root.geometry("1300x700") # Remove ou comente o tamanho fixo
        self.root.minsize(1000, 600) # Define um tamanho mínimo razoável

        # --- Frame Principal que segura o Canvas e Scrollbars ---
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Canvas para a área de rolagem ---
        self.canvas = tk.Canvas(main_frame)
        # self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # Moved packing after scrollbars

        # --- Scrollbar Vertical ---
        vsb = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Scrollbar Horizontal ---
        hsb = ttk.Scrollbar(root, orient=tk.HORIZONTAL, command=self.canvas.xview) # Coloca no root para ficar abaixo de tudo
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Pack Canvas AFTER scrollbars (to allow hsb to be below) ---
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Configurar o Canvas ---
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # --- Frame INTERNO que conterá TODO o conteúdo (Notebook, etc.) ---
        # Este frame será colocado DENTRO do canvas
        self.content_frame = ttk.Frame(self.canvas) # Pai é o canvas

        # --- Adicionar o frame interno ao canvas ---
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw") # nw = NorthWest (canto superior esquerdo)

        # --- Ligar eventos para atualizar a scrollregion ---
        self.content_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure) # Redimensionar a largura do frame interno

        # --- Ligar Scroll do Mouse (Opcional, mas recomendado) ---
        # Bind to canvas specifically for mouse wheel events inside the scrollable area
        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_mousewheel(False))


        # --- AGORA, COLOQUE SEU NOTEBOOK DENTRO DO content_frame ---
        # >> REMOVE THE DUPLICATE NOTEBOOK CREATION BELOW <<
        # self.notebook = ttk.Notebook(self.content_frame) # <-- Pai mudou para self.content_frame
        # self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10) # <-- Pack inicial

        self.conn = None
        self.cursor = None
        self.selected_student_info = None # Store info of selected student for status buttons

        self.month_codes_ordered = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        self.month_names_map = {
            'jan': 'Janeiro', 'feb': 'Fevereiro', 'mar': 'Março', 'apr': 'Abril', 'may': 'Maio', 'jun': 'Junho',
            'jul': 'Julho', 'aug': 'Agosto', 'sep': 'Setembro', 'oct': 'Outubro', 'nov': 'Novembro', 'dec': 'Dezembro'
        }

        # --- Setup Notebook for Tabs ---
        # >> ESTA É A CRIAÇÃO CORRETA DO NOTEBOOK <<
        self.notebook = ttk.Notebook(self.content_frame) # <<-- PAI DEVE SER self.content_frame
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.payments_tab = ttk.Frame(self.notebook)
        self.debtors_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.payments_tab, text="Pagamentos")
        self.notebook.add(self.debtors_tab, text="Devedores")

        # --- Setup content for each tab ---
        self.setup_payments_tab()
        self.setup_debtors_tab() # Restore this setup

        # --- Initialize Database and Load Initial Data ---
        self.setup_database()
        self.load_payment_data() # Initial load for payments tab
        self.load_debtor_data()  # Initial load for debtors tab

    # --- Funções Auxiliares para Rolagem ---
    def on_frame_configure(self, event=None):
        """Atualiza a scrollregion do canvas quando o frame interno muda de tamanho."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event=None):
        """Ajusta a largura do frame interno para corresponder à largura do canvas."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, bind_status):
        """Helper to bind/unbind mousewheel events to the canvas."""
        if bind_status:
            if sys.platform == "linux":
                self.canvas.bind_all("<Button-4>", self.on_mousewheel) # Linux scroll up
                self.canvas.bind_all("<Button-5>", self.on_mousewheel) # Linux scroll down
            else: # Windows, MacOS
                self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        else:
            if sys.platform == "linux":
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
            else: # Windows, MacOS
                self.canvas.unbind_all("<MouseWheel>")


    def on_mousewheel(self, event):
        """Callback para rolagem com a roda do mouse."""
        # Determine scroll direction and amount based on platform
        if sys.platform == "win32":
            delta = int(-1*(event.delta/120))
        elif sys.platform == "darwin": # MacOS
            delta = int(-1 * event.delta)
        else: # Linux
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = 0 # Should not happen

        # Check if vertical scrollbar is visible/needed
        if self.canvas.yview() != (0.0, 1.0):
             self.canvas.yview_scroll(delta, "units")
        # Optionally, add horizontal scroll if needed (e.g., Shift+MouseWheel)
        # elif self.canvas.xview() != (0.0, 1.0) and event.state & 0x1: # Check Shift key (platform dependent)
        #      self.canvas.xview_scroll(delta, "units")


    # --- Currency Formatting ---
    def format_currency(self, value):
        if value is None: return "0,00"
        try: return f"{float(value):.2f}".replace('.', ',')
        except (ValueError, TypeError): return "0,00"

    # --- Sua função parse_currency CORRIGIDA ---
    def parse_currency(self, value):
        if value is None: return 0.0
        if isinstance(value, (int, float, decimal.Decimal)):
            try: return float(value)
            except ValueError: print(f"Aviso: Não foi possível converter o valor numérico para float: {value}"); return 0.0
        if isinstance(value, str):
            try:
                cleaned = value.replace(PAID_MARK, '').replace(DEBTOR_MARK, '').strip()
                if not cleaned: return 0.0
                # Lógica para formato brasileiro (1.234,56)
                cleaned = cleaned.replace('.', '') # Remove separadores de milhar (.)
                cleaned = cleaned.replace(',', '.') # Substitui vírgula decimal (,) por ponto (.)
                return float(cleaned)
            except ValueError:
                    print(f"Aviso: Não foi possível interpretar a string de moeda: {value}")
                    return 0.0
        else:
            print(f"Aviso: Tipo inesperado para parse_currency: {type(value)}, valor: {value}")
            return 0.0


    # --- Database Setup and Connection ---
    def setup_database(self):
        """Set up database tables (student_payments and student_debtors)"""
        try:
            conn, cursor = self.connect_to_db()
            if not conn: return

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_payments (
                    id INT PRIMARY KEY, payment_day INT, student_name VARCHAR(50), course VARCHAR(15),
                    discount DECIMAL(10,2), jan DECIMAL(10,2), feb DECIMAL(10,2), mar DECIMAL(10,2),
                    apr DECIMAL(10,2), may DECIMAL(10,2), jun DECIMAL(10,2), jul DECIMAL(10,2),
                    aug DECIMAL(10,2), sep DECIMAL(10,2), oct DECIMAL(10,2), nov DECIMAL(10,2), dec DECIMAL(10,2)
                )""")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_debtors (
                    id INT, student_name VARCHAR(50), course VARCHAR(15), month VARCHAR(20), amount DECIMAL(10,2),
                    status VARCHAR(50) DEFAULT 'Pendente', comment TEXT DEFAULT '',
                    FOREIGN KEY (id) REFERENCES student_payments(id) ON DELETE CASCADE,
                    PRIMARY KEY (id, month)
                )""")
            conn.commit()
            conn.close()
            print("Database tables checked/created.")
        except Exception as e:
            messagebox.showerror("Database Error", f"Error setting up database: {str(e)}")

    def connect_to_db(self):
        try:
            # VERIFIQUE ESTAS CREDENCIAIS
            self.conn = psycopg2.connect(host="localhost", database="postgres", user="postgres", password="123", client_encoding="utf8")
            self.cursor = self.conn.cursor()
            return self.conn, self.cursor
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not connect: {str(e)}")
            self.conn, self.cursor = None, None
            return None, None

    # --- Payments Tab Setup ---
    def setup_payments_tab(self):
        # O pai agora é self.payments_tab, que está dentro do Notebook,
        # que está dentro do content_frame (rolável). Nenhuma mudança aqui.
        self.payments_main_frame = ttk.Frame(self.payments_tab, padding=10)
        self.payments_main_frame.pack(fill=tk.BOTH, expand=True)

        # Search bar
        self.search_frame = ttk.Frame(self.payments_main_frame, padding=5)
        self.search_frame.pack(fill=tk.X, pady=5)
        self.create_search_bar()

        # Payments Table
        self.table_frame = ttk.LabelFrame(self.payments_main_frame, text="Relatório Financeiro (Selecione Aluno para Gerenciar Status)", padding=5)
        self.table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.create_payments_table()

        # Status Buttons Frame
        self.status_button_frame = ttk.LabelFrame(self.payments_main_frame, text="Definir Status Mensal (Selecione Aluno Acima)", padding=5)
        self.status_button_frame.pack(fill=tk.X, pady=5)
        self.create_status_buttons()

        # Input Form Frame
        self.input_frame = ttk.LabelFrame(self.payments_main_frame, text="Gerenciar Alunos", padding=5)
        self.input_frame.pack(fill=tk.X, pady=5)
        self.create_payments_form()

        # Action Buttons Frame
        self.button_frame = ttk.Frame(self.payments_main_frame, padding=5)
        self.button_frame.pack(fill=tk.X, pady=5)
        self.create_payments_buttons()

    # --- Debtors Tab Setup (Restored) ---
    def setup_debtors_tab(self):
        # O pai agora é self.debtors_tab, que está dentro do Notebook,
        # que está dentro do content_frame (rolável). Nenhuma mudança aqui.
        self.debtors_main_frame = ttk.Frame(self.debtors_tab, padding=10)
        self.debtors_main_frame.pack(fill=tk.BOTH, expand=True)

        # Debtors Search Bar
        self.search_frame_debtors = ttk.Frame(self.debtors_main_frame, padding=5)
        self.search_frame_debtors.pack(fill=tk.X, pady=5)
        self.create_debtors_search_bar()

        # Debtors Table Frame
        self.debtors_table_frame = ttk.LabelFrame(self.debtors_main_frame, text="Lista de Devedores", padding=5)
        self.debtors_table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.create_debtors_table()

        # Comment and Status Frame
        self.comment_frame = ttk.LabelFrame(self.debtors_main_frame, text="Comentário e Status", padding=5)
        self.comment_frame.pack(fill=tk.X, pady=5)
        self.create_comment_section()

        # Debtors Action Buttons Frame
        self.debtors_button_frame = ttk.Frame(self.debtors_main_frame, padding=5)
        self.debtors_button_frame.pack(fill=tk.X, pady=5)
        self.create_debtors_buttons()

    # --- UI Creation Methods (Payments Tab - Reused) ---
    # Nenhuma mudança necessária aqui, os pais estão corretos via setup_payments_tab
    def create_search_bar(self):
        ttk.Label(self.search_frame, text="Buscar por Nome/ID:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(self.search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame, text="Buscar", command=self.search_students).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame, text="Mostrar Todos", command=lambda: self.load_payment_data(filter_term=None)).pack(side=tk.LEFT, padx=5)

    def search_students(self):
        """Initiates search based on the input field."""
        self.load_payment_data(filter_term=self.search_var.get().strip())

    def create_payments_table(self):
        columns = ("id", "payment_day", "student_name", "course", "discount", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
        self.payments_tree = ttk.Treeview(self.table_frame, columns=columns, show='headings')
        self.payments_tree.heading("id", text="ID"); self.payments_tree.column("id", width=50, anchor=tk.CENTER)
        self.payments_tree.heading("payment_day", text="Dia"); self.payments_tree.column("payment_day", width=35, anchor=tk.CENTER)
        self.payments_tree.heading("student_name", text="Aluno"); self.payments_tree.column("student_name", width=150)
        self.payments_tree.heading("course", text="Curso"); self.payments_tree.column("course", width=80)
        self.payments_tree.heading("discount", text="Desc."); self.payments_tree.column("discount", width=60, anchor=tk.E)
        month_cols = self.month_codes_ordered; month_names_short = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        for code, name in zip(month_cols, month_names_short): self.payments_tree.heading(code, text=name); self.payments_tree.column(code, width=80, anchor=tk.E)
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.payments_tree.yview); hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.payments_tree.xview)
        self.payments_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); self.payments_tree.grid(column=0, row=0, sticky='nsew'); vsb.grid(column=1, row=0, sticky='ns'); hsb.grid(column=0, row=1, sticky='ew')
        self.table_frame.grid_columnconfigure(0, weight=1); self.table_frame.grid_rowconfigure(0, weight=1)
        self.payments_tree.bind('<<TreeviewSelect>>', self.on_payment_select)

    def create_status_buttons(self):
        self.month_status_buttons = {}
        months_short = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        num_buttons_per_row = 6
        for i, month_code in enumerate(self.month_codes_ordered):
            month_label = months_short[i]; row_num = i // num_buttons_per_row; col_num = i % num_buttons_per_row
            btn = ttk.Button(self.status_button_frame, text=f"Status {month_label}", command=lambda mc=month_code: self.handle_status_button_click(mc), state=tk.DISABLED)
            btn.grid(row=row_num, column=col_num, padx=3, pady=3, sticky=tk.EW)
            self.month_status_buttons[month_code] = btn
        for i in range(num_buttons_per_row): self.status_button_frame.grid_columnconfigure(i, weight=1)

    def create_payments_form(self):
        row = 0
        ttk.Label(self.input_frame, text="ID:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2); self.id_var = tk.StringVar(); ttk.Entry(self.input_frame, textvariable=self.id_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(self.input_frame, text="Dia Pgto:").grid(row=row, column=2, sticky=tk.W, padx=5, pady=2); self.payment_day_var = tk.StringVar(); ttk.Entry(self.input_frame, textvariable=self.payment_day_var, width=5).grid(row=row, column=3, sticky=tk.W, padx=5, pady=2)
        row += 1
        ttk.Label(self.input_frame, text="Nome:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2); self.student_name_var = tk.StringVar(); ttk.Entry(self.input_frame, textvariable=self.student_name_var, width=40).grid(row=row, column=1, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=2)
        row += 1
        ttk.Label(self.input_frame, text="Curso:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2); self.course_var = tk.StringVar(); ttk.Entry(self.input_frame, textvariable=self.course_var, width=20).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(self.input_frame, text="Desconto:").grid(row=row, column=2, sticky=tk.W, padx=5, pady=2); self.discount_var = tk.StringVar(); ttk.Entry(self.input_frame, textvariable=self.discount_var, width=10).grid(row=row, column=3, sticky=tk.W, padx=5, pady=2)
        row += 1
        month_frame = ttk.LabelFrame(self.input_frame, text="Pagamentos Mensais (Valor Base)"); month_frame.grid(row=row, column=0, columnspan=4, sticky=tk.W+tk.E, padx=5, pady=5); self.month_vars = {}
        months_short = [("Jan", "jan"), ("Fev", "feb"), ("Mar", "mar"), ("Abr", "apr"), ("Mai", "may"), ("Jun", "jun"), ("Jul", "jul"), ("Ago", "aug"), ("Set", "sep"), ("Out", "oct"), ("Nov", "nov"), ("Dez", "dec")]
        for i, (month_name, month_code) in enumerate(months_short):
            col = i % 6; r = i // 6; ttk.Label(month_frame, text=f"{month_name}:").grid(row=r, column=col*2, sticky=tk.W, padx=5, pady=2); self.month_vars[month_code] = tk.StringVar(); ttk.Entry(month_frame, textvariable=self.month_vars[month_code], width=10).grid(row=r, column=col*2+1, sticky=tk.W, padx=5, pady=2)

    def create_payments_buttons(self):
        ttk.Button(self.button_frame, text="Adicionar", command=self.add_student).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Atualizar", command=self.update_student).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Remover", command=self.remove_student).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Limpar Campos", command=self.clear_payments_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Próximo ID", command=self.find_next_id).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Exportar Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)

    # --- UI Creation Methods (Debtors Tab - Restored) ---
    # Nenhuma mudança necessária aqui, os pais estão corretos via setup_debtors_tab
    def create_debtors_search_bar(self):
        ttk.Label(self.search_frame_debtors, text="Buscar Devedor por Nome/ID:").pack(side=tk.LEFT, padx=5)
        self.search_var_debtors = tk.StringVar()
        ttk.Entry(self.search_frame_debtors, textvariable=self.search_var_debtors, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame_debtors, text="Buscar", command=self.search_debtors).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame_debtors, text="Mostrar Todos", command=lambda: self.load_debtor_data(filter_term=None)).pack(side=tk.LEFT, padx=5)

    def create_debtors_table(self):
        columns = ("id", "student_name", "course", "month", "amount", "status", "comment")
        self.debtors_tree = ttk.Treeview(self.debtors_table_frame, columns=columns, show='headings')
        self.debtors_tree.heading("id", text="ID"); self.debtors_tree.column("id", width=60, anchor=tk.CENTER)
        self.debtors_tree.heading("student_name", text="Aluno"); self.debtors_tree.column("student_name", width=200)
        self.debtors_tree.heading("course", text="Curso"); self.debtors_tree.column("course", width=100)
        self.debtors_tree.heading("month", text="Mês"); self.debtors_tree.column("month", width=100, anchor=tk.CENTER)
        self.debtors_tree.heading("amount", text="Valor"); self.debtors_tree.column("amount", width=100, anchor=tk.E)
        self.debtors_tree.heading("status", text="Status"); self.debtors_tree.column("status", width=100, anchor=tk.CENTER)
        self.debtors_tree.heading("comment", text="Comentário"); self.debtors_tree.column("comment", width=250)

        vsb = ttk.Scrollbar(self.debtors_table_frame, orient="vertical", command=self.debtors_tree.yview)
        hsb = ttk.Scrollbar(self.debtors_table_frame, orient="horizontal", command=self.debtors_tree.xview)
        self.debtors_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.debtors_tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns'); hsb.grid(column=0, row=1, sticky='ew')
        self.debtors_table_frame.grid_columnconfigure(0, weight=1); self.debtors_table_frame.grid_rowconfigure(0, weight=1)

        self.debtors_tree.bind('<<TreeviewSelect>>', self.on_debtor_select)

        self.debtors_tree.tag_configure('Pago', background='#c8e6c9') # Light green
        self.debtors_tree.tag_configure('Em Negociação', background='#fff9c4') # Light yellow
        self.debtors_tree.tag_configure('Pendente', background='#ffcdd2') # Light red
        self.debtors_tree.tag_configure('unknown', background='#eeeeee') # Grey for fallback


    def create_comment_section(self):
        comment_content = ttk.Frame(self.comment_frame)
        comment_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(comment_content, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.debtor_status_var = tk.StringVar(value="Pendente")
        status_combo = ttk.Combobox(comment_content, textvariable=self.debtor_status_var, state="readonly", width=15)
        status_combo['values'] = ("Pendente", "Em Negociação", "Pago")
        status_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(comment_content, text="Valor:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.debtor_amount_var = tk.StringVar()
        ttk.Entry(comment_content, textvariable=self.debtor_amount_var, width=12).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Button(comment_content, text="Atualizar Status/Comentário", command=self.update_debtor_status).grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)

        ttk.Label(comment_content, text="Comentário:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.debtor_comment_var = tk.StringVar()
        ttk.Entry(comment_content, textvariable=self.debtor_comment_var, width=60).grid(row=1, column=1, columnspan=4, sticky=tk.W+tk.E, padx=5, pady=5)

        comment_content.columnconfigure(1, weight=1)

    def create_debtors_buttons(self):
        ttk.Button(self.debtors_button_frame, text="Remover da Lista", command=self.remove_from_debtors).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.debtors_button_frame, text="Limpar Campos", command=self.clear_debtor_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.debtors_button_frame, text="Exportar Devedores Excel", command=self.export_debtors_to_excel).pack(side=tk.LEFT, padx=5)


    # --- Data Loading & Display ---
    def load_payment_data(self, filter_term=None):
        print("Loading payment data...")
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return
            query = "SELECT * FROM student_payments"; params = ()
            if filter_term:
                 if filter_term.isdigit(): query += " WHERE id = %s"; params = (int(filter_term),)
                 else: query += " WHERE LOWER(student_name) LIKE LOWER(%s)"; params = (f'%{filter_term}%',)
            query += " ORDER BY id"; cursor.execute(query, params); payment_rows = cursor.fetchall(); conn.close()

            # Ensure payments_tree exists before clearing
            if hasattr(self, 'payments_tree'):
                 for item in self.payments_tree.get_children(): self.payments_tree.delete(item)
            else:
                print("Warning: payments_tree not found during load_payment_data")
                return # Cannot proceed without the tree

            if not payment_rows and filter_term: messagebox.showinfo("Busca", f"Nenhum aluno encontrado para '{filter_term}'."); return
            elif not payment_rows and not filter_term and self.is_db_empty("student_payments"): self.load_sample_data(); return

            for row_data in payment_rows:
                formatted_row = list(row_data)
                # Format discount (index 4)
                formatted_row[4] = self.format_currency(row_data[4])
                # Format monthly payments (indices 5 to 16)
                for i in range(len(self.month_codes_ordered)):
                    col_index = i + 5
                    if col_index < len(row_data):
                        formatted_row[col_index] = self.format_currency(row_data[col_index])
                    else:
                         # If data is missing for a month, append default
                         if len(formatted_row) <= col_index:
                             formatted_row.append("0,00")
                         else: # Should not happen if DB schema is correct
                             formatted_row[col_index] = "0,00" # Fallback

                # Ensure the row has the correct number of columns for the tree
                while len(formatted_row) < len(self.payments_tree['columns']):
                     formatted_row.append("0,00")

                # Insert into tree, taking only the expected number of columns
                self.payments_tree.insert('', 'end', values=tuple(formatted_row[:len(self.payments_tree['columns'])]))

            self.apply_existing_marks() # Apply marks after loading base data
            print("Payment data loaded and marks applied.")
        except AttributeError as ae:
             # Catch cases where widgets might not be fully initialized yet
             print(f"Attribute Error during payment load (potential timing issue): {ae}")
             import traceback; print(traceback.format_exc())
        except Exception as e:
            import traceback; error_details = traceback.format_exc(); print(f"Error loading payments: {str(e)}\n{error_details}")
            messagebox.showerror("Database Error", f"Error loading payment data: {str(e)}")


    def apply_existing_marks(self):
        """Applies ✅/❌ marks to the payments_tree based on student_debtors status."""
        print("Applying existing marks to payments tab...")
        try:
            # Ensure payments_tree exists
            if not hasattr(self, 'payments_tree'):
                print("Warning: payments_tree not found during apply_existing_marks")
                return

            conn, cursor = self.connect_to_db();
            if not conn: 
                return
            debtor_statuses = {}; cursor.execute("SELECT id, month, status FROM student_debtors");
            for d_id, d_month, d_status in cursor.fetchall(): debtor_statuses[(d_id, d_month)] = d_status
            conn.close()
            # >> NÃO RETORNE AQUI SE debtor_statuses ESTIVER VAZIO <<
            # Precisamos continuar para aplicar os ✅ padrão para meses pagos.
            # if not debtor_statuses: print("No debtor statuses found to apply marks."); return

            for item_id_str in self.payments_tree.get_children():
                current_values = list(self.payments_tree.item(item_id_str, 'values'))
                if not current_values or len(current_values) < 1: continue
                try: student_id = int(current_values[0])
                except (IndexError, ValueError): continue

                new_values = list(current_values); changed = False
                for i, month_code in enumerate(self.month_codes_ordered):
                    month_name_full = self.month_names_map[month_code]; col_index_in_tree = i + 5
                    if col_index_in_tree >= len(current_values): continue

                    # 1. Obtenha o valor como está na árvore AGORA (formatado, sem marca)
                    current_display_value = str(current_values[col_index_in_tree]).strip()

                    # 2. Parse o valor para verificar se é > 0 (remova marcas potenciais apenas para parse)
                    value_for_parsing = current_display_value.replace(PAID_MARK, '').replace(DEBTOR_MARK, '').strip()
                    numeric_value = self.parse_currency(value_for_parsing)

                    # 3. Determine a marca a ser adicionada
                    mark_to_add = ""
                    if numeric_value > 0:
                        db_status = debtor_statuses.get((student_id, month_name_full))
                        if db_status == 'Pago': mark_to_add = PAID_MARK
                        elif db_status == 'Pendente' or db_status == 'Em Negociação': mark_to_add = DEBTOR_MARK
                        

                    # 4. Construa o novo valor adicionando a marca ao valor JÁ FORMATADO da árvore
                    new_cell_value = current_display_value + mark_to_add

                    # 5. Verifique se o valor realmente mudou (se uma marca foi adicionada/removida)
                    if current_values[col_index_in_tree] != new_cell_value:
                        new_values[col_index_in_tree] = new_cell_value
                        changed = True

                # Atualize a linha na árvore se alguma célula mudou
                if changed:
                    try: self.payments_tree.item(item_id_str, values=tuple(new_values))
                    except Exception as update_err: print(f"Error updating tree item {item_id_str}: {update_err}")
            print("Finished applying marks.")
        except AttributeError as ae:
            print(f"Attribute Error during apply marks (potential timing issue): {ae}")
            import traceback; print(traceback.format_exc())
        except Exception as e:
            import traceback; print(f"Error applying marks: {e}\n{traceback.format_exc()}")
        
    def load_debtor_data(self, filter_term=None):
        """Loads data into the Debtors table, showing only 'Pendente' or 'Em Negociação'."""
        print("Loading filtered debtor data (Pendente/Em Negociação)...")
        try:
            # Ensure debtors_tree exists before clearing
            if not hasattr(self, 'debtors_tree'):
                print("Warning: debtors_tree not found during load_debtor_data")
                return

            conn, cursor = self.connect_to_db()
            if not conn: return

            # Base query
            query = "SELECT id, student_name, course, month, amount, status, comment FROM student_debtors"

            # --- Filtering Logic ---
            where_clauses = []
            params = []

            # 1. MANDATORY Status Filter: Only Pending or In Negotiation
            where_clauses.append("status IN (%s, %s)")
            params.extend(['Pendente', 'Em Negociação']) # Add statuses to parameters

            # 2. OPTIONAL Search Filter (ID or Name)
            if filter_term:
                search_term_lower = f'%{filter_term.lower()}%'
                if filter_term.isdigit():
                    where_clauses.append("id = %s")
                    params.append(int(filter_term))
                else:
                    where_clauses.append("LOWER(student_name) LIKE LOWER(%s)")
                    params.append(search_term_lower)

            # Combine WHERE clauses if any exist
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            # --- ORDER BY Clause ---
            # ORDER BY ensures consistent display
            query += " ORDER BY id, CASE month "
            for i, code in enumerate(self.month_codes_ordered):
                 query += f" WHEN '{self.month_names_map[code]}' THEN {i}"
            query += " ELSE 99 END" # Put unknown months last

            # --- Execute Query ---
            print(f"Executing Debtor Query: {query}") # For debugging
            print(f"Parameters: {tuple(params)}")      # For debugging
            cursor.execute(query, tuple(params)) # Pass parameters as a tuple
            debtor_rows = cursor.fetchall()
            conn.close()

            # --- Display Results ---
            self.display_debtor_data(debtor_rows) # Use helper to display

            if not debtor_rows and filter_term:
                 messagebox.showinfo("Busca Devedores", f"Nenhum devedor (Pendente/Em Negociação) encontrado para '{filter_term}'.")
            elif not debtor_rows and not filter_term:
                 print("Nenhum registro com status 'Pendente' ou 'Em Negociação' encontrado.")


            print(f"Filtered debtor data loaded. Found {len(debtor_rows)} entries.")

        except AttributeError as ae:
             print(f"Attribute Error during debtor load (potential timing issue): {ae}")
             import traceback; print(traceback.format_exc())
        except Exception as e:
             messagebox.showerror("Database Error", f"Error loading debtor data: {str(e)}")
             import traceback; print(traceback.format_exc())

        # --- Coloque esta função DENTRO da classe StudentPaymentApp ---
    # --- No mesmo nível de indentação de load_debtor_data, etc. ---

    def display_debtor_data(self, rows):
        """Clears and populates the debtors_tree with given rows and applies status tags."""
        # Ensure debtors_tree exists
        if not hasattr(self, 'debtors_tree'):
                print("Warning: debtors_tree not found during display_debtor_data")
                return

        # Clear existing treeview items
        for item in self.debtors_tree.get_children():
            try:
                self.debtors_tree.delete(item)
            except tk.TclError as e:
                print(f"Warning: Could not delete item {item} from debtors_tree: {e}")


        # Populate treeview
        for row in rows:
            # Ensure row has enough elements (id, name, course, month, amount, status, comment)
            if len(row) < 7:
                print(f"Skipping incomplete debtor row: {row}")
                continue

            formatted_row = list(row)
            # Format amount (index 4)
            formatted_row[4] = self.format_currency(row[4])

            # Determine tag based on status (index 5)
            status = formatted_row[5]
            tag = 'unknown' # Default tag
            if status == 'Pago': tag = 'Pago'
            elif status == 'Em Negociação': tag = 'Em Negociação'
            elif status == 'Pendente': tag = 'Pendente'

            # Insert row with the determined tag
            try:
                self.debtors_tree.insert('', 'end', values=tuple(formatted_row[:7]), tags=(tag,))
            except tk.TclError as e:
                 print(f"Warning: TclError inserting debtor row: {formatted_row}, Error: {e}")
            except Exception as insert_error:
                print(f"Error inserting debtor row: {formatted_row}, Error: {insert_error}")         
            
    def is_db_empty(self, table_name):
        conn, cursor = self.connect_to_db();
        if not conn: return True
        try: cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1"); return cursor.fetchone() is None
        except Exception: return True
        finally:
            if conn: conn.close()

    def load_sample_data(self):
        if not messagebox.askyesno("Banco Vazio", "Nenhum dado de pagamento encontrado. Carregar dados de exemplo?"): return
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return
            # Ensure tables exist before inserting
            self.setup_database() # Re-run setup just in case

            conn, cursor = self.connect_to_db(); # Reconnect if setup closed it
            if not conn: return

            sample_payments=[(1001,10,"Pedro Faleiro Rocha","TQI",0.00,10.00,11.00,11.00,0.00,390.10,390.55,0,0,0,0,0,0),(1002,20,"Isis Silva Pinheiro Aires","SB",20.00,270.18,270.18,270.18,10.00,0,0,0,0,0,0,0,0),(1003,10,"Pedro Motteran Thomaz Vi","FLY1",20.00,329.46,329.46,329.46,0,0,0,10.00,0,0,0,0,0), (1004, 10, "chuleto", "TO1", 0.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00)]
            insert_pay="INSERT INTO student_payments (id, payment_day, student_name, course, discount, jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING"; cursor.executemany(insert_pay, sample_payments)

            sample_debtors=[(1001,'Pedro Faleiro Rocha','TQI','Fevereiro',11.00,'Pendente',''),(1001,'Pedro Faleiro Rocha','TQI','Março',11.00,'Pendente',''),(1001,'Pedro Faleiro Rocha','TQI','Maio',390.10,'Pendente','Pagamento atrasado'),(1002,'Isis Silva Pinheiro Aires','SB','Janeiro',270.18,'Em Negociação','Combinado pagar dia 30'),(1002,'Isis Silva Pinheiro Aires','SB','Abril',10.00,'Pendente',''),(1003,'Pedro Motteran Thomaz Vi','FLY1','Fevereiro',329.46,'Pendente',''), (1004, 'chuleto', 'TO1', 'Janeiro', 10.00, 'Pendente', '')]

            insert_debt="INSERT INTO student_debtors (id, student_name, course, month, amount, status, comment) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id, month) DO UPDATE SET status=EXCLUDED.status, amount=EXCLUDED.amount, comment=EXCLUDED.comment"; cursor.executemany(insert_debt, sample_debtors)
            conn.commit(); conn.close(); messagebox.showinfo("Sucesso", "Dados de exemplo carregados.")
            self.load_payment_data(); self.load_debtor_data() # Reload both tabs
        except Exception as e:
            import traceback; print(traceback.format_exc())
            messagebox.showerror("Database Error", f"Error loading sample data: {str(e)}")
        finally:
             # Ensure connection is closed even if errors occurred during inserts
             if 'conn' in locals() and conn and not conn.closed:
                 conn.rollback()
                 conn.close()


    # --- Event Handlers ---
    def on_payment_select(self, event):
        selected_items = self.payments_tree.selection();
        if not selected_items:
            self.clear_payments_form(); self.selected_student_info = None
            # Disable status buttons only if they exist
            if hasattr(self, 'month_status_buttons'):
                for btn in self.month_status_buttons.values(): btn.config(state=tk.DISABLED)
            return
        item = selected_items[0]; values = self.payments_tree.item(item, 'values')
        if not values or len(values) < len(self.payments_tree['columns']):
             messagebox.showerror("Erro", "Erro ao ler dados da linha (incompleta)."); self.clear_payments_form(); return
        try:
            self.id_var.set(values[0]); self.payment_day_var.set(values[1]); self.student_name_var.set(values[2]); self.course_var.set(values[3])
            # Parse and reformat to handle potential marks in the value
            self.discount_var.set(self.format_currency(self.parse_currency(values[4])))
            for i, month_code in enumerate(self.month_codes_ordered):
                value_index = i + 5
                if value_index < len(values):
                    # Parse and reformat to handle potential marks in the value
                    self.month_vars[month_code].set(self.format_currency(self.parse_currency(values[value_index])))
                else: self.month_vars[month_code].set("0,00")
            self.selected_student_info = {'id': int(values[0]), 'name': values[2], 'course': values[3]}
            # Enable status buttons only if they exist
            if hasattr(self, 'month_status_buttons'):
                for btn in self.month_status_buttons.values(): btn.config(state=tk.NORMAL)
        except (IndexError, ValueError, AttributeError) as e:
             messagebox.showerror("Erro", f"Erro ao processar dados: {e}"); self.clear_payments_form()
             self.selected_student_info = None;
             if hasattr(self, 'month_status_buttons'):
                 [btn.config(state=tk.DISABLED) for btn in self.month_status_buttons.values()]


    def on_debtor_select(self, event):
        """Handles selection changes in the debtors Treeview."""
        selected_items = self.debtors_tree.selection()
        if not selected_items:
            self.clear_debtor_form()
            return

        item = selected_items[0]
        values = self.debtors_tree.item(item, 'values')

        if not values or len(values) < 7:
            messagebox.showerror("Erro", "Erro ao ler dados da linha de devedor selecionada.")
            self.clear_debtor_form()
            return

        try:
            self.debtor_amount_var.set(values[4])
            self.debtor_status_var.set(values[5])
            self.debtor_comment_var.set(values[6])
        except IndexError:
             messagebox.showerror("Erro", "Dados incompletos na linha de devedor selecionada.")
             self.clear_debtor_form()


    def handle_status_button_click(self, month_code):
        """Handles clicks on the monthly status buttons (Pagamentos Tab)."""
        print(f"\n--- handle_status_button_click START ({month_code}) ---") # DEBUG START
        if not self.selected_student_info:
            messagebox.showwarning("Aviso", "Nenhum aluno selecionado.", icon='warning')
            print("DEBUG: Nenhum aluno selecionado.") # DEBUG
            return

        student_id = self.selected_student_info['id']; student_name = self.selected_student_info['name']; course = self.selected_student_info['course']; month_name_full = self.month_names_map[month_code]
        amount = 0.0
        conn_check, cursor_check = None, None # Initialize for finally block

        print(f"DEBUG: Checking base amount for Aluno ID: {student_id}, Mês: {month_name_full}") # DEBUG
        try:
            conn_check, cursor_check = self.connect_to_db();
            if not conn_check: raise Exception("Falha DB Check.")
            # Fetch the specific month's value directly
            cursor_check.execute(f"SELECT {month_code} FROM student_payments WHERE id = %s", (student_id,)); result = cursor_check.fetchone();
            if result is None: raise Exception(f"Aluno ID {student_id} não encontrado.")
            # Use parse_currency to handle potential Decimal type from DB
            amount = self.parse_currency(result[0])
            print(f"DEBUG: Base amount fetched: {amount}") # DEBUG
        except Exception as e:
             messagebox.showerror("Erro DB", f"Erro buscar valor base: {e}");
             print(f"DEBUG: Erro ao buscar valor base: {e}") # DEBUG
             import traceback; print(traceback.format_exc()) # DEBUG
             return
        finally:
             if conn_check: conn_check.close() # Ensure connection is closed

        if amount <= 0:
            print(f"DEBUG: Amount {amount} <= 0 for {month_name_full}. Status não aplicável.") # DEBUG
            messagebox.showinfo("Info", f"Valor para {month_name_full} é {self.format_currency(amount)}. Status não aplicável.")
            conn_clean, cursor_clean = None, None
            # ... (bloco para limpar devedor com valor zero - sem prints adicionais aqui por ora) ...
            # (o print existente 'Cleaned debtor status...' já está lá)
            return

        # --- Diálogo com o usuário ---
        base_formatted_value = self.format_currency(amount)
        dialog = StatusChoiceDialog(self.root, f"Aluno: {student_name}\nMês: {month_name_full}\nValor: {base_formatted_value}", ["Pago", "Devedor"])
        result_status_choice = dialog.result
        print(f"DEBUG: User choice from dialog: {result_status_choice}") # DEBUG
        if result_status_choice is None:
            print("DEBUG: User cancelled the dialog.") # DEBUG
            return

        # --- Preparação para Atualização do Banco ---
        db_update_successful = False;
        # Define o status a ser salvo no DB
        new_debtor_status_db = 'Pago' if result_status_choice == 'Pago' else 'Pendente'
        print(f"DEBUG: Status to be saved in DB: '{new_debtor_status_db}'") # DEBUG
        print(f"DEBUG: Preparing DB update for ID: {student_id}, Mês: {month_name_full}, Valor: {amount}, Status: {new_debtor_status_db}") # DEBUG

        conn_update, cursor_update = None, None
        try:
            conn_update, cursor_update = self.connect_to_db();
            if not conn_update: raise Exception("Falha DB Update.")

            upsert_query = """INSERT INTO student_debtors (id, student_name, course, month, amount, status, comment) VALUES (%s, %s, %s, %s, %s, %s, '') ON CONFLICT (id, month) DO UPDATE SET status = EXCLUDED.status, amount = EXCLUDED.amount, student_name = EXCLUDED.student_name, course = EXCLUDED.course, comment = COALESCE(student_debtors.comment, '')"""
            params_tuple = (student_id, student_name, course, month_name_full, amount, new_debtor_status_db)

            print(f"DEBUG: Executing UPSERT query...") # DEBUG
            print(f"DEBUG: Query Params: {params_tuple}") # DEBUG
            cursor_update.execute(upsert_query, params_tuple);
            print(f"DEBUG: UPSERT query executed.") # DEBUG

            print(f"DEBUG: Committing transaction...") # DEBUG
            conn_update.commit();
            db_update_successful = True;
            print(f"DEBUG: Commit successful.") # DEBUG

            # Este print antigo já estava bom:
            print(f"DB updated via status button for {student_name}, {month_name_full}: Status={new_debtor_status_db}")

        except Exception as e:
             print(f"DEBUG: EXCEPTION during DB update!") # DEBUG
             if conn_update:
                 print("DEBUG: Rolling back transaction...") # DEBUG
                 conn_update.rollback()
             messagebox.showerror("Erro DB", f"Erro ao atualizar status: {str(e)}");
             print(f"DEBUG: Error details: {e}") # DEBUG
             import traceback; print(traceback.format_exc()) # DEBUG traceback
        finally:
             if conn_update:
                 print("DEBUG: Closing update connection.") # DEBUG
                 conn_update.close()

        # --- Recarregamento dos Dados ---
        if db_update_successful:
            print(f"DEBUG: DB update was successful. Reloading data.") # DEBUG
            messagebox.showinfo("Sucesso", f"Status de {month_name_full} ({student_name}) atualizado para '{result_status_choice}'.")
            self.load_payment_data() # Reload payments tab to show marks
            self.load_debtor_data()  # Reload debtors tab to reflect change
        else:
             print("DEBUG: DB update FAILED. Data not reloaded.") # DEBUG

        print(f"--- handle_status_button_click END ({month_code}) ---") # DEBUG END


    # --- Form Actions (Payments Tab - Minor changes for sync) ---
    def clear_payments_form(self):
        self.id_var.set(""); self.payment_day_var.set(""); self.student_name_var.set(""); self.course_var.set(""); self.discount_var.set("");
        if hasattr(self, 'month_vars'):
            [var.set("") for var in self.month_vars.values()]
        if hasattr(self, 'payments_tree'):
             self.payments_tree.selection_set(())
        self.selected_student_info = None;
        if hasattr(self, 'month_status_buttons'):
             [btn.config(state=tk.DISABLED) for btn in self.month_status_buttons.values()]


    def validate_payment_form(self, is_update=False):
        id_str = self.id_var.get();
        if not id_str or not id_str.isdigit(): messagebox.showerror("Erro Validação", "ID deve ser numérico."); return False # Clearer message
        id_val = int(id_str);
        if not (1001 <= id_val <= 9999): messagebox.showerror("Erro Validação", "ID deve estar entre 1001 e 9999."); return False
        pd_str = self.payment_day_var.get();
        if not pd_str or not pd_str.isdigit(): messagebox.showerror("Erro Validação", "Dia do Pagamento deve ser numérico."); return False
        payment_day = int(pd_str);
        if not (1 <= payment_day <= 31): messagebox.showerror("Erro Validação", "Dia do Pagamento deve ser entre 1 e 31."); return False
        if not self.student_name_var.get().strip(): messagebox.showerror("Erro Validação", "Nome do Aluno é obrigatório."); return False
        try:
             # Validate discount
             self.parse_currency(self.discount_var.get() or "0,00")
             # Validate all month values
             if hasattr(self, 'month_vars'):
                 [self.parse_currency(self.month_vars[code].get() or "0,00") for code in self.month_codes_ordered]
             else: raise ValueError("Month variables not initialized")
        except ValueError as ve: messagebox.showerror("Erro Validação", f"Valores monetários inválidos (use formato XXXX,XX). Detalhe: {ve}"); return False
        except AttributeError: messagebox.showerror("Erro Interno", "Erro ao acessar variáveis de mês."); return False


        if not is_update:
             conn, cursor = None, None
             try:
                 conn, cursor = self.connect_to_db();
                 if not conn: return False # Connection error handled in connect_to_db
                 cursor.execute("SELECT 1 FROM student_payments WHERE id = %s", (id_val,)); exists = cursor.fetchone();
                 if exists: messagebox.showerror("Erro", f"ID {id_val} já existe no sistema."); return False
             except Exception as e: messagebox.showerror("Erro DB", f"Erro ao verificar existência do ID: {e}"); return False
             finally:
                 if conn: conn.close()
        return True


    def add_student(self):
        if not self.validate_payment_form(is_update=False): return
        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return

            id_val = int(self.id_var.get()); payment_day = int(self.payment_day_var.get()); student_name = self.student_name_var.get().strip(); course = self.course_var.get().strip(); discount = self.parse_currency(self.discount_var.get() or "0,00"); month_values = {code: self.parse_currency(self.month_vars[code].get() or "0,00") for code in self.month_codes_ordered}
            insert_values = (id_val, payment_day, student_name, course, discount, month_values["jan"], month_values["feb"], month_values["mar"], month_values["apr"], month_values["may"], month_values["jun"], month_values["jul"], month_values["aug"], month_values["sep"], month_values["oct"], month_values["nov"], month_values["dec"])
            sql = """INSERT INTO student_payments (id, payment_day, student_name, course, discount, jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, insert_values); conn.commit()
            messagebox.showinfo("Sucesso", f"Aluno '{student_name}' adicionado.")
            self.load_payment_data(); self.load_debtor_data() # Refresh both
            self.clear_payments_form()
        except Exception as e:
            if conn: conn.rollback();
            messagebox.showerror("Erro DB", f"Erro ao adicionar aluno: {e}")
            import traceback; print(traceback.format_exc())
        finally:
            if conn: conn.close()


    def update_student(self):
        id_str = self.id_var.get();
        student_id_to_update = None

        # Try getting ID from form first
        if id_str and id_str.isdigit():
             student_id_to_update = int(id_str)
        else:
             # If form ID is invalid/empty, try getting from selection
             selected_items = self.payments_tree.selection()
             if selected_items:
                 item = selected_items[0];
                 try:
                     values = self.payments_tree.item(item, 'values')
                     student_id_to_update = int(values[0])
                     # Populate form with selected student's ID if missing from form
                     if not self.id_var.get(): self.id_var.set(str(student_id_to_update))
                 except (IndexError, ValueError, TypeError):
                     messagebox.showerror("Erro", "Seleção inválida ou dados da linha corrompidos."); return
             else:
                 # No selection and no valid ID in form
                 messagebox.showerror("Erro", "Selecione um aluno na tabela ou digite um ID válido no campo ID para atualizar."); return

        # Now validate the form data (ID might have been populated from selection)
        if not self.validate_payment_form(is_update=True): return

        # Re-read ID from form after validation, in case it was populated
        try:
             id_val = int(self.id_var.get())
             if id_val != student_id_to_update and student_id_to_update is not None:
                 # This case should be rare if logic above is correct, but good to check
                 if not messagebox.askyesno("Aviso", f"O ID no formulário ({id_val}) é diferente do ID selecionado ({student_id_to_update}). Deseja atualizar o aluno com ID {id_val}?"):
                     return
        except ValueError: # Should be caught by validation, but as safety
             messagebox.showerror("Erro Interno", "ID inválido após validação."); return


        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return

            # Check if the student ID to be updated actually exists
            cursor.execute("SELECT 1 FROM student_payments WHERE id = %s", (id_val,));
            if not cursor.fetchone():
                messagebox.showerror("Erro", f"ID {id_val} não encontrado no banco de dados para atualização."); return

            # Proceed with update
            payment_day = int(self.payment_day_var.get()); student_name = self.student_name_var.get().strip(); course = self.course_var.get().strip(); discount = self.parse_currency(self.discount_var.get() or "0,00"); month_values = {code: self.parse_currency(self.month_vars[code].get() or "0,00") for code in self.month_codes_ordered}

            update_sql = """UPDATE student_payments SET payment_day=%s, student_name=%s, course=%s, discount=%s, jan=%s, feb=%s, mar=%s, apr=%s, may=%s, jun=%s, jul=%s, aug=%s, sep=%s, oct=%s, nov=%s, dec=%s WHERE id=%s"""
            update_values = (payment_day, student_name, course, discount, month_values["jan"], month_values["feb"], month_values["mar"], month_values["apr"], month_values["may"], month_values["jun"], month_values["jul"], month_values["aug"], month_values["sep"], month_values["oct"], month_values["nov"], month_values["dec"], id_val)
            cursor.execute(update_sql, update_values)

            # Update corresponding entries in student_debtors (or remove if amount becomes zero)
            for month_code, amount in month_values.items():
                 month_name = self.month_names_map[month_code]
                 # Update only existing debtor entries if amount > 0 AND status is not 'Pago'
                 # Or remove debtor entry if amount is zero
                 if amount > 0:
                      # Update details but respect existing status unless it needs creating
                      # Maybe just update amount, name, course? Status is handled elsewhere.
                     cursor.execute("""
                         UPDATE student_debtors
                         SET student_name=%s, course=%s, amount=%s
                         WHERE id=%s AND month=%s
                     """, (student_name, course, amount, id_val, month_name))
                 else:
                     # If payment amount becomes 0, remove any corresponding debtor entry
                     cursor.execute("DELETE FROM student_debtors WHERE id = %s AND month = %s", (id_val, month_name))

            conn.commit()
            messagebox.showinfo("Sucesso", f"Aluno '{student_name}' (ID: {id_val}) atualizado.")
            self.load_payment_data(); self.load_debtor_data() # Refresh both
            self.clear_payments_form()

        except Exception as e:
            if conn: conn.rollback();
            messagebox.showerror("Erro DB", f"Erro ao atualizar aluno: {e}")
            import traceback; print(traceback.format_exc())
        finally:
            if conn: conn.close()


    def remove_student(self):
        id_to_remove = None; student_name_display = "Aluno desconhecido"
        id_str = self.id_var.get();

        if id_str and id_str.isdigit():
            id_to_remove = int(id_str)
            # Try to get name from form if available
            student_name_display = self.student_name_var.get().strip() or f"ID {id_to_remove}"
        else:
            selected_items = self.payments_tree.selection()
            if selected_items:
                item = selected_items[0];
                try:
                    values = self.payments_tree.item(item, 'values')
                    id_to_remove = int(values[0])
                    student_name_display = values[2] # Get name from selected row
                except (IndexError, ValueError, TypeError):
                    messagebox.showerror("Erro", "Seleção inválida ou dados da linha corrompidos."); return
            else:
                 messagebox.showerror("Erro", "Selecione um aluno na tabela ou digite um ID válido para remover."); return

        if not messagebox.askyesno("Confirmar", f"Remover '{student_name_display}' (ID: {id_to_remove})?\n\nATENÇÃO: Todos os dados de pagamento E de débitos deste aluno serão REMOVIDOS permanentemente!"):
            return

        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return
            # Deletion from student_payments will cascade to student_debtors due to FOREIGN KEY ON DELETE CASCADE
            cursor.execute("DELETE FROM student_payments WHERE id = %s", (id_to_remove,));
            rows_deleted = cursor.rowcount;
            conn.commit()

            if rows_deleted > 0:
                messagebox.showinfo("Sucesso", f"Aluno '{student_name_display}' removido com sucesso.");
                self.load_payment_data(); self.load_debtor_data(); # Refresh tables
                self.clear_payments_form(); self.clear_debtor_form() # Clear forms
            else:
                # This case might occur if the user typed an ID that doesn't exist
                messagebox.showerror("Erro", f"Aluno ID {id_to_remove} não encontrado no banco de dados.");
                # Still refresh tables and clear forms in case view was stale
                self.load_payment_data(); self.load_debtor_data();
                self.clear_payments_form(); self.clear_debtor_form()
        except Exception as e:
            if conn: conn.rollback();
            messagebox.showerror("Erro DB", f"Erro ao remover aluno: {e}")
            import traceback; print(traceback.format_exc())
        finally:
            if conn: conn.close()


    def find_next_id(self):
        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db();
            if not conn: return
            cursor.execute("SELECT id FROM student_payments WHERE id >= 1001 ORDER BY id"); existing_ids = {row[0] for row in cursor.fetchall()};
            next_id = 1001;
            while next_id in existing_ids: next_id += 1
            if next_id <= 9999: self.id_var.set(str(next_id)); messagebox.showinfo("Próximo ID", f"Próximo ID disponível: {next_id}")
            else: messagebox.showinfo("Próximo ID", "Não há mais IDs disponíveis na faixa 1001-9999.")
        except Exception as e: messagebox.showerror("Erro DB", f"Erro ao buscar próximo ID: {e}");
        finally:
             if conn: conn.close()


        # --- MODIFICADO para exportar com UNICODES ---
    def export_to_excel(self):
        """Exports the current view of the Payments table WITH Unicode marks to Excel."""
        try:
            # Garante que a árvore de pagamentos existe
            if not hasattr(self, 'payments_tree'):
                messagebox.showerror("Erro", "Tabela de pagamentos não inicializada.")
                return

            # Pede ao usuário o local para salvar o arquivo Excel
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Salvar Planilha de Pagamentos"
            )
            # Se o usuário cancelar, não faz nada
            if not file_path:
                return

            data_to_export = []
            # Pega os nomes das colunas como definidos nos cabeçalhos da Treeview
            columns = [self.payments_tree.heading(col)['text'] for col in self.payments_tree['columns']]
            data_to_export.append(columns)

            # Itera sobre cada linha (item) na Treeview de pagamentos
            for item_id in self.payments_tree.get_children():
                # Pega os valores da linha diretamente da Treeview.
                # Estes valores já incluem as marcas ✅/❌ aplicadas por apply_existing_marks.
                values = list(self.payments_tree.item(item_id, 'values'))
                data_to_export.append(values)

            # Verifica se há dados para exportar (além dos cabeçalhos)
            if len(data_to_export) <= 1:
                messagebox.showinfo("Exportar", "Não há dados na tabela de pagamentos para exportar.")
                return

            # Cria o DataFrame do Pandas diretamente com os dados coletados (que incluem as marcas)
            df = pd.DataFrame(data_to_export[1:], columns=data_to_export[0])

            # --- NÃO HÁ LIMPEZA AQUI ---
            # Os dados são mantidos como strings com as marcas Unicode.

            # Usa o ExcelWriter para salvar o DataFrame no arquivo .xlsx
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Pagamentos')
                # Ajusta a largura das colunas na planilha para melhor visualização
                worksheet = writer.sheets['Pagamentos']
                for i, col in enumerate(df.columns):
                    column_letter = chr(65 + i) # Converte índice da coluna para letra (A, B, C...)
                    try:
                        # Calcula o comprimento máximo do conteúdo na coluna (incluindo cabeçalho e marcas)
                        max_len = max(df[col].astype(str).map(len).max(), len(str(col)))
                        # Define a largura da coluna com um pequeno preenchimento extra
                        worksheet.column_dimensions[column_letter].width = max_len + 3
                    except Exception as width_err:
                        # Fallback em caso de erro no cálculo da largura
                        print(f"Aviso: Não foi possível calcular a largura da coluna {col}: {width_err}")
                        worksheet.column_dimensions[column_letter].width = 15

            # Informa o usuário que a exportação foi bem-sucedida
            messagebox.showinfo("Sucesso", f"Dados de pagamentos (com marcas) exportados para:\n{file_path}")

            # Tenta abrir o arquivo Excel gerado automaticamente
            try:
                if os.name == 'nt': # Windows
                    os.startfile(file_path)
                elif sys.platform == 'darwin': # MacOS
                    os.system(f'open "{file_path}"')
                else: # Linux
                    os.system(f'xdg-open "{file_path}"')
            except Exception as e:
                # Informa se não foi possível abrir o arquivo
                messagebox.showinfo("Arquivo Salvo", f"Não foi possível abrir o arquivo automaticamente:\n{file_path}\nErro: {e}")

        except Exception as e:
            # Captura e mostra qualquer erro inesperado durante a exportação
            import traceback;
            messagebox.showerror("Erro Exportação", f"Erro ao exportar Pagamentos:\n{str(e)}\n{traceback.format_exc()}")

    # --- Actions (Debtors Tab - Restored/Modified) ---
    def search_debtors(self):
        """Initiates search on the Debtors tab."""
        self.load_debtor_data(filter_term=self.search_var_debtors.get().strip())

    def clear_debtor_form(self):
        """Clears the fields in the comment/status section."""
        self.debtor_status_var.set("Pendente") # Default status
        self.debtor_comment_var.set("")
        self.debtor_amount_var.set("")
        if hasattr(self, 'debtors_tree'):
             self.debtors_tree.selection_set(()) # Deselect any row

    def update_debtor_status(self):
        """Updates status, comment, and potentially amount from the Debtors tab form."""
        selected_items = self.debtors_tree.selection()
        if not selected_items:
            messagebox.showerror("Erro", "Selecione um registro na lista de devedores para atualizar.")
            return

        item = selected_items[0]
        values = self.debtors_tree.item(item, 'values')
        if not values or len(values) < 7:
            messagebox.showerror("Erro", "Dados incompletos na linha de devedor selecionada."); return

        try:
            id_val = int(values[0])
            month = values[3] # Get month name from the selected row
            new_status = self.debtor_status_var.get() # Get from combobox
            new_comment = self.debtor_comment_var.get().strip() # Get from entry
            # Get amount from entry and parse it using the robust function
            new_amount = self.parse_currency(self.debtor_amount_var.get())
        except (IndexError, ValueError, TypeError) as e:
            messagebox.showerror("Erro", f"Erro ao ler dados da seleção ou do formulário: {e}")
            return

        if new_amount < 0:
            messagebox.showerror("Erro de Validação", "O valor não pode ser negativo.")
            return
        if not new_status:
            messagebox.showerror("Erro de Validação", "Selecione um Status válido.")
            return


        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db()
            if not conn: return

            # Update the student_debtors table
            cursor.execute("""
                UPDATE student_debtors
                SET status=%s, comment=%s, amount=%s
                WHERE id=%s AND month=%s
            """, (new_status, new_comment, new_amount, id_val, month))
            conn.commit()
            messagebox.showinfo("Sucesso", f"Registro de débito para ID {id_val}, Mês {month} atualizado.")
            # Refresh both tabs to ensure consistency
            self.load_debtor_data()
            self.load_payment_data() # To update marks on payments tab

        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao atualizar registro do devedor: {e}")
            import traceback; print(traceback.format_exc())
        finally:
            if conn: conn.close()


    def remove_from_debtors(self):
        """Removes a selected entry from the student_debtors list/table."""
        selected_items = self.debtors_tree.selection()
        if not selected_items:
            messagebox.showerror("Erro", "Selecione um registro na lista de devedores para remover.")
            return

        item = selected_items[0]
        values = self.debtors_tree.item(item, 'values')
        if not values or len(values) < 4:
             messagebox.showerror("Erro", "Dados incompletos na linha de devedor selecionada."); return

        try:
            id_val = int(values[0])
            student_name = values[1]
            month = values[3]
        except (IndexError, ValueError, TypeError):
            messagebox.showerror("Erro", "Não foi possível obter ID e Mês da linha selecionada.")
            return

        if not messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover o registro de débito para:\n\nAluno: {student_name} (ID: {id_val})\nMês: {month}\n\nIsso removerá a marca ❌ e o registro da lista de devedores, mas NÃO afetará o valor registrado na aba Pagamentos."):
            return

        conn, cursor = None, None
        try:
            conn, cursor = self.connect_to_db()
            if not conn: return

            cursor.execute("DELETE FROM student_debtors WHERE id=%s AND month=%s", (id_val, month))
            rows_deleted = cursor.rowcount
            conn.commit()

            if rows_deleted > 0:
                messagebox.showinfo("Sucesso", f"Registro de débito para {month} removido com sucesso.")
                self.load_debtor_data()  # Refresh this tab
                self.load_payment_data() # Refresh payments tab to remove mark
                self.clear_debtor_form() # Clear form fields
            else:
                messagebox.showerror("Erro", "Registro de débito não encontrado no banco (pode já ter sido removido).")
                # Still refresh in case view was stale
                self.load_debtor_data()
                self.load_payment_data()

        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao remover registro de débito: {e}")
            import traceback; print(traceback.format_exc())
        finally:
            if conn: conn.close()


    
        # --- MODIFICADO para exportar DEVEDORES com valores formatados como texto ---
    def export_debtors_to_excel(self):
        """Exports the current view of the Debtors table with formatted values as text to Excel."""
        try:
            # Garante que a árvore de devedores existe
            if not hasattr(self, 'debtors_tree'):
                messagebox.showerror("Erro", "Tabela de devedores não inicializada.")
                return

            # Pede ao usuário o local para salvar o arquivo Excel
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Salvar Planilha de Devedores"
            )
            # Se o usuário cancelar, não faz nada
            if not file_path:
                return

            data_to_export = []
            # Pega os nomes das colunas como definidos nos cabeçalhos da Treeview
            columns = [self.debtors_tree.heading(col)['text'] for col in self.debtors_tree['columns']]
            data_to_export.append(columns) # Adiciona cabeçalhos

            # Itera sobre cada linha (item) na Treeview de devedores
            for item_id in self.debtors_tree.get_children():
                # Pega os valores da linha diretamente da Treeview.
                # Estes valores já estão formatados (Valor com vírgula, Status como texto).
                values = list(self.debtors_tree.item(item_id, 'values'))
                if values and len(values) == 7: # Garante que a linha tem a quantidade esperada de colunas
                     data_to_export.append(values)

            # Verifica se há dados para exportar (além dos cabeçalhos)
            if len(data_to_export) <= 1:
                 messagebox.showinfo("Exportar Devedores", "Não há dados na lista de devedores para exportar.")
                 return

            # Cria o DataFrame do Pandas diretamente com os dados coletados (strings formatadas)
            df = pd.DataFrame(data_to_export[1:], columns=data_to_export[0])

            # --- REMOVIDO O BLOCO DE LIMPEZA do VALOR ---
            # A coluna 'Valor' será exportada como texto formatado (ex: "270,18")
            # if 'Valor' in df.columns: df['Valor'] = df['Valor'].apply(lambda x: self.parse_currency(x) if isinstance(x, str) else x) # REMOVIDO

            # Usa o ExcelWriter para salvar o DataFrame no arquivo .xlsx
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Devedores')
                # Ajusta a largura das colunas na planilha para melhor visualização
                worksheet = writer.sheets['Devedores']
                for i, col in enumerate(df.columns):
                    column_letter = chr(65 + i) # Converte índice da coluna para letra (A, B, C...)
                    try:
                        # Calcula o comprimento máximo do conteúdo na coluna (incluindo cabeçalho)
                        max_len = max(df[col].astype(str).map(len).max(), len(str(col)))
                        # Define a largura da coluna com um pequeno preenchimento extra
                        worksheet.column_dimensions[column_letter].width = max_len + 3
                    except Exception as width_err:
                        # Fallback em caso de erro no cálculo da largura
                        print(f"Aviso: Não foi possível calcular a largura da coluna {col}: {width_err}")
                        worksheet.column_dimensions[column_letter].width = 15

            # Informa o usuário que a exportação foi bem-sucedida
            messagebox.showinfo("Sucesso", f"Dados de devedores exportados para:\n{file_path}")

            # Tenta abrir o arquivo Excel gerado automaticamente
            try:
                if os.name == 'nt': # Windows
                    os.startfile(file_path)
                elif sys.platform == 'darwin': # MacOS
                    os.system(f'open "{file_path}"')
                else: # Linux
                    os.system(f'xdg-open "{file_path}"')
            except Exception as e:
                # Informa se não foi possível abrir o arquivo
                messagebox.showinfo("Arquivo Salvo", f"Não foi possível abrir o arquivo automaticamente:\n{file_path}\nErro: {e}")

        except Exception as e:
            # Captura e mostra qualquer erro inesperado durante a exportação
            import traceback
            messagebox.showerror("Erro de Exportação", f"Ocorreu um erro ao exportar devedores para Excel:\n{str(e)}\n\n{traceback.format_exc()}")   


# --- Helper Dialog Class (Unchanged) ---
class StatusChoiceDialog(simpledialog.Dialog):
    def __init__(self, parent, title, options):
        self.options = options; self.result = None;
        # Ensure parent is valid for the Dialog
        if not isinstance(parent, (tk.Tk, tk.Toplevel)):
             parent = tk._default_root # Fallback if parent is invalid
        super().__init__(parent, title=title)

    def body(self, master):
        self.var = tk.StringVar(master);
        default_option = self.options[1] if len(self.options) > 1 else self.options[0];
        self.var.set(default_option);
        ttk.Label(master, text="Marcar como:").grid(row=0, columnspan=2, sticky=tk.W, padx=5, pady=5);
        ttk.Radiobutton(master, text=self.options[0], variable=self.var, value=self.options[0]).grid(row=1, column=0, sticky=tk.W, padx=15, pady=2);
        ttk.Radiobutton(master, text=self.options[1], variable=self.var, value=self.options[1]).grid(row=1, column=1, sticky=tk.W, padx=15, pady=2);
        return None # focus default

    def buttonbox(self):
        box=ttk.Frame(self);
        ok_button=ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE);
        ok_button.pack(side=tk.LEFT, padx=5, pady=5);
        cancel_button=ttk.Button(box, text="Cancelar", width=10, command=self.cancel);
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5);
        self.bind("<Return>", self.ok);
        self.bind("<Escape>", self.cancel);
        box.pack()

    def apply(self):
        self.result = self.var.get()

# --- Application Exit ---
def close_app(root_window, app_instance):
    if messagebox.askyesno("Sair","Tem certeza que deseja sair?"):
        # Explicitly unbind mousewheel events to prevent errors after destroy
        if hasattr(app_instance, 'canvas'):
             app_instance._bind_mousewheel(False) # Unbind

        if hasattr(app_instance,'conn') and app_instance.conn and not app_instance.conn.closed:
            try: app_instance.conn.close(); print("DB connection closed.")
            except Exception as e: print(f"Error closing DB: {e}")
        root_window.destroy()

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    try: style.theme_use('clam') # Or 'vista', 'xpnative', 'aqua' depending on OS
    except tk.TclError: print("Clam theme not available, using default.")

    # Apply theme before creating app instance
    root.update_idletasks()

    app = StudentPaymentApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: close_app(root, app))
    root.mainloop()