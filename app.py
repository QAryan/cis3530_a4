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
       sort_by = "total_hours"
   # if sort_order not in ["asc", "desc"]:
   #     sort_order = "asc"
    
    query = sql.SQL("""select concat(fname,' ',minit,'. ' ,lname) as full_name,
    dname as department,
    coalesce(number_of_dependents,0) as dependents,
   coalesce(number_of_projects,0),
    coalesce(total_hours,0) as total_hours
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
    where department.dname like {department}
    and concat(fname,' ',minit,'. ' ,lname) ILIKE {nameSearch}
    ORDER BY {sort_by} {sort_order};""").format(
        sort_by=sql.Identifier(sort_by),
        sort_order=sql.SQL(sort_order.upper()),
        department=sql.Literal(f"%{department}%"),
        nameSearch=sql.Literal(f"%{nameSearch}%") )
    
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
    if sort_by == "coalesce(total_hours,0)":
       sort_by = "total_hours"
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
    if logged_in_user is None:
        return redirect("/emptyHome")
    deptQuery = """
    select 
    dname,
    dnumber,
    CASE
        WHEN concat(fname,' ',minit,'. ' ,lname) = ' . ' THEN 'N/A'
        ELSE concat(fname,' ',minit,'. ' ,lname)
        END AS full_name,
    number_of_employees,
    coalesce(total.total_hours,0)
    from department
    left join employee
    on department.mgr_ssn = employee.ssn
    left join
    (select dno, count(dno) as number_of_employees
    from employee
    group by(dno)
    having count(dno) >= 1) as e on department.dnumber = e.dno
    left join
    (select sum(hours)as total_hours, dnum from
    (select hours,dnum,dname from works_on as w
    left join project as p on w.pno =p.pnumber
    left join department as d on p.dnum = d.dnumber)
    group by dnum) as total on total.dnum = department.dnumber"""
    # setup db
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(deptQuery)
    rows = cursor.fetchall()
    departments = [
                    {"Dname": r[0], "Dnumber": r[1], "MgrName": r[2], "NumEmployees": r[3], "TotalHours": r[4]} for r in rows
                ]
    cursor.close()
    conn.close()

    return render_template("departments.html", 
                                 title="Departments Page", 
                                 user=logged_in_user,
                                    departments=departments
                                 )
    
# --- EMPLOYEEE MANAGEMENT ---

# employee management routes
@app.route("/employee_management")
def employee_management():
    if logged_in_user is None:
        return redirect("/emptyHome")
    
    department = request.args.get("department") or ""
    nameSearch = request.args.get("name") or ""
    sort_by = request.args.get("sort_by") or "full_name"
    sort_order = request.args.get("sort_order") or "asc"
    
    if department == "All":
        department = ""
    if sort_by == "total_hours":
       sort_by = "total_hours"
       
    employee_query = sql.SQL("""select concat(fname,' ',minit,'. ' ,lname) as full_name,
    dname as department,
    coalesce(number_of_dependents,0) as dependents,
    coalesce(number_of_projects,0),
    coalesce(total_hours,0) as total_hours,
    ssn
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
    where department.dname like {department}
    and concat(fname,' ',minit,'. ' ,lname) ILIKE {nameSearch}
    ORDER BY {sort_by} {sort_order};""").format(
        sort_by=sql.Identifier(sort_by),
        sort_order=sql.SQL(sort_order.upper()),
        department=sql.Literal(f"%{department}%"),
        nameSearch=sql.Literal(f"%{nameSearch}%") )
    
    departmentQuery = "select dname from department;"
    if logged_in_user is None:
        return redirect("/emptyHome")
    
     # setup db
   
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(employee_query)
    rows = cursor.fetchall()
    employees = [
                    {"FullName": r[0], "Department": r[1], "Dependents": r[2], "Projects": r[3], "Hours": r[4], "ssn": r[5]} for r in rows
                ]
    cursor.execute(departmentQuery)
    deptRows = cursor.fetchall()
    departments = [r[0] for r in deptRows]
    cursor.close()
    conn.close()
    
    if sort_by == "coalesce(total_hours,0)":
         sort_by = "total_hours"
    
    return render_template("management.html", 
                                    title="Employee Management",
                                    user=logged_in_user,
                                    employees=employees,
                                    selected_department=department,
                                    departments=departments,
                                    name_search=nameSearch,
                                    sort_by=sort_by,
                                    sort_order=sort_order
                                 )
    
