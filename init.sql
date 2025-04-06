# TODO add any additional tables here

CREATE TABLE Chatroom (
    chatroom_id INT AUTO_INCREMENT PRIMARY KEY,
    chatroom_name VARCHAR(80) NOT NULL,
    description VARCHAR(200)
);

CREATE TABLE ChatroomMembers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chatroom_id INT NOT NULL,
    profile_id INT NOT NULL,
    FOREIGN KEY (chatroom_id) REFERENCES Chatroom(chatroom_id)
);

CREATE TABLE ChatroomMessages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    chatroom_id INT NOT NULL,
    sent_by INT NOT NULL,
    message VARCHAR(500) NOT NULL,
    image VARCHAR(255),  -- Column to store image filename (or reference)
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (chatroom_id) REFERENCES Chatroom(chatroom_id)
);


CREATE TABLE Auth (
    profile_id INT PRIMARY KEY,
    access_token VARCHAR(500) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    biography TEXT
);