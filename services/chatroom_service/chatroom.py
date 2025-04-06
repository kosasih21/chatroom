from flask import Flask, request, jsonify, session, render_template, redirect, url_for, abort, make_response
import os
import datetime
import requests
from flask_wtf.csrf import CSRFProtect
import sys
import json
import pymysql

# Initialize flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'abcd1234'
csrf = CSRFProtect(app)

def db_connect():
    """
    Helper function connects to database and
    returns connection object.
    Connection parameters must be passed in
    environment.
    """
    db_host = os.environ['DB_HOST']
    db_name = os.environ['DB_NAME']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        db=db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def authenticate():
    """
    Validate correct login with access token.
    """
    profile_id = request.args.get("profile_id")
    access_token = request.args.get("access_token")

    if not profile_id or not access_token:
        abort(400, description="Both profile_id and access_token are required.")

    # verify token
    auth_response = requests.post("http://auth_service/authenticate_token", json={
        "access_token": access_token,
        "profile_id": profile_id
    })

    if auth_response.status_code != 200:
        abort(400, description="Token authentication failed")

    print("DEBUG: Auth successful, response:", auth_response.json(), file=sys.stderr)
    return profile_id, access_token


def lookup_username(profile_id):
    response = requests.get(f'http://profile_service/get_username/{profile_id}')
    if response.status_code == 200:
        return response.json().get('username')
    else:
        return None


def get_message_data(cursor, room_id, profile_id):
    # Query to fetch messages with sender's username and profile ID
    sql = """SELECT message, timestamp, sent_by FROM ChatroomMessages 
        WHERE chatroom_id = %s
        ORDER BY timestamp ASC"""
    cursor.execute(sql, (room_id,))
    messages = cursor.fetchall()

    message_data = []
    cached_usernames = {}
    for message in messages:
        message_data.append({
            'message': message['message'],
            'timestamp': message['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'username': cached_usernames.get(message['sent_by']) or cached_usernames.setdefault(message['sent_by'], lookup_username(message['sent_by']) or "<unknown>"),
            'user': message['sent_by'],
            'color': 'white' if str(message['sent_by']) == profile_id else 'lightgray'
        })
    return message_data


@app.route("/", methods=['GET'])
def home():
    profile_id = request.args.get("profile_id")
    access_token = request.args.get("access_token")
    return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token))


@app.route("/send_message", methods=['POST'])
def send_message():
    """
    Invoked by client to send a message to room.
    """
    print("DEBUG: Received JSON:", request.json, file=sys.stderr)
    profile_id, access_token = authenticate()

    room_id = request.json['room_id']
    message = request.json['message']

    image = request.json.get('image', None)
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            # Updated SQL query to insert into the new "image" column
            sql = "INSERT INTO ChatroomMessages (chatroom_id, sent_by, message, image, timestamp) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (room_id, profile_id, message, image, datetime.datetime.now()))
        connection.commit()
    finally:
        connection.close()

    return jsonify({'message': 'Ok'})


@app.route('/create_chatroom', methods=['GET', 'POST'])
def create_chatroom():

    profile_id, access_token = authenticate()
    
    if request.method == 'POST':
        # when submission to create chatroom
        chatroom_name = request.form['chatroom_name']
        description = request.form['description']

        connection = db_connect()

        try:
            with connection.cursor() as cursor:
                # Create a new chatroom
                sql = "INSERT INTO Chatroom (chatroom_name, description) VALUES (%s, %s)"
                cursor.execute(sql, (chatroom_name, description))
                new_chatroom_id = cursor.lastrowid

                # Add the creator as a member of the new chatroom
                sql = "INSERT INTO ChatroomMembers (chatroom_id, profile_id) VALUES (%s, %s)"
                cursor.execute(sql, (new_chatroom_id, profile_id))

            connection.commit()
        finally:
            connection.close()
        return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token))

    return render_template('create_chatroom.html')  # Render the form for GET requests
   

