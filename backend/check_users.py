from app.database import SessionLocal
from app import models
from app.security import verify_password, hash_password

def check():
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        print(f"Users found: {len(users)}")
        for u in users:
            print(f"User: {u.username}, Role: {u.role}")
            print(f"  Password 'Jour2Demo123!' valid? {verify_password('Jour2Demo123!', u.password_hash)}")
            print(f"  Password '123456' valid? {verify_password('123456', u.password_hash)}")

        # Create/Update user test@paytome.com
        target_user = "test@paytome.com"
        target_pass = "123456"
        
        user = db.query(models.User).filter(models.User.username == target_user).first()
        if not user:
            print(f"Creating user {target_user}...")
            user = models.User(
                username=target_user, 
                password_hash=hash_password(target_pass), 
                role="admin"
            )
            db.add(user)
        else:
            print(f"Resetting password for {target_user}...")
            user.password_hash = hash_password(target_pass)
        
        db.commit()
        print(f"SUCCESS: User '{target_user}' is ready with password '{target_pass}'.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
