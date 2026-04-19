from dotenv import load_dotenv

load_dotenv()

from ml_inference_app import create_ml_inference_app


app = create_ml_inference_app()
