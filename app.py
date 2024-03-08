from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt


from flask import Flask, render_template, request, redirect, url_for
import core.time_variables as tv
from database.database import (
    get_db_connection,
    get_table_from_database
)
from database.create_tables import (
    create_initial_tables,
    get_list_of_table_year_and_month,
    create_tables_6_months_ahead,
)

from core.period_prediction import (
    get_period_start_days,
    get_period_end_days,
    average_time_between_periods,
    average_menstruation_length,
    predict_future_period_days,
)

app = Flask(__name__)

bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)


# @app.route('/dashboard', methods=['GET', 'POST'])
# @login_required
# def dashboard():
#     return render_template('dashboard.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Create the flask app

# -------------------------------------------- CREATE TABLES IN DATABASE --------------------------------------------------#

# Create the initial 12 months of tables in the database if there are not already tables in the database
create_initial_tables()

# Get list of the table years and months as strings for each table already created (ex: ['2022', '08'])
table_years_and_months = get_list_of_table_year_and_month()

# Create any tables for the next 6 months that are not already in the database.
create_tables_6_months_ahead(table_years_and_months=table_years_and_months)

# ------------------------------------------------------------------------------------------------------------------------#


# -------------------------------------- PREDICT FUTURE PERIOD DAYS IF POSSIBLE ------------------------------------------#

# set list of periods start days to 'period_start_days'
period_start_days = get_period_start_days()

# set list of periods end days to 'period_end_days'
period_end_days = get_period_end_days()

# if period_start_days and period_end_days are not empty, the below will work
try:
    # set calculated average time between periods to 'avg_time_between_periods'
    avg_time_between_periods = average_time_between_periods(
        period_start_days=period_start_days, period_end_days=period_end_days
    )
    # set calculated average length of period to 'avg_menstruation_length'
    avg_menstruation_length = average_menstruation_length(
        period_start_days=period_start_days, period_end_days=period_end_days
    )
    # set predicted future period days equal to 'predicted_period_days'
    predicted_period_days = predict_future_period_days(
        last_period_end_day=period_end_days[-1],
        avg_time_between_periods=avg_time_between_periods,
        avg_menstruation_length=avg_menstruation_length,
    )
except:
    pass

# ------------------------------------------------------------------------------------------------------------------------#


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template(
        "index.html", current_month=tv.current_month_name, current_year=tv.current_year
    )

# Need an updated list of table years and months because if someone creates the database and has to add any six months ahead tables,
#       they will not be included in the previous list of table_years_and_months
updated_table_years_and_months = get_list_of_table_year_and_month()


@app.route("/calendar", methods=['GET', 'POST'])
@login_required
def calendar():
    """View the calendar for the given month and year. Can click on specific days to edit details and navigate to other months."""
    # Get the name of the month from the url arg 'month'
    month_name = request.args.get("month")
    # Get month number in calendar year as an int (ex: 5)
    month_number = tv.list_of_months.index(month_name) + 1
    # Get month number in calendar year as a string with a leading 0 if it is under 10 (ex: '05')
    month_number_string = str(month_number).rjust(2, "0")
    # Get the year from the url arg 'year'
    year = request.args.get("year")
    # month name and year as a string
    month_and_year_name = f"{month_name} {year}"
    # month year and number as a list
    month_year_and_number = [year, month_number_string]
    # index number in updated_table_years_and_months for the given month_year_and_number
    table_years_and_months_index = updated_table_years_and_months.index(
        month_year_and_number
    )
    # Get the table number of the given month as a string, add leading 0 if under 10
    table_number = str((table_years_and_months_index) + 1).rjust(2, "0")
    # Get all day entries in the month given
    month_days = get_table_from_database(
        tablename=f"table_{table_number}_{month_name}_{year}"
    )
    first_of_month_weekday = tv.get_1st_day_in_month_weekday(
        year=int(year), month=month_number
    )

    # Try to get the next year and month from the updated_table_years_and_months list.
    try:
        # Get the name of the next month after the month currently viewing
        next_year_and_month_from_list = updated_table_years_and_months[
            table_years_and_months_index + 1
        ]

        # Get the name of the next month by subtracting 1 from the next month number to get the corresponding index in list_of_months
        next_month = tv.list_of_months[int(next_year_and_month_from_list[1]) - 1]

        # Get the next month year by getting the item at index 0 in next_year_and_month_from_list
        next_month_year = next_year_and_month_from_list[0]

    # If not there (IndexError), next_month and next_month_year = None
    except IndexError:
        # if returns index error, means it is the last table
        next_month = None
        next_month_year = None

    # Get the previous year and month from the updated_table_years_and_months list if the index is greater than 0.
    if table_years_and_months_index - 1 >= 0:
        previous_year_and_month_from_list = updated_table_years_and_months[
            table_years_and_months_index - 1
        ]

        # Get the name of the previous month by subtracting 1 from the previous month number to get the corresponding index in list_of_months
        previous_month = tv.list_of_months[
            int(previous_year_and_month_from_list[1]) - 1
        ]

        # Get the previous month year by getting the item at index 0 in previous_year_and_month_from_list
        previous_month_year = previous_year_and_month_from_list[0]

    # If less than 0 (meaning it will go backwards through the list starting at -1), previous_month and previous_month_year = None
    else:
        previous_month = None
        previous_month_year = None

    # Try to get the predicted future period days if there are any. If there are not,  predicted_days_of_period = None
    try:
        # set predicted_days_of_period equal to predicted_period_days
        predicted_days_of_period = predicted_period_days
    except NameError:
        # if gives a NameError, means there are no predicted days yet, so set predicted_period_days to None
        predicted_days_of_period = None

    # Send user to the homepage by rendering "index.html" with the following parameters
    return render_template(
        "calendar.html",
        predicted_period_days=predicted_days_of_period,
        days=month_days,
        weekday=first_of_month_weekday,
        month_and_year=month_and_year_name,
        year=year,
        current_month=tv.current_month_name,
        current_month_year=tv.current_year,
        month=month_name,
        next_month=next_month,
        next_month_year=next_month_year,
        previous_month=previous_month,
        previous_month_year=previous_month_year,
    )


