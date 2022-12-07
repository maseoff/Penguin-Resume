from fun import FUNNY_LIST
from random import choice, randint

from flask import Flask, render_template, request, redirect, send_file, session, url_for
from werkzeug.utils import secure_filename

import base64
import os
import pandas as pd
import pdfkit
import re


PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
PDFKIT_OPTIONS = {"enable-local-file-access": ""}

DEBUG = True

DATABASE_USERS = pd.DataFrame(
    columns=[
        "username",
        "password"
    ]

)
DATABASE_RESUMES = pd.DataFrame(
    columns=[
        "username",
        "name",
        "surname",
        "email",
        "phone",
        "vk",
        "github",
        "telegram",
        "education",
        "work_experience",
        "skills",
        "hobby",
    ]
)

UPLOAD_FOLDER = "temp/images"
RESUME_FOLDER = "temp/resumes"

DEFAULT_RESUME_IMAGES_FOLDER = "static/images/resume"


app = Flask(__name__)
app.secret_key = "2960eb29-734f-4533-8a47-3cfe096ca063-a0270c54-4a55-42b0-b7a7-58336f6226bd"

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, UPLOAD_FOLDER)
app.config["RESUME_FOLDER"] = os.path.join(app.root_path, RESUME_FOLDER)


@app.route(rule="/")
def home() -> str:
    username = get_username()
    is_authorized = is_authorized_user(username)

    return render_template(
        template_name_or_list="home.html",
        title="Home",
        is_authed=is_authorized,
    )


@app.route(rule="/auth", methods=["GET", "POST"])
def auth() -> str:
    username = get_username()
    if is_authorized_user(username):
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template(
            template_name_or_list="auth.html",
            title="Auth",
            is_authed=False,
        )

    username = request.form["username"]
    password = request.form["password"]

    if not is_correct_auth_data(username, password):
        return render_template(
            template_name_or_list="auth.html",
            title="Auth",
            is_authed=False,
            error="Can't auth. Is your data correct?"
        )

    session["username"] = request.form["username"]
    return redirect(url_for("home"))


@app.route(rule="/signup", methods=["GET", "POST"])
def signup() -> str:
    username = get_username()
    if is_authorized_user(username):
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template(
            template_name_or_list="signup.html",
            title="Sign Up",
            is_authed=False,
        )

    username = request.form["username"]
    password = request.form["password"]
    repeated = request.form["repeated_password"]
    love = int(request.form["love_for_penguins"])

    error_message = ""
    if any(
        [
            not username,
            not password,
            not repeated,
        ]
    ) and not error_message:
       error_message = "Something is missed"

    if not re.match(r"^[a-zA-Z0-9]+$", username) and not error_message:
        error_message = "Username can hold only latin letters and digits"

    if len(username) < 3 and not error_message:
        error_message = "Username is quite short"

    if password != repeated and not error_message:
        error_message = "Passwords do not match"

    if love < 6 and not error_message:
        error_message = "You do not love penguins enough"

    if error_message:
        return render_template(
            template_name_or_list="signup.html",
            title="Sign Up",
            is_authed=False,
            error=error_message,
        )

    if not is_unique_username(username):
        return render_template(
            template_name_or_list="signup.html",
            title="Sign Up",
            is_authed=False,
            error="Username already exists",
        )

    add_user_to_database(
        username=username,
        password=password,
    )

    session["username"] = username
    return redirect(url_for("home")) 


@app.route(rule="/logout")
def logout() -> str:
    session.pop("username", None)
    return redirect(url_for("home"))


@app.route(rule="/fun")
def fun() -> str:
    username = get_username()
    is_authorized = is_authorized_user(username)

    pair = choice(FUNNY_LIST)
    return render_template(
        template_name_or_list="fun.html",
        title="Fun",
        is_authed=is_authorized,
        image_name=pair["name"],
        image_url=pair["url"],
    )


