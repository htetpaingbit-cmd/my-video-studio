import streamlit as st
import yt_dlp
import subprocess
import os
import re
import tempfile
import time

st.set_page_config(page_title="All-in-One Video Studio", page_icon="🎬", layout="centered")

# Cloud ပေါ်မှာဆိုရင် 'ffmpeg' ကိုပဲ တိုက်ရိုက်သုံးမယ်
def get_ffmpeg_path():
    if os.path.exists('ffmpeg.exe'):
        return 'ffmpeg.exe'
    return 'ffmpeg'

# ... (အောက်က ကုဒ်အပိုင်းများကို ယခင်အတိုင်း ထားထားပါ) ...
    try:
        # Cloud ပေါ်တွင် imageio_ffmpeg မှတစ်ဆင့် FFmpeg လမ်းကြောင်းကို ယူမည်
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'

def get_video_duration(input_file):
    try:
        cmd = [get_ffmpeg_path(), '-i', input_file]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, errors='ignore')
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if match:
            hours, minutes, seconds = map(float, match.groups())
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        pass
    return None

# Website ခေါင်းစဉ်
st.title("🎬 Pro Video Studio (Web)")
st.markdown("Video များကို သေးအောင်ချုံ့မည်၊ Websites အားလုံးမှ Video များကို ဒေါင်းလုဒ်ဆွဲမည်။")

# Tabs ၂ ခု ခွဲခြင်း
tab1, tab2 = st.tabs(["🎥 Video Compressor", "⬇️ Video Downloader"])

