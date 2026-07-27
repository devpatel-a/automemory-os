# SQLAlchemy CRUD

## Create

Uses:

- SessionLocal
- add()
- commit()
- refresh()

## Read

Uses:

db.query(Model).all()

The application now stores memories in PostgreSQL instead of an in-memory Python list.

## Update

1. Query the record.
2. Modify the object's attributes.
3. Commit the transaction.
4. Refresh the object.

## Delete

1. Query the record.
2. Delete it with db.delete().
3. Commit the transaction.