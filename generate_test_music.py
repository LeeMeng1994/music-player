"""生成测试音乐文件"""
import os
import struct
import wave
import math

OUTPUT_DIR = "test_music"

def generate_wav(filename, duration=5, freq=440, sample_rate=44100):
    """生成 WAV 测试音频"""
    num_samples = int(duration * sample_rate)
    
    with wave.open(os.path.join(OUTPUT_DIR, filename), 'w') as wav:
        wav.setnchannels(2)  # 立体声
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        
        for i in range(num_samples):
            # 左声道
            t = i / sample_rate
            value_left = int(32767 * 0.5 * math.sin(2 * math.pi * freq * t))
            # 右声道（不同频率）
            value_right = int(32767 * 0.5 * math.sin(2 * math.pi * (freq * 1.5) * t))
            
            # 添加淡入淡出
            fade_duration = 0.1
            if t < fade_duration:
                fade = t / fade_duration
            elif t > duration - fade_duration:
                fade = (duration - t) / fade_duration
            else:
                fade = 1.0
            
            value_left = int(value_left * fade)
            value_right = int(value_right * fade)
            
            wav.writeframes(struct.pack('<hh', value_left, value_right))

def generate_mp3(filename, duration=5):
    """生成 MP3 测试音频（通过 pydub）"""
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
        
        # 生成正弦波
        sine = Sine(440)
        audio = sine.to_audio_segment(duration=duration * 1000)
        
        # 添加淡入淡出
        audio = audio.fade_in(100).fade_out(100)
        
        # 导出为 MP3
        audio.export(os.path.join(OUTPUT_DIR, filename), format="mp3", tags={
            'title': '测试音乐 - 440Hz',
            'artist': '测试生成器',
            'album': '测试专辑'
        })
        print(f"已生成: {filename}")
    except Exception as e:
        print(f"生成 {filename} 失败: {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("正在生成测试音乐文件...")
    
    # 生成不同频率的 WAV 文件
    frequencies = [
        ("测试音乐_低音.wav", 220, "低音测试 220Hz"),
        ("测试音乐_中音.wav", 440, "中音测试 440Hz"),
        ("测试音乐_高音.wav", 880, "高音测试 880Hz"),
    ]
    
    for filename, freq, desc in frequencies:
        print(f"生成 {desc}...")
        generate_wav(filename, duration=5, freq=freq)
        print(f"  [OK] {filename}")
    
    # 生成长一点的音乐
    print("生成 30 秒测试音乐...")
    generate_wav("测试音乐_长音频.wav", duration=30, freq=523)
    print("  [OK] 测试音乐_长音频.wav")
    
    # 生成 MP3（如果 pydub 可用）
    print("生成 MP3 格式...")
    generate_mp3("测试音乐_立体声.mp3", duration=5)
    
    print("\n测试音乐生成完成！")
    print(f"位置: {os.path.abspath(OUTPUT_DIR)}")
    print("\n文件列表:")
    for f in os.listdir(OUTPUT_DIR):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"  {f} ({size/1024:.1f} KB)")

if __name__ == "__main__":
    main()
