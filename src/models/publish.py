import glob
import os

from dotenv import load_dotenv
from supabase import Client, create_client


BUCKET_NAME = "mandi-vault"


def publish_models(models_dir: str = "models") -> None:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required to publish models.")

    client: Client = create_client(supabase_url, supabase_key)
    model_paths = glob.glob(os.path.join(models_dir, "crop_model_*.pkl"))
    if not model_paths:
        raise FileNotFoundError(f"No crop models found in {models_dir}.")

    for model_path in model_paths:
        file_name = os.path.basename(model_path)
        with open(model_path, "rb") as model_file:
            client.storage.from_(BUCKET_NAME).upload(
                path=file_name,
                file=model_file.read(),
                file_options={"content-type": "application/octet-stream", "upsert": "true"},
            )
        print(f"Published {file_name} to Supabase.")


if __name__ == "__main__":
    publish_models()
