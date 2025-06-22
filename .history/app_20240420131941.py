from flask import Flask, Response, request, render_template, jsonify, redirect, url_for, request, flash, session
import pymongo
import secrets
import json
from bson.objectid import ObjectId
from bson.json_util import dumps
from functools import wraps

app=Flask(__name__)
app.secret_key = secrets.token_hex(32)

try:
    mongo = pymongo.MongoClient(
        host = 'localhost',
        port = 27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo.ParkingManagementSystemDb #connect to mongodb1
    users_collection = db.admin
    user_collection = db["customer"]
    #cart_collection = db["cart"]
    mongo.server_info() #trigger exception if cannot connect to db
except:
    print("Error connecting to MongoDB")

@app.route('/get/admin', methods=['GET'])
def displayall():
  try:
    documents = db.admin.find()
    output = [{item: data[item] for item in data if item != '_id'} for data in documents]
    return jsonify(output)
  except Exception as ex:
    response = Response("Search Records Error!!",status=500,mimetype='application/json')
    return response

# Route for signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        if user_collection.find_one({'username': username}):
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))

        # Insert user data into databaseFF
        user_data = {'username': username, 'password': password}
        user_collection.insert_one(user_data)

        flash('Signup successful. You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')
    
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

# Route to get all employees
@app.route('/get/allusers', methods=['GET'])
def get_all_users():
    try:
        # Fetch all documents from the 'employee' collection
        documents = db.user.find()

        # Format the response excluding the _id field
        output = [{item: data[item] for item in data if item != '_id'} for data in documents]

        return jsonify(output)

    except Exception as ex:
        app.logger.error(f"Error retrieving all employees: {ex}")
        return Response("Internal Server Error", status=500, mimetype='application/json')   
      
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
    
# Flask route to render the profile page
@app.route('/profile')
def profile():
    try:
        # Assuming you have a collection named 'users' in your MongoDB
        # Fetch user details from the 'users' collection
        user = db.user.find_one({'username': session['username']})
        
        if user:
            # Render the profile template with the user details
            return render_template('profile.html', user=user)
        else:
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

                return redirect(url_for('user_details'))
            else:
                flash('Invalid username or password', 'error')

    return render_template('login.html')


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
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'username' in session and 'password' in session:
        # Check if the user is an admin
        admin_user = users_collection.find_one({'username': session['username'], 'password': session['password']})
        if admin_user:
            # Render the admin panel page
            return render_template('admin.html')
    
    # If user is not authenticated or not an admin, redirect to login page
    flash('Unauthorized access', 'error')
    return redirect(url_for('login'))

  
if __name__ == '__main__':
    app.run(port=5000, debug=True)