@app.route("/employee_management/add", methods=["GET", "POST"])
def add_employee():
    # if POST, try adding the employee
    if request.method == "POST":
        #get form data (there is a lot)
        fname = request.form["fname"].strip()
        minit = request.form["minit"].strip()
        lname = request.form["lname"].strip()
        ssn = request.form["ssn"].strip()
        address = request.form["address"].strip()
        sex = request.form["sex"].strip()
        salary = request.form["salary"].strip()
        super_ssn = request.form["super_ssn"].strip()
        dno = request.form["dno"].strip()
        bdate = request.form["bdate"].strip()
        empdate = request.form["empdate"].strip()
        
        # validate form data
        if not fname or not minit or not lname or not ssn or not address or not sex or not salary or not dno or not bdate or not empdate:
            flash("All fields are required!", "error")
            return render_template("add_employee.html")
        
        try:
            # setup db
            conn = get_db_connection()
            cursor = conn.cursor() 
            
            # check ssn is unique
            unique_ssn_query = "SELECT COUNT(*) FROM employee WHERE ssn = %s;"
            cursor.execute(unique_ssn_query, (ssn,))
            ssn_exists = cursor.fetchone()[0]
            
            if ssn_exists:
                flash("SSN already exists!", "error")
                cursor.close()
                conn.close()
                return render_template("add_employee.html")
            
            # check supervisor exists
            if super_ssn:
                supervisor_query = "SELECT COUNT(*) FROM employee WHERE ssn = %s;"
                cursor.execute(supervisor_query, (super_ssn,))
                supervisor_exists = cursor.fetchone()[0]
                
                if not supervisor_exists:
                    flash("Supervisor SSN does not exist!", "error")
                    cursor.close()
                    conn.close()
                    return render_template("add_employee.html")
                
            # check department exists
            department_query = "SELECT COUNT(*) FROM department WHERE dnumber = %s;"
            cursor.execute(department_query, (dno,))
            department_exists = cursor.fetchone()[0]
            if not department_exists:
                flash("Department number does not exist!", "error")
                cursor.close()
                conn.close()
                return render_template("add_employee.html")
            
            # insert new employee into the employee table
            insert_query = """INSERT INTO Employee
            (Fname, Minit, Lname, Ssn, Address, Sex, Salary, Super_ssn, Dno, BDate, EmpDate)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            cursor.execute(insert_query, 
                           (fname, minit, lname, ssn, address, sex, 
                            salary, super_ssn if super_ssn else None, 
                            dno, bdate, empdate))
            
            # commit and close conn
            conn.commit()
            cursor.close()
            conn.close()
            flash("Employee added successfully!", "success")
            return redirect(url_for("employee_management"))
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif request.method == "GET":
        return render_template("add_employee.html")

@app.route("/employee_management/edit/<ssn>", methods=["GET", "POST"])
def edit_employee(ssn):
    if logged_in_user is None:
        return redirect("/emptyHome")
    
    
    
    if request.method == "POST":
        # get form data
        address = request.form["address"].strip()
        salary = request.form["salary"].strip()
        dno = request.form["dno"].strip()
        
        # validate form data
        if not address or not salary or not dno:
            flash("All fields are required!", "error")
            return redirect(url_for("edit_employee", ssn=ssn))
        try:
            # setup db
            conn = get_db_connection()
            cursor = conn.cursor() 
            
            # check department exists
            department_query = "SELECT COUNT(*) FROM department WHERE dnumber = %s;"
            cursor.execute(department_query, (dno,))
            department_exists = cursor.fetchone()[0]
            
            if not department_exists:
                flash("Department number does not exist!", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("edit_employee", ssn=ssn))
            
            # update employee info
            update_query = """UPDATE Employee
                              SET Address = %s,Salary = %s,DNo = %s
                              WHERE ssn = %s;"""
            cursor.execute(update_query, (address, salary, dno, ssn))
            
            # commit and close conn
            conn.commit()
            cursor.close()
            conn.close()
            flash("Employee info updated successfully!", "success")
            return redirect(url_for("employee_management"))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        # update values from form
    elif request.method == "GET":
        # setup db
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # get employee info
        employee_query = "SELECT FName, MInit, LName, ssn, Address, Salary, Dno FROM Employee WHERE ssn = %s;"
        cursor.execute(employee_query, (ssn,))
        employee = cursor.fetchone()
        
        if not employee:
            flash("Employee not found!", "error")
            cursor.close()
            conn.close()
            return redirect(url_for("employee_management"))
        
        employee_data = {
            'FName': employee[0],
            'MInit': employee[1],
            'LName': employee[2],
            'ssn': employee[3],
            'Address': employee[4],
            'Salary': int(employee[5]),
            'Dno': employee[6]
            }
                        
        # close conn
        cursor.close()
        conn.close()
        
    return render_template("edit_employee.html", employee=employee_data)

@app.route("/employee_management/delete/<ssn>", methods=["POST", "GET"])
def delete_employee(ssn):
    if logged_in_user is None:
        return redirect("/emptyHome")
    
    try:
        # setup db
        conn = get_db_connection()
        cursor = conn.cursor() 
        
        # delete employee from the employee table
        delete_query = "DELETE FROM Employee WHERE ssn = %s;"
        cursor.execute(delete_query, (ssn,))
        
        # commit and close conn
        conn.commit()
        cursor.close()
        conn.close()
        flash("Employee deleted successfully!", "success")
    except IntegrityError:
        cursor.close()
        conn.close()
        flash("Cannot delete employee: They are still assigned to projects, have dependents, or a supervisor/manager.", "error")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return redirect(url_for("employee_management"))
    
    
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
    if logged_in_user is None:
        return redirect("/emptyHome")
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
    if logged_in_user is None:
        return redirect("/emptyHome")
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
    
@app.route("/logout")
def logout():
    global logged_in_user
    logged_in_user = None
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

def get_logged_in_user():
    return logged_in_user

if __name__ == "__main__":
    app.run(debug=True)