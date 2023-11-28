FROM python:3
RUN mkdir -p /app/github_mock
COPY requirements.txt /app/.
COPY *.py /app/.
COPY github_mock/* /app/github_mock/.
RUN pip install -r /app/requirements.txt
# CMD PYTHONUNBUFFERED=1 python3 /app/flaskapp.py
CMD cd /app; PYTHONUNBUFFERED=1 PYTHONPATH=. python3 run.py
