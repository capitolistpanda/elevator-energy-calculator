from flask import Flask, render_template, request, g
import sqlite3

app = Flask(__name__)
DATABASE = 'elevator_data.db'

def get_db():
    """ Establish database connection and ensure foreign keys are enabled. """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # Ensure foreign keys are enabled
    return db

def init_db():
    """ Initialize the database if it does not exist. """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_energy REAL NOT NULL,
                yearly_energy REAL NOT NULL
            )
        ''')
        db.commit()
        cursor.close()  # Close the cursor

@app.teardown_appcontext
def close_db(exception):
    """ Ensure database connection is closed after request. """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def calculate_energy(nd, uc, ns, type, cb, rl, src, ssc, xpzone, sez, sfl, Erc, Esc, v, a, j, td, Pid, Pst5, Pst30, dop):
    """ Perform elevator energy calculations. """
    usage_categories = {
        1: (50, 0.13, 0.55, 0.32),
        2: (125, 0.23, 0.45, 0.32),
        3: (300, 0.36, 0.31, 0.33),
        4: (750, 0.45, 0.19, 0.36),
        5: (1500, 0.42, 0.17, 0.41),
        6: (2500, 0.42, 0.17, 0.41)
    }

    if nd == 0:
        nd, Rid, Rst5, Rst30 = usage_categories.get(uc, usage_categories[3])  # Default to category 3 if missing
    else:
        Rid, Rst5, Rst30 = usage_categories[min(usage_categories.keys(), key=lambda x: abs(x - nd))][1:]

    stop_factors = {2: 1, 3: 0.67, 4: 0.49, 5: 0.44, 6: 0.39, 7: 0.32}
    S = stop_factors.get(ns, 0.49)  # Default to 4-floor value

    load_factors = {800: 0.075, 1275: 0.045, 2000: 0.03, float('inf'): 0.02}
    Q = next(value for key, value in load_factors.items() if rl <= key)

    cb_factors = {50: 1 - 0.0164 * Q, 40: 1 - 0.0192 * Q, 30: 1 - 0.0197 * Q, 0: 1 + 0.0071 * Q, 35: 1 + 0.01 * Q, 70: 1 + 0.0187 * Q}
    kL = cb_factors.get(cb, 1)

    if xpzone == 2:
        sav = S * src
    else:
        sez_factors = {75: 0.58, 150: 0.42}
        kez = sez_factors.get(sez, 0.42)
        sav = S * (src - (sez - sfl)) + kez * (sez - sfl)

    Erm = (Erc - Esc) / (2 * (src - ssc))
    Essc = 0.5 * (Erc - 2 * Erm * src)
    Erav = 2 * Erm * sav + 2 * Essc
    Erd = kL * nd * Erav

    tav = sav / v + v / a + a / j + td
    trd = nd * tav / 3600
    tnr = 24 - trd
    Enr = tnr / 100 * (Pid * Rid + Pst5 * Rst5 + Pst30 * Rst30)
    Ed = (Erd + Enr) / 1000
    Ey = Ed * dop

    return round(Ed, 2), round(Ey, 2)

@app.route('/')
def index():
    """ Render home page with past calculations. """
    db = get_db()
    with db:
        cur = db.execute('SELECT * FROM calculations ORDER BY id DESC LIMIT 5')
        past_results = cur.fetchall()
    return render_template('index.html', past_results=past_results)

@app.route('/calculate', methods=['POST'])
def calculate():
    """ Handle form submission and perform calculations. """
    try:
        data = {key: float(request.form.get(key, 0)) for key in [
            "nd", "uc", "ns", "type", "cb", "rl", "src", "ssc", "xpzone", "sez", "sfl", "Erc", "Esc",
            "v", "a", "j", "td", "Pid", "Pst5", "Pst30", "dop"
        ]}

        Ed, Ey = calculate_energy(**data)

        db = get_db()
        with db:
            db.execute('INSERT INTO calculations (daily_energy, yearly_energy) VALUES (?, ?)', (Ed, Ey))

        return render_template('result.html', energy=Ed, yearly=Ey)

    except Exception as e:
        return f"Error: {str(e)}", 400

if __name__ == '__main__':
    init_db()  # Ensure database is initialized before running
    app.run(debug=True)
