import sys
import csv
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTextEdit, QListWidget,
    QMessageBox, QStatusBar, QFrame, QFileDialog
)

from postcode_service import PostcodeService

DATA_PATH = "data"  # folder with all.json + state json files


# ---------- Premium minimal black/white theme ----------
APP_STYLE = """
QMainWindow { background: #0B0B0C; }

QLabel { color: #F2F2F2; }
QLabel#muted { color: #A6A6A6; }
QLabel#title { color: #FFFFFF; }

QFrame#card {
  background: #111112;
  border: 1px solid #1F1F20;
  border-radius: 16px;
}

/* Inputs */
QLineEdit {
  background: #0F0F10;
  border: 1px solid #242426;
  border-radius: 12px;
  padding: 10px 12px;
  color: #F2F2F2;
  font-size: 13px;
}
QLineEdit:focus { border: 1px solid #3A3A3D; }

/* Text areas */
QTextEdit {
  background: #0F0F10;
  border: 1px solid #242426;
  border-radius: 14px;
  padding: 12px;
  color: #F2F2F2;
  font-size: 13px;
}

/* List */
QListWidget {
  background: #0F0F10;
  border: 1px solid #242426;
  border-radius: 14px;
  padding: 6px;
  color: #F2F2F2;
  font-size: 13px;
}
QListWidget::item { padding: 10px 10px; border-radius: 10px; }
QListWidget::item:selected { background: #1D1D1F; }
QListWidget::item:hover { background: #161618; }

/* Buttons (premium outline) */
QPushButton {
  background: transparent;
  border: 1px solid #2B2B2E;
  color: #F2F2F2;
  border-radius: 12px;
  padding: 10px 14px;
  font-weight: 600;
}
QPushButton:hover { border: 1px solid #4A4A4F; background: #121213; }
QPushButton:pressed { background: #0F0F10; }

QPushButton#primary {
  background: #FFFFFF;
  color: #0B0B0C;
  border: 1px solid #FFFFFF;
}
QPushButton#primary:hover { background: #EDEDED; border: 1px solid #EDEDED; }

QPushButton:disabled { color: #777; border: 1px solid #222; }

/* Pill chips */
QPushButton#chip {
  background: #0F0F10;
  border: 1px solid #242426;
  color: #F2F2F2;
  border-radius: 999px;
  padding: 6px 12px;
  font-weight: 600;
}
QPushButton#chip:hover {
  border: 1px solid #3A3A3D;
  background: #121213;
}

/* Tabs */
QTabWidget::pane { border: 0; }
QTabBar::tab {
  background: transparent;
  color: #A6A6A6;
  padding: 10px 14px;
  margin-right: 10px;
  border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
  color: #FFFFFF;
  border-bottom: 2px solid #FFFFFF;
}

/* Status bar */
QStatusBar { background: #0B0B0C; color: #A6A6A6; }
"""