@app.route('/chatrooms', methods=["GET"])
def chatrooms():

    profile_id, access_token = authenticate()

    username = lookup_username(profile_id) or "<unknown>"

    # Establish a connection to the database
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            # Fetch all chatrooms
            sql = "SELECT * FROM Chatroom"
            cursor.execute(sql)
            rooms = cursor.fetchall()

            # Fetch all chatroom members
            sql = "SELECT * FROM ChatroomMembers"
            cursor.execute(sql)
            chatroomMembers = cursor.fetchall()
    finally:
        connection.close()

    app_message = request.args.get("app_message")

    # rooms = Chatroom.query.all()
    # chatroomMembers = ChatroomMembers.query.all()
    return render_template(
            'chatrooms.html', 
            rooms=rooms, 
            chatroomMembers=chatroomMembers, 
            current_user=profile_id,
            current_username=username,
            app_message=app_message
        )


@app.route('/chatroom_refresh/<int:room_id>', methods=['GET'])
def chatroom_refesh(room_id):
    # Get profile id and access_token
    profile_id, access_token = authenticate()
    
    # Connect to the database
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            message_data = get_message_data(cursor, room_id, profile_id)
    finally:
        connection.close()

    return jsonify(message_data)


@app.route('/chatroom/<int:room_id>', methods=['GET', 'POST'])
def chatroom(room_id):
    # Get profile id and access_token
    profile_id, access_token = authenticate()
    
    # Connect to the database
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            # Fetch the chatroom
            sql = "SELECT * FROM Chatroom WHERE chatroom_id = %s"
            cursor.execute(sql, (room_id,))
            room = cursor.fetchone()

            if not room:
                return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token))

            # Fetch the chatroom members and check if the user is a member
            sql = "SELECT profile_id FROM ChatroomMembers WHERE chatroom_id = %s"
            cursor.execute(sql, (room_id,))
            member_ids = cursor.fetchall()
            member_ids = [member['profile_id'] for member in member_ids]

            if int(profile_id) not in member_ids:
                return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token, app_message="You must join the chatroom before entering."))

            message_data = get_message_data(cursor, room_id, profile_id)

    finally:
        connection.close()

    # get user's username
    username = lookup_username(profile_id) or "<unknown>"

    return render_template('chatroom.html', room=room, room_id=room_id,
        messages=message_data, username=username, 
        profile_id=profile_id) # Render the form for GET requests


@app.route('/join_chatroom/<int:room_id>', methods=['POST'])
def join_chatroom(room_id):
    # Get args
    profile_id, access_token = authenticate()

     # Establish a connection to the MySQL database
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            # Check if the user is already a member
            cursor.execute("SELECT * FROM ChatroomMembers WHERE chatroom_id=%s AND profile_id=%s", (room_id, profile_id))
            existing_member = cursor.fetchone()

            if not existing_member:
                # Add the user to the ChatroomMembers table
                cursor.execute("INSERT INTO ChatroomMembers (chatroom_id, profile_id) VALUES (%s, %s)", (room_id, profile_id))
                connection.commit()
    finally:
        connection.close()

    return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token))  # Redirect to the list of chatrooms


@app.route('/leave_chatroom/<int:room_id>', methods=['POST'])
def leave_chatroom(room_id):
    profile_id = request.args.get("profile_id")
    access_token = request.args.get("access_token")

    # Establish a connection to the MySQL database
    connection = db_connect()

    try:
        with connection.cursor() as cursor:
            # Remove the user from the ChatroomMembers table
            cursor.execute("DELETE FROM ChatroomMembers WHERE chatroom_id=%s AND profile_id=%s", (room_id, profile_id))
            connection.commit()
    finally:
        connection.close()

    return redirect(url_for('chatrooms', profile_id=profile_id, access_token=access_token))  # Redirect to the list of chatrooms


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=80)
