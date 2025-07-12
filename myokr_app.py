import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, date
import json
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# Database setup
def init_database():
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            department_id INTEGER,
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Organizations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Departments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            organization_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations (id)
        )
    ''')
    
    # Teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            department_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    ''')
    
    # OKRs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okrs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            objective TEXT NOT NULL,
            key_results TEXT NOT NULL,
            progress REAL DEFAULT 0,
            status TEXT DEFAULT 'Not Started',
            team_id INTEGER,
            assigned_user_id INTEGER,
            created_by INTEGER,
            start_date DATE,
            end_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id),
            FOREIGN KEY (assigned_user_id) REFERENCES users (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Authentication functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_user(username: str, email: str, password: str, role: str, department_id: int = None, team_id: int = None):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, department_id, team_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, hash_password(password), role, department_id, team_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, email, password_hash, role, department_id, team_id
        FROM users WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user[3]):
        return {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'role': user[4],
            'department_id': user[5],
            'team_id': user[6]
        }
    return None

# Database helper functions
def get_organizations():
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM organizations')
    orgs = cursor.fetchall()
    conn.close()
    return orgs

def get_departments(org_id: int = None):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    if org_id:
        cursor.execute('SELECT * FROM departments WHERE organization_id = ?', (org_id,))
    else:
        cursor.execute('SELECT * FROM departments')
    deps = cursor.fetchall()
    conn.close()
    return deps

def get_teams(department_id: int = None):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    if department_id:
        cursor.execute('SELECT * FROM teams WHERE department_id = ?', (department_id,))
    else:
        cursor.execute('SELECT * FROM teams')
    teams = cursor.fetchall()
    conn.close()
    return teams

def get_team_users(team_id: int):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role FROM users WHERE team_id = ?', (team_id,))
    users = cursor.fetchall()
    conn.close()
    return users

# OKR functions
def create_okr(title: str, description: str, objective: str, key_results: List[str], 
               team_id: int, assigned_user_id: int, created_by: int, start_date: date, end_date: date):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO okrs (title, description, objective, key_results, team_id, 
                         assigned_user_id, created_by, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, objective, json.dumps(key_results), team_id, 
          assigned_user_id, created_by, start_date, end_date))
    
    conn.commit()
    conn.close()

def get_okrs(team_id: int = None, user_id: int = None):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    if team_id:
        cursor.execute('''
            SELECT o.*, u.username as assigned_user, c.username as created_by_user, t.name as team_name
            FROM okrs o
            LEFT JOIN users u ON o.assigned_user_id = u.id
            LEFT JOIN users c ON o.created_by = c.id
            LEFT JOIN teams t ON o.team_id = t.id
            WHERE o.team_id = ?
        ''', (team_id,))
    elif user_id:
        cursor.execute('''
            SELECT o.*, u.username as assigned_user, c.username as created_by_user, t.name as team_name
            FROM okrs o
            LEFT JOIN users u ON o.assigned_user_id = u.id
            LEFT JOIN users c ON o.created_by = c.id
            LEFT JOIN teams t ON o.team_id = t.id
            WHERE o.assigned_user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT o.*, u.username as assigned_user, c.username as created_by_user, t.name as team_name
            FROM okrs o
            LEFT JOIN users u ON o.assigned_user_id = u.id
            LEFT JOIN users c ON o.created_by = c.id
            LEFT JOIN teams t ON o.team_id = t.id
        ''')
    
    okrs = cursor.fetchall()
    conn.close()
    return okrs

