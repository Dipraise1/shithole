from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import emoji
from collections import defaultdict
import os
from dotenv import load_dotenv
import gunicorn  # for production server

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Use environment variables for configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///shithole.db')
if DATABASE_URL.startswith("postgres://"):  # Fix for newer SQLAlchemy versions
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

db = SQLAlchemy(app)

# Database Models
class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    flag = db.Column(db.String(10), nullable=False)
    votes = db.Column(db.Integer, default=0)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    country = db.relationship('Country', backref=db.backref('votes_rel', lazy=True))

# Get real IP address considering proxy headers
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

@app.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    countries = Country.query.all()
    total_votes = sum(country.votes for country in countries)
    
    leaderboard = []
    for country in sorted(countries, key=lambda x: x.votes, reverse=True):
        percentage = round((country.votes / total_votes * 100) if total_votes > 0 else 0, 2)
        leaderboard.append({
            'country': country.name,
            'flag': country.flag,
            'percentage': percentage
        })
    
    return jsonify({'leaderboard': leaderboard})

@app.route('/vote', methods=['POST'])
def cast_vote():
    data = request.get_json()
    country_name = data.get('country')
    ip_address = get_client_ip()

    if not country_name:
        return jsonify({'error': 'Missing country name'}), 400

    country = Country.query.filter_by(name=country_name).first()
    if not country:
        return jsonify({'error': 'Invalid country'}), 404

    try:
        new_vote = Vote(ip_address=ip_address, country_id=country.id)
        db.session.add(new_vote)
        country.votes += 1
        db.session.commit()

        return jsonify({
            'leaderboard': get_leaderboard().json['leaderboard'],
            'user_votes': get_my_votes().json
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/my-votes', methods=['GET'])
def get_my_votes():
    ip_address = get_client_ip()
    user_votes = Vote.query.filter_by(ip_address=ip_address)\
                          .order_by(Vote.timestamp.desc())\
                          .all()
    
    votes = [{
        'country': vote.country.name,
        'timestamp': vote.timestamp.isoformat()
    } for vote in user_votes]
    
    return jsonify({'votes': votes})

@app.route('/stats', methods=['GET'])
def get_stats():
    votes = Vote.query.all()
    unique_voters = len(set(vote.ip_address for vote in votes))
    total_votes = len(votes)
    
    votes_per_ip = defaultdict(int)
    for vote in votes:
        votes_per_ip[vote.ip_address] += 1
    
    votes_per_ip_average = (
        sum(votes_per_ip.values()) / len(votes_per_ip)
        if votes_per_ip else 0
    )
    
    return jsonify({
        'unique_voters': unique_voters,
        'total_votes': total_votes,
        'votes_per_ip_average': votes_per_ip_average
    })

def init_db():
    with app.app_context():
        db.create_all()
        
        countries_data = [
           ("United States", "🇺🇸"), ("China", "🇨🇳"), ("Brazil", "🇧🇷"), ("Russia", "🇷🇺"),
("United Kingdom", "🇬🇧"), ("Germany", "🇩🇪"), ("France", "🇫🇷"), ("Italy", "🇮🇹"),
("Canada", "🇨🇦"), ("Spain", "🇪🇸"), ("Japan", "🇯🇵"), ("South Korea", "🇰🇷"),
("Australia", "🇦🇺"), ("Netherlands", "🇳🇱"), ("Sweden", "🇸🇪"), ("Switzerland", "🇨🇭"),
("Norway", "🇳🇴"), ("Denmark", "🇩🇰"), ("Belgium", "🇧🇪"), ("Finland", "🇫🇮"),
("Ireland", "🇮🇪"), ("Singapore", "🇸🇬"), ("Malaysia", "🇲🇾"), ("Thailand", "🇹🇭"),
("New Zealand", "🇳🇿"), ("Saudi Arabia", "🇸🇦"), ("Argentina", "🇦🇷"),
("Colombia", "🇨🇴"), ("Chile", "🇨🇱"), ("South Africa", "🇿🇦"), ("Nigeria", "🇳🇬"),
("Egypt", "🇪🇬"), ("Pakistan", "🇵🇰"), ("Bangladesh", "🇧🇩"), ("Israel", "🇮🇱"),
("Greece", "🇬🇷"), ("Portugal", "🇵🇹"), ("Czechia", "🇨🇿"), ("Poland", "🇵🇱"),
("Hungary", "🇭🇺"), ("Austria", "🇦🇹"), ("Romania", "🇷🇴"), ("Bulgaria", "🇧🇬"),
("Slovakia", "🇸🇰"), ("Croatia", "🇭🇷"), ("Serbia", "🇷🇸"), ("Albania", "🇦🇱"),
("Slovenia", "🇸🇮"), ("Estonia", "🇪🇪"), ("Latvia", "🇱🇻"), ("Lithuania", "🇱🇹"),
("Iceland", "🇮🇸"), ("Ukraine", "🇺🇦"), ("Belarus", "🇧🇾"), ("Georgia", "🇬🇪"),
("Kazakhstan", "🇰🇿"), ("Uzbekistan", "🇺🇿"), ("Kyrgyzstan", "🇰🇬"), ("Mongolia", "🇲🇳"),
("Myanmar", "🇲🇲"), ("Laos", "🇱🇦"), ("Cambodia", "🇰🇭"), ("Nepal", "🇳🇵"),
("Bhutan", "🇧🇹"), ("Sri Lanka", "🇱🇰"), ("Maldives", "🇲🇻"), ("Afghanistan", "🇦🇫"),
("Iran", "🇮🇷"), ("Iraq", "🇮🇶"), ("Syria", "🇸🇾"), ("Lebanon", "🇱🇧"),
("Jordan", "🇯🇴"), ("Palestine", "🇵🇸"), ("Oman", "🇴🇲"), ("Yemen", "🇾🇪"),
("Qatar", "🇶🇦"), ("Kuwait", "🇰🇼"), ("Bahrain", "🇧🇭"), ("UAE", "🇦🇪"),
("Morocco", "🇲🇦"), ("Algeria", "🇩🇿"), ("Tunisia", "🇹🇳"), ("Libya", "🇱🇾"),
("Sudan", "🇸🇩"), ("Ethiopia", "🇪🇹"), ("Kenya", "🇰🇪"), ("Tanzania", "🇹🇿"),
("Uganda", "🇺🇬"), ("Rwanda", "🇷🇼"), ("Zambia", "🇿🇲"), ("Zimbabwe", "🇿🇼"),
("Botswana", "🇧🇼"), ("Namibia", "🇳🇦"), ("Angola", "🇦🇴"), ("Mozambique", "🇲🇿"),
           
        ]
        
        for country_name, flag in countries_data:
            if not Country.query.filter_by(name=country_name).first():
                country = Country(name=country_name, flag=flag)
                db.session.add(country)
        
        db.session.commit()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    if os.getenv('ENVIRONMENT') == 'production':
        # Production
        app.run(host='0.0.0.0', port=port)
    else:
        # Development
        app.run(debug=True, port=port)