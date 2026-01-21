import json
import psycopg2

def lambda_handler(event, context):
    conn = psycopg2.connect(
        host="answer-engine-db.c1ueg0ewk14l.us-east-1.rds.amazonaws.com",
        port=5432,
        database="postgres",
        user="postgres",
        password="AnswerEngine2024DB",
        sslmode="require"
    )
    cursor = conn.cursor()

    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR(500)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255)",
    ]

    results = []
    for migration in migrations:
        try:
            cursor.execute(migration)
            conn.commit()
            results.append(f"Success: {migration}")
        except Exception as e:
            results.append(f"Error: {str(e)}")
            conn.rollback()

    cursor.close()
    conn.close()

    return {"statusCode": 200, "body": json.dumps(results)}
