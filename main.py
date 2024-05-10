from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5

from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text,ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import RegistrationForm,LoginForm,CommentForm
from forms import CreatePostForm
from typing import List

import os
from dotenv import load_dotenv
'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASH_KEY")   
ckeditor = CKEditor(app)
Bootstrap5(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
# TODO: Configure Flask-Login
login_manager=LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URI",'sqlite:///posts.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    author_id:Mapped[int]=mapped_column(Integer,ForeignKey("user_table.id"))
    # parent:Mapped["User"]=relationship(back_populates="children")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # author_id:Mapped[str]=mapped_column(String,nullable=False)

    author: Mapped[str] = relationship("User", back_populates="children")
    comments:Mapped[List["Comment"]]=relationship(back_populates="post")
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    


# TODO: Create a User table for all your registered users. 
class User(db.Model,UserMixin):
    __tablename__="user_table"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    name:Mapped[str]=mapped_column(String(50),nullable=False)
    email:Mapped[str]=mapped_column(String(100),unique=True,nullable=False)
    password:Mapped[str]=mapped_column(String(100),nullable=False)
    children:Mapped[List["BlogPost"]]=relationship(back_populates="author")
    comments:Mapped[List["Comment"]]=relationship(back_populates="comment_author")

class Comment(db.Model):
    __tablename__="comment"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    author_id:Mapped[int]=mapped_column(Integer,ForeignKey("user_table.id"))
    comment_author:Mapped[str]=relationship("User",back_populates="comments")

    
    post_id:Mapped[int]=mapped_column(Integer,ForeignKey("blog_posts.id"))
    post:Mapped[str]=relationship("BlogPost",back_populates="comments")
    
    text:Mapped[str]=mapped_column(String,nullable=False)

with app.app_context():
    db.create_all()


#Decorator for ADMIN ONLY ROUTE
def admin_only(function):
    @wraps(function)
    def admin_wrapper(*args,**kwargs):
        if current_user.id==1:
            
            return function(*args,**kwargs)
        else:
            return abort(403)
    return admin_wrapper
# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=["POST","GET"])
def register():
    is_active=current_user.is_active
    form=RegistrationForm()
    if form.validate_on_submit():
        form_name=form.name.data
        form_password=form.password.data
        form_email= form.email.data
        database_user=db.session.execute(db.select(User).where(User.email==form_email)).scalar()
        if database_user:
            flash("User already exist. Please Login!!!")
            return redirect(url_for("login"))
        hash_password=generate_password_hash(form_password,method="pbkdf2",salt_length=8)
        new_user=User(name=form_name,
                      email=form_email,
                      password=hash_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html",form=form,is_active=is_active)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=["POST","GET"])
def login():
    is_active=current_user.is_active
    form=LoginForm()
    if form.validate_on_submit():
        form_email=form.email.data
        form_password=form.password.data
        database_user=db.session.execute(db.select(User).where(User.email==form_email)).scalar()
       
        if not database_user:
            flash("User not Found.")
            return redirect(url_for("login"))
        
        elif check_password_hash(database_user.password,form_password):
            login_user(database_user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Incorrect Pasword")
            return redirect(url_for("login"))
    return render_template("login.html",form=form,is_active=is_active)


@app.route('/logout')

def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
def get_all_posts():
    is_active=current_user.is_active
    
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts,is_active=is_active,current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=["POST","GET"])

def show_post(post_id):
    is_active=current_user.is_active
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_list=db.session.execute(db.select(Comment)).scalars().all()
    form= CommentForm()
    
    if form.validate_on_submit():

        form_comment=form.comment.data
        if is_active:
            new_comment=Comment(text=form_comment,
                                comment_author=current_user,
                                post=requested_post)
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post',post_id=post_id))
        else:
            flash("Login Required!!!")
            return redirect(url_for("show_post", post_id=post_id))
    return render_template("post.html",gravatar=gravatar,comment_list=comment_list, post=requested_post,is_active=is_active,current_user=current_user,form=form)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    is_active=current_user.is_active
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,is_active=is_active)


# TODO: Use a decorator so only an admin user can edit a post

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    is_active=current_user.is_active
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,is_active=is_active)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    comment_to_delete=db.session.execute(db.select(Comment).where(Comment.post_id==post_id)).scalars().all()
    for comment in comment_to_delete:
        db.session.delete(comment)
        db.session.commit()
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    is_active=current_user.is_active
    return render_template("about.html",is_active=is_active)


@app.route("/contact")
def contact():
    is_active=current_user.is_active
    return render_template("contact.html",is_active=is_active)


if __name__ == "__main__":
    app.run(debug=False, port=5002)
