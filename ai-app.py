import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.parse
from google import genai
from google.genai.errors import ServerError, APIError
import streamlit as st
import stripe  # مكتبة الدفع Stripe

# ضع مفتاحك التجريبي السري هنا (مثال: sk_test_...)
stripe.api_key = ""

# دعم اللغة العربية وتفادي خطأ التشفير
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')

# إعداد الصفحة وتصميمها
st.set_page_config(page_title="صانع البرامج الذكي العالمي", page_icon="🤖", layout="centered")

# قاموس لغات العالم لترجمة واجهة المستخدم
UI_TEXTS = {
    "العربية (Arabic)": {
        "title": "🤖 صانع ومقسم البرامج الآلي الذكي (بكل لغات العالم)",
        "sidebar_login": "🔐 تسجيل الدخول أو إنشاء حساب",
        "email_prompt": "البريد الإلكتروني:",
        "username_prompt": "اسم المستخدم:",
        "password_prompt": "كلمة المرور:",
        "missing_fields": "👈 يرجى إدخال البريد الإلكتروني، اسم المستخدم، وكلمة المرور كاملة في القائمة الجانبية.",
        "new_user": "🎉 مرحبًا بك كمستخدم جديد! تم إنشاء حسابك ومنحك 500 نقطة مجانية للبدء.",
        "welcome_back": "👋 مرحبًا بعودتك،",
        "points_label": "📊 رصيد نقاطك المتبقي في حسابك:",
        "history_header": "📜 سجل تطبيقاتك السابقة",
        "no_history": "لا توجد طلبات سابقة حتى الآن.",
        "charge_page_toggle": "💳 فتح صفحة شحن الرصيد",
        "charge_title": "💳 بوابة شحن الرصيد الاقتصادية",
        "charge_desc": "نقاطك الحالية غير كافية أو تود شحن حسابك. اختر باقة الشحن المناسبة:",
        "currency_prompt": "🌍 اختر عملة الدفع الخاصة ببلدك:",
        "pay_button": "💳 ادفع الآن بـ",
        "pay_success_msg": "🔄 جاري تحويلك إلى صفحة الدفع الآمنة (Stripe)...",
        "idea_prompt": "اكتب فكرة البرنامج الذي تريده في الأسفل (تكلفة الطلب:",
        "points_cost_suffix": "نقطة).",
        "tech_prompt": "🛠️ اختر لغة البرمجة أو التقنية المطلوبة:",
        "idea_input": "ما هو البرنامج أو التطبيق الذي تريد مني تصميمه وبرمجته اليوم؟",
        "idea_placeholder": "مثال: نظام إدارة مهام يومية بلغة C# أو Python",
        "generate_btn": "🚀 ابدأ صناعة البرنامج الآن",
        "insufficient_funds": "❌ رصيدك غير كافٍ لتنفيذ هذا الطلب (التكلفة",
        "generating_info": "جاري التفكير، وتصميم وبرمجة مشروعك باللغة المطلوبة بدقة واحترافية... انتظر لحظة...",
        "error_msg": "عذرًا، واجه السيرفر ضغطًا عاليًا أو مشكلة مؤقتة. يرجى المحاولة مرة أخرى بعد قليل. التفاصيل:",
        "success_files": "🎉 تم إنشاء ملفات مشروعك وتوزيعها بالكامل بنجاح!",
        "preview_header": "👀 معاينة الأكواد المولدة للملفات:",
        "download_zip": "📥 اضغط هنا لتحميل مشروعك الكامل (ZIP)",
        "backup_success": "✅ تم حفظ الملف كاملاً بنجاح في:",
        "preview_backup": "👀 معاينة محتوى المشروع:"
    },
    "English": {
        "title": "🤖 Smart Automated Software Creator & Divider",
        "sidebar_login": "🔐 Login or Register",
        "email_prompt": "Email Address:",
        "username_prompt": "Username:",
        "password_prompt": "Password:",
        "missing_fields": "👈 Please enter your email, username, and password in the sidebar.",
        "new_user": "🎉 Welcome! Your account has been created with 500 free points to get started.",
        "welcome_back": "👋 Welcome back,",
        "points_label": "📊 Remaining balance in your account:",
        "history_header": "📜 Previous Apps History",
        "no_history": "No previous requests yet.",
        "charge_page_toggle": "💳 Open Top-up Page",
        "charge_title": "💳 Economy Balance Recharge Portal",
        "charge_desc": "Your current points are insufficient or you wish to top up. Choose a recharge package:",
        "currency_prompt": "🌍 Choose your local payment currency:",
        "pay_button": "💳 Pay Now with",
        "pay_success_msg": "🔄 Redirecting to secure payment gateway (Stripe)...",
        "idea_prompt": "Write the idea of the app you want below (Request cost:",
        "points_cost_suffix": "points).",
        "tech_prompt": "🛠️ Choose the required programming language or technology:",
        "idea_input": "What software or app would you like me to design and code today?",
        "idea_placeholder": "e.g., A daily task management system in C# or Python",
        "generate_btn": "🚀 Start Building App Now",
        "insufficient_funds": "❌ Your balance is insufficient for this request (Cost",
        "generating_info": "Thinking, designing, and coding your project precisely... Please wait a moment...",
        "error_msg": "Sorry, the server experienced high traffic or a temporary issue. Please try again later. Details:",
        "success_files": "🎉 Your project files have been successfully generated and structured!",
        "preview_header": "👀 Generated Files Code Preview:",
        "download_zip": "📥 Click here to download your complete project (ZIP)",
        "backup_success": "✅ File successfully saved at:",
        "preview_backup": "👀 Project Content Preview:"
    }
}

