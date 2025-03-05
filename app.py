from flask import Flask, render_template, request, g
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'elevator_data.db'


def get_db():
    """ Establish database connection and ensure foreign keys are enabled. """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # Ensure foreign keys are enabled
    return db


def reset_database():
    """ Completely delete the old database file and reset it """
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    init_db()


def init_db():
    """ Create a fresh database with the correct table structure. """
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
        cursor.close()


@app.teardown_appcontext
def close_db(exception):
    """ Ensure database connection is closed after request. """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def calculate_energy(trips, usage_category, stops, type, counterbalance, load, src, ssc, energy_ref, energy_short, speed, acceleration, jerk, door_time, idle_power, standby5, standby30, operating_days, nd=0):
    """Calculate energy based on elevator parameters."""
    
    usage_categories = {
        1: (50, 0.13, 0.55, 0.32),
        2: (125, 0.23, 0.45, 0.32),
        3: (300, 0.36, 0.31, 0.33),
        4: (750, 0.45, 0.19, 0.36),
        5: (1500, 0.42, 0.17, 0.41),
        6: (2500, 0.42, 0.17, 0.41)
    }

    if nd == 0:
        nd, Rid, Rst5, Rst30 = usage_categories.get(usage_category, usage_categories[3])  # Default to category 3 if missing
    else:
        Rid, Rst5, Rst30 = usage_categories[min(usage_categories.keys(), key=lambda x: abs(x - nd))][1:]

    stop_factors = {2: 1, 3: 0.67, 4: 0.49, 5: 0.44, 6: 0.39, 7: 0.32}
    S = stop_factors.get(stops, 0.49)

    load_factors = {800: 0.075, 1275: 0.045, 2000: 0.03, float('inf'): 0.02}
    Q = next(value for key, value in load_factors.items() if load <= key)

    cb_factors = {50: 1 - 0.0164 * Q, 40: 1 - 0.0192 * Q, 30: 1 - 0.0197 * Q, 0: 1 + 0.0071 * Q, 35: 1 + 0.01 * Q, 70: 1 + 0.0187 * Q}
    kL = cb_factors.get(counterbalance, 1)

    sav = S * src

    Erm = (energy_ref - energy_short) / (2 * (src - ssc))
    Essc = 0.5 * (energy_ref - 2 * Erm * src)
    Erav = 2 * Erm * sav + 2 * Essc
    Erd = kL * nd * Erav

    tav = sav / speed + speed / acceleration + acceleration / jerk + door_time
    trd = nd * tav / 3600
    tnr = 24 - trd
    Enr = tnr / 100 * (idle_power * Rid + standby5 * Rst5 + standby30 * Rst30)
    Ed = (Erd + Enr) / 1000
    Ey = Ed * operating_days

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
    data = {}

    for key in request.form:
        value = request.form[key]
        try:
            data[key] = float(value)
        except ValueError:
            data[key] = value

    print("Received Form Data:", data)  # Debugging print

    # Ensure required keys are correctly mapped
    required_keys = ['usage_category', 'stops', 'type', 'counterbalance', 'load', 'src', 'ssc', 'energy_ref', 'energy_short', 
                     'speed', 'acceleration', 'jerk', 'door_time', 'idle_power', 'standby5', 'standby30', 'operating_days']

    for key in required_keys:
        if key not in data:
            return f"Error: Missing required field '{key}'", 400

    # Perform energy calculation
    Ed, Ey = calculate_energy(**data)

    # Insert results into the database
    db = get_db()
    db.execute('INSERT INTO calculations (daily_energy, yearly_energy) VALUES (?, ?)', (Ed, Ey))
    db.commit()

    # Return the calculated values to the template
    return render_template('result.html', energy=Ed, yearly=Ey)


if __name__ == '__main__':
    with app.app_context():
        reset_database()  # Forces database reset every time the app starts.
    app.run(debug=True)