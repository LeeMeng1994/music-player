# 音乐播放器

一个基于 PyQt6 的本地音乐播放器，支持多种音频格式，具备播放列表、歌词显示、迷你模式等功能。

## 功能特性

- **多格式支持**：mp3, flac, wav, aac, ogg, m4a, wma, ape, opus, mka
- **播放列表**：添加、删除、清空歌曲，支持拖拽导入
- **LRC 歌词**：同步滚动显示，支持 UTF-8/GBK 编码
- **播放模式**：顺序播放、随机播放、单曲循环
- **迷你模式**：无边框置顶小窗口，带歌词显示
- **系统托盘**：最小化到托盘，右键快捷操作
- **元数据读取**：自动读取歌曲标题、艺术家、专辑信息

## 运行方式

```bash
pip install PyQt6 mutagen
python main.py
```

## 打包

```bash
pip install pyinstaller
pyinstaller 音乐播放器.spec
```

## 技术栈

- Python 3.12
- PyQt6
- mutagen（音频元数据）
- PyInstaller

## 作者

萌哥