from app import app, db, User

with app.app_context():
    # Check all users
    users = User.query.all()
    print("Users in database:")
    for user in users:
        print(f"ID: {user.id}, Username: {user.username}, Password: {user.password}, Email: {user.email}")
    
    # Check specifically for your email
    user = User.query.filter_by(email='ksivakannan2005@gmail.com').first()
    if user:
        print(f"\nFound user: {user.username} with password: {user.password}")
    else:
        print("\nNo user found with email: ksivakannan2005@gmail.com")