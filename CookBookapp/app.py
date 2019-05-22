from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
import  datetime
from data import Recipes
#from flaskext.mysql import MySQL
from flask_mysqldb import MySQL
#from flask_wtf import FlaskForm
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQLs
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '*****'
app.config['MYSQL_DB'] = 'myrecipes'
## set it here to dictionary - because fetchall() returns a tuple and I wanted dictionary
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)


# Index
@app.route('/')
def index():
    return render_template('home.html')


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Recipes
@app.route('/recipes')
def recipes():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get recipes
    result = cur.execute("SELECT * FROM recipes")

    recipes = cur.fetchall()

    if result > 0:
        return render_template('recipes.html', recipes=recipes)
    else:
        msg = 'No Recipes Found'
        return render_template('recipes.html', msg=msg)
    # Close connection
    cur.close()


#Single recipe
@app.route('/recipe/<string:id>/')
def recipe(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get recipe
    result = cur.execute("SELECT * FROM recipes WHERE id = %s", [id])

    recipe = cur.fetchone()

    return render_template('recipe.html', recipe=recipe)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get recipes
    # Show recipe only from the user logged in
    result = cur.execute("SELECT * FROM recipes WHERE author = %s", [session['username']])

    recipes = cur.fetchall()


    if result > 0:
        return render_template('dashboard.html', recipes=recipes)
    else:
        msg = 'No Recipes Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()


# Recipe form class
class RecipeForm(Form):
    name = StringField('Name', [validators.length(min=5, max=100)])
    ingredients = TextAreaField('Ingredients', [validators.length(min=10)])
    instructions = TextAreaField('Instructions',[validators.length(min=10)])
    serving_size = StringField('Serving Size', [validators.length(min=1)])
    category = StringField('Category',[validators.length(min=5)])
    notes = TextAreaField('Notes')

# Add recipe
@app.route('/add_recipe', methods=['GET', 'POST'])
@is_logged_in
def add_recipe():
    form = RecipeForm(request.form)
    if request.method == 'POST' and form.validate():

        name = form.name.data
        ingredients = form.ingredients.data
        instructions = form.instructions.data
        serving_size = form.serving_size.data
        category = form.category.data
        notes = form.notes.data


        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO recipes(name, ingredients,instructions,serving_size,category,notes,author) VALUES(%s, %s, %s, %s, %s, %s, %s)",
                    (name, ingredients,instructions,serving_size,category,notes , session['username']))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Recipe Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_recipe.html', form=form)


# Edit recipe
@app.route('/edit_recipe/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_recipe(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get recipe by id
    result = cur.execute("SELECT * from recipes where id = %s", [id])

    recipe = cur.fetchone()
    cur.close()
    # Get form
    form = RecipeForm(request.form)

    # Populate recipe form fields
    form.name.data = recipe['name']
    form.ingredients.data = recipe['ingredients']
    form.instructions.data = recipe['instructions']
    form.serving_size.data = recipe['serving_size']
    form.category.data = recipe['category']
    form.notes.data = recipe['notes']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        serving_size = request.form['serving_size']
        category = request.form['category']
        notes = request.form['notes']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(name)

        # Execute
        cur.execute ("UPDATE recipes SET name=%s, ingredients=%s, instructions=%s, serving_size=%s, category = %s,notes = %s, date_modified = %s WHERE id=%s",(name, ingredients, instructions,
                                                                                                                                            serving_size, category, notes, datetime.datetime.now(), id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Recipe Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_recipe.html', form=form)

# Delete recipe
@app.route('/delete_recipe/<string:id>', methods=['POST'])
@is_logged_in
def delete_recipe(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM recipes WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Recipe Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
