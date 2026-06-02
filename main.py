import sys
import os
import json
import random

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QListWidget, QListWidgetItem,
    QSplitter, QMenu, QSystemTrayIcon, QStyle
)
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut, QFont, QIcon, QAction

APP_TITLE = "音乐播放器"
CONFIG_FILE = "music_config.json"

SUPPORTED_FORMATS = [
    "*.mp3", "*.flac", "*.wav", "*.aac", "*.ogg", "*.m4a", "*.wma",
    "*.ape", "*.opus", "*.mka"
]

PLAY_MODES = ["顺序播放", "随机播放", "单曲循环"]


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self.playlist = []
        self.current_index = -1
        self.play_mode = 0  # 0=顺序, 1=随机, 2=单曲循环
        self.volume = 80
        self.is_mini_mode = False

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(self.volume / 100)

        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        self._init_ui()
        self._init_shortcuts()
        self._init_tray()
        self._load_config()
        self.setAcceptDrops(True)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：播放列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 播放列表标题栏
        header = QWidget()
        header.setStyleSheet("background-color: #1a1a2e; color: #e0e0e0;")
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(10, 6, 10, 6)

        lbl_title = QLabel("播放列表")
        lbl_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        hlayout.addWidget(lbl_title)
        hlayout.addStretch()

        btn_add = QPushButton("+ 添加")
        btn_add.setFixedSize(60, 26)
        btn_add.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        btn_add.clicked.connect(self.add_files)
        hlayout.addWidget(btn_add)

        btn_clear = QPushButton("清空")
        btn_clear.setFixedSize(40, 26)
        btn_clear.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        btn_clear.clicked.connect(self._clear_playlist)
        hlayout.addWidget(btn_clear)

        left_layout.addWidget(header)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setFont(QFont("Microsoft YaHei", 10))
        self.playlist_widget.setStyleSheet("""
            QListWidget { background-color: #12121e; color: #e0e0e0; border: none; padding: 4px; }
            QListWidget::item { padding: 10px 12px; border-radius: 4px; margin: 2px 0; }
            QListWidget::item:selected { background-color: #2d4a6f; color: #ffffff; }
            QListWidget::item:hover { background-color: #1e1e3a; }
        """)
        self.playlist_widget.itemClicked.connect(self._on_playlist_clicked)
        self.playlist_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_widget.customContextMenuRequested.connect(self._on_playlist_context_menu)
        left_layout.addWidget(self.playlist_widget)

        left.setMaximumWidth(380)
        left.setMinimumWidth(260)
        splitter.addWidget(left)

        # 右侧：主播放区
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # 歌曲信息区
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_cover = QLabel("🎵")
        self.lbl_cover.setFont(QFont("Segoe UI Emoji", 72))
        self.lbl_cover.setStyleSheet("color: #4a9eff;")
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setFixedSize(200, 200)
        info_layout.addWidget(self.lbl_cover)

        self.lbl_title = QLabel("未播放")
        self.lbl_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #ffffff;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.lbl_title)

        self.lbl_artist = QLabel("")
        self.lbl_artist.setFont(QFont("Microsoft YaHei", 12))
        self.lbl_artist.setStyleSheet("color: #888;")
        self.lbl_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.lbl_artist)

        self.lbl_album = QLabel("")
        self.lbl_album.setFont(QFont("Microsoft YaHei", 10))
        self.lbl_album.setStyleSheet("color: #666;")
        self.lbl_album.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.lbl_album)

        right_layout.addWidget(info_widget, 1)

        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.progress_slider.sliderReleased.connect(self._on_seek)
        self.progress_slider.valueChanged.connect(self._on_seek_drag)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #3a3a5a; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #4a9eff; border-radius: 2px; }
            QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0; background: #4a9eff; border-radius: 7px; }
        """)
        right_layout.addWidget(self.progress_slider)

        # 时间显示
        time_layout = QHBoxLayout()
        self.lbl_current = QLabel("00:00")
        self.lbl_current.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        time_layout.addWidget(self.lbl_current)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_total)
        right_layout.addLayout(time_layout)

        # 控制按钮
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(15)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_mode = QPushButton("🔁")
        self.btn_mode.setFixedSize(36, 36)
        self.btn_mode.setToolTip(PLAY_MODES[self.play_mode])
        self.btn_mode.clicked.connect(self.cycle_mode)
        ctrl_layout.addWidget(self.btn_mode)

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.setFont(QFont("Segoe UI", 14))
        self.btn_prev.clicked.connect(self.play_prev)
        ctrl_layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(60, 60)
        self.btn_play.setFont(QFont("Segoe UI", 20))
        self.btn_play.setStyleSheet("""
            QPushButton { background-color: #4a9eff; border-radius: 30px; color: white; }
            QPushButton:hover { background-color: #5aadff; }
        """)
        self.btn_play.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.setFont(QFont("Segoe UI", 14))
        self.btn_next.clicked.connect(self.play_next)
        ctrl_layout.addWidget(self.btn_next)

        self.btn_random = QPushButton("🔀")
        self.btn_random.setFixedSize(36, 36)
        self.btn_random.setToolTip("随机播放")
        self.btn_random.clicked.connect(self.toggle_random)
        ctrl_layout.addWidget(self.btn_random)

        right_layout.addLayout(ctrl_layout)

        # 音量控制
        vol_layout = QHBoxLayout()
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedSize(28, 28)
        self.btn_mute.clicked.connect(self.toggle_mute)
        vol_layout.addWidget(self.btn_mute)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.volume)
        self.slider_volume.setFixedWidth(100)
        self.slider_volume.valueChanged.connect(self.set_volume)
        vol_layout.addWidget(self.slider_volume)

        vol_layout.addStretch()

        self.btn_mini = QPushButton("🗕")
        self.btn_mini.setFixedSize(28, 28)
        self.btn_mini.setToolTip("迷你模式")
        self.btn_mini.clicked.connect(self.toggle_mini_mode)
        vol_layout.addWidget(self.btn_mini)

        right_layout.addLayout(vol_layout)

        splitter.addWidget(right)
        splitter.setSizes([320, 780])
        layout.addWidget(splitter)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f1a; }
            QWidget { background-color: #0f0f1a; color: #e0e0e0; }
            QPushButton {
                background-color: transparent; border: none; color: #e0e0e0;
                font-size: 14px; padding: 6px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #2a2a4a; }
        """)

    def _init_shortcuts(self):
        shortcuts = [
            ("Space", self.toggle_play),
            ("Ctrl+O", self.add_files),
            ("Ctrl+Right", lambda: self.seek(5000)),
            ("Ctrl+Left", lambda: self.seek(-5000)),
            ("Right", lambda: self.seek(3000)),
            ("Left", lambda: self.seek(-3000)),
            ("Up", self.volume_up),
            ("Down", self.volume_down),
            ("M", self.toggle_mute),
            ("N", self.play_next),
            ("P", self.play_prev),
            ("Ctrl+Q", self.close),
            ("Delete", self.remove_current),
        ]
        for key, callback in shortcuts:
            QShortcut(QKeySequence(key), self, activated=callback)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.tray_icon.setToolTip(APP_TITLE)

        tray_menu = QMenu()
        tray_menu.addAction("显示", self.show)
        tray_menu.addAction("播放/暂停", self.toggle_play)
        tray_menu.addAction("上一首", self.play_prev)
        tray_menu.addAction("下一首", self.play_next)
        tray_menu.addSeparator()
        tray_menu.addAction("退出", self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.volume = config.get('volume', 80)
                    self.slider_volume.setValue(self.volume)
                    self.audio_output.setVolume(self.volume / 100)
                    self.play_mode = config.get('play_mode', 0)
                    self._update_mode_button()
                    saved = config.get('playlist', [])
                    if saved:
                        self.playlist = [p for p in saved if os.path.exists(p)]
                        self._refresh_playlist_ui()
        except Exception as e:
            print(f"加载配置失败: {e}")

    def _save_config(self):
        try:
            config = {
                'volume': self.volume,
                'play_mode': self.play_mode,
                'playlist': self.playlist,
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def add_files(self):
        filters = "音乐文件 (" + " ".join(SUPPORTED_FORMATS) + ");;所有文件 (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择音乐文件", "", filters)
        if files:
            self._add_to_playlist(files)

    def _add_to_playlist(self, files):
        start_idx = len(self.playlist)
        for f in files:
            if f not in self.playlist:
                self.playlist.append(f)
        self._refresh_playlist_ui()
        if start_idx == 0 and self.playlist:
            self.play_at_index(0)

    def _refresh_playlist_ui(self):
        self.playlist_widget.clear()
        for i, path in enumerate(self.playlist):
            name = os.path.basename(path)
            # 尝试读取元数据
            try:
                from mutagen import File
                audio = File(path)
                if audio and audio.tags:
                    title = audio.tags.get('TIT2', [name])[0] if hasattr(audio.tags, 'get') else name
                    artist = audio.tags.get('TPE1', [''])[0] if hasattr(audio.tags, 'get') else ''
                    display = f"{title}"
                    if artist:
                        display += f" - {artist}"
                else:
                    display = name
            except:
                display = name

            item = QListWidgetItem(f"{i+1}. {display}")
            item.setToolTip(path)
            self.playlist_widget.addItem(item)
        if self.current_index >= 0:
            self.playlist_widget.setCurrentRow(self.current_index)

    def _on_playlist_clicked(self, item):
        idx = self.playlist_widget.row(item)
        self.play_at_index(idx)

    def _on_playlist_context_menu(self, pos):
        item = self.playlist_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        idx = self.playlist_widget.row(item)
        menu.addAction("▶ 播放", lambda: self.play_at_index(idx))
        menu.addAction("🗑 删除", lambda: self._remove_item(idx))
        menu.addSeparator()
        menu.addAction("清空列表", self._clear_playlist)
        menu.exec(self.playlist_widget.mapToGlobal(pos))

    def _remove_item(self, idx):
        if 0 <= idx < len(self.playlist):
            is_current = (idx == self.current_index)
            self.playlist.pop(idx)
            if is_current:
                self.media_player.stop()
                self.current_index = -1
                if self.playlist:
                    new_idx = min(idx, len(self.playlist) - 1)
                    self.play_at_index(new_idx)
            elif idx < self.current_index:
                self.current_index -= 1
            self._refresh_playlist_ui()

    def _clear_playlist(self):
        self.playlist.clear()
        self.current_index = -1
        self.media_player.stop()
        self._refresh_playlist_ui()
        self.lbl_title.setText("未播放")
        self.lbl_artist.setText("")
        self.lbl_album.setText("")

    def play_at_index(self, index):
        if 0 <= index < len(self.playlist):
            self.current_index = index
            path = self.playlist[index]
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self._update_song_info(path)
            self.media_player.play()
            self._refresh_playlist_ui()

    def _update_song_info(self, path):
        try:
            from mutagen import File
            audio = File(path)
            if audio and audio.tags:
                title = str(audio.tags.get('TIT2', [''])[0]) if hasattr(audio.tags, 'get') else ''
                artist = str(audio.tags.get('TPE1', [''])[0]) if hasattr(audio.tags, 'get') else ''
                album = str(audio.tags.get('TALB', [''])[0]) if hasattr(audio.tags, 'get') else ''
                self.lbl_title.setText(title or os.path.basename(path))
                self.lbl_artist.setText(artist)
                self.lbl_album.setText(album)
            else:
                self.lbl_title.setText(os.path.basename(path))
                self.lbl_artist.setText("")
                self.lbl_album.setText("")
        except Exception as e:
            self.lbl_title.setText(os.path.basename(path))
            self.lbl_artist.setText("")
            self.lbl_album.setText("")

    def _fmt_time(self, ms):
        if ms <= 0:
            return "00:00"
        s = ms // 1000
        m = s // 60
        s = s % 60
        h = m // 60
        m = m % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _on_position_changed(self, pos):
        dur = self.media_player.duration()
        if dur > 0:
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(int(pos / dur * 1000))
            self.progress_slider.blockSignals(False)
            self.lbl_current.setText(self._fmt_time(pos))

    def _on_duration_changed(self, dur):
        self.lbl_total.setText(self._fmt_time(dur))

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
            self.tray_icon.setToolTip(f"{APP_TITLE} - 播放中")
        else:
            self.btn_play.setText("▶")
            self.tray_icon.setToolTip(f"{APP_TITLE} - 已暂停")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next_auto()

    def _play_next_auto(self):
        if self.play_mode == 2:  # 单曲循环
            self.media_player.setPosition(0)
            self.media_player.play()
        elif self.play_mode == 1:  # 随机
            if self.playlist:
                idx = random.randint(0, len(self.playlist) - 1)
                self.play_at_index(idx)
        else:  # 顺序
            self.play_next()

    def _on_seek_start(self):
        self._was_playing = (self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        self.media_player.pause()

    def _on_seek_drag(self, value):
        dur = self.media_player.duration()
        if dur > 0:
            pos = int(value / 1000 * dur)
            self.lbl_current.setText(self._fmt_time(pos))

    def _on_seek(self):
        dur = self.media_player.duration()
        if dur > 0:
            pos = int(self.progress_slider.value() / 1000 * dur)
            self.media_player.setPosition(pos)
            if getattr(self, '_was_playing', False):
                self.media_player.play()

    def seek(self, delta_ms):
        pos = self.media_player.position() + delta_ms
        pos = max(0, min(pos, self.media_player.duration()))
        self.media_player.setPosition(pos)

    def toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            if self.media_player.source().isEmpty() and self.playlist:
                self.play_at_index(self.current_index if self.current_index >= 0 else 0)
            else:
                self.media_player.play()

    def play_prev(self):
        if self.playlist:
            if self.play_mode == 1:  # 随机
                idx = random.randint(0, len(self.playlist) - 1)
            else:
                idx = (self.current_index - 1) % len(self.playlist)
            self.play_at_index(idx)

    def play_next(self):
        if self.playlist:
            if self.play_mode == 1:  # 随机
                idx = random.randint(0, len(self.playlist) - 1)
            else:
                idx = self.current_index + 1
                if idx >= len(self.playlist):
                    idx = 0
            self.play_at_index(idx)

    def cycle_mode(self):
        self.play_mode = (self.play_mode + 1) % 3
        self._update_mode_button()

    def _update_mode_button(self):
        icons = ["🔁", "🔀", "🔂"]
        self.btn_mode.setText(icons[self.play_mode])
        self.btn_mode.setToolTip(PLAY_MODES[self.play_mode])

    def toggle_random(self):
        if self.play_mode == 1:
            self.play_mode = 0
        else:
            self.play_mode = 1
        self._update_mode_button()

    def set_volume(self, vol):
        self.volume = vol
        self.audio_output.setVolume(vol / 100)
        self.btn_mute.setText("🔊" if vol > 0 else "🔇")

    def volume_up(self):
        v = min(self.volume + 5, 100)
        self.slider_volume.setValue(v)

    def volume_down(self):
        v = max(self.volume - 5, 0)
        self.slider_volume.setValue(v)

    def toggle_mute(self):
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        self.btn_mute.setText("🔇" if muted else "🔊")

    def toggle_mini_mode(self):
        if self.is_mini_mode:
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def enter_mini_mode(self):
        self.is_mini_mode = True
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(400, 120)
        self.show()

    def exit_mini_mode(self):
        self.is_mini_mode = False
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(1100, 700)
        self.show()

    def remove_current(self):
        if 0 <= self.current_index < len(self.playlist):
            self.playlist.pop(self.current_index)
            if self.current_index >= len(self.playlist):
                self.current_index = len(self.playlist) - 1
            self._refresh_playlist_ui()
            if self.current_index >= 0:
                self.play_at_index(self.current_index)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
        if files:
            self._add_to_playlist(files)

    def closeEvent(self, event):
        self._save_config()
        self.media_player.stop()
        self.tray_icon.hide()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background-color: #0f0f1a; }
        QMenu { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #3a3a5a; }
        QMenu::item:selected { background-color: #2d4a6f; }
        QDialog { background-color: #1a1a2e; color: #e0e0e0; }
    """)

    window = MusicPlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
