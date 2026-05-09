"""
デュエル・マスターズ GUI版
tkinter (Python標準) を使用して別ウィンドウで動作。
起動: python gui_main.py
"""
import tkinter as tk
import threading
import queue
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── テーマ定数 ─────────────────────────────────────────────────
BG_MAIN  = "#F8F9FA"
BG_TEXT  = "#FFFFFF"
FG_TEXT  = "#1A1A2E"
BG_INPUT = "#FFFFFF"
CLR_SEP  = "#DEE2E6"
CLR_TTL  = "#3730A3"
BG_BTN   = "#1565C0"
FG_BTN   = "#FFFFFF"
BG_BTN_A = "#0D47A1"
BG_CLR   = "#6B7280"
BG_CLR_A = "#4B5563"

FONT_MAIN  = ("Consolas", 14)
FONT_BOLD  = ("Consolas", 14, "bold")
FONT_INPUT = ("Consolas", 14)
FONT_TITLE = ("Yu Gothic UI", 20, "bold")
FONT_LABEL = ("Yu Gothic UI", 12)
FONT_BTN   = ("Yu Gothic UI", 12, "bold")
FONT_STAT  = ("Yu Gothic UI", 10)

# テキストカラー（行の内容で自動判定）
_TAG_CFG = {
    "header":  {"foreground": "#4338CA"},
    "sep":     {"foreground": "#9CA3AF"},
    "log":     {"foreground": "#047857"},
    "trigger": {"foreground": "#B45309"},
    "win":     {"foreground": "#92400E"},
    "ai":      {"foreground": "#B91C1C"},
    "echo":    {"foreground": "#6B7280"},
    "mana":    {"foreground": "#1565C0"},
}


def _detect_tag(line: str) -> str:
    if re.search(r"[═]{4,}", line):
        return "header"
    if re.search(r"[─]{4,}", line):
        return "sep"
    if "★" in line or "シールドトリガー" in line:
        return "trigger"
    if "勝者" in line or "の勝利" in line:
        return "win"
    if "[AI]" in line or re.match(r"\s*AI", line):
        return "ai"
    if line.strip().startswith(">>"):
        return "log"
    if "マナ:" in line:
        return "mana"
    return ""


# ── I/O リダイレクト ───────────────────────────────────────────

class _Stdout:
    def __init__(self, win: "GameWindow"):
        self._win = win

    def write(self, text: str):
        if text:
            self._win._text_queue.put(text)

    def flush(self):
        pass


class _Stdin:
    def __init__(self, win: "GameWindow"):
        self._win = win

    def readline(self) -> str:
        return self._win.get_input() + "\n"

    def read(self, _n: int = -1) -> str:
        return self.readline()


# ── メインウィンドウ ───────────────────────────────────────────

class GameWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("デュエル・マスターズ")
        self.root.configure(bg=BG_MAIN)
        self.root.state("zoomed")   # 起動時に最大化

        self._text_queue: queue.Queue[str] = queue.Queue()
        self._input_event = threading.Event()
        self._input_value = ""
        self._line_buf = ""

        self._build_ui()
        self._configure_tags()
        self._poll_queue()

        sys.stdout = _Stdout(self)
        sys.stderr = _Stdout(self)
        sys.stdin  = _Stdin(self)

    # ── UI 構築 ──────────────────────────────────────────────
    # 重要: tkinter pack では「下部固定要素を先に BOTTOM で pack」してから
    #       expand=True のウィジェットを pack しないと入力欄が画面外に出る。

    def _build_ui(self):
        # ── TOP: ヘッダー（タイトル + クリアボタン）──
        hdr = tk.Frame(self.root, bg=BG_MAIN)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=28, pady=(16, 0))

        tk.Label(
            hdr,
            text="⚔  デュエル・マスターズ",
            bg=BG_MAIN, fg=CLR_TTL,
            font=FONT_TITLE,
            anchor="w",
        ).pack(side=tk.LEFT)

        tk.Button(
            hdr,
            text="ログをクリア",
            bg=BG_CLR, fg=FG_BTN,
            font=FONT_BTN,
            relief=tk.FLAT,
            padx=14, pady=4,
            command=self._clear_log,
            cursor="hand2",
            activebackground=BG_CLR_A,
            activeforeground=FG_BTN,
        ).pack(side=tk.RIGHT)

        tk.Frame(self.root, bg=CLR_SEP, height=2).pack(
            side=tk.TOP, fill=tk.X, padx=28, pady=(10, 0))

        # ── BOTTOM: ステータスバー（先に pack して領域を確保）──
        self.status_var = tk.StringVar(value="読み込み中...")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=BG_MAIN, fg="#6B7280",
            font=FONT_STAT,
            anchor="w",
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(0, 8))

        # ── BOTTOM: 入力行区切り線 ──
        tk.Frame(self.root, bg=CLR_SEP, height=2).pack(
            side=tk.BOTTOM, fill=tk.X, padx=28)

        # ── BOTTOM: 入力行 ──
        in_row = tk.Frame(self.root, bg=BG_MAIN)
        in_row.pack(side=tk.BOTTOM, fill=tk.X, padx=28, pady=12)

        tk.Label(
            in_row,
            text="入力:",
            bg=BG_MAIN, fg="#374151",
            font=FONT_LABEL,
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(
            in_row,
            textvariable=self.input_var,
            bg=BG_INPUT, fg=FG_TEXT,
            font=FONT_INPUT,
            relief=tk.FLAT,
            highlightbackground=CLR_SEP,
            highlightthickness=2,
            insertbackground=FG_TEXT,
            state=tk.DISABLED,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.entry.bind("<Return>", lambda _: self._submit())

        self.btn = tk.Button(
            in_row,
            text="送信  ↵",
            bg=BG_BTN, fg=FG_BTN,
            font=FONT_BTN,
            relief=tk.FLAT,
            padx=20, pady=7,
            command=self._submit,
            state=tk.DISABLED,
            cursor="hand2",
            activebackground=BG_BTN_A,
            activeforeground=FG_BTN,
        )
        self.btn.pack(side=tk.LEFT, padx=(12, 0))

        # ── CENTER: テキストエリア（残りのスペースを全て使う）──
        txt_wrap = tk.Frame(self.root, bg=BG_MAIN)
        txt_wrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=28, pady=(10, 0))

        vsb = tk.Scrollbar(txt_wrap, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        hsb = tk.Scrollbar(txt_wrap, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.text = tk.Text(
            txt_wrap,
            state=tk.DISABLED,
            bg=BG_TEXT, fg=FG_TEXT,
            font=FONT_MAIN,
            wrap=tk.NONE,
            padx=16, pady=12,
            relief=tk.FLAT,
            highlightbackground=CLR_SEP,
            highlightthickness=1,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectbackground="#BFDBFE",
            cursor="arrow",
            spacing1=2,
            spacing3=2,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self.text.yview)
        hsb.config(command=self.text.xview)

    def _configure_tags(self):
        for name, cfg in _TAG_CFG.items():
            fnt = FONT_BOLD if name in ("trigger", "win", "header") else FONT_MAIN
            self.text.tag_configure(name, font=fnt, **cfg)

    # ── ログクリア ────────────────────────────────────────────

    def _clear_log(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)

    # ── テキストキュー処理 ─────────────────────────────────────

    def _poll_queue(self):
        self._flush_queue()
        self.root.after(40, self._poll_queue)

    def _flush_queue(self):
        chunks: list[str] = []
        while True:
            try:
                chunks.append(self._text_queue.get_nowait())
            except queue.Empty:
                break
        if chunks:
            self._insert_text("".join(chunks))

    def _insert_text(self, text: str):
        self.text.config(state=tk.NORMAL)
        buf = self._line_buf + text
        self._line_buf = ""
        lines = buf.split("\n")
        for i, line in enumerate(lines):
            if i < len(lines) - 1:
                tag = _detect_tag(line)
                self.text.insert(tk.END, line + "\n", tag if tag else ())
            else:
                self._line_buf = line
        self.text.config(state=tk.DISABLED)
        self.text.see(tk.END)

    def _flush_line_buf(self):
        if self._line_buf:
            self.text.config(state=tk.NORMAL)
            tag = _detect_tag(self._line_buf)
            self.text.insert(tk.END, self._line_buf, tag if tag else ())
            self._line_buf = ""
            self.text.config(state=tk.DISABLED)
            self.text.see(tk.END)

    # ── 入力処理 ──────────────────────────────────────────────

    def _enable_input(self):
        self.entry.config(state=tk.NORMAL)
        self.btn.config(state=tk.NORMAL)
        self.entry.focus_set()
        self.status_var.set("⌨  入力待ち...")

    def _disable_input(self):
        self.entry.config(state=tk.DISABLED)
        self.btn.config(state=tk.DISABLED)
        self.status_var.set("処理中...")

    def _submit(self):
        if self.entry.cget("state") == tk.DISABLED:
            return
        val = self.input_var.get()
        self.input_var.set("")
        self._disable_input()
        self._input_value = val
        self._input_event.set()

    def get_input(self) -> str:
        self._input_event.clear()

        def _prepare():
            self._flush_queue()
            self._flush_line_buf()
            self._enable_input()

        self.root.after(0, _prepare)
        self._input_event.wait()

        self._text_queue.put(f"{self._input_value}\n")
        return self._input_value

    # ── ゲームスレッド起動 ─────────────────────────────────────

    def run(self):
        def _game():
            try:
                import main as gm
                gm.main()
            except SystemExit:
                pass
            except Exception as exc:
                import traceback
                self._text_queue.put(
                    f"\n[エラー発生]\n{exc}\n{traceback.format_exc()}\n"
                )
            finally:
                self._text_queue.put(
                    "\n══════════════════════════════════════════\n"
                    "  ゲーム終了。ウィンドウを閉じてください。\n"
                    "══════════════════════════════════════════\n"
                )
                self.root.after(0, lambda: self.status_var.set("ゲーム終了"))

        threading.Thread(target=_game, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    GameWindow().run()
