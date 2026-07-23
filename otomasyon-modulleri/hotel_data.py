#!/usr/bin/env python3
"""
Lato Otel Veri Katmanı — Excel HOTEL_DB → JSON mapping.

7 otel, 19 personel, 9 acente, 16 tedarikçi veri yapısı.
seed_hotel_db() ile mock veri oluşturur, gerçek veri geldikçe güncellenir.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

# ── Sabitler ───────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "hotel_db.json"

GROUP_CHAT_ID = -1003776134843

# Telegram topic ID'leri
TOPIC_GEN = 1
TOPIC_TECH = 130       # ⚡ Elektrik & Havuz
TOPIC_TEKNIK = 131     # 🔧 Teknik Bakım
TOPIC_OPS = 132        # 🛎️ Operasyon
TOPIC_PURCH = 133      # 📦 Satın Alma & Muhasebe
TOPIC_FNB = 134        # 🍽️ F&B
TOPIC_IT = 135         # 💻 IT
TOPIC_CEVIRI = 146     # 🌐 Çeviri

SEASONS = {11: "HIGH", 0: "HIGH", 1: "HIGH", 2: "HIGH",
           3: "MID", 4: "LOW", 5: "LOW", 6: "LOW", 7: "LOW",
           8: "LOW", 9: "MID", 10: "HIGH"}

# ── Veri İşlemleri ─────────────────────────────────────────────────
def load_data() -> dict:
    if DB_PATH.exists():
        with open(DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return seed_hotel_db()

def save_data(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_hotel(slug: str) -> dict | None:
    for h in load_data().get("hotels", []):
        if h["slug"] == slug:
            return h
    return None

def get_staff() -> list:
    return load_data().get("staff", [])

def get_agencies() -> list:
    return load_data().get("agencies", [])

def get_suppliers() -> list:
    return load_data().get("suppliers", [])

def get_season(month: int | None = None) -> str:
    m = month if month is not None else datetime.now().month
    return SEASONS.get(m - 1, "MID")

# ── Seed Veri ──────────────────────────────────────────────────────
def seed_hotel_db() -> dict:
    """Excel analizinden türetilen mock veri."""
    today = datetime.now().date()

    # Gerçek 7 Lato oteli (AGENTS.md ile senkron — toplam 819 oda).
    # Doluluk/ADR eğrileri MOCK — gerçek Excel/PMS verisi geldikçe güncellenir.
    hotels = [
        {"name": "The Natural Resort", "slug": "natural-resort", "rooms": 294,
         "occupancy": [0.70,0.72,0.60,0.40,0.28,0.25,0.27,0.30,0.38,0.52,0.65,0.75],
         "adr": [620,600,500,380,290,280,300,320,380,460,580,650],
         "pms_id": None, "pms": "Manual",
         "location": "TBD (saha)", "type": "Resort"},
        {"name": "Trend Kamala", "slug": "trend-kamala", "rooms": 124,
         "occupancy": [0.75,0.78,0.65,0.42,0.30,0.25,0.28,0.32,0.40,0.55,0.70,0.80],
         "adr": [720,700,580,440,330,320,340,370,430,520,660,750],
         "pms_id": None, "pms": "Manual",
         "location": "Kamala, Kathu", "type": "Boutique Hotel"},
        {"name": "Case Del Sol", "slug": "case-del-sol", "rooms": 180,
         "occupancy": [0.78,0.80,0.68,0.45,0.28,0.22,0.25,0.30,0.38,0.58,0.72,0.82],
         "adr": [950,920,750,550,410,400,420,460,530,680,850,980],
         "pms_id": None, "pms": "Manual",
         "location": "Patong, Kathu (plaj kenarı — spec)", "type": "Boutique Villa"},
        {"name": "In On The Beach", "slug": "in-on-the-beach", "rooms": 55,
         "occupancy": [0.85,0.88,0.75,0.52,0.35,0.30,0.32,0.38,0.48,0.65,0.80,0.90],
         "adr": [980,950,780,590,440,420,450,500,580,720,900,1030],
         "pms_id": None, "pms": "Manual",
         "location": "plaj kenarı (spec — marine grade)", "type": "Beachfront Hotel"},
        {"name": "The Phulin Otel", "slug": "phulin-otel", "rooms": 106,
         "occupancy": [0.76,0.79,0.66,0.44,0.30,0.26,0.29,0.33,0.42,0.56,0.71,0.81],
         "adr": [680,660,540,410,310,300,320,350,410,500,630,710],
         "pms_id": None, "pms": "Manual",
         "location": "TBD (saha)", "type": "Hotel"},
        {"name": "Adema Karon", "slug": "adema-karon", "rooms": 29,
         "occupancy": [0.72,0.74,0.62,0.42,0.30,0.26,0.28,0.32,0.40,0.54,0.67,0.77],
         "adr": [580,560,460,350,260,250,270,290,350,430,540,610],
         "pms_id": None, "pms": "Manual",
         "location": "Karon, Mueang Phuket", "type": "Boutique Hotel"},
        {"name": "The Brook Pool Resort", "slug": "brook-pool-resort", "rooms": 31,
         "occupancy": [0.82,0.85,0.71,0.48,0.32,0.28,0.30,0.35,0.45,0.62,0.78,0.88],
         "adr": [850,820,680,520,390,380,410,440,510,620,780,890],
         "pms_id": "101027", "pms": "Elektraweb",
         "location": "TBD (saha — oteller/brook-pool-resort.md)", "type": "Boutique Resort"},
    ]

    for h in hotels:
        h["monthly_revenue"] = [int(h["rooms"] * h["occupancy"][i] * h["adr"][i] * 30)
                                for i in range(12)]

    staff = [
        {"name": "Somchai Charoenkit", "department": "TEKNIK", "hotel": "brook-pool-resort",
         "role": "Teknik Şef", "nationality": "TH", "wp_expiry": "2026-09-15"},
        {"name": "Nongluck Phromma", "department": "HK", "hotel": "brook-pool-resort",
         "role": "Housekeeping Lider", "nationality": "TH", "wp_expiry": None},
        {"name": "Kanya Suwanno", "department": "FB", "hotel": "brook-pool-resort",
         "role": "Şef Garson", "nationality": "TH", "wp_expiry": None},
        {"name": "Ahmet Yılmaz", "department": "YONETIM", "hotel": "brook-pool-resort",
         "role": "GM", "nationality": "TR", "wp_expiry": "2026-07-05"},
        {"name": "Prasert Wongchai", "department": "TEKNIK", "hotel": "trend-kamala",
         "role": "Elektrikçi", "nationality": "TH", "wp_expiry": "2026-08-20"},
        {"name": "Mehmet Demir", "department": "YONETIM", "hotel": "trend-kamala",
         "role": "Operasyon Müdürü", "nationality": "TR", "wp_expiry": "2026-06-28"},
        {"name": "Sunan Thaworn", "department": "ON_BURO", "hotel": "case-del-sol",
         "role": "Resepsiyon Şefi", "nationality": "TH", "wp_expiry": None},
        {"name": "Anucha Petchsri", "department": "GUVENLIK", "hotel": "natural-resort",
         "role": "Güvenlik Amiri", "nationality": "TH", "wp_expiry": None},
        {"name": "Fatma Kaya", "department": "MUHASEBE", "hotel": "brook-pool-resort",
         "role": "Muhasebe Müdürü", "nationality": "TR", "wp_expiry": "2026-11-10"},
        {"name": "Wichai Kaewsing", "department": "FB", "hotel": "phulin-otel",
         "role": "Aşçıbaşı", "nationality": "TH", "wp_expiry": None},
        {"name": "Hüseyin Şahin", "department": "TEKNIK", "hotel": "adema-karon",
         "role": "Bakım Şefi", "nationality": "TR", "wp_expiry": "2026-07-12"},
        {"name": "Niran Jantarak", "department": "HK", "hotel": "in-on-the-beach",
         "role": "Housekeeping", "nationality": "TH", "wp_expiry": None},
        {"name": "Busaba Chaimongkol", "department": "ON_BURO", "hotel": "trend-kamala",
         "role": "Resepsiyon", "nationality": "TH", "wp_expiry": None},
        {"name": "Alexey Petrov", "department": "ON_BURO", "hotel": "natural-resort",
         "role": "Guest Relations", "nationality": "RU", "wp_expiry": "2026-06-30"},
        {"name": "Rattana Sornci", "department": "HK", "hotel": "phulin-otel",
         "role": "Housekeeping", "nationality": "TH", "wp_expiry": None},
        {"name": "Kemal Aydın", "department": "TEKNIK", "hotel": "brook-pool-resort",
         "role": "Havuz Uzmanı", "nationality": "TR", "wp_expiry": "2026-10-01"},
        {"name": "Pim Tantawan", "department": "FB", "hotel": "adema-karon",
         "role": "Garson", "nationality": "TH", "wp_expiry": None},
        {"name": "Chai Wongwit", "department": "GUVENLIK", "hotel": "brook-pool-resort",
         "role": "Güvenlik", "nationality": "TH", "wp_expiry": None},
        {"name": "Somporn Laokiat", "department": "TEKNIK", "hotel": "natural-resort",
         "role": "Klima Teknisyeni", "nationality": "TH", "wp_expiry": "2026-09-25"},
    ]

    agencies = [
        {"name": "Booking.com", "type": "OTA", "commission_pct": 0.15,
         "payment_status": "Güncel", "commission_thb": 145000},
        {"name": "Agoda", "type": "OTA", "commission_pct": 0.17,
         "payment_status": "Güncel", "commission_thb": 98000},
        {"name": "Expedia", "type": "OTA", "commission_pct": 0.18,
         "payment_status": "Beklemede", "commission_thb": 42000},
        {"name": "Airbnb", "type": "OTA", "commission_pct": 0.03,
         "payment_status": "Güncel", "commission_thb": 28000},
        {"name": "Sunmar Tour", "type": "TA", "commission_pct": 0.20,
         "payment_status": "Gecikti", "commission_thb": 67000},
        {"name": "Coral Travel", "type": "TA", "commission_pct": 0.18,
         "payment_status": "Güncel", "commission_thb": 35000},
        {"name": "Pegas Touristik", "type": "TA", "commission_pct": 0.20,
         "payment_status": "Güncel", "commission_thb": 41000},
        {"name": "Anex Tour", "type": "TA", "commission_pct": 0.19,
         "payment_status": "Beklemede", "commission_thb": 31000},
        {"name": "Fun&Sun", "type": "TA", "commission_pct": 0.18,
         "payment_status": "Güncel", "commission_thb": 24000},
    ]

    suppliers = [
        {"name": "PEA Electricity", "category": "Elektrik", "contract_expiry": None,
         "monthly_avg_thb": 68608, "last_invoice_thb": 71200},
        {"name": "Phuket Water Authority", "category": "Su", "contract_expiry": None,
         "monthly_avg_thb": 18500, "last_invoice_thb": 16200},
        {"name": "AIS Business", "category": "İnternet", "contract_expiry": "2026-12-31",
         "monthly_avg_thb": 4200, "last_invoice_thb": 4200},
        {"name": "Makro Wholesale", "category": "F&B Tedarik", "contract_expiry": None,
         "monthly_avg_thb": 95000, "last_invoice_thb": 102000},
        {"name": "Global House", "category": "Teknik Malzeme", "contract_expiry": None,
         "monthly_avg_thb": 15000, "last_invoice_thb": 8500},
        {"name": "Pool Pro Thailand", "category": "Havuz Kimyasal", "contract_expiry": "2026-09-30",
         "monthly_avg_thb": 8200, "last_invoice_thb": 8200},
        {"name": "Aqua Pool Service", "category": "Havuz Bakım", "contract_expiry": "2026-06-15",
         "monthly_avg_thb": 12000, "last_invoice_thb": 12000},
        {"name": "Big C Supercenter", "category": "F&B Tedarik", "contract_expiry": None,
         "monthly_avg_thb": 45000, "last_invoice_thb": 38000},
        {"name": "Lazada Business", "category": "İT Sarf", "contract_expiry": None,
         "monthly_avg_thb": 3500, "last_invoice_thb": 2200},
        {"name": "Thai Watsadu", "category": "Yapı Malzeme", "contract_expiry": None,
         "monthly_avg_thb": 8000, "last_invoice_thb": 3500},
        {"name": "CP Fresh Mart", "category": "F&B Tedarik", "contract_expiry": "2027-01-31",
         "monthly_avg_thb": 28000, "last_invoice_thb": 31000},
        {"name": "Bangkok Insurance", "category": "Sigorta", "contract_expiry": "2026-10-31",
         "monthly_avg_thb": 0, "last_invoice_thb": 0},
        {"name": "JVC Professional", "category": "AV Ekipman", "contract_expiry": None,
         "monthly_avg_thb": 0, "last_invoice_thb": 0},
        {"name": "Electrical Plus Phuket", "category": "Elektrik Malzeme", "contract_expiry": None,
         "monthly_avg_thb": 6500, "last_invoice_thb": 9200},
        {"name": "CleanPro Supply", "category": "Temizlik Malzeme", "contract_expiry": "2026-08-31",
         "monthly_avg_thb": 12000, "last_invoice_thb": 11500},
        {"name": "Gas Tech Thailand", "category": "LPG/Doğalgaz", "contract_expiry": None,
         "monthly_avg_thb": 8500, "last_invoice_thb": 7800},
    ]

    operations = [
        {"task": "TM30 bildirim kontrolü", "department": "YONETIM", "priority": "KRITIK",
         "deadline": today.isoformat(), "status": "Beklemede"},
        {"task": "Yangın güvenlik sertifikası yenileme", "department": "TEKNIK", "priority": "YUKSEK",
         "deadline": (today + timedelta(days=15)).isoformat(), "status": "Beklemede"},
        {"task": "Otel lisansı yenileme", "department": "YONETIM", "priority": "YUKSEK",
         "deadline": (today + timedelta(days=45)).isoformat(), "status": "Beklemede"},
        {"task": "Havuz su analizi", "department": "TEKNIK", "priority": "NORMAL",
         "deadline": today.isoformat(), "status": "Tamamlandi"},
    ]

    financial = {
        "months": ["Oca","Şub","Mar","Nis","May","Haz","Tem"],
        "revenue": [485000, 512000, 408000, 298000, 210000, 195000, 205000],
        "expenses": [420000, 445000, 395000, 340000, 393350, 396440, 403729],
        "break_even_adr": 684,
        "reconciliation": {
            "brook-pool-resort": {"bank_statement": 303620, "accounting": 129290,
                      "discrepancy": 174330, "discrepancy_pct": 135,
                      "notes": "PEA elektriği bankadan 68,608 THB çekilmiş, muhasebe 9,290 THB. Maaş + servis charge tutarsız. Çamaşırhane ve temizlik muhasebede yok."}
        }
    }

    data = {
        "version": "2.1",
        "updated": datetime.now().isoformat(),
        "hotels": hotels,
        "staff": staff,
        "agencies": agencies,
        "suppliers": suppliers,
        "operations": operations,
        "financial": financial,
    }

    save_data(data)
    return data


if __name__ == "__main__":
    d = seed_hotel_db()
    print(f"✅ Veritabanı oluşturuldu: {DB_PATH}")
    print(f"   {len(d['hotels'])} otel, {len(d['staff'])} personel, "
          f"{len(d['agencies'])} acente, {len(d['suppliers'])} tedarikçi")
    total_rooms = sum(h["rooms"] for h in d["hotels"])
    print(f"   Toplam {total_rooms} oda")
