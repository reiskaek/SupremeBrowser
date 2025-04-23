import sys
import os
import requests
from urllib.parse import urlparse
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QHBoxLayout, \
    QListWidget, QListWidgetItem, QTabWidget, QMenu, QLabel, QDialog, QVBoxLayout, QFormLayout, QDateTimeEdit
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl, QSize, Qt, QDateTime
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut

os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
os.environ["WEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --ignore-gpu-blocklist"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--use-gl=angle"

BOOKMARKS_FILE = "bookmarks.txt"
HISTORY_FILE = "history.txt"
ICON_CACHE_DIR = "favicons"
DEFAULT_ICON = "favicon_not_found.png"

if not os.path.exists(ICON_CACHE_DIR):
    os.makedirs(ICON_CACHE_DIR)

class HistoryItemDialog(QDialog):
    def __init__(self, history_item, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History Item Details")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.timestamp_edit = QDateTimeEdit(QDateTime.currentDateTime(), self)
        self.timestamp_edit.setDateTime(QDateTime.fromString(history_item['timestamp'], "yyyy-MM-dd hh:mm:ss"))
        form_layout.addRow("Timestamp", self.timestamp_edit)

        self.url_label = QLabel(history_item['url'], self)
        form_layout.addRow("URL", self.url_label)

        self.delete_button = QPushButton("Delete History Item", self)
        self.delete_button.clicked.connect(self.delete_history_item)

        layout.addLayout(form_layout)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)
        self.history_item = history_item

    def delete_history_item(self):
        # Logic to delete the history item
        self.accept()


class WebViewSetup(QWidget):
    def __init__(self, parent=None, tab_index=None, tab_widget=None):
        super().__init__(parent)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://maniksharma.xyz/SupremeBrowser"))
        self.browser.urlChanged.connect(self.update_url)
        self.browser.titleChanged.connect(self.update_tab_title)  # Updates tab title
        self.browser.iconChanged.connect(self.update_tab_icon)  # Updates tab icon
        self.browser.loadFinished.connect(self.handle_load_finished)

        self.browser.page().settings().setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, False)

        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.load_url)

        self.back_button = QPushButton("←")
        self.back_button.clicked.connect(self.browser.back)

        self.forward_button = QPushButton("→")
        self.forward_button.clicked.connect(self.browser.forward)

        self.favourite_button = QPushButton("⭐")
        self.favourite_button.clicked.connect(self.add_favourite)

        self.bookmarks_list = QListWidget()
        self.bookmarks_list.setFixedWidth(80)
        self.bookmarks_list.setIconSize(QSize(64, 64))
        self.bookmarks_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)  # Enable drag-and-drop
        self.bookmarks_list.setDefaultDropAction(Qt.DropAction.MoveAction)  # Ensure that the move action is triggered
        self.bookmarks_list.itemClicked.connect(self.load_favourite)
        self.bookmarks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmarks_list.customContextMenuRequested.connect(self.bookmarks_context_menu)

        self.history_list = QListWidget()
        self.history_list.setFixedWidth(200)
        self.history_list.setVisible(False)
        self.history_list.itemClicked.connect(self.load_history_item)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.history_context_menu)

        self.history_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self.history_shortcut.activated.connect(self.toggle_history)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.address_bar)
        nav_layout.addWidget(self.favourite_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.bookmarks_list)

        content_layout = QVBoxLayout()
        content_layout.addLayout(nav_layout)
        content_layout.addWidget(self.browser)
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

        self.favourites = {}
        self.history = []
        self.load_bookmarks()
        self.load_history()

        self.tab_index = tab_index  # Store the tab index
        self.tab_widget = tab_widget  # Store reference to tab widget

    def load_url(self):
        url = self.address_bar.text().strip()
        if "." not in url or " " in url:
            url = f"https://www.duckduckgo.com/search?q={url}"
        elif not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        self.browser.setUrl(QUrl(url))

    def handle_load_finished(self, success):
        if not success:
            url = self.browser.url().toString()
            search_url = QUrl(f"https://www.duckduckgo.com/search?q={url}")
            self.browser.setUrl(search_url)

    def update_url(self, url):
        url_str = url.toString()
        self.address_bar.setText(url_str)
        if url_str not in self.history:
            self.history.append(url_str)
            self.history_list.addItem(url_str)
            self.save_history()

    def update_tab_title(self, title):
        """ Updates the correct tab title dynamically """
        if self.tab_widget:
            index = self.tab_widget.indexOf(self.parent())  # Get the actual index
            if index != -1:
                self.tab_widget.setTabText(index, title if title else "New Tab")

    def update_tab_icon(self, icon):
        """ Updates the correct tab icon dynamically """
        if self.tab_widget:
            index = self.tab_widget.indexOf(self.parent())  # Get the actual index
            if index != -1:
                self.tab_widget.setTabIcon(index, icon)

    def add_favourite(self):
        url = self.browser.url().toString()
        parsed_url = urlparse(url)
        short_name = parsed_url.netloc.replace("www.", "").split(".")[0]

        if short_name and short_name not in self.favourites:
            self.favourites[short_name] = url
            icon_path = self.download_favicon(parsed_url.netloc)
            item = QListWidgetItem()
            item.setIcon(QIcon(icon_path))
            item.setData(32, short_name)
            item.setToolTip(url if icon_path == DEFAULT_ICON else "")
            self.bookmarks_list.addItem(item)
            self.save_bookmarks()

    def load_favourite(self, item):
        short_name = item.data(32)
        url = self.favourites.get(short_name, f"https://{short_name}.com")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        self.browser.setUrl(QUrl(url))

    def save_bookmarks(self):
        with open(BOOKMARKS_FILE, "w") as f:
            for short_name, url in self.favourites.items():
                f.write(f"{short_name} {url}\n")

    def load_bookmarks(self):
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, "r") as f:
                for line_num, line in enumerate(f, start=1):
                    parts = line.strip().split(" ", 1)
                    if len(parts) != 2:
                        print(f"[Bookmarks] Skipping invalid line {line_num}: {line.strip()}")
                        continue
                    short_name, url = parts
                    self.favourites[short_name] = url
                    icon_path = self.download_favicon(urlparse(url).netloc)
                    item = QListWidgetItem()
                    item.setIcon(QIcon(icon_path))
                    item.setData(32, short_name)
                    item.setToolTip(url if icon_path == DEFAULT_ICON else "")
                    self.bookmarks_list.addItem(item)

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            for url in self.history:
                f.write(url + "\n")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                for line in f:
                    url = line.strip()
                    timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                    self.history.append({'url': url, 'timestamp': timestamp})
                    self.history_list.addItem(f"{timestamp} - {url}")

    def toggle_history(self):
        self.history_list.setVisible(not self.history_list.isVisible())

    def load_history_item(self, item):
        url = item.text().split(" - ")[1]
        self.browser.setUrl(QUrl(url))

    def history_context_menu(self, pos):
        item = self.history_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Delete")
            details_action = menu.addAction("Details")
            action = menu.exec(self.history_list.mapToGlobal(pos))
            if action == delete_action:
                self.history_list.takeItem(self.history_list.row(item))
                self.history.remove(next(h for h in self.history if h['url'] == item.text().split(" - ")[1]))
                self.save_history()
            elif action == details_action:
                history_item = next(h for h in self.history if h['url'] == item.text().split(" - ")[1])
                dialog = HistoryItemDialog(history_item)
                dialog.exec()

    def bookmarks_context_menu(self, pos):
        item = self.bookmarks_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Delete Bookmark")
            action = menu.exec(self.bookmarks_list.mapToGlobal(pos))
            if action == delete_action:
                self.favourites.pop(item.data(32), None)
                self.bookmarks_list.takeItem(self.bookmarks_list.row(item))
                self.save_bookmarks()

    def download_favicon(self, domain):
        icon_path = os.path.join(ICON_CACHE_DIR, f"{domain}.ico")
        if not os.path.exists(icon_path):
            url = f"https://www.google.com/s2/favicons?domain={domain}"
            try:
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(icon_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                else:
                    icon_path = DEFAULT_ICON
            except requests.RequestException:
                icon_path = DEFAULT_ICON
        return icon_path

app = QApplication(sys.argv)
window = QMainWindow()

tabs = QTabWidget()
window.setCentralWidget(tabs)

tab1 = WebViewSetup(tab_widget=tabs, tab_index=0)
tabs.addTab(tab1, "New Tab")

window.show()
sys.exit(app.exec())