@app.route("/details", methods=["post", "get"])
@login_required
def day_details():
    """Edit the details of a particular day on the calendar (i.e. period started, heachache, cramps, etc.) and commit the changes to the database."""
    # establish connection to the database
    conn = get_db_connection()
    if request.method == "POST":
        # Need to set 'day_of_month', 'month', and 'year' variables again but using the form,
        #   otherwise it returns 'None' when trying to update the db
        day_of_month = request.form["day"]
        month = request.form["month"]
        year = request.form["year"]
        # Get the table name from the form
        table_name = request.form["table_name"]
        # Update the period_started in the database
        update_period_started = request.form["period_start"]
        # Update the period_ended in the database
        update_period_ended = request.form["period_ended"]
        # Update cramps in the database
        update_cramps = request.form["cramps"]
        # Update headache in the database
        update_headache = request.form["headache"]
        # Update acne in the database
        update_acne = request.form["acne"]
        # Update fatigue in the database
        update_fatigue = request.form["fatigue"]
        conn.execute(
            f"UPDATE {table_name} SET  period_started= ?, period_ended= ?, cramps = ?, headache = ?, acne = ?, fatigue = ?"
            " WHERE id = ?",
            (
                update_period_started,
                update_period_ended,
                update_cramps,
                update_headache,
                update_acne,
                update_fatigue,
                day_of_month,
            ),
        )
        # Commit the update to the database
        conn.commit()
        # Close the connection to the database
        conn.close()
        # Bring back the calendar for the same month and year
        return redirect(url_for("calendar", month=month, year=year))
    # Get the day/month/year from the url (after the /edit?)
    day_of_month = request.args.get("date")
    month = request.args.get("month")
    year = request.args.get("year")
    # Get month number in calendar year as an int (ex: 5)
    month_number = tv.list_of_months.index(month) + 1
    # Get month number in calendar year as a string with a leading 0 if it is under 10 (ex: '05')
    month_number_string = str(month_number).rjust(2, "0")
    # month year and number as a list
    month_year_and_number = [year, month_number_string]
    # index number in table_years_and_months for the given month_year_and_number
    table_years_and_months_index = updated_table_years_and_months.index(
        month_year_and_number
    )
    # Get the table number of the given month as a string, add leading 0 if under 10
    table_number = str((table_years_and_months_index) + 1).rjust(2, "0")
    # Create the table_name given the table number, month, and year
    table_name = f"table_{table_number}_{month}_{year}"
    # Select the day from the table with the given 'day_of_month'
    selected_day = conn.execute(
        f"SELECT * FROM {table_name} WHERE id = ?",
        (day_of_month,),
    ).fetchone()
    return render_template(
        "day_details.html",
        day=selected_day,
        month=month,
        year=year,
        table_name=table_name,
    )

if __name__ == "__main__":
    app.run(debug=True)
