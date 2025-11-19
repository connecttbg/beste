
from app import db, User, app

with app.app_context():
    if not User.query.filter_by(email="admin@bestenegler.no").first():
        u = User(email="admin@bestenegler.no")
        u.set_password("Admin123")
        u.is_admin = True
        db.session.add(u)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin already exists.")