WORLD_LANGUAGES = [
    "العربية (Arabic)",
    "English",
    "Español (Spanish)",
    "Français (French)",
    "Deutsch (German)",
    "中文 (Chinese)",
    "日本語 (Japanese)",
    "Русский (Russian)",
    "हिन्दी (Hindi)",
    "Português (Portuguese)"
]

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 لغة واجهة التطبيق / Interface Language")
selected_ui_lang = st.sidebar.selectbox("اختر لغة العرض:", WORLD_LANGUAGES, index=0)
texts = UI_TEXTS.get(selected_ui_lang, UI_TEXTS["العربية (Arabic)"])

st.title(texts["title"])

# 1. إعداد وتحديث قاعدة البيانات آلياً (بدون الحاجة لحذف الملف القديم)
def init_db():
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            password TEXT,
            points INTEGER
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            app_idea TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user_data(username):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, points FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def create_user(username, email, password):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (username, email, password, points) VALUES (?, ?, ?, COALESCE((SELECT points FROM users WHERE username = ?), 500))", (username, email, password, username))
    conn.commit()
    conn.close()

def update_user_points(username, new_points):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = ? WHERE username = ?", (new_points, username))
    conn.commit()
    conn.close()

def save_user_history(username, app_idea):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (username, app_idea) VALUES (?, ?)", (username, app_idea))
    conn.commit()
    conn.close()

def get_user_history(username):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT app_idea, timestamp FROM history WHERE username = ? ORDER BY id DESC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows

init_db()

# التحقق من العودة من الدفع الناجح عبر بارامترات الرابط
query_params = st.query_params
if "payment" in query_params and query_params["payment"] == "success":
    success_user = query_params.get("user", "")
    if success_user:
        conn = sqlite3.connect("users_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE username = ?", (success_user,))
        row = cursor.fetchone()
        if row:
            current_pts = row[0]
            new_pts = current_pts + 1000
            cursor.execute("UPDATE users SET points = ? WHERE username = ?", (new_pts, success_user))
            conn.commit()
        conn.close()
    st.success("🎉 تم تأكيد الدفع بنجاح عبر Stripe وتم إضافة 1000 نقطة إلى حسابك!")
    st.query_params.clear()

