import os, requests, smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

print("Email user loaded:", EMAIL_USER)
print("Email pass loaded:", EMAIL_PASS[:4] + "****" if EMAIL_PASS else "MISSING")
print("News API key loaded:", NEWS_API_KEY[:4] + "****" if NEWS_API_KEY else "MISSING")

COMPANIES = ["Blackstone", "Tesla", "Amazon", "Wells Fargo", "Meta"]
NEGATIVE_TERMS = ["abuse", "accuse", "allege", "ambush", "aml", "arraign", "arrest", "assault", "asset freeze",
    "attack", "bankrupt", "beat", "blackmail", "breach", "bribe", "chapter pre/1", "chapter 7",
    "chapter 11", "captive", "censure", "charge", "class action", "conspire", "conspirator", "co conspirator",
    "contraband", "convict", "corrupt", "counterfeit", "court", "crime", "criminal", "criticism",
    "deceive", "deception", "deprave", "defendant", "defraud", "denied", "deny", "discipline",
    "discriminate", "distort", "doj", "department of justice", "drug", "detain", "detention",
    "disgrace", "disqualify", "embattled", "embezzle", "extort", "extremist", "fail", "felon",
    "fined", "fraud", "fcpa", "foreign corrupt practices act", "fugitive", "guilty", "harass",
    "illegal", "illicit", "imprison", "incarcerate", "incrimination", "indict", "injunction",
    "inside deal", "inside info", "insolvent", "investigation", "kickback", "kidnap", "jail",
    "judgment", "larceny", "laundering", "lawsuit", "license", "liquidate", "litigation", "loss",
    "mafia", "manipulate", "misappropriate", "misconduct", "misdemeanor", "mismanage", "misrepresent",
    "mob", "money laundering", "murder", "narcotic", "negligence", "nefarious", "offend", "offensive",
    "organized crime", "panama papers", "parole", "politically exposed", "prohibit", "probation",
    "prosecute", "racketeer", "rape", "robbery", "revocation", "revoke", "risk", "sabotage",
    "sanction", "scam", "scandal", "separate", "sexual", "smuggle", "steal", "stole", "sued",
    "suing", "suspend", "terminate", "terrorist", "theft", "threat", "trafficking", "unlawful",
    "verdict", "violate", "violent", "watchlist", "wikileaks"]

def get_articles(company):
    url = f"https://newsapi.org/v2/everything?q={company}&apiKey={NEWS_API_KEY}&language=en"
    r = requests.get(url).json()
    return r.get("articles", [])

def check_negative(article, company):
    title = article.get("title") or ""
    description = article.get("description") or ""
    text = (title + " " + description).lower()
    return any(term in text for term in NEGATIVE_TERMS) and company.lower() in text

def build_report():
    flagged = []
    for company in COMPANIES:
        for a in get_articles(company):
            if check_negative(a, company):
                flagged.append(f"{company}: {a['title']} - {a['url']}")
    return flagged

def send_email(report):
    msg = MIMEText("\n".join(report) if report else "No negative news today.")
    msg["Subject"] = "Daily Risk Monitoring Report"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.sendmail(msg["From"], [msg["To"]], msg.as_string())

if __name__ == "__main__":
    report = build_report()
    send_email(report)
    print("Report sent!")
