FROM public.ecr.aws/docker/library/python:3.9.13

ENV ETHEREUM_PRIVATE_KEY=""
ENV LOGGING_LEVEL="INFO"

COPY requirements.txt /
RUN pip install wheel
RUN pip install -r /requirements.txt

COPY *.py /
# Don't run as root: 65534 is 'nobody' in this image.
USER 65534:65534
# Replace `onboarding` with desired example script.
CMD ["sh", "-c", "python onboarding.py"]