def update_okr_progress(okr_id: int, progress: float, status: str):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE okrs SET progress = ?, status = ? WHERE id = ?
    ''', (progress, status, okr_id))
    
    conn.commit()
    conn.close()

def delete_okr(okr_id: int):
    conn = sqlite3.connect('myokr.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM okrs WHERE id = ?', (okr_id,))
    conn.commit()
    conn.close()

# Initialize session state
def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None

# Main application
def main():
    st.set_page_config(
        page_title="MyOKR - Modern OKR Management",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .okr-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    init_database()
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    st.markdown('<div class="main-header"><h1 style="color: white; text-align: center;">🎯 MyOKR - Modern OKR Management</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to Your Account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        st.subheader("Create New Account")
        new_username = st.text_input("Username", key="reg_username")
        new_email = st.text_input("Email", key="reg_email")
        new_password = st.text_input("Password", type="password", key="reg_password")
        role = st.selectbox("Role", ["User", "Team Lead", "Manager", "Admin"], key="reg_role")
        
        if st.button("Register", key="register_btn"):
            if create_user(new_username, new_email, new_password, role):
                st.success("Account created successfully! Please login.")
            else:
                st.error("Username or email already exists")

def show_main_app():
    st.markdown('<div class="main-header"><h1 style="color: white; text-align: center;"> My OKR Dashboard</h1></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.user['username']}!")
        st.markdown(f"**Role:** {st.session_state.user['role']}")
        
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
        
        st.markdown("---")
        
        # Navigation
        page = st.selectbox("Navigate", [
            "Dashboard",
            "My OKRs",
            "Team OKRs",
            "Organization Setup",
            "Analytics"
        ])
    
    # Main content
    if page == "Dashboard":
        show_dashboard()
    elif page == "My OKRs":
        show_my_okrs()
    elif page == "Team OKRs":
        show_team_okrs()
    elif page == "Organization Setup":
        show_organization_setup()
    elif page == "Analytics":
        show_analytics()

def show_dashboard():
    st.markdown("##  Dashboard Overview")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get user's OKRs
    user_okrs = get_okrs(user_id=st.session_state.user['id'])
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("My OKRs", len(user_okrs))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        completed_okrs = len([okr for okr in user_okrs if okr[6] == 'Completed'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Completed", completed_okrs)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        in_progress_okrs = len([okr for okr in user_okrs if okr[6] == 'In Progress'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("In Progress", in_progress_okrs)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        if user_okrs:
            avg_progress = sum([okr[5] for okr in user_okrs]) / len(user_okrs)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Avg Progress", f"{avg_progress:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Avg Progress", "0%")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent OKRs
    st.markdown("###  Recent OKRs")
    if user_okrs:
        for okr in user_okrs[:3]:  # Show last 3 OKRs
            with st.container():
                st.markdown('<div class="okr-card">', unsafe_allow_html=True)
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{okr[1]}**")  # title
                    st.markdown(f"*{okr[3]}*")   # objective
                    st.progress(okr[5] / 100)    # progress
                
                with col2:
                    st.markdown(f"**Status:** {okr[6]}")
                    st.markdown(f"**Progress:** {okr[5]:.1f}%")
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No OKRs found. Create your first OKR in the 'My OKRs' section!")

def show_my_okrs():
    st.markdown("## My OKRs")
    
    # Create new OKR
    with st.expander("Create New OKR"):
        title = st.text_input("OKR Title")
        description = st.text_area("Description")
        objective = st.text_area("Objective")
        
        # Key Results
        st.markdown("**Key Results:**")
        key_results = []
        for i in range(3):
            kr = st.text_input(f"Key Result {i+1}", key=f"kr_{i}")
            if kr:
                key_results.append(kr)
        
        # Team selection
        teams = get_teams()
        if teams:
            team_options = {team[1]: team[0] for team in teams}
            selected_team = st.selectbox("Select Team", list(team_options.keys()))
            
            # User selection
            if selected_team:
                team_users = get_team_users(team_options[selected_team])
                if team_users:
                    user_options = {user[1]: user[0] for user in team_users}
                    selected_user = st.selectbox("Assign to User", list(user_options.keys()))
                else:
                    st.warning("No users found in selected team")
                    selected_user = None
            else:
                selected_user = None
        else:
            st.warning("No teams available. Please create a team first.")
            selected_team = None
            selected_user = None
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today())
        with col2:
            end_date = st.date_input("End Date")
        
        if st.button("Create OKR"):
            if title and objective and key_results and selected_team and selected_user:
                create_okr(
                    title, description, objective, key_results,
                    team_options[selected_team], user_options[selected_user],
                    st.session_state.user['id'], start_date, end_date
                )
                st.success("OKR created successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields")
    
    # Display existing OKRs
    st.markdown("### Your OKRs")
    user_okrs = get_okrs(user_id=st.session_state.user['id'])
    
    if user_okrs:
        for okr in user_okrs:
            with st.container():
                st.markdown('<div class="okr-card">', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"### {okr[1]}")
                    st.markdown(f"**Objective:** {okr[3]}")
                    
                    key_results = json.loads(okr[4])
                    st.markdown("**Key Results:**")
                    for i, kr in enumerate(key_results, 1):
                        st.markdown(f"  {i}. {kr}")
                
                with col2:
                    st.markdown(f"**Status:** {okr[6]}")
                    st.markdown(f"**Team:** {okr[13]}")
                    st.markdown(f"**Progress:** {okr[5]:.1f}%")
                    st.progress(okr[5] / 100)
                
                with col3:
                    # Update progress
                    new_progress = st.slider(
                        "Update Progress", 
                        0, 100, 
                        int(okr[5]), 
                        key=f"progress_{okr[0]}"
                    )
                    
                    new_status = st.selectbox(
                        "Status",
                        ["Not Started", "In Progress", "Completed", "On Hold"],
                        index=["Not Started", "In Progress", "Completed", "On Hold"].index(okr[6]),
                        key=f"status_{okr[0]}"
                    )
                    
                    if st.button("Update", key=f"update_{okr[0]}"):
                        update_okr_progress(okr[0], new_progress, new_status)
                        st.success("OKR updated!")
                        st.rerun()
                    
                    if st.button("Delete", key=f"delete_{okr[0]}"):
                        delete_okr(okr[0])
                        st.success("OKR deleted!")
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No OKRs found. Create your first OKR above!")

def show_team_okrs():
    st.markdown("## Team OKRs")
    
    if st.session_state.user['team_id']:
        team_okrs = get_okrs(team_id=st.session_state.user['team_id'])
        
        if team_okrs:
            for okr in team_okrs:
                with st.container():
                    st.markdown('<div class="okr-card">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"### {okr[1]}")
                        st.markdown(f"**Assigned to:** {okr[11]}")
                        st.markdown(f"**Objective:** {okr[3]}")
                        
                        key_results = json.loads(okr[4])
                        st.markdown("**Key Results:**")
                        for i, kr in enumerate(key_results, 1):
                            st.markdown(f"  {i}. {kr}")
                    
                    with col2:
                        st.markdown(f"**Status:** {okr[6]}")
                        st.markdown(f"**Progress:** {okr[5]:.1f}%")
                        st.progress(okr[5] / 100)
                        
                        # Show dates
                        st.markdown(f"**Start:** {okr[9]}")
                        st.markdown(f"**End:** {okr[10]}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No team OKRs found.")
    else:
        st.warning("You are not assigned to any team.")

def show_organization_setup():
    st.markdown("## Organization Setup")
    
    # Only allow admins to manage organization
    if st.session_state.user['role'] != 'Admin':
        st.error("Only administrators can manage organization structure.")
        return
    
    tab1, tab2, tab3 = st.tabs(["Organizations", "Departments", "Teams"])
    
    with tab1:
        st.subheader("Organizations")
        
        # Create organization
        with st.expander("Create New Organization"):
            org_name = st.text_input("Organization Name")
            org_description = st.text_area("Description")
            
            if st.button("Create Organization"):
                if org_name:
                    conn = sqlite3.connect('myokr.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO organizations (name, description)
                        VALUES (?, ?)
                    ''', (org_name, org_description))
                    conn.commit()
                    conn.close()
                    st.success("Organization created successfully!")
                    st.rerun()
        
        # Display organizations
        orgs = get_organizations()
        if orgs:
            for org in orgs:
                st.markdown(f"**{org[1]}** - {org[2] or 'No description'}")
    
    with tab2:
        st.subheader("Departments")
        
        # Create department
        with st.expander("Create New Department"):
            dept_name = st.text_input("Department Name")
            dept_description = st.text_area("Description", key="dept_desc")
            
            orgs = get_organizations()
            if orgs:
                org_options = {org[1]: org[0] for org in orgs}
                selected_org = st.selectbox("Select Organization", list(org_options.keys()))
                
                if st.button("Create Department"):
                    if dept_name and selected_org:
                        conn = sqlite3.connect('myokr.db')
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO departments (name, description, organization_id)
                            VALUES (?, ?, ?)
                        ''', (dept_name, dept_description, org_options[selected_org]))
                        conn.commit()
                        conn.close()
                        st.success("Department created successfully!")
                        st.rerun()
        
        # Display departments
        deps = get_departments()
        if deps:
            for dept in deps:
                st.markdown(f"**{dept[1]}** - {dept[2] or 'No description'}")
    
    with tab3:
        st.subheader("Teams")
        
        # Create team
        with st.expander("Create New Team"):
            team_name = st.text_input("Team Name")
            team_description = st.text_area("Description", key="team_desc")
            
            deps = get_departments()
            if deps:
                dept_options = {dept[1]: dept[0] for dept in deps}
                selected_dept = st.selectbox("Select Department", list(dept_options.keys()))
                
                if st.button("Create Team"):
                    if team_name and selected_dept:
                        conn = sqlite3.connect('myokr.db')
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO teams (name, description, department_id)
                            VALUES (?, ?, ?)
                        ''', (team_name, team_description, dept_options[selected_dept]))
                        conn.commit()
                        conn.close()
                        st.success("Team created successfully!")
                        st.rerun()
        
        # Display teams
        teams = get_teams()
        if teams:
            for team in teams:
                st.markdown(f"**{team[1]}** - {team[2] or 'No description'}")

