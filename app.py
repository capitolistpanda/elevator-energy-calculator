from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    trips = int(request.form['trips'])
    stops = int(request.form['stops'])
    elevator_type = request.form['type']
    counterbalance = int(request.form['counterbalance'])
    load = int(request.form['load'])
    src = float(request.form['src'])
    ssc = float(request.form['ssc'])
    energy_ref = float(request.form['energy_ref'])
    energy_short = float(request.form['energy_short'])
    speed = float(request.form['speed'])
    acceleration = float(request.form['acceleration'])
    jerk = float(request.form['jerk'])
    door_time = float(request.form['door_time'])
    idle_power = float(request.form['idle_power'])
    standby5 = float(request.form['standby5'])
    standby30 = float(request.form['standby30'])
    operating_days = int(request.form['operating_days'])

    # Determine Usage Category
    if trips == 0:
        usage_category = int(request.form['usage_category'])
    elif trips < 75:
        usage_category = 1
    elif trips < 200:
        usage_category = 2
    elif trips < 500:
        usage_category = 3
    elif trips < 1000:
        usage_category = 4
    elif trips < 2000:
        usage_category = 5
    else:
        usage_category = 6

    # Energy Calculation (Placeholder: Adapt to match full MATLAB logic)
    energy_consumption = trips * load * (0.1 if elevator_type == "hydraulic" else 0.05)

    return render_template('result.html', result=f"{energy_consumption:.2f}")

if __name__ == '__main__':
    app.run(debug=True)
