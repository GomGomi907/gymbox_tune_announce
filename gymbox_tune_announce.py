import sys
import os
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPushButton,
    QSlider, QLabel, QGroupBox, QFileDialog, QLineEdit, QTimeEdit, QMenuBar, QAction, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QTime, QSettings
from PyQt5.QtGui import QFont
import pygame

class Broadcast:
    def __init__(self, name):
        self.name = name
        self.file = None
        self.title = ""
        self.volume = 0.5
        self.schedules = []  # ["HH:MM", ...]

class MainWindow(QMainWindow):  # QWidget → QMainWindow!
    """GymBox TuneAnnounce 메인 윈도우"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymBox TuneAnnounce")
        self.resize(900, 600)
        pygame.mixer.init()
        self.music_files = []
        self.music_index = 0
        self.music_playing = False
        self.music_paused = False
        self.music_volume = 0.5
        self.broadcasts = [Broadcast("Announcement 1"), Broadcast("Announcement 2")]
        self.settings = QSettings("GymBox", "GymBoxTuneAnnounce")

        self.setup_menu()          # ★ 메뉴바 생성 및 적용
        self.setup_ui()
        self.setup_timer()
        self.load_settings()

    # ----- 메뉴바 -----
    def setup_menu(self):
        menubar = QMenuBar(self)
        # 옵션 메뉴
        option_menu = menubar.addMenu('옵션')
        action_save = QAction('설정 저장', self)
        action_save.triggered.connect(self.save_settings)
        option_menu.addAction(action_save)
        # 종료
        action_exit = QAction('종료', self)
        action_exit.triggered.connect(self.close)
        option_menu.addAction(action_exit)
        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말')
        action_about = QAction('프로그램 정보', self)
        action_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(action_about)
        # 네이티브 메뉴로 적용
        self.setMenuBar(menubar)

    def show_about_dialog(self):
        """프로그램 정보 대화상자 표시"""
        msg = QMessageBox(self)
        msg.setWindowTitle("프로그램 정보")
        msg.setText(
            "GymBox TuneAnnounce v1.0\n\n"
            "Made by LGS.\n\n"
            "음악/안내방송 자동 스케줄러\n\n"
            "tkdrmsdl90715@gmail.com"
        )
        msg.setFixedSize(600, 400)
        msg.resize(1000, 500)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # ----- UI 설정 (centralWidget으로!) -----
    def setup_ui(self):
        main_layout = QHBoxLayout()

        # 좌측: 음악 리스트
        left_layout = QVBoxLayout()
        self.music_list = QListWidget()
        btn_add_music = QPushButton("음악 추가")
        btn_del_music = QPushButton("선택 삭제")
        self.music_volume_slider = QSlider(Qt.Horizontal)
        self.music_volume_slider.setMaximum(100)
        self.music_volume_slider.setValue(int(self.music_volume*100))
        self.music_volume_slider.valueChanged.connect(self.set_music_volume)
        btn_add_music.clicked.connect(self.add_music)
        btn_del_music.clicked.connect(self.del_music)
        left_layout.addWidget(QLabel("음악 파일 목록"))
        left_layout.addWidget(self.music_list)
        left_layout.addWidget(btn_add_music)
        left_layout.addWidget(btn_del_music)
        left_layout.addWidget(QLabel("음악 볼륨"))
        left_layout.addWidget(self.music_volume_slider)

        # 좌측 하단 버튼/상태
        self.btn_start = QPushButton("재생")
        self.btn_stop = QPushButton("정지")
        self.lbl_status = QLabel("상태: 대기")
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_start)
        bottom_layout.addWidget(self.btn_stop)
        bottom_layout.addWidget(self.lbl_status)
        bottom_layout.addStretch(1)
        self.btn_start.clicked.connect(self.start_music)
        self.btn_stop.clicked.connect(self.stop_music)
        left_layout.addLayout(bottom_layout)

        # 우측: 안내방송들 (상단 시계)
        right_layout = QVBoxLayout()
        self.main_time = QLabel("--:--:--")
        self.main_time.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.main_time.setFont(QFont('Arial', 28, QFont.Bold))
        right_layout.addWidget(self.main_time)
        self.broadcast_widgets = []
        for i, bc in enumerate(self.broadcasts):
            group = QGroupBox(f"안내방송 {i+1}")
            v = QVBoxLayout()
            title_edit = QLineEdit()
            title_edit.setPlaceholderText("제목 입력")
            file_btn = QPushButton("파일 선택")
            file_label = QLabel("선택된 파일: 없음")
            vol_slider = QSlider(Qt.Horizontal)
            vol_slider.setMaximum(100)
            vol_slider.setValue(int(bc.volume*100))
            sched_list = QListWidget()
            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            add_btn = QPushButton("시간 추가")
            del_btn = QPushButton("선택 삭제")
            # 신호 연결
            file_btn.clicked.connect(lambda _, idx=i: self.select_broadcast_file(idx))
            vol_slider.valueChanged.connect(lambda val, idx=i: self.set_broadcast_volume(idx, val))
            add_btn.clicked.connect(lambda _, idx=i: self.add_schedule(idx))
            del_btn.clicked.connect(lambda _, idx=i: self.del_schedule(idx))
            v.addWidget(QLabel("제목"))
            v.addWidget(title_edit)
            v.addWidget(file_btn)
            v.addWidget(file_label)
            v.addWidget(QLabel("볼륨"))
            v.addWidget(vol_slider)
            v.addWidget(QLabel("스케줄"))
            v.addWidget(sched_list)
            hl = QHBoxLayout()
            hl.addWidget(time_edit)
            hl.addWidget(add_btn)
            hl.addWidget(del_btn)
            v.addLayout(hl)
            group.setLayout(v)
            right_layout.addWidget(group)
            # 저장
            self.broadcast_widgets.append({
                "title_edit": title_edit, "file_btn": file_btn, "file_label": file_label,
                "vol_slider": vol_slider, "sched_list": sched_list, "time_edit": time_edit
            })

        # 전체 배치
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        central_widget = QWidget()
        vbox_main = QVBoxLayout(central_widget)
        vbox_main.addLayout(main_layout)
        central_widget.setLayout(vbox_main)
        self.setCentralWidget(central_widget)  # 중앙 위젯 등록

    # ========== 음악 ==========
    def add_music(self):
        files, _ = QFileDialog.getOpenFileNames(self, "음악 파일 추가", "", "음악 파일 (*.mp3 *.wav)")
        for f in files:
            self.music_files.append(f)
            self.music_list.addItem(f)
    def del_music(self):
        idxs = self.music_list.selectedIndexes()
        for idx in reversed(idxs):
            del self.music_files[idx.row()]
            self.music_list.takeItem(idx.row())
    def set_music_volume(self, val):
        self.music_volume = val/100
        pygame.mixer.music.set_volume(self.music_volume)
    def start_music(self):
        if not self.music_files: return
        self.music_index = 0
        self.music_playing = True
        self.music_paused = False
        self.play_next_music()
    def play_next_music(self):
        if not self.music_playing: return
        if self.music_index >= len(self.music_files):
            self.music_index = 0  # 반복재생
        f = self.music_files[self.music_index]
        pygame.mixer.music.load(f)
        pygame.mixer.music.set_volume(self.music_volume)
        pygame.mixer.music.play()
        threading.Thread(target=self.wait_music_end, daemon=True).start()
    def wait_music_end(self):
        while pygame.mixer.music.get_busy():
            time.sleep(0.2)
            if not self.music_playing or self.music_paused:
                return
        self.music_index += 1
        self.play_next_music()
    def stop_music(self):
        self.music_playing = False
        pygame.mixer.music.stop()

    # ========== 안내방송 ==========
    def select_broadcast_file(self, idx):
        fname, _ = QFileDialog.getOpenFileName(self, "방송 파일 선택", "", "음악 파일 (*.mp3 *.wav)")
        if fname:
            self.broadcasts[idx].file = fname
            self.broadcast_widgets[idx]["file_label"].setText(f"선택된 파일: {os.path.basename(fname)}")
    def set_broadcast_volume(self, idx, val):
        self.broadcasts[idx].volume = val / 100
    def add_schedule(self, idx):
        time_edit = self.broadcast_widgets[idx]["time_edit"]
        t = time_edit.time().toString("HH:mm")
        if t not in self.broadcasts[idx].schedules:
            self.broadcasts[idx].schedules.append(t)
            self.broadcast_widgets[idx]["sched_list"].addItem(t)
    def del_schedule(self, idx):
        sel = self.broadcast_widgets[idx]["sched_list"].selectedItems()
        for item in sel:
            self.broadcasts[idx].schedules.remove(item.text())
            self.broadcast_widgets[idx]["sched_list"].takeItem(self.broadcast_widgets[idx]["sched_list"].row(item))

    # ========== 스케줄 & 타이머 ==========
    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_time)
        self.timer.start(1000)
        self.check_time()  # 시작시 즉시 시계 표시
    def check_time(self):
        now = QTime.currentTime()
        now_str = now.toString("HH:mm:ss")
        self.main_time.setText(now_str)
        # 안내방송 스케줄 체크
        for idx, bc in enumerate(self.broadcasts):
            if bc.file and now.toString("HH:mm") in bc.schedules:
                self.do_broadcast(idx)
                break
    def do_broadcast(self, idx):
        if not self.music_playing:
            return
        self.lbl_status.setText(f"상태: 안내방송{idx+1} 재생")
        self.music_paused = True
        pygame.mixer.music.pause()
        bc = self.broadcasts[idx]
        sound = pygame.mixer.Sound(bc.file)
        sound.set_volume(bc.volume)
        def _play():
            sound.play()
            while pygame.mixer.get_busy():
                time.sleep(0.1)
            self.music_paused = False
            pygame.mixer.music.unpause()
            self.lbl_status.setText("상태: 음악 재생중")
        threading.Thread(target=_play, daemon=True).start()

    # ========== 설정 저장 & 불러오기 ==========
    def save_settings(self):
        self.settings.setValue("music_files", self.music_files)
        self.settings.setValue("music_volume", self.music_volume_slider.value())
        for i, bc in enumerate(self.broadcasts):
            prefix = f"broadcast_{i}"
            self.settings.setValue(f"{prefix}_file", bc.file)
            self.settings.setValue(f"{prefix}_volume", bc.volume)
            self.settings.setValue(f"{prefix}_schedules", bc.schedules)
    def load_settings(self):
        music_files = self.settings.value("music_files", [])
        if music_files:
            self.music_files = music_files
            self.music_list.clear()
            for f in self.music_files:
                self.music_list.addItem(f)
        mv = self.settings.value("music_volume", None)
        if mv is not None:
            self.music_volume_slider.setValue(int(mv))
        for i, bc in enumerate(self.broadcasts):
            prefix = f"broadcast_{i}"
            file = self.settings.value(f"{prefix}_file", None)
            if file:
                bc.file = file
                self.broadcast_widgets[i]["file_label"].setText(f"선택된 파일: {os.path.basename(file)}")
            vol = self.settings.value(f"{prefix}_volume", None)
            if vol is not None:
                bc.volume = float(vol)
                self.broadcast_widgets[i]["vol_slider"].setValue(int(float(vol)*100))
            schedules = self.settings.value(f"{prefix}_schedules", [])
            if schedules:
                if isinstance(schedules, str):
                    schedules = [schedules]
                bc.schedules = schedules
                sched_list = self.broadcast_widgets[i]["sched_list"]
                sched_list.clear()
                for t in bc.schedules:
                    sched_list.addItem(t)

    # 윈도우 종료 시 설정 저장
    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
