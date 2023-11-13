from fastapi import FastAPI, Request, Form, HTTPException, Depends, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
from datetime import datetime
import hashlib
import json
import ZODB, ZODB.FileStorage
from BTrees.OOBTree import BTree
import transaction
import persistent
import re
storage = ZODB.FileStorage.FileStorage('database.fs')
db = ZODB.DB(storage)
connection = db.open()
root = connection.root
from fastapi import Depends

class Assignment(persistent.Persistent):
    def __init__(self, name, subject, due_date, detail):
        self.name = name
        self.subject = subject
        self.due_date = due_date
        self.detail = detail

class Student(persistent.Persistent):
	def __init__(self, email, password, edit):
		self.email = email
		self.password = password
		self.edit = edit

class Event(persistent.Persistent):
    def __init__(self, yyyymm, message):
        self.yyyymm = yyyymm
        self.events = [message]

root.students = BTree()
root.assignments = BTree()
root.events = BTree()

app = FastAPI()

templates = Jinja2Templates(directory="templates")



def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, email: str = Form(...), password: str = Form(...)):
    students = root.students
    if email in students:
        raise HTTPException(status_code=400, detail="Email already registered")
    if not re.match(r"[0-9]+@kmitl\.ac\.th", email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    hashed_password = hash_password(password)
    new_student = Student(email, hashed_password, False)
    students[email] = new_student
    transaction.commit()
    return RedirectResponse(url=f"/login", status_code=HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    students = root.students
    if email in students and students[email].password == hash_password(password):
        yyyymm = datetime.now().strftime("%Y%m")
        return RedirectResponse(url=f"/{email}/main/{yyyymm}", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect login"})

def is_logged_in(email: str = None):
    if email not in root.students:
        raise HTTPException(status_code=HTTP_303_SEE_OTHER, detail="/login")
    return root.students[email].email

@app.get("/{email}/main/{yyyymm}", response_class=HTMLResponse)
async def get_by_month(request: Request, yyyymm: str, email: str = Depends(is_logged_in)):
    if yyyymm in root.events:
        events = root.events[yyyymm]
    else:
        events = ["No upcoming events this month."]

    assignment_days = []
    for date, assignments_list in root.assignments.items():
        assignment_yyyymm = date[4:8] + date[2:4]
        if (assignment_yyyymm == yyyymm and assignments_list):
            assignment_days.append(int(date[:2]))
    return templates.TemplateResponse("main.html", {"request": request, "email": email, "events": events, "yyyymm": yyyymm, "assignment_days": assignment_days})

@app.get("/{email}/assignments/{date}", response_class=HTMLResponse)
async def get_assignments(request: Request, date: str, email: str = Depends(is_logged_in)):
    date_obj = datetime.strptime(date, "%d%m%Y")
    if date in root.assignments:
        assignments = root.assignments[date]
    else:
        assignments = []
    formatted_date = date_obj.strftime("%d / %B / %Y")
    return templates.TemplateResponse("assignment.html", {"request": request, "email": email, "assignments": assignments, "date": formatted_date})

@app.get("/add_assignment", response_class=HTMLResponse)
async def add_assignment_form(request: Request):
    return templates.TemplateResponse("add_assignment.html", {"request": request})

@app.post("/add_assignment", response_class=HTMLResponse)
async def add_assignment(request: Request, email: str = Form(...), password: str = Form(...), assignment_name: str = Form(...), subject: str = Form(...), due_date: str = Form(...), detail: str = Form(...)):
    students = root.students
    if email in students and students[email].password == hash_password(password):
        if due_date not in root.assignments:
            root.assignments[due_date] = []
        new_assignment = Assignment(assignment_name, subject, due_date, detail)
        root.assignments[due_date].append(new_assignment)
        transaction.commit()
        return RedirectResponse(url=f"/main/{email}", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect login"})

# @app.post("/main", response_class=HTMLResponse)
# async def main(request: Request, email: str = Form(...), password: str = Form(...)):
# 	students = root.students
# 	if email in students and students[email].password == hash_password(password):
# 		return RedirectResponse(url=f"/calendar/{email}", status_code=HTTP_302_FOUND)
# 	return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect login"})




# DO NOT TOUCH ANYTHING BELOW THIS LINE

@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin", response_class=HTMLResponse)
async def admin_login(request: Request, password: str = Form(...)):
    if password == "admin":
        return templates.TemplateResponse("admin.html", {"request": request})
    else:
        return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect password"})

@app.post("/admin_action", response_class=HTMLResponse)
async def admin_action(request: Request, action: str = Form(...), key: str = Form(...), value: str = Form(...)):
    if action == "add":
        root[key] = value
    elif action == "delete":
        del root[key]
    elif action == "update":
        root[key] = value 
    else:
        return templates.TemplateResponse("error.html", {"request": request, "error": "Invalid action"})
    transaction.commit()
    return RedirectResponse(url=f"/admin", status_code=HTTP_302_FOUND)

