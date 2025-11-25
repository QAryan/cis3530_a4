import os
from psycopg import sql, connect, IntegrityError
from flask import Flask, render_template, jsonify, request, flash, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash

# app initialization
app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for flash messages

# database config
DATABASE_CONFIG = {
    "dbname": "my_company",
    "user": "postgres",
    "password": os.environ.get("PSQL_PASS"), # set the enviornment variable PSQL_PASS to your password
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    conn = connect(**DATABASE_CONFIG)
    return conn

# GLOBAL VARIABLES
logged_in_user = None;

# ROUTES

# home route
@app.route("/")
def home():
    
    return render_template("home.html", 
                                 title="Home Page", 
                                 user=logged_in_user
                                 )

# projects route
@app.route("/projects")
def projects():
    
    return render_template("projects.html", 
                                 title="Projects Page", 
                                 user=logged_in_user
                                 )
    
# departments route
@app.route("/departments")
def departments():
    return render_template("departments.html", 
                                 title="Departments Page", 
                                 user=logged_in_user
                                 )
    
# employee management route
@app.route("/employee_management")
def employee_management():
    return render_template("management.html", 
                                 title="Employee Management Page", 
                                 user=logged_in_user
                                 )
    
# --- LOGIN AND REGISTER ---

# register user route
@app.route("/register", methods=["GET", "POST"])
def register_user():
    # if POST, register the user
    if request.method == "POST":
        # get form data
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        
        # validate form data
        if not username or not password:
            flash("Username and password are required!", "error")
            return render_template("register.html")
        
        try:
            
            # setup db
            conn = get_db_connection()
            cursor = conn.cursor() 
            
            # check username uniqueness
            check_query = "SELECT COUNT(*) FROM app_user WHERE username = %s;"
            cursor.execute(check_query, (username,))
            username_exists = cursor.fetchone()[0]
            
            if username_exists:
                flash("Username already exists!", "error")
                cursor.close()
                conn.close()
                return render_template("register.html")
            
            # Hash the password before storing it
            password_hash = generate_password_hash(password)
            
            # Insert new user into the users table
            insert_query = "INSERT INTO app_user (username, password_hash) VALUES (%s, %s);"
            cursor.execute(insert_query, (username, password_hash))
            
            # commit and close conn
            conn.commit()
            cursor.close()
            conn.close()
            
            flash("User registered successfully! You can now log in.", "success")
            return redirect(url_for("home"))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    elif request.method == "GET":
        # Display the form
        return render_template("register.html")
    
# login user route
@app.route("/login", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        # get form data
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        
        global logged_in_user
        
        # make sure we are not already logged in 
        if logged_in_user:
            flash("You are already logged in!", "error")
            return redirect(url_for("home"))
        
        if not username or not password:
            flash("Username and password are required!", "error")
            return render_template("login.html")
        
        try:
            # setup db
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # verify password correct
            query = "SELECT password_hash FROM app_user WHERE username = %s;"
            cursor.execute(query, (username,))
            result_user = cursor.fetchone()
                        
            if result_user and check_password_hash(result_user[0], password):
                flash("Login successful!", "success")
                
                logged_in_user = {"name": username,}
                
                cursor.close()
                conn.close()
                return redirect(url_for("home"))
            else:
                flash("Invalid username or password!", "error")
                cursor.close()
                conn.close()
                return render_template("login.html")
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    elif request.method == "GET":
        return render_template("login.html")
    
def get_logged_in_user():
    return logged_in_user

if __name__ == "__main__":
    app.run(debug=True)