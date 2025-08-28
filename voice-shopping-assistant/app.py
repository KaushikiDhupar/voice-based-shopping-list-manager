
from flask import Flask, request, jsonify, render_template
import sqlite3, os, json, re
from datetime import datetime, timedelta

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'shopping.db')
CAT_MAP = {
    'milk': 'dairy', 'almond milk': 'dairy', 'yogurt': 'dairy', 'cheese': 'dairy',
    'apple': 'produce', 'apples': 'produce', 'banana': 'produce', 'bananas': 'produce',
    'bread': 'bakery', 'water': 'beverages', 'toothpaste': 'personal_care',
    'chocolate': 'snacks'
}
SUBSTITUTES = {
    'milk': ['almond milk', 'soy milk'],
    'bread': ['whole wheat bread', 'gluten-free bread'],
    'yogurt': ['greek yogurt']
}

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        category TEXT,
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT NOT NULL,
        category TEXT,
        bought_at TEXT NOT NULL
    )''')
    con.commit()
    con.close()

def get_con():
    return sqlite3.connect(DB_PATH)

def categorize(item: str):
    s = item.lower()
    # find by key containment
    for k, v in CAT_MAP.items():
        if k in s:
            return v
    return None

# --- Simple rule-based NLP ---
ADD_PATTERNS = [
    r'^(please\s*)?add\s+(?P<qty>\d+)?\s*(?P<item>.+)$',
    r'^(i\s+want\s+to\s+buy|i\s+need|buy|get)\s+(?P<qty>\d+)?\s*(?P<item>.+)$'
]
REMOVE_PATTERNS = [
    r'^(please\s*)?remove\s+(?P<item>.+)$',
    r'^delete\s+(?P<item>.+)$'
]
SEARCH_PATTERNS = [
    r'^(find|search\s+for)\s+(?P<item>.+?)(\s+under\s+\$?(?P<max>\d+(?:\.\d+)?))?$'
]

QUANTITY_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

def word_to_num(s: str):
    s = s.lower().strip()
    return QUANTITY_WORDS.get(s)

def parse_text(text: str):
    t = text.strip()
    # Try search
    for pat in SEARCH_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            item = m.group('item').strip()
            maxp = m.group('max')
            return {'intent': 'search', 'item': item, 'max': float(maxp) if maxp else None}

    # Try remove
    for pat in REMOVE_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            item = m.group('item').strip()
            return {'intent': 'remove', 'item': item}

    # Try add
    for pat in ADD_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            qty_raw = (m.group('qty') or '').strip()
            item = m.group('item').strip()
            qty = 1
            if qty_raw.isdigit():
                qty = int(qty_raw)
            else:
                wnum = word_to_num(qty_raw) if qty_raw else None
                if wnum:
                    qty = wnum
            return {'intent': 'add', 'item': item, 'quantity': qty}

    # Fallback: assume add
    return {'intent': 'add', 'item': t, 'quantity': 1}

def load_products():
    p = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse', methods=['POST'])
def api_parse():
    data = request.get_json(force=True)
    text = data.get('text', '')
    parsed = parse_text(text)

    if parsed['intent'] == 'add':
        item = parsed['item']
        qty = parsed.get('quantity', 1)
        cat = categorize(item)
        con = get_con()
        cur = con.cursor()
        cur.execute('INSERT INTO list (item, quantity, category, created_at) VALUES (?, ?, ?, ?)', 
                    (item, qty, cat, datetime.utcnow().isoformat()))
        con.commit()
        # push to history
        cur.execute('INSERT INTO history (item, category, bought_at) VALUES (?, ?, ?)', 
                    (item, cat, datetime.utcnow().isoformat()))
        con.commit()
        con.close()
        return jsonify({'ok': True, 'message': f'Added {qty} × {item} to your list.'})

    if parsed['intent'] == 'remove':
        item = parsed['item'].lower()
        con = get_con()
        cur = con.cursor()
        cur.execute('DELETE FROM list WHERE lower(item) LIKE ?', (f'%{item}%',))
        con.commit()
        con.close()
        return jsonify({'ok': True, 'message': f'Removed items matching "{item}".'})

    if parsed['intent'] == 'search':
        # handled on /api/search for UI; reply here too for voice-only
        item = parsed['item']
        maxp = parsed.get('max')
        params = []
        res = []
        for p in load_products():
            if item.lower() in p['name'].lower():
                if maxp is None or p['price'] <= maxp:
                    res.append(p)
        return jsonify({'ok': True, 'message': f'Found {len(res)} results for "{item}".', 'results': res})

    return jsonify({'ok': False, 'message': 'Sorry, I could not understand.'}), 400

@app.route('/api/add', methods=['POST'])
def api_add():
    data = request.get_json(force=True)
    item = data.get('item', '').strip()
    qty = int(data.get('quantity', 1))
    if not item:
        return jsonify({'ok': False, 'error': 'item required'}), 400
    cat = categorize(item)
    con = get_con()
    cur = con.cursor()
    cur.execute('INSERT INTO list (item, quantity, category, created_at) VALUES (?, ?, ?, ?)', 
                (item, qty, cat, datetime.utcnow().isoformat()))
    con.commit()
    cur.execute('INSERT INTO history (item, category, bought_at) VALUES (?, ?, ?)', 
                (item, cat, datetime.utcnow().isoformat()))
    con.commit()
    con.close()
    return jsonify({'ok': True})

@app.route('/api/remove', methods=['POST'])
def api_remove():
    data = request.get_json(force=True)
    id_ = data.get('id')
    if not id_:
        return jsonify({'ok': False, 'error': 'id required'}), 400
    con = get_con()
    cur = con.cursor()
    cur.execute('DELETE FROM list WHERE id = ?', (id_,))
    con.commit()
    con.close()
    return jsonify({'ok': True})

@app.route('/api/list')
def api_list():
    con = get_con()
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute('SELECT * FROM list ORDER BY id DESC')
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return jsonify({'items': rows})

def seasonal_items():
    # very simple seasonal mapping by month
    month = datetime.utcnow().month
    if month in (12, 1, 2):
        return ['oranges', 'hot chocolate']
    if month in (3, 4, 5):
        return ['strawberries', 'spinach']
    if month in (6, 7, 8):
        return ['watermelon', 'lemonade']
    return ['apples', 'pumpkin']

@app.route('/api/suggest')
def api_suggest():
    # History-based frequency: items bought in last 30 days not on list
    con = get_con()
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    cur.execute('SELECT item, category, COUNT(*) as freq FROM history WHERE bought_at >= ? GROUP BY item, category ORDER BY freq DESC LIMIT 5', (since,))
    hist = [dict(r) for r in cur.fetchall()]
    cur.execute('SELECT lower(item) FROM list')
    onlist = {r[0] for r in cur.fetchall()}
    con.close()

    suggestions = []
    for h in hist:
        if h['item'].lower() not in onlist:
            suggestions.append({'item': h['item'], 'category': h['category'] or categorize(h["item"]), 'reason': 'You often buy this.'})

    # Seasonal
    for s in seasonal_items():
        if s.lower() not in onlist:
            suggestions.append({'item': s, 'category': categorize(s) or 'seasonal', 'reason': 'In season.'})

    # Example substitutes for items currently on the list
    for it in list(onlist):
        base = it.split()[0]
        subs = SUBSTITUTES.get(base, [])
        for sub in subs:
            if sub.lower() not in onlist:
                suggestions.append({'item': sub, 'category': categorize(sub), 'reason': f'Alternative for {base}.'})

    # uniqueness by item
    seen = set()
    uniq = []
    for s in suggestions:
        key = s['item'].lower()
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return jsonify({'suggestions': uniq[:8]})

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    brand = request.args.get('brand', '').strip().lower()
    maxp = request.args.get('max', '').strip()
    try:
        maxp = float(maxp) if maxp else None
    except:
        maxp = None
    results = []
    for p in load_products():
        if q and q not in p['name'].lower():
            continue
        if brand and brand not in p['brand'].lower():
            continue
        if maxp is not None and p['price'] > maxp:
            continue
        results.append(p)
    return jsonify({'results': results})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
