from database import users_collection
import bcrypt, getpass


def create_admin():

    username = "admin"

    existing_user = users_collection.find_one({
        "username": username
    })

    if existing_user is not None:
        print("Admin account already exists")
        return

    password = getpass.getpass("Enter admin password: ")

    if not password:
        print("Password cannot be empty")
        return

    hashed_password = bcrypt.hashpw(
        bytes(password, "UTF-8"),
        bcrypt.gensalt()
    )

    admin = {
        "username": username,
        "password": hashed_password,
        "role": "admin"
    }

    users_collection.insert_one(admin)

    print("Admin account created successfully")


def create_staff():

    username = "staff"

    existing_user = users_collection.find_one({
        "username": username
    })

    if existing_user is not None:
        print("Staff account already exists")
        return

    password = getpass.getpass("Enter staff password: ")

    if not password:
        print("Password cannot be empty")
        return

    hashed_password = bcrypt.hashpw(
        bytes(password, "UTF-8"),
        bcrypt.gensalt()
    )

    staff = {
        "username": username,
        "password": hashed_password,
        "role": "staff"
    }

    users_collection.insert_one(staff)

    print("Staff account created successfully")


if __name__ == "__main__":
    create_admin()
    create_staff()
