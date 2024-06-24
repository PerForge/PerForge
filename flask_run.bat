@echo off
call env\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=run.py
flask run --host=0.0.0.0 --port=5000