@app.route(rule="/create", methods=["GET", "POST"])
def create():
    username = get_username()
    if not is_authorized_user(username):
        return redirect(url_for("auth"))

    if request.method == "GET":
        data = get_saved_resume_data(username)
        return render_template(
            template_name_or_list="create.html",
            title="Create",
            is_authed=True,
            name=data["name"],
            surname=data["surname"],
            email=data["email"],
            phone=data["phone"],
            vk=data["vk"],
            github=data["github"],
            telegram=data["telegram"],
            education=data["education"],
            work_experience=data["work_experience"],
            skills=data["skills"],
            hobby=data["hobby"],
        )

    name = request.form["name"]
    surname = request.form["surname"]
    email = request.form["email"]
    phone = request.form["phone"]
    vk = request.form["vk"]
    github = request.form["github"]
    telegram = request.form["telegram"]
    education = request.form["education"]
    work_experience = request.form["work_experience"]
    skills = request.form["skills"]
    hobby = request.form["hobby"]

    if any(
            [
                not name,
                not surname,
                not email,
                not phone,
            ]
        ):
            data = get_saved_resume_data(username)
            return render_template(
                template_name_or_list="create.html",
                error="Missing required fields",
                title="Create",
                is_authed=True,
                name=name,
                surname=surname,
                email=email,
                phone=phone,
                vk=vk,
                github=github,
                telegram=telegram,
                education=education,
                work_experience=work_experience,
                skills=skills,
                hobby=hobby,
            ) 

    button = request.form["button"]
    if button == "Save":
        save_resume_data(
            username=username,
            name=name,
            surname=surname,
            email=email,
            phone=phone,
            vk=vk,
            github=github,
            telegram=telegram,
            education=education,
            work_experience=work_experience,
            skills=skills,
            hobby=hobby
        )

        return redirect(url_for("create"))

    if button == "Download":
        path_to_previous_resume = os.path.join(app.config["RESUME_FOLDER"], f"{username}.pdf")
        if os.path.exists(path_to_previous_resume):
            os.remove(path_to_previous_resume)

        file = request.files.get("avatar")
        if file.filename == "":
            filename = f"{randint(1, 4)}.jpg"

            path_to_avatar = os.path.join(app.root_path, f"{DEFAULT_RESUME_IMAGES_FOLDER}/{filename}")
            need_to_delete_avatar = False

        else:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            path_to_avatar = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            need_to_delete_avatar = True

        if need_to_delete_avatar:
            path_to_avatar = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
        else:
            path_to_avatar = os.path.join(app.root_path, DEFAULT_RESUME_IMAGES_FOLDER, filename)

        html = render_template(
            template_name_or_list="resume.html",
            encoded_avatar=get_encoded_image(path_to_avatar),
            name=name,
            surname=surname,
            email=email,
            phone=phone,
            vk=vk,
            github=github,
            telegram=telegram,
            education=education,
            work_experience=work_experience,
            skills=skills,
            hobby=hobby
        )

        path_to_resume = os.path.join(app.root_path, f"{RESUME_FOLDER}/{username}.pdf")
        pdfkit.from_string(
            input=html,
            output_path=path_to_resume,
            configuration=PDFKIT_CONFIG,
            options=PDFKIT_OPTIONS
        )

        if need_to_delete_avatar:
            os.remove(path_to_avatar)

        return send_file(path_to_resume, as_attachment=True)


@app.errorhandler(404)
def page_not_found(error):
    return redirect(url_for("home"))


def is_authorized_user(username: str | None) -> bool:
    return "username" in session and username is not None


def get_username() -> str | None:
    return session.get("username", None)


def is_unique_username(username: str) -> bool:
    return not username in DATABASE_USERS["username"].values


def add_user_to_database(username: str, password: str) -> None:
    global DATABASE_USERS
    DATABASE_USERS = pd.concat(
        [
            DATABASE_USERS,
            pd.DataFrame.from_dict(
                {
                    "username": [username],
                    "password": [password],
                },
            )
        ],
        ignore_index=True,
    )


def is_correct_auth_data(username: str, password: str) -> bool:
    global DATABASE_USERS
    return not DATABASE_USERS[
        (DATABASE_USERS["username"] == username)
        &
        (DATABASE_USERS["password"] == password)
    ].empty


def has_saved_resume_data(username: str) -> bool:
    global DATABASE_RESUMES
    return not DATABASE_RESUMES[DATABASE_RESUMES["username"] == username].empty


def get_saved_resume_data(username: str) -> dict[str, str]:
    global DATABASE_RESUMES
    if has_saved_resume_data(username):
        return DATABASE_RESUMES[DATABASE_RESUMES["username"] == username].to_dict("records")[0]

    return {
        "name": "",
        "surname": "",
        "email": "",
        "phone": "",
        "vk": "",
        "github": "",
        "telegram": "",
        "education": "",
        "work_experience": "",
        "skills": "",
        "hobby": "",
    }


def save_resume_data(
    username: str,
    name: str,
    surname: str,
    email: str,
    phone: str,
    vk: str,
    github: str,
    telegram: str,
    education: str,
    work_experience: str,
    skills: str,
    hobby: str
    ) -> None:

    global DATABASE_RESUMES
    if has_saved_resume_data:
        DATABASE_RESUMES = DATABASE_RESUMES[DATABASE_RESUMES["username"] != username]

    DATABASE_RESUMES = pd.concat(
        [
            DATABASE_RESUMES,
            pd.DataFrame.from_dict(
                {
                    "username": [username],
                    "name": [name],
                    "surname": [surname],
                    "email": [email],
                    "phone": [phone],
                    "vk": [vk],
                    "github": [github],
                    "telegram": [telegram],
                    "education": [education],
                    "work_experience": [work_experience],
                    "skills": [skills],
                    "hobby": [hobby],
                },
            )
        ],
        ignore_index=True,
    )


def get_encoded_image(path: str) -> bytes:
    """
    Источник:
    https://stackoverflow.com/questions/38329909/pdfkit-not-converting-image-to-pdf
    """

    with open(path, mode="rb") as file:
        return base64.b64encode(file.read())


if __name__ == "__main__":
    app.run(debug=DEBUG)
