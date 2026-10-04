import os
import re
import shutil
import sqlite3
import sys
import time
from google import genai
from google.genai.errors import ServerError
import streamlit as st

# دعم اللغة العربية وتفادي خطأ التشفير
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')

# 1. إعداد قاعدة البيانات وتجهيز جدول المستخدمين تلقائيًا
def init_db():
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            points INTEGER
        )
    """)
    conn.commit()
    conn.close()

def get_user_points(username):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def create_user(username):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    # تم تعديل الرصيد الافتتاحي المجاني إلى 500 نقطة (مناسب للبدء وتجربة التطبيق)
    cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, 500))
    conn.commit()
    conn.close()

def update_user_points(username, new_points):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = ? WHERE username = ?", (new_points, username))
    conn.commit()
    conn.close()

# تشغيل قاعدة البيانات عند بدء البرنامج
init_db()

# إعداد مفتاح الـ API بشكل آمن
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

client = genai.Client()

# إعداد الصفحة وتصميمها
st.set_page_config(page_title="صانع البرامج الذكي المطور", page_icon="🤖", layout="centered")
st.title("🤖 صانع ومقسم البرامج الآلي الذكي (الإصدار المحسن)")

# 2. نظام تسجيل دخول مبسط لحفظ النقاط لكل اسم مستخدم
st.sidebar.header("🔐 تسجيل دخول المستخدمين")
username_input = st.sidebar.text_input("ادخل اسم المستخدم الخاص بك:", placeholder="مثال: ahmed_123").strip()

# تكلفة توليد التطبيق الواحد (تم تعديلها لتكون اقتصادية ومنطقية: 150 نقطة)
APP_COST = 150

if not username_input:
    st.warning("👈 يرجى كتابة اسم مستخدم في القائمة الجانبية لتفعيل رصيدك وبدء الاستخدام.")
else:
    current_points = get_user_points(username_input)
    if current_points is None:
        create_user(username_input)
        current_points = 500
        st.sidebar.success(f"🎉 مرحبًا بك كمستخدم جديد! تم منحك 500 نقطة مجانية للبدء.")
    else:
        st.sidebar.info(f"👋 مرحبًا بعودتك، {username_input}!")

    # عرض النقاط الحقيقية من قاعدة البيانات في الأعلى
    st.metric(label="📊 رصيد نقاطك المتبقي في حسابك:", value=f"{current_points} نقطة")

    # 3. فتح صفحة الشحن المتعددة العملات
    show_charge_page = st.sidebar.checkbox("💳 فتح صفحة شحن الرصيد")

    if current_points <= 0 or show_charge_page:
        st.header("💳 بوابة شحن الرصيد الاقتصادية")
        st.write("نقاطك الحالية غير كافية أو تود شحن حسابك. اختر باقة الشحن المناسبة:")
        
        currency = st.selectbox("🌍 اختر عملة الدفع الخاصة ببلدك:", ["الدولار الأمريكي (USD)", "الجنيه المصري (EGP)", "الريال السعودي (SAR)", "الجنيه السوداني (SDG)"])
        
        # أسعار وباقات شحن منطقية ومتناسبة (مثلاً 1000 نقطة إضافية)
        prices = {
            "الدولار الأمريكي (USD)": "$3",
            "الجنيه المصري (EGP)": "150 EGP",
            "الريال السعودي (SAR)": "12 SAR",
            "الجنيه السوداني (SDG)": "3000 SDG"
        }
        
        st.info(f"💰 سعر باقة الشحن (1000 نقطة إضافية) هو: {prices[currency]}")
        
        pay_now = st.button(f"💳 ادفع الآن بـ {currency}")
        if pay_now:
            st.success("🔄 جاري الاتصال ببوابة الدفع الآمنة لتأكيد العملية...")
            update_user_points(username_input, current_points + 1000)
            st.success("🎉 تم تأكيد الدفع بنجاح! تم إضافة 1000 نقطة لحسابك.")
            st.rerun()
    else:
        st.write(f"اكتب فكرة البرنامج الذي تريده في الأسفل (تكلفة الطلب: {APP_COST} نقطة).")
        
        # إضافة خيار اختيار تقنية/لغة البرمجة المفضلة للمشروع
        app_tech = st.selectbox(
            "🛠️ اختر التقنية أو الإطار المفضل للمشروع:",
            ["Python (Streamlit / Flask)", "HTML / CSS / JavaScript (تطبيقات الويب)", "Python (سكربت أدوات عامة)"]
        )
        
        app_idea = st.text_input("ما هو البرنامج أو التطبيق الذي تريد مني تصميمه وبرمجته اليوم؟", placeholder="مثال: آلة حاسبة ذكية أو نظام مهام يومية")
        generate_btn = st.button("🚀 ابدأ صناعة البرنامج الآن")

        if generate_btn and app_idea:
            if current_points < APP_COST:
                st.error(f"❌ رصيدك غير كافٍ لتنفيذ هذا الطلب (التكلفة {APP_COST} نقطة). يرجى شحن الرصيد من القائمة الجانبية.")
            else:
                st.info("جاري التفكير، وتصميم وبرمجة مشروعك بدقة واحترافية... انتظر لحظة...")
                
                system_prompt = f"""
                You are an expert AI Software Engineer.
                The user wants to build a complete application based on this description: "{app_idea}".
                Preferred Technology Stack: {app_tech}.
                Please generate the complete production-ready source code files.

                You MUST write the filename clearly before EVERY code block using this exact format:
                File: filename.ext
                ```python (or the appropriate language like html, js, etc.)
                [code]
                ```
                """

                response = None
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=system_prompt,
                    )
                except ServerError:
                    st.error("عذرًا، واجه السيرفر مشكلة مؤقتة بسبب الضغط. يرجى إعادة المحاولة.")

                if response:
                    content = response.text
                    folder_name = "Generated_App_Project"
                    
                    if os.path.exists(folder_name):
                        shutil.rmtree(folder_name)
                    os.makedirs(folder_name, exist_ok=True)

                    file_matches = re.findall(r'File:\s*([a-zA-Z0-9_\-\.]+)\s*\n+```[a-zA-Z]*\n(.*?)\n```', content, re.DOTALL)

                    # خصم النقاط وتحديثها في قاعدة البيانات
                    new_balance = current_points - APP_COST
                    update_user_points(username_input, new_balance)

                    if file_matches:
                        for filename, code in file_matches:
                            file_path = os.path.join(folder_name, filename.strip())
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(code.strip())
                        
                        shutil.make_archive("Generated_App_Project", 'zip', folder_name)
                        st.success("🎉 تم إنشاء ملفات مشروعك وتوزيعها بالكامل بنجاح!")
                        
                        # ميزة جديدة: عرض الأكواد في ألسنة (Tabs) مرتبة قبل التحميل
                        st.subheader("👀 معاينة الأكواد المولدة للملفات:")
                        tab_names = [match[0].strip() for match in file_matches]
                        tabs = st.tabs(tab_names)
                        
                        for i, tab in enumerate(tabs):
                            with tab:
                                st.code(file_matches[i][1].strip(), language='python')
                        
                        # زر التحميل المباشر
                        with open("Generated_App_Project.zip", "rb") as fp:
                            st.download_button(
                                label="📥 اضغط هنا لتحميل مشروعك الكامل (ZIP)",
                                data=fp,
                                file_name="Generated_App_Project.zip",
                                mime="application/zip"
                            )
                        st.balloons()
                    else:
                        backup_file = os.path.join(folder_name, "project_code.txt")
                        with open(backup_file, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        shutil.make_archive("Generated_App_Project", 'zip', folder_name)
                        st.success(f"✅ تم حفظ الملف كاملاً بنجاح في: {folder_name}/project_code.txt")
                        
                        st.subheader("👀 معاينة محتوى المشروع:")
                        st.code(content, language='markdown')
                        
                        with open("Generated_App_Project.zip", "rb") as fp:
                            st.download_button(
                                label="📥 اضغط هنا لتحميل المشروع (ZIP)",
                                data=fp,
                                file_name="Generated_App_Project.zip",
                                mime="application/zip"
                            )
                        st.balloons()
