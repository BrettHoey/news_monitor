import streamlit as st
import requests
import sqlite3
import os
import hashlib
import re
from dotenv import load_dotenv

# Load env variables
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# --- Safe rerun workaround ---
try:
    from streamlit.runtime.scriptrunner import RerunException
    def rerun():
        raise RerunException(None)
except ImportError:
    def rerun():
        st.warning("Please refresh the page to see changes.")

# --- DATABASE SETUP ---
DB_FILE = "users.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# Add email column if missing
try:
    c.execute("SELECT email FROM users LIMIT 1")
except sqlite3.OperationalError:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    conn.commit()

c.execute("""
CREATE TABLE IF NOT EXISTS tracked_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    company TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# --- PASSWORD HASHING ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- USER FUNCTIONS ---
def create_user(username, password):
    hashed = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def check_user(username, password):
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    return row and row[0] == hash_password(password)

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    row = c.fetchone()
    return row[0] if row else None

def get_user_email(user_id):
    c.execute("SELECT email FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else ""

def update_user_email(user_id, email):
    c.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))
    conn.commit()

# --- COMPANY FUNCTIONS ---
def get_tracked_companies(user_id):
    c.execute("SELECT company FROM tracked_companies WHERE user_id=?", (user_id,))
    return [row[0] for row in c.fetchall()]

def add_tracked_company(user_id, company):
    c.execute("INSERT INTO tracked_companies (user_id, company) VALUES (?, ?)", (user_id, company))
    conn.commit()

def delete_tracked_company(user_id, company):
    c.execute("DELETE FROM tracked_companies WHERE user_id=? AND company=?", (user_id, company))
    conn.commit()

# --- FULL NEGATIVE TERMS LIST ---
NEGATIVE_TERMS = [
    "abuse", "accuse", "allege", "ambush", "aml", "arraign", "arrest", "assault", "asset freeze",
    "attack", "bankrupt", "beat", "blackmail", "breach", "bribe", "chapter pre/1",
    "chapter 7", "chapter 11", "captive", "censure", "charge", "class action", "conspire",
    "conspirator", "co conspirator", "contraband", "convict", "corrupt", "counterfeit",
    "court", "crime", "criminal", "criticism", "deceive", "deception", "deprave",
    "defendant", "defraud", "denied", "deny", "discipline", "discriminate", "distort",
    "doj", "department of justice", "drug", "detain", "detention", "disgrace",
    "disqualify", "embattled", "embezzle", "extort", "extremist", "fail", "felon",
    "fined", "fraud", "fcpa", "foreign corrupt practices act", "fugitive", "guilty",
    "harass", "illegal", "illicit", "imprison", "incarcerate", "incrimination",
    "indict", "injunction", "inside deal", "inside info", "insolvent", "investigation",
    "kickback", "kidnap", "jail", "judgment", "larceny", "laundering", "lawsuit",
    "license", "liquidate", "litigation", "loss", "mafia", "manipulate", "misappropriate",
    "misconduct", "misdemeanor", "mismanage", "misrepresent", "mob", "money laundering",
    "murder", "narcotic", "negligence", "nefarious", "offend", "offensive", "organized crime",
    "panama papers", "parole", "politically exposed", "prohibit", "probation", "prosecute",
    "racketeer", "rape", "robbery", "revocation", "revoke", "risk", "sabotage",
    "sanction", "scam", "scandal", "separate", "sexual", "smuggle", "steal",
    "stole", "sued", "suing", "suspend", "terminate", "terrorist", "theft",
    "threat", "trafficking", "unlawful", "verdict", "violate", "violent",
    "watchlist", "wikileaks"
]

# --- NEWS CHECK ---
def get_articles(company):
    url = f"https://newsapi.org/v2/everything?q={company}&apiKey={NEWS_API_KEY}&language=en"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("articles", [])
    except Exception as e:
        st.error(f"Error fetching news for {company}: {e}")
        return []

def check_negative(article, company):
    title = article.get("title") or ""
    description = article.get("description") or ""
    text = (title + " " + description).lower()

    for term in NEGATIVE_TERMS:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, text) and company.lower() in text:
            return term
    return None

# --- STREAMLIT APP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login or Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not username or not password:
            st.error("Please enter both username and password.")
        elif check_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            rerun()
        else:
            st.error("Invalid credentials")

    if st.button("Register"):
        if not username or not password:
            st.error("Please enter both username and password.")
        elif create_user(username, password):
            st.success("User created! Please login.")
        else:
            st.error("Username already exists")

else:
    st.title(f"Welcome, {st.session_state.username}")

    user_id = get_user_id(st.session_state.username)
    companies = get_tracked_companies(user_id)
    email = get_user_email(user_id)

    st.subheader("Email for Daily Alerts")
    new_email = st.text_input("Enter your email", value=email or "")
    if st.button("Save Email"):
        if new_email.strip() == "":
            st.error("Email cannot be empty.")
        else:
            update_user_email(user_id, new_email.strip())
            st.success("Email updated!")
            rerun()

    st.subheader("Tracked Companies")
    for comp in companies:
        col1, col2 = st.columns([3,1])
        with col1:
            st.write(comp)
        with col2:
            if st.button(f"Remove {comp}", key=f"remove_{comp}"):
                delete_tracked_company(user_id, comp)
                rerun()

    new_company = st.text_input("Add a new company")
    if st.button("Add Company"):
        if new_company.strip() != "" and new_company not in companies:
            add_tracked_company(user_id, new_company.strip())
            rerun()

    st.subheader("Negative News")
    for company in companies:
        st.markdown(f"### {company}")
        articles = get_articles(company)
        found = False
        for article in articles:
            term = check_negative(article, company)
            if term:
                found = True
                title = article.get("title") or "No title"
                url = article.get("url") or "#"
                st.markdown(f"🚨 {company} flagged for **{term}**  \n[{title}]({url})")
        if not found:
            st.write("No negative news found.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        rerun()