def pretty_result(title: str, lines: list[str]) -> str:
    return f"{title}\n" + ("—" * 42) + "\n" + "\n".join(lines)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Malaysia Postcode Lookup")
        self.setMinimumSize(980, 600)

        try:
            self.service = PostcodeService(DATA_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Data load error", f"Cannot load data from: {DATA_PATH}\n\n{e}")
            raise

        # recent chips
        self.recent_postcodes: list[str] = []
        self.recent_cities: list[str] = []
        self.max_chips = 8

        # last selected/loaded data (for copy/export)
        self.last_postcode_info: dict | None = None
        self.last_city_info: dict | None = None

        self._build_ui()
        self._status("Ready • Offline data loaded")

    def _status(self, msg: str):
        self.statusBar().showMessage(msg, 5000)

    def _card(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        return f

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(18, 18, 18, 14)
        main.setSpacing(14)

        # Header card
        header = self._card()
        h = QVBoxLayout(header)
        h.setContentsMargins(16, 14, 16, 14)
        h.setSpacing(4)

        title = QLabel("Malaysia Postcode Lookup")
        title.setObjectName("title")
        title.setFont(QFont("Arial", 18, QFont.Bold))

        subtitle = QLabel("Minimal • Offline • Fast • Postcode ↔ City/State")
        subtitle.setObjectName("muted")
        subtitle.setFont(QFont("Arial", 11))

        h.addWidget(title)
        h.addWidget(subtitle)
        main.addWidget(header)

        # Tabs in card
        tabs_card = self._card()
        t = QVBoxLayout(tabs_card)
        t.setContentsMargins(12, 12, 12, 12)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_postcode(), "Postcode")
        self.tabs.addTab(self._tab_city(), "City")
        t.addWidget(self.tabs)

        main.addWidget(tabs_card, 1)
        self.setStatusBar(QStatusBar())

    # ---------------- Tabs ----------------
    def _tab_postcode(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Input card
        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(16, 16, 16, 16)
        c.setSpacing(10)

        label = QLabel("Lookup by postcode")
        label.setFont(QFont("Arial", 12, QFont.Bold))

        hint = QLabel("Example: 40100 • Press Enter to lookup")
        hint.setObjectName("muted")
        hint.setFont(QFont("Arial", 10))

        c.addWidget(label)
        c.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.postcode_input = QLineEdit()
        self.postcode_input.setPlaceholderText("Enter postcode…")
        self.postcode_input.setClearButtonEnabled(True)  # ✅ clear (✕)
        self.postcode_input.returnPressed.connect(self.on_lookup_postcode)

        btn_lookup = QPushButton("Lookup")
        btn_lookup.setObjectName("primary")
        btn_lookup.clicked.connect(self.on_lookup_postcode)

        btn_validate = QPushButton("Validate")
        btn_validate.clicked.connect(self.on_validate_postcode)

        btn_copy_postcode = QPushButton("Copy postcode")
        btn_copy_postcode.clicked.connect(self.on_copy_postcode_only)

        btn_copy_address = QPushButton("Copy address")
        btn_copy_address.clicked.connect(self.on_copy_address_format)

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self.on_export_postcode_csv)

        row.addWidget(self.postcode_input, 2)
        row.addWidget(btn_lookup)
        row.addWidget(btn_validate)
        row.addWidget(btn_copy_postcode)
        row.addWidget(btn_copy_address)
        row.addWidget(btn_export)

        c.addLayout(row)

        # Chips row
        chip_row_label = QLabel("Recent postcodes")
        chip_row_label.setObjectName("muted")
        chip_row_label.setFont(QFont("Arial", 10))
        c.addWidget(chip_row_label)

        self.pc_chip_bar = QHBoxLayout()
        self.pc_chip_bar.setSpacing(8)
        self.pc_chip_bar.addStretch()
        c.addLayout(self.pc_chip_bar)

        layout.addWidget(card)

        # Output card
        out_card = self._card()
        o = QVBoxLayout(out_card)
        o.setContentsMargins(16, 16, 16, 16)
        o.setSpacing(8)

        out_label = QLabel("Result")
        out_label.setFont(QFont("Arial", 12, QFont.Bold))

        self.postcode_output = QTextEdit()
        self.postcode_output.setReadOnly(True)
        self.postcode_output.setPlaceholderText("Results will appear here…")

        o.addWidget(out_label)
        o.addWidget(self.postcode_output, 1)
        layout.addWidget(out_card, 1)

        return w

    def _tab_city(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Search card
        top = self._card()
        t = QVBoxLayout(top)
        t.setContentsMargins(16, 16, 16, 16)
        t.setSpacing(10)

        label = QLabel("Search by city")
        label.setFont(QFont("Arial", 12, QFont.Bold))

        hint = QLabel("Type to filter • Click a city to show postcodes")
        hint.setObjectName("muted")
        hint.setFont(QFont("Arial", 10))

        t.addWidget(label)
        t.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter city name… (e.g., Shah Alam)")
        self.city_input.setClearButtonEnabled(True)  # ✅ clear (✕)
        self.city_input.textChanged.connect(self.on_city_search_changed)
        self.city_input.returnPressed.connect(self.on_open_city)

        btn_show = QPushButton("Show")
        btn_show.setObjectName("primary")
        btn_show.clicked.connect(self.on_open_city)

        btn_copy_city_postcodes = QPushButton("Copy postcodes")
        btn_copy_city_postcodes.clicked.connect(self.on_copy_city_postcodes_only)

        btn_copy_city_address = QPushButton("Copy city/state")
        btn_copy_city_address.clicked.connect(self.on_copy_city_address_format)

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self.on_export_city_csv)

        row.addWidget(self.city_input, 2)
        row.addWidget(btn_show)
        row.addWidget(btn_copy_city_postcodes)
        row.addWidget(btn_copy_city_address)
        row.addWidget(btn_export)

        t.addLayout(row)

        # Chips row
        chip_row_label = QLabel("Recent cities")
        chip_row_label.setObjectName("muted")
        chip_row_label.setFont(QFont("Arial", 10))
        t.addWidget(chip_row_label)

        self.city_chip_bar = QHBoxLayout()
        self.city_chip_bar.setSpacing(8)
        self.city_chip_bar.addStretch()
        t.addLayout(self.city_chip_bar)

        layout.addWidget(top)

        # Results split
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        left = self._card()
        l = QVBoxLayout(left)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(8)

        ltitle = QLabel("Matching cities")
        ltitle.setFont(QFont("Arial", 12, QFont.Bold))

        self.city_list = QListWidget()
        self.city_list.itemClicked.connect(self.on_city_list_clicked)

        l.addWidget(ltitle)
        l.addWidget(self.city_list, 1)

        right = self._card()
        r = QVBoxLayout(right)
        r.setContentsMargins(16, 16, 16, 16)
        r.setSpacing(8)

        rtitle = QLabel("City postcodes")
        rtitle.setFont(QFont("Arial", 12, QFont.Bold))

        self.city_output = QTextEdit()
        self.city_output.setReadOnly(True)
        self.city_output.setPlaceholderText("Select a city to view postcodes…")

        r.addWidget(rtitle)
        r.addWidget(self.city_output, 1)

        bottom.addWidget(left, 1)
        bottom.addWidget(right, 2)

        layout.addLayout(bottom, 1)
        return w

    # ---------------- Chips helpers ----------------
    def _push_recent(self, arr: list[str], value: str):
        value = (value or "").strip()
        if not value:
            return
        if value in arr:
            arr.remove(value)
        arr.insert(0, value)
        del arr[self.max_chips:]

    def _rebuild_chip_bar(self, bar_layout: QHBoxLayout, items: list[str], on_click):
        # clear existing widgets (except stretch)
        while bar_layout.count() > 0:
            item = bar_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for txt in items:
            b = QPushButton(txt)
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, t=txt: on_click(t))
            bar_layout.addWidget(b)

        bar_layout.addStretch()

    def _set_postcode_from_chip(self, pc: str):
        self.postcode_input.setText(pc)
        self.on_lookup_postcode()

    def _set_city_from_chip(self, city: str):
        self.city_input.setText(city)
        self.on_open_city()

    # ---------------- Actions (Postcode) ----------------
    def on_lookup_postcode(self):
        pc = self.postcode_input.text().strip()
        if not pc:
            self._status("Enter a postcode first.")
            return

        info = self.service.lookup_by_postcode(pc)
        self.last_postcode_info = info

        # update chips
        self._push_recent(self.recent_postcodes, pc)
        self._rebuild_chip_bar(self.pc_chip_bar, self.recent_postcodes, self._set_postcode_from_chip)

        if not info:
            self.postcode_output.setText(pretty_result("Not found", [
                f"Postcode: {pc}",
                "This postcode is not in your dataset."
            ]))
            self._status("Not found.")
            return

        self.postcode_output.setText(pretty_result("Lookup result", [
            f"Postcode: {info['postcode']}",
            f"City: {info['city']}",
            f"State: {info['state']}  ({info['state_code']})",
        ]))
        self._status("Lookup complete.")

    def on_validate_postcode(self):
        pc = self.postcode_input.text().strip()
        if not pc:
            self._status("Enter a postcode first.")
            return

        res = self.service.validate_postcode(pc)
        self.last_postcode_info = res if res.get("valid") else None

        self._push_recent(self.recent_postcodes, pc)
        self._rebuild_chip_bar(self.pc_chip_bar, self.recent_postcodes, self._set_postcode_from_chip)

        if res.get("valid"):
            self.postcode_output.setText(pretty_result("Valid postcode", [
                f"Postcode: {res['postcode']}",
                f"City: {res['city']}",
                f"State: {res['state']}  ({res['state_code']})",
            ]))
            self._status("Valid.")
        else:
            self.postcode_output.setText(pretty_result("Invalid postcode", [
                f"Postcode: {res.get('postcode', pc)}",
                "Not found in dataset."
            ]))
            self._status("Invalid.")

    # ✅ Copy postcode only
    def on_copy_postcode_only(self):
        info = self.last_postcode_info
        if not info:
            self._status("No valid result to copy.")
            return
        QApplication.clipboard().setText(info["postcode"])
        self._status("Copied postcode.")

    # ✅ Copy address format
    def on_copy_address_format(self):
        info = self.last_postcode_info
        if not info:
            self._status("No valid result to copy.")
            return
        text = f"{info['postcode']}, {info['city']}, {info['state']}"
        QApplication.clipboard().setText(text)
        self._status("Copied address format.")

    # ✅ Export postcode lookup to CSV (single row)
    def on_export_postcode_csv(self):
        info = self.last_postcode_info
        if not info:
            self._status("No valid result to export.")
            return

        default_name = f"postcode_lookup_{info['postcode']}_{now_stamp()}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default_name, "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["postcode", "city", "state", "state_code"])
                w.writerow([info["postcode"], info["city"], info["state"], info.get("state_code", "")])
            self._status("Exported CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

    # ---------------- Actions (City) ----------------
    def on_city_search_changed(self, text: str):
        self.city_list.clear()
        matches = self.service.search_cities(text, limit=200)
        self.city_list.addItems(matches)
        if text.strip():
            self._status(f"{len(matches)} matches")

    def on_city_list_clicked(self, item):
        self.city_input.setText(item.text())
        self.on_open_city()

    def on_open_city(self):
        city = self.city_input.text().strip()
        if not city:
            self._status("Enter a city first.")
            return

        info = self.service.lookup_by_city(city)
        self.last_city_info = info

        # update chips
        self._push_recent(self.recent_cities, city)
        self._rebuild_chip_bar(self.city_chip_bar, self.recent_cities, self._set_city_from_chip)

        if not info:
            self.city_output.setText(pretty_result("City not found", [
                f"City: {city}",
                "Tip: Click a city from the list for exact match."
            ]))
            self._status("City not found.")
            return

        pcs = info["postcodes"]
        preview = ", ".join(pcs[:160])
        if len(pcs) > 160:
            preview += f", … (+{len(pcs)-160} more)"

        self.city_output.setText(pretty_result("City postcodes", [
            f"City: {info['city']}",
            f"State: {info['state']}  ({info['state_code']})",
            f"Total: {len(pcs)}",
            "",
            preview
        ]))
        self._status("City loaded.")

    # ✅ Copy postcodes only
    def on_copy_city_postcodes_only(self):
        info = self.last_city_info
        if not info:
            self._status("No city result to copy.")
            return
        text = ", ".join(info["postcodes"])
        QApplication.clipboard().setText(text)
        self._status("Copied postcodes.")

    # ✅ Copy "City, State" format
    def on_copy_city_address_format(self):
        info = self.last_city_info
        if not info:
            self._status("No city result to copy.")
            return
        text = f"{info['city']}, {info['state']}"
        QApplication.clipboard().setText(text)
        self._status("Copied city/state.")

    # ✅ Export city postcodes to CSV (many rows)
    def on_export_city_csv(self):
        info = self.last_city_info
        if not info:
            self._status("No city result to export.")
            return

        safe_city = info["city"].replace("/", "-")
        default_name = f"city_postcodes_{safe_city}_{now_stamp()}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default_name, "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["postcode", "city", "state", "state_code"])
                for pc in info["postcodes"]:
                    w.writerow([pc, info["city"], info["state"], info.get("state_code", "")])
            self._status("Exported CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
