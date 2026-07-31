import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import date

# -------------------- Database Setup --------------------
DB_NAME = "milk_tracker.db"

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                type TEXT,
                person TEXT,
                quantity REAL,
                rate REAL,
                amount REAL,
                notes TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    clean_user = username.strip().lower()
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                      (clean_user, hash_password(password)))
            conn.commit()
            return True, "Account created successfully! Please login."
    except sqlite3.IntegrityError:
        # User pehle se exist karta hai
        return False, "This username is already taken. Please choose another."
    except Exception as e:
        return False, f"An error occurred: {str(e)}"

def login_user(username, password):
    clean_user = username.strip().lower()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
                  (clean_user, hash_password(password)))
        result = c.fetchone()
        return result[0] if result else None

def add_transaction(user_id, date, type_, person, quantity, rate, amount, notes):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO transactions (user_id, date, type, person, quantity, rate, amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, date, type_, person, quantity, rate, amount, notes))
        conn.commit()

def delete_transaction(transaction_id, user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        # Security check: User sirf apni hi transaction delete kar paye
        c.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
        conn.commit()

def get_transactions(user_id, start_date=None, end_date=None, person_filter=None):
    conn = get_db_connection()
    query = "SELECT id, date, type, person, quantity, rate, amount, notes FROM transactions WHERE user_id = ?"
    params = [user_id]
    
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
        
    if person_filter and person_filter != "All":
        query += " AND LOWER(person) = ?"
        params.append(person_filter.lower())
    
    query += " ORDER BY date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# -------------------- App Initialization --------------------
init_db()

st.set_page_config(
    page_title="Milk Tracker",
    page_icon="🥛",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .watermark {
        position: fixed;
        bottom: 10px;
        right: 15px;
        font-size: 0.75rem;
        color: #999;
        opacity: 0.8;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🥛 Milk Tracker Pro</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Secure Person-to-Person Milk Ledger</p>', unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

# -------------------- Login / Signup Section --------------------
if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Create Account"])
    
    with tab1:
        st.markdown("#### Welcome Back")
        username = st.text_input("Username", key="login_user", placeholder="Enter username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
        
        if st.button("Login", type="primary"):
            if not username or not password:
                st.warning("Please fill in both fields.")
            else:
                user_id = login_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")
    
    with tab2:
        st.markdown("#### Create New Unique Account")
        new_user = st.text_input("Choose Username", key="signup_user", placeholder="Create unique username")
        new_pass = st.text_input("Choose Password", type="password", key="signup_pass", placeholder="Min 4 characters")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass", placeholder="Re-enter password")
        
        if st.button("Create Account", type="primary"):
            if not new_user.strip():
                st.error("Username cannot be empty.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match!")
            elif len(new_pass) < 4:
                st.error("Password must be at least 4 characters long.")
            else:
                success, msg = create_user(new_user, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

# -------------------- Main Dashboard Area --------------------
else:
    st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state.username.title()}**")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio("Navigation", ["➕ Add Entry", "📋 View & Manage Records", "📊 Summary Report"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Made with ❤️ by Aagne")

    # -------- Tab 1: Add Entry --------
    if menu == "➕ Add Entry":
        st.markdown("### ➕ Add New Milk Entry")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("📅 Date", value=date.today())
            entry_type = st.selectbox("🔄 Transaction Type", ["Buy", "Sell"])
        with col2:
            person = st.text_input("👤 Person / Customer Name", placeholder="e.g. Ramesh / Dairy")
            quantity = st.number_input("🥛 Quantity (Litres)", min_value=0.1, step=0.5, value=1.0)
        
        rate = st.number_input("💰 Rate per Litre (₹)", min_value=0.0, step=1.0, value=50.0)
        live_amount = quantity * rate
        
        st.info(f"💡 **Total Calculated Amount:** ₹ {live_amount:.2f}")
        notes = st.text_input("📝 Optional Notes", placeholder="e.g. Paid in cash, Morning batch")
        
        if st.button("💾 Save Entry", type="primary"):
            if not person.strip():
                st.warning("Please enter Person Name.")
            else:
                add_transaction(
                    st.session_state.user_id,
                    str(entry_date),
                    entry_type,
                    person.strip(),
                    quantity,
                    rate,
                    live_amount,
                    notes.strip()
                )
                st.success(f"Saved: {quantity}L {entry_type} with {person.strip()} = ₹{live_amount:.2f}")
                st.balloons()

    # -------- Tab 2: View & Delete Records --------
    elif menu == "📋 View & Manage Records":
        st.markdown("### 📋 Manage Records")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("From Date", value=date.today().replace(day=1))
        with col2:
            end = st.date_input("To Date", value=date.today())
        
        df = get_transactions(st.session_state.user_id, str(start), str(end))
        
        if df.empty:
            st.info("No records found for the selected period.")
        else:
            # Person filter
            all_persons = ["All"] + sorted(list(df['person'].unique()))
            selected_person = st.selectbox("🔍 Filter by Person", all_persons)
            
            filtered_df = get_transactions(st.session_state.user_id, str(start), str(end), selected_person)
            
            # Show table without internal DB ID
            st.dataframe(filtered_df.drop(columns=["id"]), use_container_width=True, hide_index=True)
            
            # CSV Download Option
            csv_data = filtered_df.drop(columns=["id"]).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv_data,
                file_name=f"milk_records_{start}_to_{end}.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            st.markdown("#### 🗑️ Delete an Entry")
            # Deletion helper
            entry_options = {
                f"ID {row['id']} | {row['date']} | {row['type']} | {row['person']} | {row['quantity']}L | ₹{row['amount']}": row['id']
                for _, row in filtered_df.iterrows()
            }
            if entry_options:
                selected_entry = st.selectbox("Select entry to delete", list(entry_options.keys()))
                if st.button("❌ Delete Selected Record", type="secondary"):
                    delete_id = entry_options[selected_entry]
                    delete_transaction(delete_id, st.session_state.user_id)
                    st.success("Record deleted successfully!")
                    st.rerun()

    # -------- Tab 3: Summary --------
    elif menu == "📊 Summary Report":
        st.markdown("### 📊 Comprehensive Summary")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("From", value=date.today().replace(day=1), key="sum_start")
        with col2:
            end = st.date_input("To", value=date.today(), key="sum_end")
            
        df = get_transactions(st.session_state.user_id, str(start), str(end))
        
        if df.empty:
            st.info("No data available to construct summary.")
        else:
            buy_df = df[df["type"] == "Buy"]
            sell_df = df[df["type"] == "Sell"]
            
            t_buy_qty, t_buy_amt = buy_df["quantity"].sum(), buy_df["amount"].sum()
            t_sell_qty, t_sell_amt = sell_df["quantity"].sum(), sell_df["amount"].sum()
            
            st.markdown("#### 🔵 Total Buy vs 🟢 Total Sell")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Bought (L)", f"{t_buy_qty:.1f} L")
            c2.metric("Paid (₹)", f"₹ {t_buy_amt:.2f}")
            c3.metric("Sold (L)", f"{t_sell_qty:.1f} L")
            c4.metric("Received (₹)", f"₹ {t_sell_amt:.2f}")
            
            st.markdown("---")
            st.markdown("#### 👥 Person-Wise Ledger Breakdown")
            
            # Aggregate per person
            person_summary = df.groupby(['person', 'type'])[['quantity', 'amount']].sum().reset_index()
            st.dataframe(person_summary, use_container_width=True, hide_index=True)

# -------------------- Watermark --------------------
st.markdown('<p class="watermark">Yash Patel ❤️ by Aagne</p>', unsafe_allow_html=True)