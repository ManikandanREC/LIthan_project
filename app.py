from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'host',
    'password': 'root',
    'database': 'litha'
}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            # Connect to the database
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Query to check user credentials
            query = "SELECT * FROM users1 WHERE username=%s AND password=%s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                # Store user details in session
                session['user_id'] = user[0]  # Assuming the first column is user ID
                session['username'] = user[1]  # Assuming the second column is username
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password. Please try again.', 'danger')

        except Error as e:
            flash(f"Error connecting to database: {str(e)}", 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template('signup.html')

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Query to insert new user
            query = """
            INSERT INTO users1 (username, password, email, full_name, phone_number) 
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (username, password, email, full_name, phone_number))
            connection.commit()  # Commit the transaction

            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for('login'))

        except Error as e:
            flash(f"Error connecting to database: {str(e)}", 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('signup.html')

@app.route('/profile')
def profile():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to access your profile.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Query to get user details
        query = "SELECT username, email,password, phone_number FROM users1 WHERE id=%s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        # Query to get past water calculations for this user
        query = "SELECT crop_type, soil_type, field_size, growth_stage, daily_water, total_water, calculation_date FROM water_calculations WHERE user_id=%s ORDER BY calculation_date DESC"
        cursor.execute(query, (user_id,))
        calculations = cursor.fetchall()

        return render_template('profile.html', user=user, calculations=calculations)

    except Error as e:
        flash(f"Error connecting to database: {str(e)}", 'danger')
        return redirect(url_for('login'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/water-calculator', methods=['GET', 'POST'])
def water_calculator():
    if request.method == 'POST':
        crop_type = request.form['cropType']
        soil_type = request.form['soilType']
        field_size = float(request.form['fieldSize'])
        growth_stage = request.form['growthStage']

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            # Fetch water requirements
            cursor.execute("SELECT daily, factor FROM water_requirements WHERE crop_type = %s", (crop_type,))
            water_req = cursor.fetchone()

            # Fetch soil factor
            cursor.execute("SELECT factor FROM soil_factors WHERE soil_type = %s", (soil_type,))
            soil_factor = cursor.fetchone()['factor']

            # Fetch stage factor
            cursor.execute("SELECT factor FROM stage_factors WHERE growth_stage = %s", (growth_stage,))
            stage_factor = cursor.fetchone()['factor']

            base_water = water_req['daily']
            daily_water_per_acre = base_water * soil_factor * stage_factor
            total_daily_water = daily_water_per_acre * field_size

            # Generate recommendation
            cursor.execute("SELECT recommendation FROM soil_recommendations WHERE soil_type = %s", (soil_type,))
            recommendation = cursor.fetchone()['recommendation']

            # Store calculation results
            query = """
            INSERT INTO water_calculations 
            (user_id, crop_type, soil_type, field_size, growth_stage, daily_water, total_water, recommendation, calculation_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            cursor.execute(query, (
                session.get('user_id'),
                crop_type,
                soil_type,
                field_size,
                growth_stage,
                daily_water_per_acre,
                total_daily_water,
                recommendation
            ))
            connection.commit()

            return jsonify({
                'dailyWater': f"Daily Water Requirement: {daily_water_per_acre:.1f} gallons per acre",
                'weeklyWater': f"Weekly Water Requirement: {daily_water_per_acre * 7:.1f} gallons per acre",
                'totalWater': f"Total Field Requirement: {total_daily_water:.1f} gallons per day",
                'recommendations': recommendation
            })

        except Error as e:
            print(f"Error: {e}")
            return jsonify({'error': 'An error occurred while processing your request.'}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('water-calculator.html')

if __name__ == '__main__':
    app.run(debug=True)
