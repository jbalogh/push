BEGIN TRANSACTION;
CREATE TABLE nodes (
	id INTEGER NOT NULL,
	address VARCHAR(255),
	num_connections INTEGER,
	PRIMARY KEY (id),
	UNIQUE (address)
);
CREATE TABLE users (
	id INTEGER NOT NULL,
	token VARCHAR(255),
	PRIMARY KEY (id),
	UNIQUE (token)
);
CREATE TABLE queues (
	id INTEGER NOT NULL,
	queue VARCHAR(255),
	domain VARCHAR(255),
	user_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_queues_queue ON queues (queue);
COMMIT;
