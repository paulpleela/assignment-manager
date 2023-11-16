from fastapi import FastAPI, Request, Form, HTTPException, Depends, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
from datetime import datetime
import hashlib
import json
import ZODB, ZODB.FileStorage
from BTrees.OOBTree import BTree
import transaction
import persistent
from persistent.list import PersistentList
import re
import uuid
storage = ZODB.FileStorage.FileStorage('database.fs')
db = ZODB.DB(storage)
connection = db.open()
root = connection.root

class Assignment(persistent.Persistent):
    def __init__(self, name, subject, due_date, content):
        self.name = name
        self.subject = subject
        self.due_date = due_date
        self.content = content
        self.forum = BTree()
    
    def add_message(self, comment, user, reply_user=None):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]
        new_message = Message(comment, user, time, reply_user)
        self.forum[time] = new_message


class Message(persistent.Persistent):
    def __init__(self, comment, user, time, reply_user=None):
        self.reply_user = reply_user
        self.comment = comment
        self.user = user
        self.time = time


class Student(persistent.Persistent):
	def __init__(self, email, password, edit):
		self.email = email
		self.password = password
		self.edit = edit

class Event(persistent.Persistent):
    def __init__(self, yyyymm, message):
        self.yyyymm = yyyymm
        self.events = PersistentList([message])

class LoginHistory(persistent.Persistent):
    def __init__(self, email, password, ip_address):
        self.time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.ip_address = ip_address

root.students = BTree()
root.assignments = BTree()
root.events = BTree()
root.login_history = BTree()

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
		ip_address = request.client.host
		root.login_history[email] = LoginHistory(email, password, ip_address)
		transaction.commit()
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
        assignment_yyyymm = date[:7]
        if (assignment_yyyymm == yyyymm and assignments_list):
            assignment_days.append(int(date[-2:]))
    return templates.TemplateResponse("main.html", {"request": request, "email": email, "events": events, "yyyymm": yyyymm, "assignment_days": assignment_days})

@app.get("/{email}/assignments/{date}", response_class=HTMLResponse)
async def get_assignments(request: Request, date: str, email: str = Depends(is_logged_in)):
    assignments = []
    if date in root.assignments:
        for assignment in root.assignments[date]:
            assignments.append({"subject": assignment.subject, "name": assignment.name})
    return templates.TemplateResponse("assignment.html", {"request": request, "email": email, "assignments": assignments, "date": date})

@app.get("/{email}/assignments/{date}/{assignment_index}", response_class=HTMLResponse)
async def get_assignment(request: Request, date: str, assignment_index: int, email: str = Depends(is_logged_in)):
    assignments = []
    if date in root.assignments:
        for assignment in root.assignments[date]:
            assignments.append({"subject": assignment.subject, "name": assignment.name})
    assignment_obj = root.assignments[date][assignment_index]
    return templates.TemplateResponse("forum.html", {"request": request, "email": email, "assignments": assignments,  "date": date, "assignment": assignment_obj})

@app.post("/{email}/assignments/{date}/{assignment_index}", response_class=HTMLResponse)
async def add_forum_msg(request: Request, date: str, assignment_index: int, email: str = Depends(is_logged_in), reply_user: str = Form(None), comment: str = Form(...)):
    assignments = []
    if date in root.assignments:
        for assignment in root.assignments[date]:
            assignments.append({"subject": assignment.subject, "name": assignment.name})
    
    assignment_obj = root.assignments[date][assignment_index]
    assignment_obj.add_message(comment, email, reply_user)
    transaction.commit()
    return templates.TemplateResponse("forum.html", {"request": request, "email": email, "assignments": assignments,  "date": date, "assignment": assignment_obj})

@app.get("/add_assignment", response_class=HTMLResponse)
async def add_assignment_form(request: Request):
    return templates.TemplateResponse("admin_assignment.html", {"request": request})

@app.post("/add_assignment", response_class=HTMLResponse)
async def add_assignment(request: Request, email: str = Form(...), password: str = Form(...), assignment_name: str = Form(...), subject: str = Form(...), due_date: str = Form(...), content: str = Form(...)):
    students = root.students
    if email in students and students[email].password == hash_password(password):
        if due_date not in root.assignments:
            root.assignments[due_date] = PersistentList()
        new_assignment = Assignment(assignment_name, subject, due_date, content)
        root.assignments[due_date].append(new_assignment)
        transaction.commit()
        return RedirectResponse(url=f"/{email}/main/{due_date}", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect login"})


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    unique_filename = str(uuid.uuid4()) + "_" + file.filename
    with open(unique_filename, "wb") as buffer:
        buffer.write(await file.read())
    return {"filename": unique_filename}

@app.get("/downloadfile/{filename}")
async def main(filename: str):
    return FileResponse(filename)
	
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
		students = {email: student.__dict__ for email, student in root.students.items()}
		assignments = {name: assignment.__dict__ for name, assignment in root.assignments.items()}
		events = {yyyymm: event.__dict__ for yyyymm, event in root.events.items()}
		logs = {email: log.__dict__ for email, log in root.login_history.items()}
		
		data = {
			"Students": students,
			"Assignments": assignments,
			"Event" : events,
			"Logs": logs
		}
		return templates.TemplateResponse("admin_page.html", {"request": request, "data": data})
	else:
		return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect password"})

@app.post("/admin/log", response_class=HTMLResponse)
async def admin_log(request: Request, email: str = Form(...)):
	if email not in root.students:
		return templates.TemplateResponse("error.html", {"request": request, "error": "Invalid email"})
	logs = [log.__dict__ for log in root.login_history if log.email == email]
	return templates.TemplateResponse("admin_log.html", {"request": request, "logs": logs})

@app.post("/admin_action", response_class=HTMLResponse)
async def admin_action(request: Request, action: str = Form(...), key: str = Form(...), value: str = Form(...)):
	if action == "Delete":
		del root.students[key]
	elif action == "Update":
		args : dict = eval(value) # Danger!!!
		root.students[args['email']] = Student(args['email'], args['password'], args['edit'])
		del root.students[key]
	elif action == "Create":
		args : dict = eval(value)
		root.students[args['email']] = Student(args['email'], args['password'], args['edit'])
	else:
		return templates.TemplateResponse("error.html", {"request": request, "error": "Invalid action"})
	transaction.commit()

	students = {email: student.__dict__ for email, student in root.students.items()}
	assignments = {name: assignment.__dict__ for name, assignment in root.assignments.items()}
	events = {yyyymm: event.__dict__ for yyyymm, event in root.events.items()}

	data = {
		"Students": students,
		"Assignments": assignments,
		"Event" : events
	}
	return templates.TemplateResponse("admin_page.html", {"request": request, "data": data})
