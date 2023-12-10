from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import serial
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fingerprint.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    school = db.Column(db.String(50), nullable=False)

arduino = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enroll', methods=['POST'])
def enroll():
    try:
        user_id = request.form.get('id')
        user_name = request.form.get('name')
        user_year = request.form.get('year')
        user_department = request.form.get('department')
        user_school = request.form.get('school')

        if not user_id:
            return jsonify({'status': 'Enrollment failed - Please provide a user ID'})

        existing_user = User.query.filter_by(user_id=user_id).first()

        if existing_user:
            return jsonify({'status': 'Enrollment failed - User with ID already exists'})

        with app.app_context():
            new_user = User(user_id=user_id, name=user_name, year=user_year, department=user_department, school=user_school)
            db.session.add(new_user)
            db.session.commit()

        arduino.write(f'enroll {user_id}\n'.encode())
        response = arduino.readline().decode('utf-8').strip()

        return jsonify({'status': response})
    except Exception as e:
        return jsonify({'status': f'Error: {str(e)}'})


@app.route('/verify', methods=['POST'])
def verify():
    arduino.write(b'verify')
    response = arduino.readline().decode('utf-8').strip()

    if response.startswith('User ID:'):
        # Extract the user ID from the response
        user_id = response.split(':')[-1].strip()

        # Retrieve user information from the database
        user = User.query.filter_by(user_id=user_id).first()

        if user:
            return jsonify({
                'status': 'Verification successful',
                'user_id': user.user_id,
                'name': user.name,
                'year': user.year,
                'department': user.department,
                'school': user.school
            })
        else:
            return jsonify({'status': 'User not found'})
    else:
        return jsonify({'status': response})


@app.route('/delete', methods=['POST'])
def delete():
    try:
        user_id = request.form.get('id')

        existing_user = User.query.filter_by(user_id=user_id).first()

        if not existing_user:
            return jsonify({'status': 'Deletion failed - User not found'})

        with app.app_context():
            db.session.delete(existing_user)
            db.session.commit()

        arduino.write(f'delete {user_id}\n'.encode())
        response = arduino.readline().decode('utf-8').strip()

        return jsonify({'status': response})
    except Exception as e:
        return jsonify({'status': f'Error: {str(e)}'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
