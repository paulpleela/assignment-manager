from fastapi import FastAPI, Request, Form, HTTPException, Depends, Body, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_303_SEE_OTHER
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
	def __init__(self, name, subject, due_date, content, posted_by, edu_year):
		self.name = name
		self.subject = subject
		self.due_date = due_date
		self.content = content
		self.forum = BTree()
		self.posted_by = posted_by
		self.edu_year = edu_year
    
	def add_message(self, comment, user, reply_user=None, filename=None):
		time = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]
		new_message = Message(comment, user, time, reply_user, filename)
		self.forum[time] = new_message


class Message(persistent.Persistent):
    def __init__(self, comment, user, time, reply_user=None, filename=None):
        self.reply_user = reply_user
        self.comment = comment
        self.user = user
        self.time = time
        self.filename = filename


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
	def __init__(self, email, ip_address):
		self.time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
		self.email = email
		#self.password = password
		self.ip_address = ip_address


if not hasattr(root, 'students'):
    root.students = BTree()
if not hasattr(root, 'assignments'):
    root.assignments = BTree()
if not hasattr(root, 'events'):
    root.events = BTree()
if not hasattr(root, 'login_history'):
    root.login_history = BTree()
if not hasattr(root, 'visual'):
    root.visual = {}
	
transaction.commit()
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
	if request.client.host not in root.visual:
		root.visual[request.client.host] = "dark_mode"
		transaction.commit()
	return templates.TemplateResponse("register.html", {"request": request , "visual": root.visual[request.client.host]})

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
    return RedirectResponse(url=f"/login", status_code=HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
	if request.client.host not in root.visual:
		root.visual[request.client.host] = "dark_mode"
		transaction.commit()
	return templates.TemplateResponse("login.html", {"request": request, "visual": root.visual[request.client.host]})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
	students = root.students
	if email in students and students[email].password == hash_password(password):
		yyyymm = datetime.now().strftime("%Y-%m")
		ip_address = request.client.host
		root.login_history[email] = LoginHistory(email, ip_address)
		transaction.commit()
		return RedirectResponse(url=f"/{email}/main/{yyyymm}/1", status_code=HTTP_303_SEE_OTHER)
	return templates.TemplateResponse("error.html", {"request": request, "error": "Incorrect login"})

def is_logged_in(email: str = None):
    if email not in root.students:
       raise HTTPException(status_code=HTTP_303_SEE_OTHER, detail="/login")
    return root.students[email].email


@app.get("/{email}/main/{yyyymm}/{edu_year}", response_class=HTMLResponse)
async def get_by_month(request: Request, yyyymm: str, edu_year: str, email: str = Depends(is_logged_in)):
    can_edit: bool = root.students[email].edit
    if yyyymm in root.events:
        events = root.events[yyyymm].events
    else:
        events = []

    assignment_days = []
    for date, assignments_list in root.assignments.items():
        assignment_yyyymm = date[:7]
        if assignment_yyyymm == yyyymm and assignments_list:
            flag = False
            for assignment in assignments_list:
                if assignment.edu_year == edu_year:
                    flag = True
            if flag:
                assignment_days.append(int(date[-2:]))

    return templates.TemplateResponse("main.html", {"request": request, "email": email, "events": events, "yyyymm": yyyymm, "assignment_days": assignment_days, "can_edit": can_edit, "visual": root.visual[request.client.host], "edu_year": edu_year})

@app.post("/{email}/main/{yyyymm}/{edu_year}", response_class=HTMLResponse)
async def add_event(request: Request, yyyymm: str, edu_year: str, content: str = Form(...), email: str = Depends(is_logged_in)):
    if yyyymm in root.events:
        root.events[yyyymm].events.append(content)
    else:
        new_event = Event(yyyymm, content)
        root.events[yyyymm] = new_event;
    transaction.commit()
    return RedirectResponse(url=f"/{email}/main/{yyyymm}/{edu_year}", status_code=HTTP_303_SEE_OTHER)

@app.get("/{email}/assignments/{date}", response_class=HTMLResponse)
async def get_assignments(request: Request, date: str, email: str = Depends(is_logged_in)):
	can_edit : bool = root.students[email].edit
	assignments = []
	if date in root.assignments:
		for assignment in root.assignments[date]:
			assignments.append({"subject": assignment.subject, "name": assignment.name, "edu_year": assignment.edu_year})
	return templates.TemplateResponse("assignment.html", {"request": request, "email": email, "assignments": assignments, "date": date, "can_edit": can_edit, "visual": root.visual[request.client.host]})

@app.post("/{email}/assignments/{date}", response_class=HTMLResponse)
async def add_assignment(request: Request, date: str, edu_year: str = Form(...), assignment_name: str = Form(...), subject: str = Form(...), content: str = Form(...), email: str = Depends(is_logged_in)):
    if date not in root.assignments:
        root.assignments[date] = PersistentList()
    new_assignment = Assignment(assignment_name, subject, date, content, email, edu_year)
    root.assignments[date].append(new_assignment)
    transaction.commit()
    return RedirectResponse(url=f"/{email}/assignments/{date}", status_code=HTTP_303_SEE_OTHER)

@app.get("/{email}/assignments/{date}/{assignment_index}", response_class=HTMLResponse)
async def get_assignment(request: Request, date: str, assignment_index: int, email: str = Depends(is_logged_in)):
    assignments = []
    if date in root.assignments:
        for assignment in root.assignments[date]:
            assignments.append({"subject": assignment.subject, "name": assignment.name})
    assignment_obj = root.assignments[date][assignment_index]
    return templates.TemplateResponse("forum.html", {"request": request, "email": email, "assignments": assignments,  "date": date, "assignment": assignment_obj, "visual" : root.visual[request.client.host]})

@app.post("/{email}/assignments/{date}/{assignment_index}", response_class=HTMLResponse)
async def add_forum_msg(request: Request, date: str, assignment_index: int, email: str = Depends(is_logged_in), reply_user: str = Form(None), comment: str = Form(...), file: UploadFile = File(None)):
	filename = None
	if file.size > 0:
		filename = str(uuid.uuid4()) + file.filename
		unique_filename = "./static/" + filename
		with open(unique_filename, "wb") as buffer:
			buffer.write(await file.read())

	assignment_obj = root.assignments[date][assignment_index]
	assignment_obj.add_message(comment, email, reply_user, filename)
	transaction.commit()
	return RedirectResponse(url=f"/{email}/assignments/{date}/{assignment_index}", status_code=HTTP_303_SEE_OTHER)

@app.post("/visual")
async def visual(request: Request):
	ip_address = request.client.host
	if root.visual[ip_address] == "light_mode":
		root.visual[ip_address] = "dark_mode"
	else:
		root.visual[ip_address] = "light_mode"
	transaction.commit()
	return RedirectResponse(url=f"/register", status_code=HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout(request: Request):
	ip_address = request.client.host
	del root.visual[ip_address]
	transaction.commit()
	return RedirectResponse(url=f"/login", status_code=HTTP_303_SEE_OTHER)

@app.delete("/delete_event/{yyyymm}/{index}")
async def delete_event(request: Request, yyyymm: str, index: int):
    del root.events[yyyymm].events[index]
    transaction.commit()

@app.delete("/delete_assignment/{date}/{index}")
async def delete_assignment(request: Request, date: str, index: int):
	del root.assignments[date][index]
	transaction.commit()

@app.get("/purge_database")
async def purge_database(request: Request):
	root.students = BTree()
	root.assignments = BTree()
	root.events = BTree()
	root.login_history = BTree()
	transaction.commit()
	return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)

@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
	if request.client.host not in root.visual:
		root.visual[request.client.host] = "dark_mode"
		transaction.commit()
	return templates.TemplateResponse("admin_login.html", {"request": request, "visual": root.visual[request.client.host]})

@app.post("/admin", response_class=HTMLResponse)
async def admin_login(request: Request, password: str = Form(...)):
	if password == "admin":
		students = {email: student.__dict__ for email, student in root.students.items()}
		# assignments = {name: assignment.__dict__ for name, assignment in root.assignments.items()}
		# events = {yyyymm: event.__dict__ for yyyymm, event in root.events.items()}
		logs = {email: log.__dict__ for email, log in root.login_history.items()}
		
		data = {
			"Students": students,
			# "Assignments": assignments,
			# "Event" : events,
			"Logs": logs
		}
		return templates.TemplateResponse("admin_page.html", {"request": request, "data": data , "visual": root.visual[request.client.host]})
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
		args : dict = eval(value)
		root.students[args['email']] = Student(args['email'], args['password'], args['edit'])
	elif action == "Create":
		args : dict = eval(value)
		root.students[args['email']] = Student(args['email'], args['password'], args['edit'])
	else:
		return templates.TemplateResponse("error.html", {"request": request, "error": "Invalid action"})
	transaction.commit()

	students = {email: student.__dict__ for email, student in root.students.items()}
	data = {
		"Students": students
	}
	return templates.TemplateResponse("admin_page.html", {"request": request, "data": data, "visual": root.visual[request.client.host]})

@app.get("year/{email}")
async def get_year(email: str):
	current_year = str(datetime.now().year)
	current_year = (current_year[-2:] + 43) % 100
	student_year = int(email[:2])
	return (current_year - student_year + 1)

