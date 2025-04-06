from flask import Flask, request, jsonify
import pymysql
import os
import sys
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

def get_db():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql"),
        user=os.environ.get("DB_USER", "username"),
        password=os.environ.get("DB_PASSWORD", "rootpassword"),
        database=os.environ.get("DB_NAME", "db")
    )

def hash_password(password: str) -> str:
    # Generate a random salt (16 bytes)
    salt = os.urandom(16)

    # Create a KDF instance using PBKDF2HMAC with SHA256
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode('utf-8'))
    
    # Concatenate salt and key, then encode using base64 for storage
    return base64.urlsafe_b64encode(salt + key).decode('utf-8')

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        # Decode the stored hash to retrieve salt and key
        decoded = base64.urlsafe_b64decode(stored_hash.encode('utf-8'))
        salt = decoded[:16]
        stored_key = decoded[16:]

        # Create a new KDF with the extracted salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        # This will raise an exception if the password does not match
        kdf.verify(password.encode('utf-8'), stored_key)
        return True
    except Exception:
        return False



@app.route("/new_profile", methods=["POST"])
def new_profile():
    # Create a new profile based on the parameters passed in the POST body as JSON.
    # Expected JSON: { "user_name": <str>, "password": <str>, "bio": <str> }
    data = request.get_json()
    user_name = data.get("user_name")
    password = data.get("password")
    bio = data.get("bio", "")

    if not user_name or not password:
        return jsonify({"error": "Missing user_name or password"}), 400

    # Hash the password using the cryptography package
    hashed_pw_str = hash_password(password)

    try:
        conn = get_db()
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO user_profiles (username, password_hash, biography)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (user_name, hashed_pw_str, bio))
        conn.commit()
        profile_id = cursor.lastrowid
        return jsonify({"profile_id": profile_id}), 201
    except pymysql.MySQLError as err:
        print("MySQL Error:", err, file=sys.stderr)
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        print("Exception:", str(e), file=sys.stderr)
        return jsonify({"error": "Internal error"}), 500
    finally:
        cursor.close()
        conn.close()



@app.route("/validate_user", methods=["POST"])
def validate_user():
    # Validate user credentials.
    # Expected JSON: { "user_name": <str>, "password": <str> }
    data = request.get_json()
    user_name = data.get("user_name")
    password = data.get("password")

    if not user_name or not password:
        return jsonify({"profile_id": None}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        select_query = "SELECT profile_id, password_hash FROM user_profiles WHERE username = %s"
        cursor.execute(select_query, (user_name,))
        user = cursor.fetchone()

        if user and verify_password(password, user["password_hash"]):
            return jsonify({"profile_id": user["profile_id"]}), 200
        else:
            return jsonify({"profile_id": None}), 401
    except pymysql.MySQLError as err:
        print("MySQL Error:", err, file=sys.stderr)
        return jsonify({"profile_id": None}), 500
    except Exception as e:
        print("Exception:", str(e), file=sys.stderr)
        return jsonify({"profile_id": None}), 500
    finally:
        cursor.close()
        conn.close()



@app.route('/get_username/<int:profile_id>', methods=['GET'])
def get_username(profile_id):
    # Return the username associated with the given profile_id.
    try:
        conn = get_db()
        cursor = conn.cursor()
        select_query = "SELECT username FROM user_profiles WHERE profile_id = %s"
        cursor.execute(select_query, (profile_id,))
        result = cursor.fetchone()
        if result:
            return jsonify({"username": result[0]}), 200
        else:
            return jsonify({"message": "Profile not found"}), 404
    except pymysql.MySQLError as err:
        print("MySQL Error:", err, file=sys.stderr)
        return jsonify({"message": "Database error"}), 500
    except Exception as e:
        print("Exception:", str(e), file=sys.stderr)
        return jsonify({"message": "Internal error"}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=80)