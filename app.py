from flask import Flask, Response, request, render_template, jsonify, redirect, url_for, request, flash, session
from flask import render_template, session, redirect, url_for, flash
from datetime import datetime
import pymongo
import secrets
import json
from bson.objectid import ObjectId
from bson.json_util import dumps
from functools import wraps
import datetime
app=Flask(__name__ , template_folder='templates')
app.secret_key = secrets.token_hex(32)
#carparking-vindhya
try:
    mongo = pymongo.MongoClient(
        host = 'localhost',
        port = 27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo.ParkingManagementSystemDb #connect to mongodb1
    users_collection = db.admin
    user_collection = db["user"]
    bookings_collection = db["booking"]
    vehicle_collection = db["vehicle"]
    canceled_bookings_collection = db.canceledBooking
    location_collection = db.location

    mongo.server_info() #trigger exception if cannot connect to db
except:
    print("Error connecting to MongoDB")
    
@app.route('/bookings')
def bookings():
    try:
        if 'username' not in session:
            flash('User not logged in', 'error')
            return redirect(url_for('login'))

        username = session['username']
        user_bookings = list(bookings_collection.find({'username': username}))

        return render_template('bookings.html', bookings=user_bookings)

    except Exception as ex:
        app.logger.error(f"Error fetching user bookings: {ex}")
        flash('Error fetching user bookings', 'error')
        return redirect(url_for('profile'))
    
@app.route("/cancel_booking", methods=["POST"])
def cancel_booking():
    if request.method == "POST":
        data = request.get_json()
        booking_id = data.get("bookingId")
        if booking_id:
            # Get the booking details
            booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
            if booking:
                # Get current datetime
                current_datetime = datetime.datetime.now()
                # Get booking datetime
                booking_datetime = datetime.datetime.strptime(booking['bookingDate'], "%Y-%m-%d") + datetime.timedelta(hours=int(booking['bookingStartTime'][:2]), minutes=int(booking['bookingStartTime'][3:]))
                # Calculate time difference in hours
                time_difference = (booking_datetime - current_datetime).total_seconds() / 3600
                # Check if booking date is today or in the future and if the start time is greater than 2 hours from now
                if booking_datetime.date() > current_datetime.date() or (booking_datetime.date() == current_datetime.date() and time_difference > 2):
                    # Insert the booking into the canceled bookings collection
                    canceled_bookings_collection.insert_one(booking)
                    # Delete the booking from the bookings_collection
                    result = bookings_collection.delete_one({"_id": ObjectId(booking_id)})
                    if result.deleted_count == 1:
                        return jsonify({"message": "Booking cancelled successfully"}), 200
                    else:
                        return jsonify({"error": "Failed to cancel booking"}), 400
                else:
                    return jsonify({"error": "You can only cancel bookings for today or future days and if the start time is greater than 2 hours from now"}), 400
            else:
                return jsonify({"error": "Booking not found"}), 404
        else:
            return jsonify({"error": "Invalid booking ID"}), 400
        
@app.route('/vehicle_details')
def vehicle_details():
    try:
        if 'username' not in session:
            flash('User not logged in', 'error')
            return redirect(url_for('login'))

        username = session['username']
        vehicles = list(vehicle_collection.find({'username': username}))

        return render_template('vehicle_details.html', vehicles=vehicles)

    except Exception as ex:
        app.logger.error(f"Error fetching vehicle details: {ex}")
        flash('Error fetching vehicle details', 'error')
        return redirect(url_for('profile'))
    
# Routes
@app.route('/addZone', methods=['GET', 'POST'])
def add_zone():
    if request.method == 'POST':
        zone_name = request.json.get('zoneName')
        totalSlot = int(request.json.get('totalSlot'))
        #availableSlot = request.json.get('totalSlot') # Initially, all slots are available
        new_zone = {
            'zoneName': zone_name,
            'totalSlot': totalSlot,
            'availableSlot': totalSlot
        }
        # Inserting data into the MongoDB collection
        location_collection.insert_one(new_zone)
        return jsonify({'message': 'Zone added successfully!'})
    elif request.method == 'GET':
        # Here you can return whatever is suitable for your application
        return render_template('addZone.html')
    
@app.route('/zones')
def get_zones():
    zones = list(location_collection.find({}, {'_id': 0}))
    return jsonify(zones)
    
@app.route('/canceledBooking')
def canceled_booking():
    try:
        if 'username' not in session:
            flash('User not logged in', 'error')
            return redirect(url_for('login'))

        username = session['username']
        user_canceled_booking = list(canceled_bookings_collection.find({'username': username}))

        return render_template('canceledBooking.html', user_canceled_booking=user_canceled_booking)

    except Exception as ex:
        app.logger.error(f"Error fetching canceled booking details: {ex}")
        flash('Error fetching canceled booking details', 'error')
        return redirect(url_for('profile'))

@app.route("/allCanceledBookings")
def all_canceled_bookings():
    all_canceled_bookings = canceled_bookings_collection.find()
    #all_canceled_bookings_json = dumps(all_canceled_bookings)
    return render_template('allCanceledBookings.html', all_canceled_bookings=all_canceled_bookings)
    
@app.route('/remove_vehicle/<vehicle_id>', methods=['POST'])
def remove_vehicle(vehicle_id):
    try:
        # Your code to remove the vehicle
        # Assuming you have a function to remove a vehicle by its ID
        vehicle_collection.delete_one({'_id': ObjectId(vehicle_id)})
        return jsonify({'message': 'Vehicle removed successfully', 'success': True})

    except Exception as ex:
        app.logger.error(f"Error removing vehicle: {ex}")
        return jsonify({'message': 'Error removing vehicle', 'success': False})
    
@app.route('/get/admin', methods=['GET'])
def displayall():
  try:
    documents = db.admin.find()
    output = [{item: data[item] for item in data if item != '_id'} for data in documents]
    return jsonify(output)
  except Exception as ex:
    response = Response("Search Records Error!!",status=500,mimetype='application/json')
    return response

@app.route('/verify_slot', methods=['POST'])
def verify_slot():
    booking_data = request.get_json()
    booking_date = booking_data.get('bookingDate')
    zone = booking_data.get('zone')
    start_time = booking_data.get('bookingStartTime')
    end_time = booking_data.get('bookingEndTime')

    # Check if the slot is available in MongoDB
    booked_slots_count = bookings_collection.count_documents({
        'bookingDate': booking_date,
        'zone': zone,
        'bookingStartTime': start_time,
        'bookingEndTime': end_time
    })
    
    zone_data = location_collection.find_one({'zoneName': zone})
    total_slots = zone_data.get('totalSlot', 0)
    
    available_slots = total_slots - booked_slots_count
    
    return jsonify({
        'totalSlots': total_slots,
        'bookedSlots': booked_slots_count,
        'availableSlots': available_slots
    })

    # if existing_booking:
    #     return jsonify({'available': False})
    # else:
    #     return jsonify({'available': True})

# Route for signup page
# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         # Get form data
#         username = request.form['username']
#         password = request.form['password']

#         # Check if username already exists
#         if user_collection.find_one({'username': username}):
#             flash('Username already exists. Please choose a different one.', 'error')
#             return redirect(url_for('signup'))

#         # Insert user data into database
#         user_data = {'username': username, 'password': password}
#         user_collection.insert_one(user_data)

#         flash('Signup successful. You can now login.', 'success')
#         return redirect(url_for('login'))

#     return render_template('signup.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        userId = request.form['userId']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        username = request.form['username']
        password = request.form['password']
        mobileNumber = request.form['mobileNumber']
        gender = request.form['gender']
        dob = request.form['dob']
        memberType = request.form['memberType']
        address = request.form['address']
        city = request.form['city']
        zipcode = request.form['zipcode']

        # Check if username already exists
        if user_collection.find_one({'username': username}):
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))

        # Insert user data into database
        user_data = {
            'userId': userId,
            'firstname': firstname,
            'lastname': lastname,
            'username': username,
            'mobileNumber': mobileNumber,
            'password': password,
            'gender': gender,
            'dob': dob,
            'memberType': memberType,
            'address' :address,
            'city' : city,
            'zipcode' :zipcode
        }
        user_collection.insert_one(user_data)

        flash('Signup successful. You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('login'))
    
# Route to get an employee by name
@app.route('/get/user/<user_name>', methods=['GET'])
def get_user_by_name(user_name):
    try:
        # Using a case-insensitive query to match employee name
        document = db.user.find_one({"user_name": {"$regex": f'^{user_name}$', "$options": 'i'}})
        
        if document:
            # Exclude _id field from the response
            output = {item: document[item] for item in document if item != '_id'}
            return jsonify(output)
        else:
            return Response("USER not found", status=404, mimetype='application/json')

    except Exception as ex:
        app.logger.error(f"Error retrieving user by name: {ex}")
        return Response("Internal Server Error", status=500, mimetype='application/json')   

@app.route('/allCustomers')
def get_all_users():
    try:
        # Query all documents from the users collection
        users = list(user_collection.find({}, {'_id': 0}))

        return render_template('allCustomers.html', users=users)
    except Exception as e:
        return render_template('allCustomers.html', error=str(e))

 
    
@app.route('/allVehicles')
def get_vehicles():
    try:
        # Query all documents from the vehicle collection
        vehicles = list(vehicle_collection.find({}, {'_id': 0}))

        return render_template('allVehicles.html',vehicles=vehicles)
    except Exception as e:
        return render_template('allVehicles.html', error= str(e))
    
@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    try:
        if 'username' not in session:
            return jsonify({'success': False, 'message': 'User not logged in'})

        # Get form data
        vehicleId = request.form['vehicleId']
        owner_name = request.form['ownerName']
        vehicle_brand = request.form['vehicleBrand']

        # Add username to the vehicle data
        vehicle_data = {
            'username': session['username'],
            'vehicleId': vehicleId,
            'owner_name': owner_name,
            'vehicle_brand': vehicle_brand
        }


        # Insert vehicle data into the database
        
        vehicle_collection.insert_one(vehicle_data)

        return jsonify({'success': True, 'message': 'Vehicle added successfully'})

    except Exception as ex:
        app.logger.error(f"Error adding vehicle: {ex}")
        return jsonify({'success': False, 'message': 'Error adding vehicle'})
    
@app.route('/allBookings')
def get_all_bookings():
    try:
        # Query all documents from the bookings collection
        bookings = list(bookings_collection.find({}, {'_id': 0}))

        return render_template('allBookings.html', bookings=bookings)
    except Exception as e:
        return render_template('allBookings.html', error=str(e))

@app.route('/allSlots', methods=['GET', 'POST'])
def allSlots():
    if request.method == 'POST':
        zone = request.form.get('zone')
        slots = list(bookings_collection.find({'zone': zone}, {'_id': 0}))
        return render_template('allSlots.html', zone=zone, slots=slots)
    return render_template('allSlots.html')
    
# Route to update employee details by name
@app.route('/update/user/<user_name>', methods=['PUT'])
def update_user_by_name(user_name):
    try:
        # Using a case-insensitive query to match employee name
        result = db.user.update_one(
            {"employee_name": {"$regex": f'^{user_name}$', "$options": 'i'}},
            {"$set": request.get_json()}
        )

        if result.modified_count > 0:
            return Response("User details updated successfully", status=200, mimetype='application/json')
        else:
            return Response("User not found", status=404, mimetype='application/json')

    except Exception as ex:
        app.logger.error(f"Error updating User details by name: {ex}")
        return Response("Internal Server Error", status=500, mimetype='application/json') 
      
@app.route('/')
def homePage():
    try:
        # Fetch all products from the database
        products_cursor = db.product.find()

        # Convert the cursor to a list of dictionaries
        products = list(products_cursor)

        return render_template('homePage.html', products=products)
    except Exception as ex:
        app.logger.error(f"Error fetching products: {ex}")
        flash('Error fetching products', 'error')
        return render_template('homePage.html', products=[])
    
    
@app.route('/profile')
def profile():
    try:
        # Check if the user is logged in
        if 'username' not in session:
            flash('User not logged in', 'error')
            return redirect(url_for('login'))
        
        # Fetch user details using the username stored in session
        username = session['username']
        user = user_collection.find_one({'username': username})
        
        if user:
            #Render the profile template with the user details
            return render_template('profile.html', user=user)
        
        flash('User details not found', 'error')
        return redirect(url_for('login'))
    
    except Exception as ex:
        app.logger.error(f"Error fetching user details: {ex}")
        flash('Error fetching user details', 'error')
        return redirect(url_for('login'))
  
@app.route('/select_user_type', methods=['POST'])
def select_user_type():
    user_type = request.form.get('userType')

    if user_type == 'admin':
        return redirect(url_for('login'))
    elif user_type == 'user':
        return redirect(url_for('login'))
    else:
        flash('Invalid user type selected', 'error')
        return redirect(url_for('index'))
    
@app.route('/slots')
def slots():
    # Your slots logic here
    username = session.get('username')
    
    return render_template('slots.html', username=username)

# Update the Flask route for handling login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Query MongoDB for admin details
        admin_user = users_collection.find_one({'username': username, 'password': password})

        if admin_user: 
            # Store admin credentials in the session
            session['username'] = username
            session['password'] = password

            return redirect(url_for('admin_panel'))
        else:
            # Query MongoDB for user details
            user_user = db.user.find_one({'username': username, 'password': password})

            if user_user:
                # Store user credentials in the session
                session['username'] = username
                session['password'] = password

                return redirect(url_for('slotsHomePage'))
            else:
                flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/slotsHomePage')
def slotsHomePage():
    # Your logic here
    username = session.get('username')
    return render_template('slotsHomePage.html', username=username)


# New route for employee details
@app.route('/user_details')
def user_details():
    # Check if user is authenticated as an employee
    try:
    # if 'username' in session and 'password' in session == 'employee':
        # Fetch employee details based on the stored credentials
        user = db.user.find_one({'username': session['username'], 'password': session['password']})

        if user:
            return render_template('user_details.html', user=user)
        else:
            flash('Unauthorized access', 'error')
            return redirect(url_for('login'))

    except Exception as ex:
        app.logger.error(f"Error fetching user data: {ex}")
        flash(f'Error fetching user data: {ex}', 'error')

    return render_template('user_details.html', user={})



# Route to render the update employee page
@app.route('/update_user/<user_name>', methods=['GET', 'POST'])
def update_user_page(user_name):
    try:
        # Fetch the employee details from the database using the employee name
        user = db.user.find_one({"user_name": {"$regex": f'^{user_name}$', "$options": 'i'}})

        if user:
            # Render the update employee page with the employee details
            return render_template('update_user.html', user=user)
        else:
            return Response("User not found", status=404, mimetype='application/json')

    except Exception as ex:
        app.logger.error(f"Error rendering update_user page: {ex}")
        return Response("Internal Server Error", status=500, mimetype='application/json')

# Route to handle the form submission for updating employee details
@app.route('/submit_update_user/<user_name>', methods=['POST'])
def submit_update_user(user_name):
    try:
        # Use the employee name parameter to identify the employee being updated
        user_name = user_name

        # Update the employee details in the database using request.form.to_dict()
        updated_user_data = request.form.to_dict()

        # Assuming you have a 'employee' collection in your MongoDB
        result = db.user.update_one(
            {"user_name": {"$regex": f'^{user_name}$', "$options": 'i'}},
            {"$set": request.form.to_dict()}
        )

        if result.modified_count > 0:
            flash('user details updated successfully', 'success')
        else:
            flash('user not found', 'error')

    except Exception as ex:
        app.logger.error(f"Error updating user details: {ex}")
        flash('Error updating user details', 'error')

    # Redirect to the admin page after the update
    return redirect(url_for('admin'))

# Route for admin panel
@app.route('/admin_homePage', methods=['GET', 'POST'])
def admin_panel():
    if 'username' in session and 'password' in session:
        # Check if the user is an admin
        admin_user = users_collection.find_one({'username': session['username'], 'password': session['password']})
        if admin_user:
            # Render the admin panel page
            return render_template('admin_homePage.html')
    
    # If user is not authenticated or not an admin, redirect to login page
    flash('Unauthorized access', 'error')
    return redirect(url_for('login'))

@app.route('/save_booking', methods=['POST'])
def save_booking():
    try:
        if 'username' not in session:
            return jsonify({'success': False, 'message': 'User not logged in'})

        # Get JSON data
        bookingData = request.json
        
        # Add username to the booking data
        bookingData['username'] = session['username']

        # Insert booking data into the database
        bookings_collection.insert_one(bookingData)
        

        return jsonify({'success': True, 'message': 'Booking successful'})

    except Exception as ex:
        app.logger.error(f"Error saving booking: {ex}")
        return jsonify({'success': False, 'message': 'Error saving booking'})

@app.route('/payment', methods=['POST'])
def payment():
    try:
        if 'username' not in session:
            flash('User not logged in', 'error')
            return redirect(url_for('login'))

        # Get payment data from the form
        cardType = request.form['cardType']
        cardName = request.form['cardName']
        cardNumber = request.form['cardNumber']
        expDate = request.form['expDate']
        cvv = request.form['cvv']

        # Your payment processing logic here

        flash('Payment processed successfully!', 'success')
        return redirect(url_for('bookings'))

    except Exception as ex:
        app.logger.error(f"Error processing payment: {ex}")
        flash('Error processing payment', 'error')
        return redirect(url_for('slots'))

  
if __name__ == '__main__':
    app.run(port=5000, debug=True)