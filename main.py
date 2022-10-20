from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
# from decorators import admin_only
from functools import wraps
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from flask_gravatar import Gravatar
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# Creating a login manager
login_manager = LoginManager()
# Configuring my Flask app for login
login_manager.init_app(app)

# Initializing gravatar images with the Flask application
gravatar = Gravatar(
    app=app,
    size=100,
    rating='x',
    force_default=False
)


# Providing a user_loader callback. This callback is used to reload the user object from the user ID stored in the
# session. It should take the str ID of a user and return the corresponding user object
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

# Creating a class for creating user tables (apart the db.Model, the class also inherits from UserMixin class - this
# will be needed for user authentication). Also, blog_users and blog_posts tables have a bidirectional one-to-many
# relationship
class User(UserMixin, db.Model):
    __tablename__ = "blog_users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    # Specifying the relationship between blog_users table and blog_posts table. The back_populates parameter
    # is used to make this a bidirectional one-to-many relationship.
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    # NOTE: it seems that posts is a hidden column (it does not appear in the blog_posts table) used to
    # establish a bidirectional relationship between blog_users and blog_posts tables
    posts = relationship("BlogPost", back_populates="author")
    # Specifying the relationship between blog_users and blog_comments table. The back_populates parameter
    # is used to make this a bidirectional one-to-many relationship
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Adding an author_id column to blog_posts table that is a foreign key used to connect to the
    # blog_users table
    author_id = db.Column(db.Integer, db.ForeignKey("blog_users.id"))
    # Specifying the relationship between blog_posts table and blog_users table. The back_populates parameter
    # is used to make this a bidirectional many-to-one relationship.
    # The "blog_posts" refers to the posts property in the User class.
    # NOTE: it seems that author is now a hidden column (it does not appear in the blog_posts table) used to
    # establish a bidirectional relationship between blog_posts and blog_users tables. Also, the author property
    # of BlogPost is now a property of its parent (User) class
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="post")


class Comment(db.Model):
    __tablename__ = "blog_comments"
    id = db.Column(db.Integer, primary_key=True)
    # Creating a foreign key that will be used to connect to blog_users table
    author_id = db.Column(db.Integer, db.ForeignKey("blog_users.id"))
    # Specifying the relationship between blog_posts table and blog_users table. The back_populates parameter
    # is used to make this a bidirectional many-to-one relationship (if I understand it correctly, it back populates
    # the blog_comments property inside blog_users table)
    author = relationship("User", back_populates="comments")
    # Creating a foreign key that will be used to connect to blog_users table
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


# Creating the tables (this method will not re-create the tables if they are already created)
db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    # Creating a form for registering
    register_form = RegisterForm()
    # If the register form is submitted and validated
    if register_form.validate_on_submit():
        # And if there are no existing users with the email address that was submitted in the register form
        existing_user = db.session.query(User).filter(User.email == register_form.email.data).first()
        if not existing_user:
            # A new user is created
            new_user = User(
                email=register_form.email.data,
                # Using pbkdf2:sha256 method and adding 8 characters of salt (i. e. 8 random characters) to make the
                # password harder to decrypt
                password=generate_password_hash(
                    password=register_form.password.data, method="pbkdf2:sha256", salt_length=8
                ),
                name=register_form.name.data
            )
            # And added to the database
            db.session.add(new_user)
            db.session.commit()
            # After being added to the database, the user is logged and authenticated using Flask-Login
            login_user(new_user)
            # Then, the user is redirected to the URL associated with get_all_posts function (i. e. the home page).
            return redirect(url_for("get_all_posts"))
        # Otherwise, if the user with that email address already exists
        else:
            # The user is redirected to the login page and asked to login instead
            flash('You have already signed up with that email, log in instead!')
            return redirect(url_for("login"))
    # If it's a GET request, the register.html page is rendered with the registration form as a variable,
    # so that it can be referenced and used inside register.html
    return render_template("register.html", form=register_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    # Creating a login form
    login_form = LoginForm()
    # If the login_form is submitted and validated
    if login_form.validate_on_submit():
        # The function searches for the user in the database using the email submitted in the login form
        user = db.session.query(User).filter(User.email == login_form.email.data).first()
        # And if the user exists in the database and the password they entered (after it's hashed) matches the
        # hashed password in the database
        if user:
            if check_password_hash(user.password, login_form.password.data):
                # The function logs the user in
                login_user(user)
                # And redirects them to the home page
                return redirect(url_for("get_all_posts"))
            # Otherwise, the user is redirected back to the login page and a flash message is displayed asking
            # them to try again
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))
        # If the user does not exist, a flash message is displayed
        flash("Wrong email address, please try again.")
        return redirect(url_for("login"))
    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    # Logging the user out with logout_user
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    # Getting the requested post using the post ID that was specified in the URL
    requested_post = BlogPost.query.get(post_id)
    # Creating the comment form
    comment_form = CommentForm()
    # Getting all comments for this blog posts
    comments = db.session.query(Comment).filter(Comment.post_id == post_id).all()
    # If the user tries to post a comment and their comment submit is validated
    if comment_form.validate_on_submit():
        # And if they are logged in
        if current_user.is_authenticated:
            # Their comment is added to the database
            new_comment = Comment(
                author_id=current_user.id,
                post_id=post_id,
                text=comment_form.comment.data
            )
            db.session.add(new_comment)
            db.session.commit()
            # And they are redirected back to the same blog post page
            return redirect(url_for("show_post", post_id=post_id))
        # Otherwise, they are redirected to the login page and get a flash message asking to register or login
        flash("You need to login or register to comment.")
        return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, form=comment_form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


def admin_only(function):
    # Copying the original functions information to the new function
    @wraps(function)
    # Creating a new, decorated function
    def decorated_function(*args, **kwargs):
        # Which checks if the current user is authenticated (needed to add this in order for the
        # "AttributeError: 'AnonymousUserMixin' object has no attribute 'id'" error to disappear
        if current_user.is_authenticated:
            # And checks if the current user id is equal to 1
            if current_user.id == 1:
                # And if it is, the decorated function runs the original function
                return function(*args, **kwargs)
            # However, if the current user id is not 1, the function renders a "forbidden resource" message on screen
            return abort(403)
        # If the current user is not authenticated, the function renders a "forbidden resource" message on screen
        return abort(403)
    return decorated_function


@app.route("/new-post", methods=["GET", "POST"])
# Decorating the function with admin_only to make sure that only the admin can add new blog posts
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            author_id=current_user.id,
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=date.today().strftime("%B %d, %Y"),
            body=form.body.data,
            img_url=form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        author_id=current_user.id,
        author=post.author,
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    # Changing the port in order to fix the "App crash" error when deploying the app on Heroku
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