# ضع مفتاح الـ API الصحيح هنا (الذي يبدأ بـ AIzaSy...)
client = genai.Client(api_key="مفتاحك_هنا")

# دالة الانتظار وإعادة المحاولة التلقائية عند ضغط السيرفر
def generate_content_with_retry(prompt_text, max_retries=10, initial_delay=5):
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text,
            )
            return response
        except (ServerError, APIError, Exception) as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "overloaded" in error_str.lower() or "UNAUTHENTICATED" in error_str:
                if attempt < max_retries:
                    st.warning(f"⏳ السيرفر مضغوط أو قيد الانتظار (محاولة {attempt}/{max_retries}). جاري الانتظار لمدة {delay} ثانية وإعادة المحاولة تلقائياً...")
                    time.sleep(delay)
                    delay *= 1.5  # مضاعفة وقت الانتظار تدريجياً لضمان النجاح
                    continue
            if attempt < max_retries:
                time.sleep(delay)
            else:
                raise e

# 2. القائمة الجانبية لتسجيل الدخول
st.sidebar.header(texts["sidebar_login"])
email_input = st.sidebar.text_input(texts["email_prompt"], placeholder="example@domain.com").strip()
username_input = st.sidebar.text_input(texts["username_prompt"], placeholder="مثال: ahmed_123").strip()
password_input = st.sidebar.text_input(texts["password_prompt"], type="password", placeholder="******").strip()

APP_COST = 150

if not username_input or not password_input or not email_input:
    st.warning(texts["missing_fields"])
