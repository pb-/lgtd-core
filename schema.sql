CREATE TABLE users (
	id INTEGER NOT NULL,
	name TEXT NOT NULL,
	password TEXT NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name COLLATE NOCASE)
);

CREATE TABLE commands (
	user_id INTEGER NOT NULL,
	app_id TEXT NOT NULL,
	rev INTEGER NOT NULL,
	iv TEXT NOT NULL,
	mac TEXT NOT NULL,
	cmd TEXT NOT NULL,
	PRIMARY KEY (user_id, app_id, rev),
	FOREIGN KEY (user_id) REFERENCES users(id)
);
