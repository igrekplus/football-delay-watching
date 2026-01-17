import os
import sys

from google.cloud import storage

BUCKET_NAME = "football-delay-watching-cache"
TEST_BLOB_NAME = "debug_test.txt"
TEST_CONTENT = "Hello from minimal debug script"


def debug_gcs():
    print("=== Minimal GCS Debug Script ===")

    # 1. Check Env Vars
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds}")

    try:
        # 2. Initialize Client
        print("Initializing storage.Client()...")
        client = storage.Client()
        print(f"Client project: {client.project}")

        # 3. Get Bucket
        print(f"Getting bucket: {BUCKET_NAME}")
        bucket = client.bucket(BUCKET_NAME)

        if not bucket.exists():
            print(f"ERROR: Bucket {BUCKET_NAME} does not exist or not accessible.")
            return False

        # 4. Write Test
        print("Testing WRITE...")
        blob = bucket.blob(TEST_BLOB_NAME)
        blob.upload_from_string(TEST_CONTENT)
        print("WRITE success.")

        # 5. Read Test
        print("Testing READ...")
        content = blob.download_as_text()
        print(f"READ content: {content}")

        if content == TEST_CONTENT:
            print("READ verification success.")
        else:
            print("READ verification FAILED (content mismatch).")

        # 6. Cleanup
        print("Cleaning up...")
        blob.delete()
        print("Cleanup success.")

        print("=== ALL TESTS PASSED ===")
        return True

    except Exception as e:
        print("=== ERROR OCCURRED ===")
        print(str(e))
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if debug_gcs():
        sys.exit(0)
    else:
        sys.exit(1)
