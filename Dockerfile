FROM python:3.12-slim

WORKDIR /app

RUN python3 -m venv env
RUN /app/env/bin/pip install gunicorn flask python-dotenv

CMD ["/app/env/bin/gunicorn", "-b", "[::]:8000", "-w", "2", "atcfeed:app"]