def show_analytics():
    st.markdown("## Analytics Dashboard")
    
    # Get all OKRs for analytics
    all_okrs = get_okrs()
    
    if not all_okrs:
        st.info("No OKRs available for analytics.")
        return
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(all_okrs, columns=[
        'id', 'title', 'description', 'objective', 'key_results', 'progress',
        'status', 'team_id', 'assigned_user_id', 'created_by', 'start_date',
        'end_date', 'created_at', 'assigned_user', 'created_by_user', 'team_name'
    ])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Progress distribution
        st.subheader("Progress Distribution")
        progress_bins = pd.cut(df['progress'], bins=[0, 25, 50, 75, 100], 
                              labels=['0-25%', '26-50%', '51-75%', '76-100%'])
        progress_counts = progress_bins.value_counts()
        
        fig = px.pie(values=progress_counts.values, names=progress_counts.index,
                     title="OKR Progress Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Status distribution
        st.subheader("Status Distribution")
        status_counts = df['status'].value_counts()
        
        fig = px.bar(x=status_counts.index, y=status_counts.values,
                     title="OKR Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    # Team performance
    st.subheader("Team Performance")
    team_stats = df.groupby('team_name').agg({
        'progress': 'mean',
        'id': 'count'
    }).round(2)
    team_stats.columns = ['Average Progress', 'Total OKRs']
    
    fig = px.bar(x=team_stats.index, y=team_stats['Average Progress'],
                 title="Average Progress by Team")
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.subheader("Detailed OKR Table")
    display_df = df[['title', 'objective', 'progress', 'status', 'assigned_user', 'team_name']]
    st.dataframe(display_df, use_container_width=True)

if __name__ == "__main__":
    main()