else:
    user_row = get_user_data(username_input)
    if user_row is None or user_row[1] is None:
        create_user(username_input, email_input, password_input)
        current_points = 500
        st.sidebar.success(texts["new_user"])
    else:
        db_email, db_password, current_points = user_row
        if db_password and db_password != password_input:
            st.sidebar.error("❌ كلمة المرور غير صحيحة لهذا المستخدم!")
            st.stop()
        else:
            create_user(username_input, email_input, password_input)
            st.sidebar.info(f"{texts['welcome_back']} {username_input}!")

    if current_points is None:
        current_points = 500

    st.metric(label=texts["points_label"], value=f"{current_points} نقطة")

    st.sidebar.markdown("---")
    st.sidebar.header(texts["history_header"])
    user_history = get_user_history(username_input)
    if user_history:
        for idea, time_stamp in user_history[:5]:
            st.sidebar.text(f"• {idea} \n  ({time_stamp})")
    else:
        st.sidebar.info(texts["no_history"])

    show_charge_page = st.sidebar.checkbox(texts["charge_page_toggle"])

    if current_points <= 0 or show_charge_page:
        st.header(texts["charge_title"])
        st.write(texts["charge_desc"])
        
        currency = st.selectbox(texts["currency_prompt"], ["الدولار الأمريكي (USD)", "الجنيه المصري (EGP)", "الريال السعودي (SAR)", "الجنيه السوداني (SDG)"])
        
        prices = {
            "الدولار الأمريكي (USD)": "$3",
            "الجنيه المصري (EGP)": "150 EGP",
            "الريال السعودي (SAR)": "12 SAR",
            "الجنيه السوداني (SDG)": "3000 SDG"
        }
        
        st.info(f"💰 سعر باقة الشحن (1000 نقطة إضافية) هو: {prices[currency]}")
        
        pay_now = st.button(f"{texts['pay_button']} {currency}")
        if pay_now:
            st.info(texts["pay_success_msg"])
            try:
                encoded_user = urllib.parse.quote(username_input)

                checkout_session = stripe.checkout.Session.create(
                    customer_email=email_input,
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': '1000 نقطة - صانع البرامج الذكي',
                            },
                            'unit_amount': 300,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=f"http://localhost:8501/?payment=success&user={encoded_user}",
                    cancel_url=f"http://localhost:8501/?payment=cancel",
                )
                
                st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_session.url}">', unsafe_allow_html=True)
                st.markdown(f"إذا لم يتم تحويلك تلقائياً، [اضغط هنا للتوجه إلى صفحة الدفع]({checkout_session.url})")
            except Exception as e:
                st.error(f"خطأ في الاتصال ببوابة الدفع: {e}")
    else:
        st.write(f"{texts['idea_prompt']} {APP_COST} {texts['points_cost_suffix']}")
        
        app_tech = st.selectbox(
            texts["tech_prompt"],
            [
                "Python (General / Flask / Streamlit)",
                "JavaScript / TypeScript (Node.js / React / Next.js)",
                "HTML / CSS / JavaScript (تطبيقات الويب)",
                "C++ (أنظمة وبرمجيات سريعة)",
                "C# (.NET / CSharp)",
                "Java (تطبيقات المؤسسات والأندرويد)",
                "PHP (Laravel / WordPress / Web)",
                "Ruby (Ruby on Rails)",
                "Go / Golang (خوادم عالية الأداء)",
                "Rust (برمجيات آمنة وعالية الأداء)",
                "Swift (تطبيقات iOS / Mac)",
                "Kotlin (تطبيقات Android الحديثة)",
                "SQL / Database (قواعد بيانات وهندسة بيانات)",
                "Flutter / Dart (تطبيقات الهواتف متعددة المنصات)",
                "Shell Script / Bash (أدوات النظام والأتمتة)"
            ]
        )
        
        app_idea = st.text_input(texts["idea_input"], placeholder=texts["idea_placeholder"])
        generate_btn = st.button(texts["generate_btn"])

        if generate_btn and app_idea:
            if current_points < APP_COST:
                st.error(f"{texts['insufficient_funds']} {APP_COST} نقطة). يرجى شحن الرصيد من القائمة الجانبية.")
            else:
                st.info(texts["generating_info"])
                
                system_prompt = f"""
                You are an expert multilingual AI Software Engineer.
                The user wants to build a complete application based on this description: "{app_idea}".
                Selected Technology / Programming Language: {app_tech}.
                Please generate the complete, production-ready source code files using the selected technology.

                You MUST write the filename clearly before EVERY code block using this exact format:
                File: filename.ext
                ```[language_extension]
                [code]
                ```
                """

                response = None
                try:
                    response = generate_content_with_retry(system_prompt)
                except Exception as e:
                    st.error(f"{texts['error_msg']} {e}")

                if response:
                    content = response.text
                    folder_name = "Generated_App_Project"
                    
                    if os.path.exists(folder_name):
                        shutil.rmtree(folder_name)
                    os.makedirs(folder_name, exist_ok=True)

                    file_matches = re.findall(r'File:\s*([a-zA-Z0-9_\-\.]+)\s*\n+```[a-zA-Z]*\n(.*?)\n```', content, re.DOTALL)

                    new_balance = current_points - APP_COST
                    update_user_points(username_input, new_balance)
                    save_user_history(username_input, app_idea)

                    if file_matches:
                        for filename, code in file_matches:
                            file_path = os.path.join(folder_name, filename.strip())
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(code.strip())
                        
                        shutil.make_archive("Generated_App_Project", 'zip', folder_name)
                        st.success(texts["success_files"])
                        
                        st.subheader(texts["preview_header"])
                        tab_names = [match[0].strip() for match in file_matches]
                        tabs = st.tabs(tab_names)
                        
                        for i, tab in enumerate(tabs):
                            with tab:
                                st.code(file_matches[i][1].strip())
                        
                        with open("Generated_App_Project.zip", "rb") as fp:
                            st.download_button(
                                label=texts["download_zip"],
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
                        st.success(f"{texts['backup_success']} {folder_name}/project_code.txt")
                        
                        st.subheader(texts["preview_backup"])
                        st.code(content, language='markdown')
                        
                        with open("Generated_App_Project.zip", "rb") as fp:
                            st.download_button(
                                label=texts["download_zip"],
                                data=fp,
                                file_name="Generated_App_Project.zip",
                                mime="application/zip"
                            )
                        st.balloons()
