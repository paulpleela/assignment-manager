
# Assignment Manager

The Assignment Manager is a web application designed for Software Engineering students to effectively manage and track their assignments. This project provides a platform for students to access a calendar displaying upcoming assignments and events. Additionally, it offers a forum feature for students to discuss assignment details, promoting collaboration within the community.

- [Features](#features)
  - [User Authentication](#user-authentication)
  - [Admin Dashboard](#admin-dashboard)
  - [Main Calendar](#main-calendar)
  - [View Assignments](#view-assignments)
- [Technologies Used](#technologies-used)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [Contributors](#contributors)
- [License](#license)


## Features

### User Authentication

* **Student Accounts:** Students can register and log in using their KMITL email address and a password. The login page also has an option to toggle between light and dark mode.
* **Admin Access:** Admins have a separate login page, accessible with an admin passcode, enabling them to use the admin dashboard.
![login page](https://i.imgur.com/ZW9SxVo.png)

### Admin Dashboard

* **User Management:** Admins can add, edit, and remove student accounts.
* **User Permissions:** Admins can grant specific users the ability to add and remove assignments and events on the calendar.
* **User Logs:** Admins can see user activity and access times.
* **Purge Database:** Admins have the option to reset all user and calendar data.
![admin dashboard](https://i.imgur.com/yZaKeqi.png)

### Main Calendar

* **Upcoming Assignments:** Assignments are marked in the main calendar with an indicator for all students to view. Clicking on a date will open up a list of all the assignments due on that day.
* **Year of Study Selection:** Users can choose to view only the assignments relevant to their year of study from a dropdown menu.
* **Upcoming Events:** A list of events is displayed in each month of the calendar. Permitted users can add and remove events from this list.
![main calendar](https://i.imgur.com/NwuIH1K.png)

### View Assignments

* **Assignments List:** Displays a list of assignments due on the date chosen from the main calendar. Permitted users can add and remove assignments from this list.
* **Assignment Page:** Clicking on an assignment in this list opens up its assignment page. This page shows assignment details and has a discussion forum that can post messages and files.
![assignment forum](https://i.imgur.com/7Fw0Xy3.png)


## Technologies Used

* **Front-end:** HTML, CSS, JavaScript
* **Back-end:** FastAPI
* **Database:** ZODB (for storing login data, assignment information, and forum messages)
* **Template Engine:** Jinja2


## Getting Started

Follow these steps to set up and run the Homework Calendar web application on your local machine:

### Prerequisites

- [Python](https://www.python.org/) (version 3.8 or higher)
- [Pip](https://pip.pypa.io/en/stable/installation/) (Python package installer)

### Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/Pixako-Unrealistia/Assignment-manager.git
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1. Start the FastAPI server (The default port is 8000):

    ```bash
    uvicorn api:app
    ```

2. Open your web browser and go to [http://localhost:8000/login](http://localhost:8000/login) to access the Assignment Manager web application.


## Contributors

- **[Parisorn Prasartkul](https://github.com/ppparisorn)**
- **[Peeranat Leelawattanapanit](https://github.com/paulpleela)**
- **[Sorawis Chongterdtoonskul ](https://github.com/Pixako-Unrealistia)**


## License

[MIT](https://choosealicense.com/licenses/mit/)