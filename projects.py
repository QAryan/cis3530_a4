from psycopg import sql

def get_all_projects(conn, sort_by='headcount', order='DESC'):

    cursor = conn.cursor()
    
    # Query using the AllProjectsWithHeadcount view with dynamic sorting
    query = sql.SQL("""
        SELECT 
            p.Pnumber,
            p.Pname,
            d.Dname AS department_name,
            p.headcount,
            p.total_hours
        FROM AllProjectsWithHeadcount p
        JOIN Department d ON d.Dnumber = p.Dnum
        ORDER BY {sort_column} {order}
    """).format(
        sort_column=sql.Identifier(sort_by),
        order=sql.SQL(order)
    )
    
    cursor.execute(query)
    projects = cursor.fetchall()
    
    # Convert to list of dictionaries for easier template access
    projects_list = []
    for project in projects:
        projects_list.append({
            'pnumber': project[0],
            'pname': project[1],
            'department_name': project[2],
            'headcount': project[3],
            'total_hours': float(project[4])
        })
    
    cursor.close()
    return projects_list


def get_project_details(conn, project_id):

    cursor = conn.cursor()
    
    # Get project details
    query = """
        SELECT 
            p.Pnumber,
            p.Pname,
            p.Plocation,
            d.Dname AS department_name,
            apwh.headcount,
            apwh.total_hours
        FROM Project p
        JOIN Department d ON d.Dnumber = p.Dnum
        JOIN AllProjectsWithHeadcount apwh ON apwh.Pnumber = p.Pnumber
        WHERE p.Pnumber = %s
    """
    cursor.execute(query, (project_id,))
    project = cursor.fetchone()
    
    cursor.close()
    
    if not project:
        return None
    
    project_data = {
        'pnumber': project[0],
        'pname': project[1],
        'plocation': project[2],
        'department_name': project[3],
        'headcount': project[4],
        'total_hours': float(project[5])
    }
    
    return project_data


def get_project_employees(conn, project_id):
    
    cursor = conn.cursor()
    
    # Get employees assigned to this project
    query = """
        SELECT 
            e.Ssn,
            e.Fname,
            e.Lname,
            w.Hours
        FROM Employee e
        JOIN Works_On w ON w.Essn = e.Ssn
        WHERE w.Pno = %s
        ORDER BY e.Lname, e.Fname
    """
    cursor.execute(query, (project_id,))
    employees = cursor.fetchall()
    
    employees_list = []
    for emp in employees:
        employees_list.append({
            'ssn': emp[0],
            'fname': emp[1],
            'lname': emp[2],
            'hours': float(emp[3])
        })
    
    cursor.close()
    return employees_list


def validate_sort_parameters(sort_by, order):
    
    # Whitelist: only allow sorting by headcount or total_hours
    allowed_sorts = ['headcount', 'total_hours']
    allowed_orders = ['ASC', 'DESC']
    
    if sort_by not in allowed_sorts:
        sort_by = 'headcount'
    if order.upper() not in allowed_orders:
        order = 'DESC'
    
    return sort_by, order.upper()
