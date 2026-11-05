import requests

# Địa chỉ server cục bộ của bạn
url = "http://127.0.0.1:8000/lesson/get-audio"

# Giả lập tham số gửi lên giống như ESP32 gọi:
# hour=8 (Buổi sáng -> Cấp độ A2), user_action=normal
params = {
    "hour": 8,
    "user_action": "normal"
}

print("⏳ Đang gửi request tới Server FastAPI...")
response = requests.get(url, params=params)

if response.status_code == 200:
    print("✅ Gọi API thành công!")
    print(f"📊 Cấp độ CEFR nhận được từ Header: {response.headers.get('X-CEFR-Level')}")
    print(f"⚡ Tốc độ phát đề xuất (Speed): {response.headers.get('X-Playback-Speed')}")
    print(f"📚 Chủ đề bài học: {response.headers.get('X-Lesson-Topic')}")

    # Lưu thử file MP3 trả về để nghe thử trên máy tính
    output_file = "server_lesson_output.mp3"
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"🎧 Đã lưu file audio phản hồi từ server tại: {output_file}")
else:
    print(f"❌ Lỗi từ server: {response.status_code} - {response.text}")