# ==========================================
# TAB 1: COMPRESSOR
# ==========================================
with tab1:
    st.header("Video Compressor")
    uploaded_file = st.file_uploader("ချုံ့လိုသော Video ဖိုင်ကို ရွေးချယ်ပါ (Drag & Drop လုပ်နိုင်သည်)", type=['mp4', 'mkv', 'mov', 'avi'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # Key သတ်မှတ်ထားသည်
        target_mb = st.number_input("Target Size (MB)", min_value=1, value=50, key="comp_size")
    with col2:
        resolution = st.selectbox("Resolution", ["Original", "1080p", "720p", "640p", "540p", "480p", "360p"], key="comp_res")
    with col3:
        out_format = st.selectbox("Format", ["mp4", "mp3"], key="comp_format")

    if uploaded_file is not None:
        if st.button("🚀 Compress စတင်မည်", use_container_width=True, key="comp_btn"):
            # Temp ဖိုင်များ ဖန်တီးခြင်း
            temp_dir = tempfile.mkdtemp()
            input_path = os.path.join(temp_dir, uploaded_file.name)
            output_name = f"Compressed_{target_mb}MB.{out_format}"
            output_path = os.path.join(temp_dir, output_name)

            # Upload လုပ်ထားသော ဖိုင်ကို သိမ်းဆည်းခြင်း
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            duration = get_video_duration(input_path)
            
            if duration:
                ffmpeg_cmd = get_ffmpeg_path()

                if out_format == "mp3":
                    audio_bitrate = max(32, min(320, (target_mb * 8192) / duration))
                    command = [ffmpeg_cmd, '-y', '-i', input_path, '-vn', '-c:a', 'libmp3lame', '-b:a', f'{int(audio_bitrate)}k', output_path]
                else:
                    total_bitrate = (target_mb * 8192) / duration
                    video_bitrate = max(50, total_bitrate - 96)
                    
                    scale_filter = ['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2']
                    if resolution != "Original":
                        scale_filter = ['-vf', f'scale=-2:{resolution.replace("p","")}']

                    command = [
                        ffmpeg_cmd, '-y', '-i', input_path, '-c:v', 'libx265', '-pix_fmt', 'yuv420p',
                        '-b:v', f'{int(video_bitrate)}k', '-maxrate', f'{int(video_bitrate * 1.5)}k', 
                        '-bufsize', f'{int(video_bitrate * 2)}k', '-preset', 'fast', '-c:a', 'aac', '-b:a', '96k'
                    ] + scale_filter + [output_path]

                # Progress ပြသရန် နေရာများ
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                status_text.info("ပြင်ဆင်နေပါသည်...")

                # FFmpeg Run ခြင်း (Progress သိနိုင်ရန် Popen သုံးခြင်း)
                try:
                    process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, errors='ignore')
                    start_time = time.time()
                    
                    for line in process.stderr:
                        match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                        if match and duration > 0:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = current_sec / duration
                            if percent > 1.0: percent = 1.0
                            
                            elapsed_real = time.time() - start_time
                            if current_sec > 0:
                                est_total = (elapsed_real / current_sec) * duration
                                eta_sec = max(0, est_total - elapsed_real)
                                eta_str = f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
                            else:
                                eta_str = "..."
                            
                            progress_bar.progress(percent)
                            status_text.info(f"လုပ်ဆောင်နေပါသည်... {percent*100:.1f}% (ပြီးဆုံးရန်: {eta_str})")

                    process.wait()
                    
                    if process.returncode == 0 and os.path.exists(output_path):
                        progress_bar.progress(1.0)
                        status_text.success(f"🎉 အောင်မြင်စွာ လုပ်ဆောင်ပြီးပါပြီ! ({os.path.getsize(output_path) / (1024*1024):.1f} MB)")
                        with open(output_path, "rb") as file:
                            st.download_button(
                                label="📥 Download ရယူရန် နှိပ်ပါ",
                                data=file,
                                file_name=output_name,
                                mime="video/mp4" if out_format == "mp4" else "audio/mpeg",
                                use_container_width=True,
                                key="comp_download"
                            )
                    else:
                        status_text.error("ဖိုင် ထွက်မလာပါ။ အမှားအယွင်းရှိနိုင်ပါသည်။")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("ဗီဒီယို ကြာချိန်ကို ဖတ်၍မရပါ။")


# ==========================================
# TAB 2: DOWNLOADER
# ==========================================
with tab2:
    st.header("Video Downloader")
    st.info("Websites အားလုံးမှ Link များကို ထည့်နိုင်သည်။ 18+ နှင့် Login လိုအပ်သော ဖိုင်များအတွက် Cookie ရွေးပေးပါ။")
    
    url = st.text_input("Video Link (URL) ကို ဒီမှာထည့်ပါ:", key="dl_url")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # Key သတ်မှတ်ထားသည်
        dl_format = st.selectbox("Format", ["mp4", "mp3"], key="dl_format")
    with col2:
        dl_resolution = st.selectbox("Resolution", ["အကောင်းဆုံး (Best)", "1080p", "720p", "480p", "360p"], key="dl_res")
    with col3:
        browser_choice = st.selectbox("Browser Cookie", ["မသုံးပါ (Default)", "Chrome", "Edge", "Firefox", "Brave", "Opera"], key="dl_cookie")

    if st.button("⬇️ Download ဆွဲမည်", use_container_width=True, key="dl_btn"):
        if url:
            # Progress ပြသရန် နေရာများ
            dl_progress_bar = st.progress(0.0)
            dl_status_text = st.empty()
            dl_status_text.info("အချက်အလက်များ ရှာဖွေနေပါသည်...")

            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%')).strip()
                    speed_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', '...')).strip()
                    eta_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_eta_str', '...')).strip()
                    
                    try:
                        val = float(percent_str.replace('%', '')) / 100.0
                        if val > 1.0: val = 1.0
                    except:
                        val = 0.0
                        
                    dl_progress_bar.progress(val)
                    dl_status_text.info(f"ဒေါင်းလုဒ်: {percent_str} | Speed: {speed_str} | ပြီးဆုံးရန်: {eta_str}")
                    
                elif d['status'] == 'finished':
                    dl_progress_bar.progress(1.0)
                    dl_status_text.warning("ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ... ဖိုင်များကို ပေါင်းစပ်နေပါသည်!")
temp_dir = tempfile.mkdtemp()
            output_template = os.path.join(temp_dir, 'video_output.%(ext)s')

            ydl_opts = {
                'outtmpl': output_template,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'nocheckcertificate': True,
                'geo_bypass': True,
            }

            if browser_choice != "မသုံးပါ (Default)":
                ydl_opts['cookiesfrombrowser'] = (browser_choice.lower(), )

            if dl_format == "mp3":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                final_ext = "mp3"
            else:
                if dl_resolution == "အကောင်းဆုံး (Best)":
                    ydl_opts['format'] = 'best[ext=mp4]/best'
                else:
                    height = dl_resolution.replace("p", "")
                    ydl_opts['format'] = f'best[height<={height}][ext=mp4]/best'
                final_ext = "mp4"
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'Downloaded_Video')
                    
                    downloaded_file = os.path.join(temp_dir, f"video_output.{final_ext}")
                    
                    if os.path.exists(downloaded_file):
                        dl_status_text.success("🎉 အောင်မြင်စွာ ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ!")
                        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                        
                        with open(downloaded_file, "rb") as file:
                            st.download_button(
                                label="📥 ဖိုင်ကို Download လုပ်ရန် နှိပ်ပါ",
                                data=file,
                                file_name=f"{safe_title}.{final_ext}",
                                mime="video/mp4" if dl_format == "mp4" else "audio/mpeg",
                                use_container_width=True,
                                key="dl_download"
                            )
                    else:
                        dl_status_text.error("ဖိုင်ကို ရှာမတွေ့ပါ။")
            except Exception as e:
                error_msg = str(e)
                if "Sign in" in error_msg or "age-restricted" in error_msg:
                    dl_status_text.error("❌ ဒေါင်းရန်ခွင့်ပြုချက် မရှိပါ။ Browser Cookie ကို ရွေးချယ်ပြီး ပြန်စမ်းကြည့်ပါ။")
                else:
                    dl_status_text.error(f"ဒေါင်းလုဒ်ဆွဲရာတွင် အမှားဖြစ်ပါသည်: {error_msg[:100]}...")
        else:
            st.warning("ကျေးဇူးပြု၍ Link အရင်ထည့်ပါ။")
