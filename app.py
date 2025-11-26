import os
from psycopg import sql, connect, IntegrityError
from flask import Flask, render_template, jsonify, request, flash, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import projects

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
    department = request.args.get("department") or ""
    nameSearch = request.args.get("name") or ""
    sort_by = request.args.get("sort_by") or "full_name"
    sort_order = request.args.get("sort_order") or "asc"
    if department == "All":
        department = ""
    if sort_by == "total_hours":
       sort_by = "coalesce(total_hours,0)"
   # if sort_order not in ["asc", "desc"]:
   #     sort_order = "asc"
    
    query = f"""select concat(fname,' ',minit,'. ' ,lname) as full_name,
    dname as department,
    coalesce(number_of_dependents,0) as dependents,
   coalesce(number_of_projects,0),
    coalesce(total_hours,0)
    from employee
    left join
    (select essn, count(essn) as number_of_dependents
    from dependent
    group by(essn)
    having count(essn) >= 1) as d on employee.ssn = d.essn
    left join
    department on employee.dno = department.dnumber
    left join 
    (select essn, count(essn) as number_of_projects
    from works_on
    group by(essn)
    having count(essn) >= 1) as p on employee.ssn = p.essn
    left join
    (select essn, sum(hours) as total_hours
    from works_on
    group by(essn)) as h on h.essn = employee.ssn
    where department.dname like '%{department}%'
    and concat(fname,' ',minit,'. ' ,lname) ILIKE '%{nameSearch}%'
    ORDER BY {sort_by} {sort_order};"""
    
    departmentQuery = "select dname from department;"
    if logged_in_user is None:
        return redirect("/emptyHome")
    
     # setup db
   
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    employees = [
                    {"FullName": r[0], "Department": r[1], "Dependents": r[2], "Projects": r[3], "Hours": r[4]} for r in rows
                ]
    cursor.execute(departmentQuery)
    deptRows = cursor.fetchall()
    departments = [r[0] for r in deptRows]
    cursor.close()
    conn.close()
    
    return render_template("home.html", 
                                 title="Home Page", 
                                 user=logged_in_user,
                                    employees=employees,
                                    selected_department=department,
                                    departments=departments,
                                    name_search=nameSearch,
                                    sort_by=sort_by,
                                    sort_order=sort_order
                                 )
@app.route("/emptyHome")
def empty_home():
    return render_template("emptyHome.html", 
                                 title="Home Page", 
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

# --- PROJECTS ---

# projects list route
@app.route("/projects")
def projects_list():
    # Get sort parameter from query string (default to headcount DESC)
    sort_by = request.args.get('sort', 'headcount')
    order = request.args.get('order', 'DESC')
    
    # Validate and sanitize sort parameters
    sort_by, order = projects.validate_sort_parameters(sort_by, order)
    
    try:
        # setup db
        conn = get_db_connection()
        
        # Get all projects using the projects module
        projects_data = projects.get_all_projects(conn, sort_by, order)
        
        conn.close()
        
        return render_template("projects.html",
                             title="Projects",
                             projects=projects_data,
                             current_sort=sort_by,
                             current_order=order,
                             user=logged_in_user)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# project details route
@app.route("/projects/<int:project_id>")
def project_details(project_id):
    try:
        # setup db
        conn = get_db_connection()
        
        # Get project details using the projects module
        project_data = projects.get_project_details(conn, project_id)
        
        if not project_data:
            conn.close()
            flash("Project not found!", "error")
            return redirect(url_for("projects_list"))
        
        # Get employees assigned to this project
        employees_list = projects.get_project_employees(conn, project_id)
        
        conn.close()
        
        return render_template("project_details.html",
                             title=f"Project: {project_data['pname']}",
                             project=project_data,
                             employees=employees_list,
                             user=logged_in_user)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def get_logged_in_user():
    return logged_in_user

if __name__ == "__main__":
    app.run(debug=True)