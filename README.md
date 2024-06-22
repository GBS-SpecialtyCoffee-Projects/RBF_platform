# RBF Platform

Welcome to the RBF Platform project! This project is designed to manage users (farmers and roasters) and their interactions in a specialty coffee context.

## Table of Contents
- [Introduction](#introduction)
- [Technologies](#technologies)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The RBF Platform is a web application built using Django that helps farmers and roasters create accounts, manage their profiles, and interact with each other through a structured workflow. The platform includes features such as registration, login, and dashboard management for both user types.

## Technologies

- **Backend**: Django (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling Framework**: Bootstrap, Jquery
- **Database**: MySQL
- **Version Control**: Git, GitHub

## Getting Started

Follow these steps to get the project up and running on your local machine:

### Prerequisites

- Python 3.9
- Django 4.1
- Git
- mysql installed

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kei-Nie/RBF_platform.git
   cd RBF_platform

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
3. **Activate the virtual environment(using conda will be much easier):**
   ```bash
   source venv/bin/activate
4. **Install dependencies(using conda will be easier):**
   ```bash
   pip install -r requirements.txt
5. **Login to mysql and create a database named rbf_platform.**
   ```bash
   create database rbf_platform;
6. **Go to setting.py and change the password to your mysql password.**
   ```bash
   DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "rbf_platform",
        "USER": "root",
        "PASSWORD": "yourpassword",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    }
}
6. **Apply migrations:**
   ```bash
   python manage.py makemigrations base
   python manage.py migrate
6. **Run the development server:**
   ```bash
   python manage.py runserver

