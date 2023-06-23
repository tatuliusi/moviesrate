import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///imdb.db'
app.config['SQLALCHEMY_BINDS'] = {'contacts': 'sqlite:///contacts.db'}
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    movie_name = db.Column(db.String, unique=True)
    release_year = db.Column(db.Integer)
    ranking = db.Column(db.Float)


class Contact(db.Model):
    __tablename__ = 'contacts'
    __bind_key__ = 'contacts'
    __table_args__ = {'bind_key': 'contacts'}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    website = db.Column(db.String(100))
    message = db.Column(db.Text)


@app.before_request
def perform_tasks_before_request():
    if not app.config.get('TASKS_COMPLETED'):
        create_tables()
        populate_ranking_data()
        app.config['TASKS_COMPLETED'] = True


def create_tables():
    db.create_all()


def populate_ranking_data():
    if not Movie.query.first():
        payloads = {'groups': 'top_250', 'start': 1}
        url = 'https://www.imdb.com/search/title/'
        h = {'Accept-Language': 'en-US'}

        def parse_ranking_data():
            all_movies = []
            while payloads['start'] < 250:
                response = requests.get(url, params=payloads, headers=h)
                content = response.text
                soup = BeautifulSoup(content, 'html.parser')
                movies_soup = soup.find('div', class_='lister-list')
                if movies_soup is not None:
                    movies = movies_soup.find_all('div', class_='lister-item')
                    for movie in movies:
                        movie_name = movie.h3.a.text
                        release_year = movie.find('span', class_='lister-item-year').text
                        release_year = release_year.replace('(', '').replace(')', '')
                        ranking = float(movie.strong.text)
                        all_movies.append({'movie_name': movie_name, 'release_year': release_year, 'ranking': ranking})
                payloads['start'] += 50
            return all_movies

        ranking_data = parse_ranking_data()

        for data in ranking_data:
            existing_movie = Movie.query.filter_by(movie_name=data['movie_name']).first()
            if existing_movie is None:
                movie_obj = Movie(movie_name=data['movie_name'], release_year=data['release_year'],
                                  ranking=data['ranking'])
                db.session.add(movie_obj)
        db.session.commit()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/review')
def review():
    return render_template('review.html')


@app.route('/ranking')
def ranking():
    movies = Movie.query.limit(100).all()
    return render_template('ranking.html', movies=movies)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        existing_contact = Contact.query.filter_by(name=name).first()
        if existing_contact is None:
            contact = Contact(name=name, email=email, message=message)
            db.session.add(contact)
            db.session.commit()
            flash('Contact information saved successfully!', 'success')
        else:
            flash('Contact information already exists!', 'info')
        return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/single')
def single():
    return render_template('single.html')


if __name__ == '__main__':
    app.run(debug=True)
